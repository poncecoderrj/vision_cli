import os
import sys
import time
import json
from enum import Enum

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.padding import Padding
from rich.table import Table
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich.markup import escape
from rich.rule import Rule
from rich import box

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import Completer, Completion, ThreadedCompleter

# ── Windows raw-input capture (for queue-while-streaming) ─────────────────────

_HAS_MSVCRT = False
try:
    from input_queue import StreamInputCapture as _StreamInputCapture
    _HAS_MSVCRT = True
except Exception:
    _StreamInputCapture = None  # type: ignore

# ── Theme ─────────────────────────────────────────────────────────────────────

CORAL = "#d97757"   # assistant bullet, input box, welcome
GREEN = "#7fae5f"   # completed tool bullet / connectors
CYAN  = "#56b6c2"
GOLD  = "#e5c07b"
MUTED = "#9a9a9a"
DIMC  = "grey42"

console = Console(safe_box=False)

# ── Agent modes ───────────────────────────────────────────────────────────────

class AgentMode(Enum):
    ACCEPT = "accept"
    PLAN   = "plan"
    AUTO   = "auto"

_state = {"mode": AgentMode.ACCEPT}

def get_mode() -> AgentMode:
    return _state["mode"]

def cycle_mode() -> AgentMode:
    modes = list(AgentMode)
    _state["mode"] = modes[(modes.index(_state["mode"]) + 1) % len(modes)]
    return _state["mode"]

# (pt_style_class, label shown under the input box)
_MODE_DISPLAY = {
    AgentMode.ACCEPT: ("class:mode.accept", "modo aprovação"),
    AgentMode.PLAN:   ("class:mode.plan",   "modo plano"),
    AgentMode.AUTO:   ("class:mode.auto",   "modo automático"),
}

# ── Session stats ─────────────────────────────────────────────────────────────

_stats = {"tokens_in": 0, "tokens_out": 0, "tool_calls": 0, "start": time.perf_counter()}

def track_tool_call():
    _stats["tool_calls"] += 1

# ── prompt_toolkit input box (Claude-style rounded box) ─────────────────────────

_PT_STYLE = PTStyle.from_dict({
    "box":         CORAL,
    "prompt":      f"{CORAL} bold",
    "input":       "",
    "placeholder": "#6b6b6b",
    "hint":        "#6b6b6b",
    "tokens":      "#6b6b6b",
    "tokens.hi":   "#9a9a9a",
    "mode.accept": f"{CYAN} bold",
    "mode.plan":   f"{GOLD} bold",
    "mode.auto":   f"{GREEN} bold",
    # Completion menu
    "completion-menu":                     "bg:#2a2a2a #cccccc",
    "completion-menu.completion":          "bg:#2a2a2a #cccccc",
    "completion-menu.completion.current":  f"bg:{CORAL} #ffffff bold",
    "completion-menu.meta.completion":     "bg:#333333 #888888",
    "completion-menu.meta.completion.current": f"bg:{CORAL} #dddddd",
    "scrollbar.background":                "bg:#3a3a3a",
    "scrollbar.button":                    f"bg:{CORAL}",
})

_EXIT_SENTINEL = "\x00__EXIT__\x00"
_PLACEHOLDER = "Pergunte algo, ou peça uma tarefa…"


class _PlaceholderProcessor(Processor):
    """Show faint placeholder text only when the buffer is empty."""

    def apply_transformation(self, ti):
        if not ti.document.text and ti.lineno == 0:
            return Transformation([("class:placeholder", _PLACEHOLDER)])
        return Transformation(ti.fragments)


class SlashCommandCompleter(Completer):
    """Triggers on '/' at start of input, completes special commands and skills."""

    def get_completions(self, document, complete_event):
        import re
        from pathlib import Path

        text_before = document.text_before_cursor
        
        # Simplified regex: match '/' at start or after whitespace
        # This ensures we catch "/" even with no characters after it
        m = re.search(r"(?:^|\s)/(\w*)$", text_before)
        if m is None:
            return

        partial = m.group(1).lower()
        
        # Special commands
        special_commands = [
            ("resume", "Continuar sessão anterior"),
            ("config", "Ver/editar configurações"),
            ("skills", "Listar skills disponíveis"),
            ("help", "Ajuda"),
            ("clear", "Limpar tela"),
            ("exit", "Sair"),
        ]
        
        # Load available skills from multiple possible locations
        skills_paths = [Path("skills"), Path("src/skills")]
        skill_list = []
        seen_skills = set()
        
        for skills_path in skills_paths:
            if skills_path.exists():
                for skill_file in skills_path.glob("*.md"):
                    skill_name = skill_file.stem
                    if skill_name not in seen_skills:
                        skill_list.append((skill_name, f"Skill: {skill_name}"))
                        seen_skills.add(skill_name)
        
        # Combine all options
        all_options = special_commands + skill_list
        
        count = 0
        for name, description in all_options:
            if count >= 50:
                break
            if not name.lower().startswith(partial):
                continue
            
            insert = name
            display_name = f"/{name}"
            
            yield Completion(
                text=insert,
                start_position=-len(partial),
                display=display_name,
                display_meta=description,
            )
            count += 1


class AtMentionCompleter(Completer):
    """Triggers on '@' in the input buffer, completes file/dir paths from cwd or common locations."""

    _SKIP = {"__pycache__", "node_modules", ".git", ".venv", "venv",
              "dist", "build", ".idea", ".mypy_cache", ".pytest_cache"}
    
    # Common directories to search for files
    _SEARCH_DIRS = [".", "src", "docs", "tests", "app", "lib", "packages"]

    def get_completions(self, document, complete_event):
        import re, os
        from pathlib import Path as _Path

        text_before = document.text_before_cursor
        # Simplified regex: match @ at start of text or after whitespace
        # This ensures we catch "@" even with no characters after it
        m = re.search(r"(?:^|\s)@(\S*)$", text_before)
        if m is None:
            return

        partial = m.group(1)

        # Split into directory part and filename fragment
        norm = partial.replace("\\", "/")
        if "/" in norm:
            sep = norm.rfind("/")
            dir_part = norm[:sep] or "."
            name_frag = norm[sep + 1:]
            base = _Path(dir_part)
            if not base.is_absolute():
                base = _Path.cwd() / base
        else:
            base = _Path.cwd()
            dir_part = ""
            name_frag = norm

        # If base doesn't exist or is empty, search in common directories
        should_search_common = not base.exists() or not base.is_dir() or (not dir_part and not name_frag)
        
        if should_search_common:
            # Search in common directories for any files/dirs
            for search_dir in self._SEARCH_DIRS:
                search_path = _Path.cwd() / search_dir
                if search_path.exists() and search_path.is_dir():
                    try:
                        for entry in search_path.iterdir():
                            if entry.name in self._SKIP:
                                continue
                            # Show both files and directories
                            suffix = "/" if entry.is_dir() else ""
                            rel_path = f"{search_dir}/{entry.name}{suffix}"
                            display_name = entry.name + suffix
                            file_type = "diretório" if entry.is_dir() else "arquivo"
                            yield Completion(
                                text=rel_path,
                                start_position=-len(partial),
                                display=display_name,
                                display_meta=f"@{file_type} em {search_dir}",
                            )
                    except (PermissionError, OSError):
                        pass
            
            # Also search in root cwd
            try:
                for entry in _Path.cwd().iterdir():
                    if entry.name in self._SKIP:
                        continue
                    if entry.name.startswith("_"):
                        continue
                    suffix = "/" if entry.is_dir() else ""
                    display_name = entry.name + suffix
                    file_type = "diretório" if entry.is_dir() else "arquivo"
                    yield Completion(
                        text=entry.name + suffix,
                        start_position=-len(partial),
                        display=display_name,
                        display_meta=f"@{file_type}",
                    )
            except (PermissionError, OSError):
                pass
            
            return

        try:
            entries = sorted(base.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        except PermissionError:
            return

        count = 0
        for entry in entries:
            if count >= 60:
                break
            if not entry.name.startswith(name_frag):
                continue
            if entry.name.startswith(".") and not name_frag.startswith("."):
                continue
            if entry.name in self._SKIP:
                continue

            suffix = "/" if entry.is_dir() else ""
            display_name = entry.name + suffix
            insert = (dir_part + "/" + entry.name + suffix) if dir_part else (entry.name + suffix)

            yield Completion(
                text=insert,
                start_position=-len(partial),
                display=display_name,
                display_meta=str(entry.resolve()),
            )
            count += 1


def _hborder(left: str, right: str):
    def _gen():
        w = max(get_app().output.get_size().columns, 4)
        return [("class:box", left + "─" * (w - 2) + right)]
    return _gen


def _line_prefix(line_number, wrap_count):
    return [("class:prompt", "> ")] if (line_number == 0 and wrap_count == 0) else [("class:prompt", "  ")]


def _hint_line():
    w = max(get_app().output.get_size().columns, 20)
    left = "  ↵ enviar   ·   shift+tab muda modo   ·   ctrl+c sai"
    style_cls, label = _MODE_DISPLAY[get_mode()]
    pad = max(1, w - len(left) - len(label) - 2)
    return [("class:hint", left + " " * pad), (style_cls, label + "  ")]


def _token_line():
    """Token usage shown above the input box (Claude-style)."""
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
        """Force trigger completion menu when typing / or @"""
        text_before = buf.document.text_before_cursor
        if text_before and (text_before.endswith('/') or text_before.endswith('@')):
            # Trigger completion explicitly
            buf.complete()
        else:
            # Default tab behavior - insert tab or complete
            buf.complete()

    @kb.add("escape", "enter")  # Alt+Enter → newline
    def _(event):
        buf.insert_text("\n")

    input_window = Window(
        BufferControl(
            buffer=buf,
            input_processors=[_PlaceholderProcessor()],
        ),
        get_line_prefix=_line_prefix,
        wrap_lines=True,
        height=D(min=1, max=6),  # compacto: 1 linha, cresce até 6
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

    return Application(
        layout=Layout(body, focused_element=input_window),
        key_bindings=kb,
        style=_PT_STYLE,
        full_screen=False,
        mouse_support=False,
        erase_when_done=True,
    )


# Fallback simple prompt (if the full Application can't run)
_fallback_session: "PromptSession | None" = None

def _fallback_prompt() -> str:
    global _fallback_session
    if _fallback_session is None:
        _fallback_session = PromptSession(history=InMemoryHistory())
    from prompt_toolkit.formatted_text import HTML
    return _fallback_session.prompt(HTML(f"<b>> </b>"))


class CombinedCompleter(Completer):
    """Combines SlashCommandCompleter and AtMentionCompleter."""
    
    def __init__(self):
        self.slash_completer = SlashCommandCompleter()
        self.at_completer = AtMentionCompleter()
    
    def get_completions(self, document, complete_event):
        # Try slash completer first
        for completion in self.slash_completer.get_completions(document, complete_event):
            yield completion
        
        # Try @ completer
        for completion in self.at_completer.get_completions(document, complete_event):
            yield completion


def get_user_input() -> str:
    try:
        # Remove ThreadedCompleter to avoid race conditions
        # Use direct CombinedCompleter for more reliable completion
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
        console.print(f"\n  [{MUTED}]até logo 👋[/{MUTED}]\n")
        sys.exit(0)
    return text


# ── Header / welcome ───────────────────────────────────────────────────────────

def print_header(model_name: str, base_url: str):
    cwd = os.getcwd()
    body = (
        f"[bold {CORAL}]✻[/bold {CORAL}] [bold]Bem-vindo ao Agente CLI[/bold]\n\n"
        f"  [{MUTED}]modelo [/{MUTED}]  [white]{escape(model_name)}[/white]\n"
        f"  [{MUTED}]conexão[/{MUTED}]  [{GREEN}]●[/{GREEN}] [white]{escape(base_url)}[/white]\n"
        f"  [{MUTED}]pasta  [/{MUTED}]  [white]{escape(cwd)}[/white]"
    )
    console.print()
    console.print(Panel(body, box=box.ROUNDED, border_style=CORAL, padding=(1, 2), expand=True))
    console.print(
        f"  [{DIMC}]shift+tab[/{DIMC}] [{MUTED}]alterna entre aprovação · plano · automático[/{MUTED}]"
    )
    console.print()


# ── Conversation rendering ──────────────────────────────────────────────────────

def print_user_message(text: str):
    """Echo the user's submission (the input box is erased on submit)."""
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        prefix = f"[{CORAL}]>[/{CORAL}] " if i == 0 else "  "
        console.print(f"{prefix}[{MUTED}]{escape(line)}[/{MUTED}]")
    console.print()


def _bullet_block(bullet: str, bullet_color: str, content) -> Table:
    grid = Table.grid(padding=(0, 0))
    grid.add_column(width=2, no_wrap=True)
    grid.add_column(ratio=1, overflow="fold")
    grid.add_row(Text(f"{bullet} ", style=bullet_color), content)
    return grid


def print_agent_message(text: str):
    console.print(_bullet_block("⏺", f"bold {CORAL}", Markdown(text)))
    console.print()


def print_tool_result(tool_name: str, fn_args: dict, result: str, duration: float):
    arg_str = ", ".join(str(v) for v in fn_args.values())
    arg_str = arg_str[:70] + ("…" if len(arg_str) > 70 else "")

    header = Text()
    header.append(f"{tool_name}", style="bold white")
    header.append(f"({arg_str})", style=MUTED)
    console.print(_bullet_block("⏺", f"bold {GREEN}", header))

    preview = result.strip().split("\n")
    first = preview[0][:90] if preview else ""
    extra = f"  [+{len(preview) - 1} linhas]" if len(preview) > 1 else ""
    console.print(
        f"  [{GREEN}]⎿[/{GREEN}]  [{MUTED}]{escape(first)}{escape(extra)}[/{MUTED}]"
        f"  [{DIMC}]({duration:.1f}s)[/{DIMC}]"
    )
    console.print()


# ── System / errors / stats ─────────────────────────────────────────────────────

def print_system_message(text: str):
    console.print(f"  [{DIMC}]·[/{DIMC}] [{MUTED}]{escape(text)}[/{MUTED}]")


def print_error(text: str):
    console.print()
    console.print(_bullet_block("⏺", "bold red", Text(text, style="red")))
    console.print()


def print_session_stats():
    elapsed = time.perf_counter() - _stats["start"]
    m, s = divmod(int(elapsed), 60)
    total = _stats["tokens_in"] + _stats["tokens_out"]
    n = _stats["tool_calls"]
    tool_word = "ferramenta" if n == 1 else "ferramentas"
    console.print()
    console.print(Panel(
        f"[{MUTED}]tokens[/{MUTED}] [white]{total:,}[/white]"
        f"   [{DIMC}]·[/{DIMC}]   [{MUTED}]{tool_word}[/{MUTED}] [white]{n}[/white]"
        f"   [{DIMC}]·[/{DIMC}]   [{MUTED}]tempo[/{MUTED}] [white]{m:02d}:{s:02d}[/white]",
        box=box.ROUNDED, border_style=DIMC, padding=(0, 2), expand=False,
    ))
    console.print()


# ── Approval prompts ─────────────────────────────────────────────────────────────

def _simple_prompt(message_html: str) -> str:
    global _fallback_session
    if _fallback_session is None:
        _fallback_session = PromptSession(history=InMemoryHistory())
    from prompt_toolkit.formatted_text import HTML
    return _fallback_session.prompt(HTML(message_html)).strip()


# Variável global para armazenar a instância atual de captura
_current_capture = None

def set_current_capture(capture):
    """Define a instância de captura atual para acesso global."""
    global _current_capture
    _current_capture = capture

def _key_prompt(valid_keys: list, cancel_key: str = "") -> str:
    """Single-keypress prompt — no Enter needed. Returns the pressed key immediately."""
    _cancel = cancel_key or valid_keys[-1]
    
    # Pausa captura do input_queue para evitar conflito com msvcrt/prompt_toolkit
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
        style=_PT_STYLE,
        full_screen=False,
        mouse_support=False,
        erase_when_done=True,
    )
    try:
        result = app.run()
        # Pequeno delay para garantir que o terminal esteja pronto após o prompt
        time.sleep(0.05)
        # Retoma captura se estava pausada
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
    """Approval for file mutations. Returns True (ok) / False (cancel) / str (instruction)."""
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


def prompt_ask_user(
    question: str,
    options: list,
    *,
    step: int = 0,
    total: int = 0,
    skill_name: str = "",
) -> str:
    """Show a decision panel with numbered options. Returns the chosen option text."""
    console.print()
    if step and total:
        tag = f"  [{DIMC}]etapa {step} de {total}[/{DIMC}]"
        if skill_name:
            tag += f"  [{DIMC}]·  /{escape(skill_name)}[/{DIMC}]"
        console.print(tag)

    rows = []
    for i, opt in enumerate(options, 1):
        rows.append(f"   [{CYAN}]{i}.[/{CYAN}] [white]{escape(str(opt))}[/white]")
    body = f"[bold white]{escape(question)}[/bold white]\n\n" + "\n".join(rows)
    console.print(Panel(body, box=box.ROUNDED, border_style=GOLD, padding=(1, 2)))
    try:
        answer = _simple_prompt("<b><ansiyellow>></ansiyellow></b> ").strip()
        if answer.isdigit():
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return str(options[idx])
        return answer if answer else (str(options[0]) if options else "")
    except (KeyboardInterrupt, EOFError):
        return str(options[0]) if options else ""


def prompt_ask_text(
    question: str,
    default: str = "",
    *,
    step: int = 0,
    total: int = 0,
    skill_name: str = "",
) -> str:
    """Show a free-text question panel. Returns the typed answer."""
    console.print()
    if step and total:
        tag = f"  [{DIMC}]etapa {step} de {total}[/{DIMC}]"
        if skill_name:
            tag += f"  [{DIMC}]·  /{escape(skill_name)}[/{DIMC}]"
        console.print(tag)

    hint = f"  [{DIMC}]padrão: {escape(default)}[/{DIMC}]" if default else ""
    body = f"[bold white]{escape(question)}[/bold white]"
    if hint:
        body += f"\n{hint}"
    console.print(Panel(body, box=box.ROUNDED, border_style=GOLD, padding=(1, 2)))
    try:
        answer = _simple_prompt("<b><ansiyellow>></ansiyellow></b> ").strip()
        return answer if answer else default
    except (KeyboardInterrupt, EOFError):
        return default


def run_skill_wizard(questions: list, skill_name: str = "") -> dict:
    """Run a multi-step skill wizard. Returns {id: answer}."""
    total = len(questions)
    answers: dict[str, str] = {}

    for i, q in enumerate(questions, 1):
        qid     = q.get("id", f"q{i}")
        ask_txt = q.get("ask", "")
        options = q.get("options", [])
        default = q.get("default", "")

        # Conditional: skip if "if": "other_id=value" not matched
        condition = q.get("if", "")
        if condition and "=" in condition:
            cid, cval = condition.split("=", 1)
            if answers.get(cid, "").lower() != cval.strip().lower():
                continue

        if options:
            answer = prompt_ask_user(
                ask_txt, options,
                step=i, total=total, skill_name=skill_name,
            )
        else:
            answer = prompt_ask_text(
                ask_txt, default,
                step=i, total=total, skill_name=skill_name,
            )
        answers[qid] = answer

    # ── Summary ─────────────────────────────────────────────────────────────
    console.print()
    rows = []
    for q in questions:
        qid = q.get("id", "")
        if qid not in answers:
            continue
        label = q.get("label", q.get("ask", qid))
        label = label if len(label) <= 28 else label[:25] + "…"
        rows.append(
            f"  [{MUTED}]{escape(label):<28}[/{MUTED}]"
            f"  [bold white]{escape(answers[qid])}[/bold white]"
        )
    console.print(Panel(
        "\n".join(rows),
        title=f"[bold {GREEN}]✓ configurações confirmadas[/bold {GREEN}]",
        title_align="left",
        box=box.ROUNDED, border_style=GREEN, padding=(1, 2),
    ))
    console.print()
    return answers


def prompt_plan_approval(tool_calls: dict) -> bool:
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


# ── AgentStream (live streaming display) ─────────────────────────────────────────

_REASONING_LIVE_LINES = 8   # linhas do raciocínio mostradas ao vivo
_ANSWER_LIVE_LINES = 15     # linhas da resposta mostradas ao vivo (markdown completo no fim)


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
        self._spinner = Spinner("dots", style=CORAL)
        self._pending_tools: list[str] = []
        self._input_capture = _StreamInputCapture() if _HAS_MSVCRT else None
        # Pass self (has __rich__) so the auto-refresh thread re-renders the
        # timer/text every frame. We do NOT refresh manually — mixing manual
        # refresh() with the auto-refresh thread is what causes flicker.
        self._live = Live(
            self,
            console=console,
            refresh_per_second=10,
            transient=True,
            auto_refresh=True,
            vertical_overflow="crop",
        )

    # ── lifecycle ──────────────────────────────────────────────
    def __enter__(self):
        self._live.start()
        if self._input_capture is not None:
            self._input_capture.start()
            set_current_capture(self._input_capture)
        return self

    def __exit__(self, *args):
        if self._input_capture is not None:
            self._input_capture.stop()
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
            print_agent_message(self._text)

    def get_queued_inputs(self) -> list:
        """Return messages typed during streaming (Enter-submitted). Clears the queue."""
        if self._input_capture is not None:
            return self._input_capture.drain()
        return []

    def __rich__(self) -> Group:
        return self._render()

    def _refresh(self):
        # No-op on purpose: the Live auto-refresh thread repaints on a steady
        # cadence by calling __rich__. Forcing extra refreshes here causes the
        # screen to flicker. Mutating state is enough; the next frame picks it up.
        pass

    # ── status / rendering ─────────────────────────────────────
    def _status_line(self) -> Text:
        elapsed = time.perf_counter() - self._start
        if self._reasoning_active:
            label = "Pensando"
        elif self._text.strip():
            label = "Escrevendo"
        else:
            label = "Trabalhando"
        t = Text()
        t.append(label, style=f"bold {CORAL}")
        t.append("… ", style=CORAL)
        t.append(f"({elapsed:.1f}s", style=DIMC)
        if self._tokens_out or self._tokens_in:
            t.append(f"  ↑{self._tokens_in} ↓{self._tokens_out}", style=DIMC)
        t.append(")", style=DIMC)
        return t

    def _render(self) -> Group:
        grid = Table.grid(padding=(0, 1))
        grid.add_column(no_wrap=True)
        grid.add_column(no_wrap=True)
        grid.add_row(self._spinner, self._status_line())

        parts: list = [Text(""), grid]

        # Reasoning: live stream (truncated) while active, compact once collapsed
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

        # Pending tool calls
        for name in self._pending_tools:
            parts.append(Text.from_markup(
                f"  [{GREEN}]⏺[/{GREEN}] [bold white]{escape(name)}[/bold white] [{DIMC}]preparando…[/{DIMC}]"
            ))

        # Answer: while streaming show only the tail (bounded height = no
        # flicker / no overflow jank). Full markdown is printed on finalize.
        if self._text.strip():
            lines = self._text.split("\n")
            shown = lines[-_ANSWER_LIVE_LINES:]
            truncated = len(lines) > _ANSWER_LIVE_LINES
            body = Text(("…\n" if truncated else "") + "\n".join(shown), style="white")
            parts.append(Text(""))
            parts.append(_bullet_block("⏺", f"bold {CORAL}", body))

        # ── Input queue indicator (typing while streaming) ──────────────────
        if self._input_capture is not None:
            buf_text = self._input_capture.buffer
            qsize   = self._input_capture.queue_size
            parts.append(Text(""))
            if qsize > 0:
                label = f"{qsize} mensagem{'ns' if qsize > 1 else ''} na fila"
                parts.append(Text.from_markup(f"  [{GOLD}]⏳ {label}[/{GOLD}]"))
            cursor  = "▌" if buf_text else ""
            display = escape(buf_text[-60:]) if len(buf_text) > 60 else escape(buf_text)
            parts.append(Text.from_markup(
                f"  [{MUTED}]···[/{MUTED}] [{DIMC}]{display}{cursor}[/{DIMC}]"
            ))

        return Group(*parts)

    # ── input from the agent loop ──────────────────────────────
    def set_reasoning(self, full: str):
        if full and not self._reasoning_started:
            self._reasoning_started = True
            self._reasoning_active = True
            self._reasoning_start = time.perf_counter()
        self._reasoning = full
        self._refresh()

    def set_answer(self, full: str):
        if full.strip():
            self._collapse_reasoning()
        self._text = full
        self._refresh()

    def add_text(self, chunk: str):
        self.set_answer(self._text + chunk)

    def _collapse_reasoning(self):
        if self._reasoning_active:
            self._reasoning_active = False
            self._reasoning_dur = time.perf_counter() - (self._reasoning_start or self._start)

    def add_tool_pending(self, tool_name: str):
        if tool_name and tool_name not in self._pending_tools:
            self._pending_tools.append(tool_name)
            self._refresh()

    def set_usage(self, tokens_in: int, tokens_out: int):
        _stats["tokens_in"] += tokens_in - self._tokens_in
        _stats["tokens_out"] += tokens_out - self._tokens_out
        self._tokens_in = tokens_in
        self._tokens_out = tokens_out
        self._refresh()
