"""
Read-only navigation tools: list_dir, glob_files, search_code.
"""

import os
import re
from pathlib import Path
from .base import Tool, ToolResult

MAX_GREP_RESULTS = 60
MAX_GLOB_RESULTS = 200
IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".idea", ".mypy_cache", ".pytest_cache", ".next",
}


def _resolve(path: str) -> Path:
    return Path(os.path.expandvars(path)).expanduser().resolve()


class ListDirTool(Tool):
    name = "list_dir"
    description = "List the contents of a directory (folders first)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: current)."},
        },
        "required": [],
    }

    def execute(self, path: str = ".") -> ToolResult:
        p = _resolve(path)
        if not p.exists():
            msg = f"Erro: diretório não encontrado: {p}"
            return ToolResult(success=False, output=msg, error=msg)
        if not p.is_dir():
            msg = f"Erro: '{p}' não é um diretório."
            return ToolResult(success=False, output=msg, error=msg)
        try:
            entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        except Exception as e:
            msg = f"Erro ao listar diretório: {e}"
            return ToolResult(success=False, output=msg, error=msg)

        lines = [f"{p}", "─" * 40]
        for e in entries:
            if e.is_dir():
                lines.append(f"  📁 {e.name}/")
            else:
                try:
                    size = e.stat().st_size
                except OSError:
                    size = 0
                lines.append(f"  📄 {e.name}  ({size:,} B)")
        if len(lines) == 2:
            lines.append("  (vazio)")
        return ToolResult(success=True, output="\n".join(lines))


class GlobFilesTool(Tool):
    name = "glob_files"
    description = "Find files matching a glob pattern, e.g. '**/*.py' or 'src/*.js'."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern."},
            "path":    {"type": "string", "description": "Base directory (default: current)."},
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = ".") -> ToolResult:
        base = _resolve(path)
        if not base.exists():
            msg = f"Erro: diretório base não encontrado: {base}"
            return ToolResult(success=False, output=msg, error=msg)
        try:
            matches = [
                m for m in base.glob(pattern)
                if not any(part in IGNORE_DIRS for part in m.parts)
            ]
        except Exception as e:
            msg = f"Erro no glob: {e}"
            return ToolResult(success=False, output=msg, error=msg)

        matches = sorted(matches, key=lambda m: m.stat().st_mtime if m.exists() else 0, reverse=True)
        if not matches:
            return ToolResult(success=True, output=f"Nenhum arquivo corresponde a '{pattern}' em {base}.")

        shown = matches[:MAX_GLOB_RESULTS]
        out = [str(m) for m in shown]
        if len(matches) > MAX_GLOB_RESULTS:
            out.append(f"... (+{len(matches) - MAX_GLOB_RESULTS} arquivos)")
        return ToolResult(success=True, output="\n".join(out))


class SearchCodeTool(Tool):
    name = "search_code"
    description = "Search file contents by regular expression (like grep). Returns file:line: matches."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for."},
            "path":    {"type": "string", "description": "Base directory or file (default: current)."},
            "glob":    {"type": "string", "description": "Filter files, e.g. '*.py' (default: all)."},
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = ".", glob: str = "*") -> ToolResult:
        base = _resolve(path)
        try:
            regex = re.compile(pattern)
        except re.error as e:
            msg = f"Erro: regex inválida: {e}"
            return ToolResult(success=False, output=msg, error=msg)
        if not base.exists():
            msg = f"Erro: caminho não encontrado: {base}"
            return ToolResult(success=False, output=msg, error=msg)

        results: list[str] = []
        files = [base] if base.is_file() else base.rglob(glob)
        for f in files:
            if not f.is_file():
                continue
            if any(part in IGNORE_DIRS for part in f.parts):
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if regex.search(line):
                            results.append(f"{f}:{i}: {line.rstrip()[:200]}")
                            if len(results) >= MAX_GREP_RESULTS:
                                results.append(f"... (limite de {MAX_GREP_RESULTS} resultados atingido)")
                                return ToolResult(success=True, output="\n".join(results))
            except (OSError, UnicodeError):
                continue

        output = "\n".join(results) if results else f"Nenhuma ocorrência de '{pattern}'."
        return ToolResult(success=True, output=output)


__all__ = ["ListDirTool", "GlobFilesTool", "SearchCodeTool"]
