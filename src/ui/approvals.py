"""
User approval prompts for commands, file mutations, and plan confirmation.
"""

import time

from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
from rich import box

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit import PromptSession

from .theme import console, PT_STYLE, CORAL, GREEN, CYAN, GOLD, MUTED, DIMC

_fallback_session: "PromptSession | None" = None
_current_capture = None


def set_current_capture(capture):
    global _current_capture
    _current_capture = capture


def _simple_prompt(message_html: str) -> str:
    global _fallback_session
    if _fallback_session is None:
        _fallback_session = PromptSession(history=InMemoryHistory())
    from prompt_toolkit.formatted_text import HTML
    return _fallback_session.prompt(HTML(message_html)).strip()


def _key_prompt(valid_keys: list, cancel_key: str = "") -> str:
    _cancel = cancel_key or valid_keys[-1]

    _capture_paused = False
    if _current_capture is not None and hasattr(_current_capture, '_active') and _current_capture._active:
        _current_capture.stop()
        _capture_paused = True

    kb = KeyBindings()
    for key in valid_keys:
        def _make(k):
            @kb.add(k)
            def _(event, _k=k):
                event.app.exit(result=_k)
        _make(key)

    @kb.add("c-c")
    @kb.add("escape")
    def _on_cancel(event):
        event.app.exit(result=_cancel)

    app = Application(
        layout=Layout(Window(FormattedTextControl(""), height=1)),
        key_bindings=kb,
        style=PT_STYLE,
        full_screen=False,
        mouse_support=False,
        erase_when_done=True,
    )
    try:
        result = app.run()
        time.sleep(0.05)
        if _capture_paused and _current_capture is not None:
            _current_capture.start()
        return result if result else _cancel
    except (KeyboardInterrupt, EOFError):
        if _capture_paused and _current_capture is not None:
            _current_capture.start()
        return _cancel


def prompt_command_approval(command: str) -> "int | str":
    console.print()
    console.print(Panel(
        Text(command, style="bold white"),
        title=f"[bold red]⚠ aprovação necessária[/bold red]",
        title_align="left",
        box=box.ROUNDED, border_style="red", padding=(0, 2),
    ))
    console.print(
        f"  [{CYAN} bold][ 1  permitir ][/{CYAN} bold]  "
        f"[{CYAN}][ 2  sempre ][/{CYAN}]  "
        f"[white][ 3  cancelar ][/white]  "
        f"[{GOLD}][ 4  instrução ][/{GOLD}]"
    )
    console.print()
    try:
        answer = _key_prompt(["1", "2", "3", "4"], cancel_key="3")
        if answer == "4":
            console.print()
            custom = _simple_prompt("<b><ansiblue>instrução:</ansiblue></b> ")
            return custom if custom else 3
        return int(answer)
    except (KeyboardInterrupt, EOFError, ValueError):
        return 3


def prompt_simple_approval(title: str, detail: str, *, border: str = "red"):
    console.print()
    console.print(Panel(
        Text(detail, style="white"),
        title=f"[bold {border}]{escape(title)}[/bold {border}]",
        title_align="left",
        box=box.ROUNDED, border_style=border, padding=(0, 2),
    ))
    console.print(
        f"  [{CYAN} bold][ 1  permitir ][/{CYAN} bold]  "
        f"[white][ 2  cancelar ][/white]  "
        f"[{GOLD}][ 3  instrução ][/{GOLD}]"
    )
    console.print()
    try:
        answer = _key_prompt(["1", "2", "3"], cancel_key="2")
        if answer == "1":
            return True
        if answer == "3":
            console.print()
            custom = _simple_prompt("<b><ansiblue>instrução:</ansiblue></b> ")
            return custom if custom else False
        return False
    except (KeyboardInterrupt, EOFError):
        return False


def prompt_plan_approval(tool_calls: dict) -> bool:
    import json
    rows = []
    for i, tc in enumerate(tool_calls.values(), 1):
        try:
            args = json.loads(tc["arguments"]) if tc["arguments"].strip() else {}
        except Exception:
            args = {}
        arg_str = ", ".join(str(v) for v in args.values())[:60]
        rows.append(f"  [{GOLD}]{i}.[/{GOLD}] [bold white]{escape(tc['name'])}[/bold white][{MUTED}]({escape(arg_str)})[/{MUTED}]")

    console.print()
    console.print(Panel(
        "\n".join(rows),
        title=f"[bold {GOLD}]◈ plano de execução[/bold {GOLD}]",
        title_align="left",
        box=box.ROUNDED, border_style=GOLD, padding=(1, 2),
    ))
    console.print(
        f"  [{GREEN} bold][ s  executar ][/{GREEN} bold]  "
        f"[white][ n  cancelar ][/white]"
    )
    console.print()
    try:
        answer = _key_prompt(["s", "y", "n"], cancel_key="n")
        return answer in ("s", "y")
    except (KeyboardInterrupt, EOFError):
        return False


__all__ = [
    "set_current_capture",
    "prompt_command_approval",
    "prompt_simple_approval",
    "prompt_plan_approval",
]
