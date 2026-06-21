"""
Interactive input box built with prompt_toolkit.
"""

import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application, get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import Processor, Transformation

from .theme import console, PT_STYLE, CORAL, MUTED
from .modes import get_mode, cycle_mode, MODE_DISPLAY, _stats
from .completers import CombinedCompleter

_EXIT_SENTINEL = "\x00__EXIT__\x00"
_PLACEHOLDER   = "Pergunte algo, ou peça uma tarefa…"


class _PlaceholderProcessor(Processor):
    def apply_transformation(self, ti):
        if not ti.document.text and ti.lineno == 0:
            return Transformation([("class:placeholder", _PLACEHOLDER)])
        return Transformation(ti.fragments)


def _hborder(left: str, right: str):
    def _gen():
        w = max(get_app().output.get_size().columns, 4)
        return [("class:box", left + "─" * (w - 2) + right)]
    return _gen


def _line_prefix(line_number, wrap_count):
    return [("class:prompt", "> ")] if (line_number == 0 and wrap_count == 0) \
        else [("class:prompt", "  ")]


def _hint_line():
    w = max(get_app().output.get_size().columns, 20)
    left = "  ↵ enviar   ·   shift+tab muda modo   ·   ctrl+c sai"
    style_cls, label = MODE_DISPLAY[get_mode()]
    pad = max(1, w - len(left) - len(label) - 2)
    return [("class:hint", left + " " * pad), (style_cls, label + "  ")]


def _token_line():
    ti = _stats["tokens_in"]
    to = _stats["tokens_out"]
    total = ti + to
    if total == 0:
        return [("class:tokens", "  pronto")]
    return [
        ("class:tokens",    "  "),
        ("class:tokens.hi", f"{total:,}"),
        ("class:tokens",    " tokens   ·   "),
        ("class:tokens",    f"↑ {ti:,}  ↓ {to:,}"),
    ]


def _build_input_app(buf: Buffer) -> Application:
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        event.app.exit(result=buf.text)

    @kb.add("c-c")
    @kb.add("c-d")
    def _(event):
        event.app.exit(result=_EXIT_SENTINEL)

    @kb.add("s-tab")
    def _(event):
        cycle_mode()
        event.app.invalidate()

    @kb.add("tab")
    def _(event):
        if buf.complete_state:
            buf.complete_next()
        else:
            buf.start_completion(select_first=False)

    @kb.add("escape", "enter")
    def _(event):
        buf.insert_text("\n")

    input_window = Window(
        BufferControl(buffer=buf, input_processors=[_PlaceholderProcessor()]),
        get_line_prefix=_line_prefix,
        wrap_lines=True,
        height=D(min=1, max=6),
        style="class:input",
    )

    body = HSplit([
        Window(FormattedTextControl(_token_line), height=1),
        Window(FormattedTextControl(_hborder("╭", "╮")), height=1),
        VSplit([
            Window(width=1, char="│", style="class:box"),
            Window(width=1),
            input_window,
            Window(width=1),
            Window(width=1, char="│", style="class:box"),
        ]),
        Window(FormattedTextControl(_hborder("╰", "╯")), height=1),
        Window(FormattedTextControl(_hint_line), height=1),
    ])

    root = FloatContainer(
        content=body,
        floats=[
            Float(
                xcursor=True,
                ycursor=True,
                content=CompletionsMenu(max_height=16, scroll_offset=1),
            )
        ],
    )

    return Application(
        layout=Layout(root, focused_element=input_window),
        key_bindings=kb,
        style=PT_STYLE,
        full_screen=False,
        mouse_support=False,
        erase_when_done=True,
    )


_fallback_session: "PromptSession | None" = None


def _fallback_prompt() -> str:
    global _fallback_session
    if _fallback_session is None:
        _fallback_session = PromptSession(history=InMemoryHistory())
    from prompt_toolkit.formatted_text import HTML
    return _fallback_session.prompt(HTML(f"<b>> </b>"))


def get_user_input() -> str:
    try:
        buf = Buffer(
            multiline=True,
            completer=CombinedCompleter(),
            complete_while_typing=True,
        )
        text = _build_input_app(buf).run()
    except Exception:
        try:
            text = _fallback_prompt()
        except (KeyboardInterrupt, EOFError):
            text = _EXIT_SENTINEL

    if text == _EXIT_SENTINEL:
        try:
            from src.session.store import has_current_session
            if has_current_session():
                console.print(
                    f"\n  [{MUTED}]sessão salva  ·  use [/{MUTED}][{CORAL}]/resume[/{CORAL}]"
                    f"[{MUTED}] para continuar  ·  até logo[/{MUTED}]\n"
                )
            else:
                console.print(f"\n  [{MUTED}]até logo[/{MUTED}]\n")
        except Exception:
            console.print(f"\n  [{MUTED}]até logo[/{MUTED}]\n")
        sys.exit(0)
    return text


__all__ = ["get_user_input", "_EXIT_SENTINEL"]
