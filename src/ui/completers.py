"""
Autocomplete providers for slash commands and @file mentions.
"""

import re
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion


class SlashCommandCompleter(Completer):
    """Triggers on '/' in input, completes special commands and skills."""

    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        m = re.search(r"(?:^|\s)/(\w*)$", text_before)
        if m is None:
            return

        partial = m.group(1).lower()
        special_commands = [
            ("resume",  "Continuar sessão anterior"),
            ("config",  "Ver/editar configurações"),
            ("skills",  "Listar skills disponíveis"),
            ("help",    "Ajuda"),
            ("clear",   "Limpar tela"),
            ("exit",    "Sair"),
        ]

        skills_paths = [Path("skills"), Path("src/skills")]
        skill_list = []
        seen = set()
        for sp in skills_paths:
            if sp.exists():
                for sf in sp.glob("*.md"):
                    if sf.stem not in seen:
                        skill_list.append((sf.stem, f"Skill: {sf.stem}"))
                        seen.add(sf.stem)

        count = 0
        for name, description in special_commands + skill_list:
            if count >= 50:
                break
            if not name.lower().startswith(partial):
                continue
            yield Completion(
                text=name,
                start_position=-len(partial),
                display=f"/{name}",
                display_meta=description,
            )
            count += 1


class AtMentionCompleter(Completer):
    """Triggers on '@' in input, completes file/directory paths."""

    _SKIP = {"__pycache__", "node_modules", ".git", ".venv", "venv",
              "dist", "build", ".idea", ".mypy_cache", ".pytest_cache"}
    _SEARCH_DIRS = [".", "src", "docs", "tests", "app", "lib", "packages"]

    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        m = re.search(r"(?:^|\s)@(\S*)$", text_before)
        if m is None:
            return

        partial = m.group(1)
        norm = partial.replace("\\", "/")
        if "/" in norm:
            sep = norm.rfind("/")
            dir_part = norm[:sep] or "."
            name_frag = norm[sep + 1:]
            base = Path(dir_part)
            if not base.is_absolute():
                base = Path.cwd() / base
        else:
            base = Path.cwd()
            dir_part = ""
            name_frag = norm

        should_search_common = (
            not base.exists() or not base.is_dir()
            or (not dir_part and not name_frag)
        )

        if should_search_common:
            for search_dir in self._SEARCH_DIRS:
                search_path = Path.cwd() / search_dir
                if search_path.exists() and search_path.is_dir():
                    try:
                        for entry in search_path.iterdir():
                            if entry.name in self._SKIP:
                                continue
                            suffix = "/" if entry.is_dir() else ""
                            rel_path = f"{search_dir}/{entry.name}{suffix}"
                            file_type = "diretório" if entry.is_dir() else "arquivo"
                            yield Completion(
                                text=rel_path,
                                start_position=-len(partial),
                                display=entry.name + suffix,
                                display_meta=f"@{file_type} em {search_dir}",
                            )
                    except (PermissionError, OSError):
                        pass

            try:
                for entry in Path.cwd().iterdir():
                    if entry.name in self._SKIP or entry.name.startswith("_"):
                        continue
                    suffix = "/" if entry.is_dir() else ""
                    file_type = "diretório" if entry.is_dir() else "arquivo"
                    yield Completion(
                        text=entry.name + suffix,
                        start_position=-len(partial),
                        display=entry.name + suffix,
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
            insert = (dir_part + "/" + entry.name + suffix) if dir_part else (entry.name + suffix)
            yield Completion(
                text=insert,
                start_position=-len(partial),
                display=entry.name + suffix,
                display_meta=str(entry.resolve()),
            )
            count += 1


class CombinedCompleter(Completer):
    def __init__(self):
        self.slash = SlashCommandCompleter()
        self.at = AtMentionCompleter()

    def get_completions(self, document, complete_event):
        yield from self.slash.get_completions(document, complete_event)
        yield from self.at.get_completions(document, complete_event)


__all__ = ["SlashCommandCompleter", "AtMentionCompleter", "CombinedCompleter"]
