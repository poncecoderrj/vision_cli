"""
Tool execution and @mention expansion.
"""

import inspect
import json
import os
import re
import time
from pathlib import Path


def expand_at_mentions(text: str) -> str:
    """Replace @filepath references with actual file contents."""
    pattern = re.compile(r'@([\w./\\-]+)')

    def _replace(m):
        raw = m.group(1).rstrip(".,;:!?")
        p = Path(raw)
        if not p.is_absolute():
            p = Path(os.getcwd()) / p
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                ext = p.suffix.lstrip(".")
                return f"[conteúdo de @{raw}]\n```{ext}\n{content}\n```"
            except Exception:
                pass
        return m.group(0)

    return pattern.sub(_replace, text)


def execute_tool(tc: dict, available_tools: dict) -> str:
    """Execute a single tool call dict and return its string output."""
    from src.tools.base import ToolResult
    from src.ui.output import print_error, print_system_message, print_tool_result
    from src.ui.modes import track_tool_call

    fn_name = tc["name"]
    try:
        fn_args = json.loads(tc["arguments"]) if tc["arguments"].strip() else {}
    except json.JSONDecodeError:
        fn_args = {}

    tool = available_tools.get(fn_name)
    if tool is None:
        return f"Tool '{fn_name}' não encontrada."

    try:
        sig = inspect.signature(tool.execute)
        required_args = [
            p for p, v in sig.parameters.items()
            if v.default is inspect.Parameter.empty
            and v.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and p != "self"
        ]
        missing = [a for a in required_args if a not in fn_args or fn_args[a] == ""]
        if missing:
            return f"Erro: {fn_name} requer: {', '.join(required_args)}. Faltando: {', '.join(missing)}"
    except Exception as e:
        print_system_message(f"Aviso: não foi possível validar argumentos de {fn_name}: {e}")

    track_tool_call()
    t0 = time.perf_counter()
    try:
        result = tool.execute(**fn_args)
    except TypeError as e:
        err = f"Erro de argumentos em {fn_name}: {e}"
        print_error(err)
        return err
    except Exception as e:
        err = f"Erro ao executar {fn_name}: {type(e).__name__}: {e}"
        print_error(err)
        return err

    output = result.output if isinstance(result, ToolResult) else str(result)
    print_tool_result(fn_name, fn_args, output, time.perf_counter() - t0)
    return output


__all__ = ["expand_at_mentions", "execute_tool"]
