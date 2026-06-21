"""
FallbackParser: converte texto do usuário em tool calls quando o LLM não gera chamadas.
"""

import re
from typing import Any, Dict, List


class FallbackParser:
    def __init__(self, cwd: str = "."):
        self.cwd = cwd

    def parse(self, user_input: str) -> List[Dict[str, Any]]:
        """Tenta mapear texto livre para uma tool call. Retorna lista (vazia se não reconhecido)."""
        lower = user_input.lower().strip()

        # 1. Leitura de arquivo
        for pattern in (
            r'(?:leia|read|mostre|exiba|cat|abr[ia]r?|open|show me|me mostre|gostaria de ver|dê me|give me)\s+(?:o\s+)?(?:arquivo|file|conteúdo de|content of)?\s*["\']?([^"\']+)["\']?',
            r'(?:conteúdo|content)\s+(?:do|da|de)?\s*["\']?([^"\']+)["\']?',
            r'(?:o que tem no|what is in)\s+(?:arquivo|file)?\s*["\']?([^"\']+)["\']?',
        ):
            m = re.search(pattern, lower)
            if m:
                return [{"name": "read_file", "arguments": {"path": m.group(1).strip()}}]

        # 2. Escrita em arquivo
        m = re.search(
            r'(?:escreva|write|salve|save|crie|create)\s+(.+?)\s+'
            r'(?:no|em|para|no arquivo|em arquivo|in file|no caminho)\s+["\']?([^"\']+)["\']?',
            lower,
        )
        if m:
            return [{"name": "write_file", "arguments": {"path": m.group(2).strip(), "content": m.group(1).strip()}}]

        # 3. Listar diretório
        if re.search(r'(?:liste|list|ls|dir|mostre arquivos|show files|arquivos em|o que tem em|tree|estrutura|listar|contents of)', lower):
            pm = re.search(r'(?:em|in|de|do|da|no|na|pasta|diretório|directory)\s+["\']?([^"\']+)["\']?', lower)
            path = pm.group(1).strip() if pm else self.cwd
            return [{"name": "list_dir", "arguments": {"path": path}}]

        # 4. Comando shell
        m = re.search(r'(?:execute|run|exec|rode|comando|terminal)\s+(.+?)(?:$|,|\.)', lower)
        if m:
            return [{"name": "run_shell", "arguments": {"command": m.group(1).strip()}}]

        # 5. Busca no código
        m = re.search(r'(?:busque|search|procure|find|localize)\s+(?:por|for)?\s+["\']?([^"\']+)["\']?', lower)
        if m:
            return [{"name": "search_code", "arguments": {"query": m.group(1).strip()}}]

        # 6. Web search + fetch
        m = re.search(r'(?:pesquise|web search|busque na web|google|pesquisa na internet|o que é|what is|quem é|who is|pesquisar)\s+["\']?([^"\']+)["\']?', lower)
        if m:
            return [{"name": "web_search_fetch", "arguments": {"query": m.group(1).strip()}}]

        # 7. Explorar projeto
        if re.search(r'(?:explore|explorar|analise|mapeie|investigue)', lower):
            pm = re.search(r'["\']?([^"\']+)["\']?\s*$', lower)
            path = pm.group(1).strip() if pm else self.cwd
            return [{"name": "list_dir", "arguments": {"path": path}}]

        return []


__all__ = ["FallbackParser"]
