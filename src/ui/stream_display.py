"""
AgentStream — live Rich display during LLM streaming.
"""

import time

from rich.console import Group
from rich.live import Live
from rich.padding import Padding
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich.markup import escape

from .theme import console, CORAL, GREEN, GOLD, MUTED, DIMC
from .modes import _stats
from .output import _bullet_block
from .approvals import set_current_capture

_HAS_MSVCRT = False
_get_global_capture = None
try:
    from input_queue import get_global_capture as _get_global_capture
    _HAS_MSVCRT = True
except Exception:
    pass

_REASONING_LIVE_LINES = 8
_ANSWER_LIVE_LINES    = 15


class AgentStream:
    """Live display while the LLM streams: spinner, timer, reasoning, answer."""

    def __init__(self):
        self._text = ""
        self._reasoning = ""
        self._reasoning_started = False
        self._reasoning_active = False
        self._reasoning_start = 0.0
        self._reasoning_dur = 0.0
        self._tokens_in = 0
        self._tokens_out = 0
        self._start = time.perf_counter()
        self._spinner = Spinner("star", style=CORAL)
        self._pending_tools: list[str] = []
        self._input_capture = _get_global_capture() if _HAS_MSVCRT else None
        self._live = Live(
            self,
            console=console,
            refresh_per_second=10,
            transient=True,
            auto_refresh=True,
            vertical_overflow="crop",
        )

    def __enter__(self):
        self._live.start()
        if self._input_capture is not None:
            if not self._input_capture._active:
                self._input_capture.start()
            set_current_capture(self._input_capture)
        return self

    def __exit__(self, *args):
        if self._input_capture is not None:
            # Não para o capture global — ele persiste entre tool calls
            set_current_capture(None)
        self._collapse_reasoning()
        self._live.stop()
        if self._reasoning.strip():
            console.print(
                f"  [italic grey42]✻ reasoning[/italic grey42]"
                f"  [italic {DIMC}]· {self._reasoning_dur:.1f}s[/italic {DIMC}]"
            )
            console.print()
        if self._text.strip():
            from .output import print_agent_message
            print_agent_message(self._text)
        # Linha estática de tokens — sempre visível após a resposta
        if self._tokens_in or self._tokens_out:
            def _fmt(n: int) -> str:
                return f"{n / 1000:.1f}k" if n >= 1000 else str(n)
            console.print(
                f"  [{DIMC}]✶ {_fmt(self._tokens_out)} tokens  ·  "
                f"{_fmt(self._tokens_in)} contexto[/{DIMC}]"
            )
            console.print()

    def get_queued_inputs(self) -> list:
        if self._input_capture is not None:
            return self._input_capture.drain()
        return []

    def __rich__(self) -> Group:
        return self._render()

    # ── status / rendering ──────────────────────────────────────────────────────
    def _status_line(self) -> Text:
        elapsed = time.perf_counter() - self._start
        elapsed_s = int(elapsed)
        mins, secs = divmod(elapsed_s, 60)

        if self._reasoning_active:
            label = "Pensando"
        elif self._text.strip():
            label = "Escrevendo"
        else:
            label = "Processando"

        def _fmt(n: int) -> str:
            return f"{n / 1000:.1f}k" if n >= 1000 else str(n)

        time_str = f"{mins}m {secs}s" if mins else f"{secs}s"

        t = Text()
        t.append(label, style=f"bold {CORAL}")
        t.append("… ", style=CORAL)
        t.append(f"({time_str}", style=DIMC)
        if self._tokens_out:
            t.append(f" · ↓ {_fmt(self._tokens_out)} tokens", style=DIMC)
        if self._tokens_in:
            t.append(f" · ↑ {_fmt(self._tokens_in)}", style=DIMC)
        t.append(")", style=DIMC)
        return t

    def _render(self) -> Group:
        grid = Table.grid(padding=(0, 1))
        grid.add_column(no_wrap=True)
        grid.add_column(no_wrap=True)
        grid.add_row(self._spinner, self._status_line())

        parts: list = [Text(""), grid]

        if self._reasoning_active and self._reasoning.strip():
            lines = self._reasoning.strip().split("\n")
            shown = lines[-_REASONING_LIVE_LINES:]
            if len(lines) > _REASONING_LIVE_LINES:
                shown = ["…"] + shown
            parts.append(Text(""))
            parts.append(Text.from_markup(f"  [italic grey42]✻ pensando…[/italic grey42]"))
            parts.append(Padding(Text("\n".join(shown), style="italic grey42"), (0, 0, 0, 4)))
        elif self._reasoning.strip():
            parts.append(Text(""))
            parts.append(Text.from_markup(
                f"  [italic grey42]✻ reasoning · {self._reasoning_dur:.1f}s[/italic grey42]"
            ))

        for name in self._pending_tools:
            parts.append(Text.from_markup(
                f"  [{GREEN}]⏺[/{GREEN}] [bold white]{escape(name)}[/bold white] [{DIMC}]preparando…[/{DIMC}]"
            ))

        if self._text.strip():
            lines = self._text.split("\n")
            shown = lines[-_ANSWER_LIVE_LINES:]
            truncated = len(lines) > _ANSWER_LIVE_LINES
            body = Text(("…\n" if truncated else "") + "\n".join(shown), style="white")
            parts.append(Text(""))
            parts.append(_bullet_block("⏺", f"bold {CORAL}", body))

        if self._input_capture is not None:
            buf_text = self._input_capture.buffer
            qsize    = self._input_capture.queue_size
            parts.append(Text(""))
            if qsize > 0:
                label = f"{qsize} mensagem{'ns' if qsize > 1 else ''} aguardando"
                parts.append(Text.from_markup(f"  [{GOLD}]⏳ {label}[/{GOLD}]"))
            cursor  = "▌"
            display = escape(buf_text[-80:]) if len(buf_text) > 80 else escape(buf_text)
            parts.append(Text.from_markup(
                f"  [{MUTED}]╰─ pode digitar:[/{MUTED}] [{DIMC}]{display}[/{DIMC}][bold {CORAL}]{cursor}[/bold {CORAL}]"
            ))
            parts.append(Text.from_markup(
                f"  [{DIMC}]   ↵ envia para fila  ·  mensagem chega assim que a IA terminar[/{DIMC}]"
            ))

        return Group(*parts)

    # ── input from the agent loop ───────────────────────────────────────────────
    def set_reasoning(self, full: str):
        if full and not self._reasoning_started:
            self._reasoning_started = True
            self._reasoning_active = True
            self._reasoning_start = time.perf_counter()
        self._reasoning = full

    def set_answer(self, full: str):
        if full.strip():
            self._collapse_reasoning()
        self._text = full

    def add_text(self, chunk: str):
        self.set_answer(self._text + chunk)
        estimated = max(len(self._text) // 4, 1)
        if estimated > self._tokens_out:
            diff = estimated - self._tokens_out
            self._tokens_out = estimated
            _stats["tokens_out"] = _stats["tokens_out"] + diff

    def _collapse_reasoning(self):
        if self._reasoning_active:
            self._reasoning_active = False
            self._reasoning_dur = time.perf_counter() - (self._reasoning_start or self._start)

    def add_tool_pending(self, tool_name: str):
        if tool_name and tool_name not in self._pending_tools:
            self._pending_tools.append(tool_name)

    def set_usage(self, tokens_in: int, tokens_out: int):
        _stats["tokens_in"] += tokens_in - self._tokens_in
        _stats["tokens_out"] += tokens_out - self._tokens_out
        self._tokens_in = tokens_in
        self._tokens_out = tokens_out


__all__ = ["AgentStream"]
