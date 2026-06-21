"""
File system mutation tools: read, write, edit, delete.
"""

import os
from pathlib import Path
from .base import Tool, ToolResult

MAX_READ_CHARS = 60_000


def _resolve(path: str) -> Path:
    return Path(os.path.expandvars(path)).expanduser().resolve()


def _approval_needed() -> bool:
    from ui import get_mode, AgentMode
    return get_mode() == AgentMode.ACCEPT


def _ask(title: str, detail: str):
    """Returns None to proceed, or str with error/instruction."""
    if not _approval_needed():
        return None
    from ui import prompt_simple_approval
    decision = prompt_simple_approval(title, detail)
    if decision is True:
        return None
    if isinstance(decision, str):
        return f"Usuário não aprovou e pediu em vez disso: {decision}"
    return "Operação cancelada pelo usuário."


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read the contents of a text file. Use before editing to see exact content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path":   {"type": "string",  "description": "Path to the file."},
            "offset": {"type": "integer", "description": "Optional 1-based start line."},
            "limit":  {"type": "integer", "description": "Optional number of lines to read."},
        },
        "required": ["path"],
    }

    def execute(self, path: str, offset: int = 0, limit: int = 0) -> ToolResult:
        p = _resolve(path)
        if not p.exists():
            msg = f"Erro: arquivo não encontrado: {p}"
            return ToolResult(success=False, output=msg, error=msg)
        if p.is_dir():
            msg = f"Erro: '{p}' é um diretório. Use list_dir."
            return ToolResult(success=False, output=msg, error=msg)
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            msg = f"Erro: '{p}' parece ser um arquivo binário (não é texto)."
            return ToolResult(success=False, output=msg, error=msg)
        except Exception as e:
            msg = f"Erro ao ler arquivo: {e}"
            return ToolResult(success=False, output=msg, error=msg)

        lines = text.split("\n")
        total = len(lines)
        start = max(offset - 1, 0) if offset else 0
        end = (start + limit) if limit else total
        chunk = "\n".join(lines[start:end])

        truncated = False
        if len(chunk) > MAX_READ_CHARS:
            chunk = chunk[:MAX_READ_CHARS]
            truncated = True

        header = f"{p}  ({total} linhas)"
        if offset or limit:
            header += f"  [linhas {start + 1}-{min(end, total)}]"
        note = "\n\n[... conteúdo truncado ...]" if truncated else ""
        output = f"{header}\n{'─' * 40}\n{chunk}{note}"
        return ToolResult(success=True, output=output)


class WriteFileTool(Tool):
    name = "write_file"
    description = "Create a new file or overwrite an existing one with the given content."
    parameters = {
        "type": "object",
        "properties": {
            "path":    {"type": "string", "description": "Path to the file."},
            "content": {"type": "string", "description": "Full content to write."},
        },
        "required": ["path", "content"],
    }

    def execute(self, path: str, content: str) -> ToolResult:
        p = _resolve(path)
        exists = p.exists()
        action = "Sobrescrever arquivo" if exists else "Criar arquivo"
        n_lines = content.count("\n") + 1
        detail = f"{p}\n\n{n_lines} linhas · {len(content):,} caracteres"

        blocked = _ask(f"⚠ {action}", detail)
        if blocked:
            return ToolResult(success=False, output=blocked, error=blocked)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        except Exception as e:
            msg = f"Erro ao escrever arquivo: {e}"
            return ToolResult(success=False, output=msg, error=msg)
        msg = f"{'Sobrescrito' if exists else 'Criado'}: {p} ({n_lines} linhas)"
        return ToolResult(success=True, output=msg)


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Replace an exact string in a file. old_string must match exactly "
        "(including indentation) and be unique unless replace_all is true."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path":        {"type": "string",  "description": "Path to the file."},
            "old_string":  {"type": "string",  "description": "Exact text to find."},
            "new_string":  {"type": "string",  "description": "Text to replace it with."},
            "replace_all": {"type": "boolean", "description": "Replace all occurrences (default false)."},
        },
        "required": ["path", "old_string", "new_string"],
    }

    def execute(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> ToolResult:
        p = _resolve(path)
        if not p.exists():
            msg = f"Erro: arquivo não encontrado: {p}"
            return ToolResult(success=False, output=msg, error=msg)
        if not old_string:
            msg = "Erro: old_string é obrigatório e não pode ser vazio."
            return ToolResult(success=False, output=msg, error=msg)
        if not new_string:
            msg = "Erro: new_string é obrigatório e não pode ser vazio."
            return ToolResult(success=False, output=msg, error=msg)
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            msg = f"Erro ao ler arquivo: {e}"
            return ToolResult(success=False, output=msg, error=msg)

        count = text.count(old_string)
        if count == 0:
            msg = "Erro: old_string não encontrado no arquivo. Verifique espaços/indentação exatos."
            return ToolResult(success=False, output=msg, error=msg)
        if count > 1 and not replace_all:
            msg = (f"Erro: old_string aparece {count}× — não é único. "
                   f"Inclua mais contexto ou use replace_all=true.")
            return ToolResult(success=False, output=msg, error=msg)

        preview_old = (old_string[:120] + "…") if len(old_string) > 120 else old_string
        preview_new = (new_string[:120] + "…") if len(new_string) > 120 else new_string
        detail = f"{p}\n\n- {preview_old}\n+ {preview_new}"
        if replace_all:
            detail += f"\n\n(substituindo {count} ocorrências)"

        blocked = _ask("⚠ Editar arquivo", detail)
        if blocked:
            return ToolResult(success=False, output=blocked, error=blocked)

        new_text = text.replace(old_string, new_string) if replace_all \
            else text.replace(old_string, new_string, 1)
        try:
            p.write_text(new_text, encoding="utf-8")
        except Exception as e:
            msg = f"Erro ao salvar arquivo: {e}"
            return ToolResult(success=False, output=msg, error=msg)
        n = count if replace_all else 1
        msg = f"Editado: {p} ({n} substituição{'ões' if n > 1 else ''})"
        return ToolResult(success=True, output=msg)


class DeleteFileTool(Tool):
    name = "delete_file"
    description = "Delete a single file (not directories)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to delete."},
        },
        "required": ["path"],
    }

    def execute(self, path: str) -> ToolResult:
        p = _resolve(path)
        if not p.exists():
            msg = f"Erro: arquivo não encontrado: {p}"
            return ToolResult(success=False, output=msg, error=msg)
        if p.is_dir():
            msg = f"Erro: '{p}' é um diretório. Por segurança, delete diretórios via run_shell explicitamente."
            return ToolResult(success=False, output=msg, error=msg)

        blocked = _ask("⚠ Deletar arquivo", str(p))
        if blocked:
            return ToolResult(success=False, output=blocked, error=blocked)
        try:
            p.unlink()
        except Exception as e:
            msg = f"Erro ao deletar: {e}"
            return ToolResult(success=False, output=msg, error=msg)
        return ToolResult(success=True, output=f"Deletado: {p}")


__all__ = ["ReadFileTool", "WriteFileTool", "EditFileTool", "DeleteFileTool"]
