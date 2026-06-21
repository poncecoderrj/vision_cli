"""
Skill wizard and free-text/option prompts.
"""

from rich.panel import Panel
from rich.markup import escape
from rich import box

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit import PromptSession

from .theme import console, CYAN, GOLD, GREEN, MUTED, DIMC

_fallback_session: "PromptSession | None" = None


def _simple_prompt(message_html: str) -> str:
    global _fallback_session
    if _fallback_session is None:
        _fallback_session = PromptSession(history=InMemoryHistory())
    from prompt_toolkit.formatted_text import HTML
    return _fallback_session.prompt(HTML(message_html)).strip()


def prompt_ask_user(
    question: str,
    options: list,
    *,
    step: int = 0,
    total: int = 0,
    skill_name: str = "",
) -> str:
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
    total = len(questions)
    answers: dict[str, str] = {}

    for i, q in enumerate(questions, 1):
        qid     = q.get("id", f"q{i}")
        ask_txt = q.get("ask", "")
        options = q.get("options", [])
        default = q.get("default", "")

        condition = q.get("if", "")
        if condition and "=" in condition:
            cid, cval = condition.split("=", 1)
            if answers.get(cid, "").lower() != cval.strip().lower():
                continue

        if options:
            answer = prompt_ask_user(ask_txt, options, step=i, total=total, skill_name=skill_name)
        else:
            answer = prompt_ask_text(ask_txt, default, step=i, total=total, skill_name=skill_name)
        answers[qid] = answer

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


__all__ = ["prompt_ask_user", "prompt_ask_text", "run_skill_wizard"]
