"""
Skills management: list, load, parse, display.
"""

import json
import re
from pathlib import Path

from rich.panel import Panel
from rich.markup import escape
from rich import box

_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


def list_skills() -> dict[str, Path]:
    if not _SKILLS_DIR.exists():
        return {}
    return {p.stem: p for p in sorted(_SKILLS_DIR.glob("*.md"))}


def load_skill(name: str) -> "str | None":
    skills = list_skills()
    if name in skills:
        return skills[name].read_text(encoding="utf-8")
    return None


def parse_skill_questions(content: str) -> list[dict]:
    m = re.search(r'<!--\s*QUESTIONS\s*\n(.*?)\n-->', content, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(1).strip())
    except Exception:
        return []


def print_skills_panel(detail: bool = False):
    from src.ui.theme import console, GOLD, DIMC
    skills = list_skills()
    if not skills:
        console.print(f"  [grey42]Nenhuma skill encontrada em skills/[/grey42]")
        return

    console.print()
    rows = []
    for name, path in skills.items():
        content = path.read_text(encoding="utf-8")
        title = content.split("\n")[0].lstrip("# ").strip()
        questions = parse_skill_questions(content)
        q_count = f"  [{DIMC}]{len(questions)} perguntas[/{DIMC}]" if questions else ""
        rows.append(f"  [{GOLD}]/{name:<14}[/{GOLD}] [white]{escape(title)}[/white]{q_count}")

        if detail and questions:
            for q in questions:
                ask = q.get("ask", "")[:60]
                opts = q.get("options", [])
                opt_preview = "  ·  " + " / ".join(str(o) for o in opts[:3]) if opts else ""
                if len(opts) > 3:
                    opt_preview += f" (+{len(opts)-3})"
                rows.append(f"    [{DIMC}]→ {escape(ask)}{escape(opt_preview)}[/{DIMC}]")

    console.print(Panel(
        "\n".join(rows),
        title=f"[bold {GOLD}]◈ skills disponíveis[/bold {GOLD}]",
        title_align="left",
        box=box.ROUNDED, border_style=GOLD, padding=(1, 2),
    ))
    console.print(
        f"  [{DIMC}]/nome-da-skill  ativa a skill com wizard de configuração"
        f"   ·   /  ou  /skills  mostra esta lista[/{DIMC}]"
    )
    console.print()


def print_skill_activated(name: str, title_line: str):
    from src.ui.theme import console, MUTED, GREEN
    console.print()
    console.print(Panel(
        f"[bold white]{escape(title_line)}[/bold white]\n"
        f"  [{MUTED}]roteiro carregado — o agente vai seguir os passos definidos[/{MUTED}]",
        title=f"[bold {GREEN}]✓ skill ativada: /{name}[/bold {GREEN}]",
        title_align="left",
        box=box.ROUNDED, border_style=GREEN, padding=(0, 2),
    ))
    console.print()


def print_skills_hint(skills: dict):
    from src.ui.theme import console, GOLD, DIMC
    if not skills:
        return
    names = "  ".join(f"[{GOLD}]/{n}[/{GOLD}]" for n in skills)
    console.print(f"  [{DIMC}]skills:[/{DIMC}]  {names}")
    console.print(f"  [{DIMC}]/skills para ver detalhes[/{DIMC}]")
    console.print()


__all__ = [
    "list_skills", "load_skill", "parse_skill_questions",
    "print_skills_panel", "print_skill_activated", "print_skills_hint",
]
