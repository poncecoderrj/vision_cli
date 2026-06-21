"""
Slash command handler: /skills, /resume, /save, /clear, /<skill-name>.
"""

from rich.panel import Panel
from rich.markup import escape
from rich import box

from src.ui.theme import console, GOLD, GREEN, MUTED, DIMC
from src.ui.output import print_system_message
from src.skills.manager import (
    list_skills, load_skill, parse_skill_questions,
    print_skills_panel, print_skill_activated,
)
from src.session.store import load_session, list_sessions, save_named_session
from src.tools import AVAILABLE_TOOLS


def handle_slash_command(
    cmd: str, rest: str, messages: list,
    model_name: str, base_url: str,
) -> "tuple[bool, str]":
    """
    Handle /command input.
    Returns (consumed, effective_user_msg).
    consumed=True means skip LLM for this turn.
    """
    from src.ui.wizard import run_skill_wizard

    name = cmd.lstrip("/").lower().strip()

    if name in ("", "skills", "help", "ajuda"):
        print_skills_panel(detail=True)
        return True, ""

    if name in ("clear", "limpar", "reset"):
        del messages[1:]
        print_system_message("Conversa resetada. Skill desativada.")
        return True, ""

    # ── /resume ──────────────────────────────────────────────────────────────
    if name in ("resume", "retomar"):
        arg = rest.strip()
        if arg in ("list", "lista"):
            sessions = list_sessions()
            if not sessions:
                print_system_message("Nenhuma sessão salva em .visions/")
                return True, ""
            rows = []
            for s in sessions:
                saved = s["saved_at"][:16].replace("T", " ")
                rows.append(
                    f"  [{GOLD}]{s['name']:<22}[/{GOLD}]"
                    f"  [white]{s['turns']} turnos[/white]"
                    f"  [{MUTED}]{saved}[/{MUTED}]"
                )
            console.print()
            console.print(Panel(
                "\n".join(rows),
                title=f"[bold {GOLD}]◈ sessões salvas[/bold {GOLD}]",
                title_align="left",
                box=box.ROUNDED, border_style=GOLD, padding=(1, 2),
            ))
            console.print()
            return True, ""

        data = load_session(arg)
        if data is None:
            label = arg if arg else "session_current"
            print_system_message(f"Sessão '{label}' não encontrada em .visions/")
            return True, ""

        loaded = data.get("messages", [])
        non_system = [m for m in loaded if m.get("role") != "system"]
        del messages[1:]
        messages.extend(non_system)

        turns    = data.get("turns", "?")
        saved_at = data.get("saved_at", "")[:16].replace("T", " ")
        console.print()
        console.print(Panel(
            f"  [white]{turns} turnos restaurados[/white]\n"
            f"  [{MUTED}]salvo em {escape(saved_at)}[/{MUTED}]",
            title=f"[bold {GREEN}]✓ sessão restaurada[/bold {GREEN}]",
            title_align="left",
            box=box.ROUNDED, border_style=GREEN, padding=(0, 2),
        ))
        console.print()
        return True, ""

    # ── /save ────────────────────────────────────────────────────────────────
    if name in ("save", "salvar"):
        save_name = rest.strip()
        if not save_name:
            print_system_message("Uso: /save nome-da-sessao")
            return True, ""
        path = save_named_session(messages, save_name, model_name, base_url)
        print_system_message(f"Sessão salva: {path}")
        return True, ""

    # ── /explore ─────────────────────────────────────────────────────────────
    if name in ("explore", "explorar"):
        import os
        path = rest.strip() or os.getcwd()

        list_tool = AVAILABLE_TOOLS.get("list_dir")
        if list_tool:
            res = list_tool.execute(path=path)
            console.print(f"\n[bold]{escape(path)}[/bold]")
            console.print(res.output if res.success else f"[red]{res.error}[/red]")

        read_tool = AVAILABLE_TOOLS.get("read_file")
        if read_tool:
            for fname in ("README.md", "pyproject.toml", "setup.py", "main.py"):
                fpath = os.path.join(path, fname)
                res = read_tool.execute(path=fpath)
                if res.success:
                    preview = "\n".join(res.output.splitlines()[:20])
                    console.print(f"\n[{GOLD}]── {fname} (primeiras 20 linhas)[/{GOLD}]")
                    console.print(f"[{DIMC}]{escape(preview)}[/{DIMC}]")
                    break

        search_tool = AVAILABLE_TOOLS.get("search_code")
        if search_tool:
            for pattern in ("class.*Tool", "def execute", "async def"):
                res = search_tool.execute(query=pattern, path=path)
                if res.success and res.output.strip():
                    preview = res.output[:400] + ("…" if len(res.output) > 400 else "")
                    console.print(f"\n[{MUTED}]── ocorrências de '{pattern}'[/{MUTED}]")
                    console.print(f"[{DIMC}]{escape(preview)}[/{DIMC}]")
        console.print()
        return True, ""

    # ── /analyze ─────────────────────────────────────────────────────────────
    if name in ("analyze", "analisar", "análise"):
        from src.core.analyzer import MetricsAnalyzer
        import json as _json
        analyzer = MetricsAnalyzer()
        report = analyzer.analyze_stats()
        console.print()
        console.print(f"[bold {GOLD}]◈ Relatório de métricas[/bold {GOLD}]")
        console.print(f"[{DIMC}]{escape(_json.dumps(report, ensure_ascii=False, indent=2))}[/{DIMC}]")
        console.print(f"\n[bold {GOLD}]◈ Sugestões[/bold {GOLD}]")
        console.print(f"[white]{escape(analyzer.generate_prompt_boost())}[/white]")
        console.print()
        return True, ""

    # ── /<skill-name> ────────────────────────────────────────────────────────
    skill_content = load_skill(name)
    if skill_content:
        title_line = skill_content.split("\n")[0].lstrip("# ").strip()
        print_skill_activated(name, title_line)

        questions = parse_skill_questions(skill_content)
        config_block = ""
        if questions:
            answers = run_skill_wizard(questions, skill_name=name)
            lines = [f"  {k}: {v}" for k, v in answers.items()]
            config_block = (
                "\n\nCONFIGURAÇÕES ESCOLHIDAS PELO USUÁRIO (use exatamente estas):\n"
                + "\n".join(lines)
                + "\n\nAgora execute os passos da skill com essas configurações."
            )

        messages[:] = [m for m in messages if not m.get("_skill")]
        messages.insert(1, {
            "role": "system",
            "content": f"SKILL ATIVA — siga o roteiro abaixo à risca:\n\n{skill_content}{config_block}",
            "_skill": True,
        })

        if rest.strip():
            return False, rest
        if config_block:
            return False, "Execute agora seguindo o roteiro da skill com as configurações acima."
        return True, ""

    return False, cmd + (" " + rest if rest else "")


__all__ = ["handle_slash_command"]
