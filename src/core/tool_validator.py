"""
ToolValidator: valida tool calls contra o registry, tenta reparo heurístico e por LLM.
"""

import difflib
import json
import re
from typing import Any, Callable, Dict, List, Optional

from src.tools.base import Tool


class ToolValidator:
    def __init__(self, llm_client: Optional[Callable] = None, cwd: str = "."):
        self.llm_client = llm_client
        self.cwd = cwd

    def _heuristic_repair(
        self,
        tool_call: Dict[str, Any],
        tools: Dict[str, Tool],
        last_user_message: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Tenta corrigir argumentos faltantes com heurísticas antes de chamar o LLM."""
        tool_name = tool_call.get("name")
        if not tool_name or tool_name not in tools:
            return None

        tool = tools[tool_name]
        required = tool.parameters.get("required", [])
        args = dict(tool_call.get("arguments") or {})

        for arg in required:
            if args.get(arg) not in (None, ""):
                continue

            if arg == "path":
                path_match = re.search(r'["\']([^"\']+)["\']', last_user_message)
                if path_match:
                    args["path"] = path_match.group(1)
                elif tool_name in ("list_dir", "read_file"):
                    args["path"] = self.cwd
                else:
                    return None

            elif arg == "query":
                if not last_user_message:
                    return None
                clean = re.sub(
                    r'(pesquise|busque|procure|search|find|por|for)\s+',
                    '', last_user_message, flags=re.I
                ).strip()
                args["query"] = clean if clean else last_user_message

            elif arg == "content":
                if not last_user_message:
                    return None
                m = re.search(
                    r'(?:escreva|write|salve|save)\s+["\']?([^"\']+)["\']?',
                    last_user_message, re.I
                )
                args["content"] = m.group(1) if m else None
                if not args["content"]:
                    return None

            else:
                return None

        tool_call = dict(tool_call)
        tool_call["arguments"] = args
        return tool_call

    def validate(self, tool_call: Dict[str, Any], tools: Dict[str, Tool]) -> Dict[str, Any]:
        """Valida se a tool call é executável. Retorna a call ou levanta ValueError."""
        if "name" not in tool_call or "arguments" not in tool_call:
            raise ValueError("Tool call malformada: faltando 'name' ou 'arguments'")

        tool_name = tool_call["name"]
        if tool_name not in tools:
            matches = difflib.get_close_matches(tool_name, tools.keys(), n=1, cutoff=0.6)
            if matches:
                raise ValueError(
                    f"Ferramenta '{tool_name}' não encontrada. Você quis dizer '{matches[0]}'?"
                )
            raise ValueError(f"Ferramenta '{tool_name}' não existe.")

        tool = tools[tool_name]
        required = tool.parameters.get("required", [])
        args = tool_call.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                raise ValueError(f"Argumentos inválidos (não é JSON): {args}")

        missing = [a for a in required if a not in args or args[a] in (None, "")]
        if missing:
            raise ValueError(
                f"Argumentos obrigatórios faltando: {missing}. Recebido: {list(args.keys())}"
            )

        return tool_call

    def repair(
        self,
        tool_call: Dict[str, Any],
        tools: Dict[str, Tool],
        conversation: List[Dict],
        last_user_message: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Tenta reparar: heurística → validação → LLM."""
        # 1. Heurística
        heuristic = self._heuristic_repair(tool_call, tools, last_user_message)
        if heuristic:
            try:
                return self.validate(heuristic, tools)
            except ValueError:
                pass

        # 2. Tentar validar o original (pode já estar OK)
        try:
            return self.validate(tool_call, tools)
        except ValueError as e:
            if not self.llm_client:
                return None

        # 3. LLM repair
        tool_schemas = {
            name: {
                "description": t.description,
                "required": t.parameters.get("required", []),
                "properties": list(t.parameters.get("properties", {}).keys()),
            }
            for name, t in tools.items()
        }

        repair_prompt = (
            f"Corrija esta tool call que falhou com o erro: {e}\n\n"
            f"Tool call original: {json.dumps(tool_call)}\n\n"
            f"Ferramentas disponíveis: {json.dumps(tool_schemas, ensure_ascii=False)}\n\n"
            f"Última mensagem do usuário: {last_user_message}\n\n"
            'Responda APENAS com um JSON válido com "name" e "arguments". '
            'Se não for possível corrigir, responda {"error": "motivo"}.'
        )

        try:
            response = self.llm_client(repair_prompt)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                return None
            repaired = json.loads(json_match.group())
            if "error" in repaired:
                return None
            return self.validate(repaired, tools)
        except Exception:
            return None


__all__ = ["ToolValidator"]
