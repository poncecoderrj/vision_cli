"""
Console output helpers: header, user/agent messages, tool results, stats.
"""

import os
import time

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markup import escape
from rich.rule import Rule
from rich import box

from .theme import console, CORAL, GREEN, GOLD, MUTED, DIMC
from .modes import _stats


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


def print_user_message(text: str):
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

    is_error = result.strip().startswith("Erro:") or result.strip().startswith("Error:")
    if is_error:
        preview_lines = result.strip().split("\n")
        for line in preview_lines[:5]:
            console.print(f"  [{GREEN}]⎿[/{GREEN}]  [red]{escape(line)}[/red]")
        if len(preview_lines) > 5:
            console.print(f"  [{GREEN}]⎿[/{GREEN}]  [{MUTED}][+{len(preview_lines) - 5} linhas...][/{MUTED}]")
    else:
        preview = result.strip().split("\n")
        first = preview[0][:90] if preview else ""
        extra = f"  [+{len(preview) - 1} linhas]" if len(preview) > 1 else ""
        console.print(
            f"  [{GREEN}]⎿[/{GREEN}]  [{MUTED}]{escape(first)}{escape(extra)}[/{MUTED}]"
            f"  [{DIMC}]({duration:.1f}s)[/{DIMC}]"
        )
    console.print()


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


__all__ = [
    "print_header", "print_user_message", "print_agent_message",
    "print_tool_result", "print_system_message", "print_error",
    "print_session_stats", "_bullet_block",
]
