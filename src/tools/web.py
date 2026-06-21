"""
Web tools: web_search, fetch_url, search_github.
"""

import os
import re
import html as _html
from urllib.parse import urlparse, parse_qs

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

import httpx

from .base import Tool, ToolResult

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgenteCLI/1.0"


def _unwrap_ddg(href: str) -> str:
    if "uddg=" in href:
        qs = parse_qs(urlparse(href).query)
        if qs.get("uddg"):
            return qs["uddg"][0]
    if href.startswith("//"):
        return "https:" + href
    return href


def _strip_tags(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|head|nav|footer)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/h[1-6]|/li|/tr|/section)\s*/?>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = _html.unescape(raw)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _search_ddg_html(query: str, max_results: int) -> list[tuple]:
    resp = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={"User-Agent": _UA},
        timeout=20,
        follow_redirects=True,
    )
    resp.raise_for_status()
    page = resp.text
    anchors = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
    out = []
    for i, (href, title) in enumerate(anchors[:max_results]):
        snippet = _strip_tags(snippets[i]) if i < len(snippets) else ""
        out.append((_strip_tags(title), _unwrap_ddg(href), snippet[:280]))
    return out


def _search_ddgs_lib(query: str, max_results: int) -> list[tuple]:
    if DDGS is None:
        return []
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception:
        return []
    return [
        (r.get("title", ""), r.get("href", ""), (r.get("body") or "")[:280])
        for r in (results or [])
    ]


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web for snippets (titles + short summaries). "
        "RETURNS ONLY SNIPPETS - NOT FULL CONTENT! For detailed info, you MUST call "
        "fetch_url(url) on each result. Tip: use 'site:' to target sources."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query":       {"type": "string",  "description": "The search query."},
            "max_results": {"type": "integer", "description": "Max results (default 5)."},
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        max_results = int(max_results) if str(max_results).isdigit() else 5
        results: list[tuple] = []
        err = None
        for fn in (_search_ddg_html, _search_ddgs_lib):
            try:
                results = fn(query, max_results)
            except Exception as e:
                err = e
                results = []
            if results:
                break

        if not results:
            msg = ("Nenhum resultado encontrado."
                   + (f" (erro: {err})" if err else "")
                   + "\nDica: tente reformular a query, ou use fetch_url se já tiver a URL.")
            return ToolResult(success=True, output=msg)

        out = []
        for i, (title, url, snippet) in enumerate(results, 1):
            out.append(f"{i}. {title or '(sem título)'}\n   {snippet}\n   {url}")
        out.append(
            "\n⚠️ IMPORTANTE: Os resultados acima são APENAS snippets. "
            "Para obter informação detalhada, use fetch_url(url) em cada link relevante."
        )
        return ToolResult(success=True, output="\n\n".join(out))


class FetchUrlTool(Tool):
    name = "fetch_url"
    description = (
        "MAIN TOOL for reading web content. ALWAYS use this AFTER web_search to get full "
        "article/tutorial/documentation text. web_search only gives snippets - fetch_url gives "
        "complete content. Call this multiple times for different URLs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url":       {"type": "string",  "description": "The URL to fetch."},
            "max_chars": {"type": "integer", "description": "Max characters to return (default 8000)."},
        },
        "required": ["url"],
    }

    def execute(self, url: str, max_chars: int = 8000) -> ToolResult:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=20,
                             headers={"User-Agent": _UA})
            resp.raise_for_status()
        except Exception as e:
            msg = (f"Erro ao buscar URL ({e}). NÃO desista: tente outra URL dos "
                   f"resultados, ou faça um novo web_search e abra outro link.")
            return ToolResult(success=False, output=msg, error=str(e))

        ctype = resp.headers.get("content-type", "")
        text = _html_to_text(resp.text) if "html" in ctype else resp.text
        truncated = len(text) > max_chars
        text = text[:max_chars]
        note = "\n\n[... conteúdo truncado ...]" if truncated else ""
        output = f"{url}\n{'─' * 40}\n{text}{note}"
        return ToolResult(success=True, output=output)


class SearchGithubTool(Tool):
    name = "search_github"
    description = (
        "Search GitHub for repositories (or code). "
        "Great for finding real code examples and libraries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query":       {"type": "string", "description": "Search query, e.g. 'react ecommerce template'."},
            "kind":        {"type": "string", "enum": ["repositories", "code"],
                            "description": "What to search (default repositories)."},
            "max_results": {"type": "integer", "description": "Max results (default 5)."},
        },
        "required": ["query"],
    }

    def execute(self, query: str, kind: str = "repositories", max_results: int = 5) -> ToolResult:
        kind = kind if kind in ("repositories", "code") else "repositories"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "AgenteCLI"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if kind == "code" and not token:
            msg = ("Busca de código no GitHub exige GITHUB_TOKEN no .env. "
                   "Use kind='repositories' ou configure o token.")
            return ToolResult(success=False, output=msg, error=msg)
        try:
            resp = httpx.get(
                f"https://api.github.com/search/{kind}",
                params={"q": query, "per_page": max_results},
                headers=headers, timeout=20,
            )
            resp.raise_for_status()
        except Exception as e:
            msg = f"Erro na busca GitHub: {e}"
            return ToolResult(success=False, output=msg, error=str(e))

        items = resp.json().get("items", [])
        if not items:
            msg = ("Nenhum resultado no GitHub. Tente termos diferentes/mais simples, "
                   "ou use web_search com 'site:github.com ...'.")
            return ToolResult(success=True, output=msg)
        out = []
        for it in items:
            if kind == "repositories":
                desc = (it.get("description") or "")[:160]
                out.append(
                    f"⭐ {it.get('stargazers_count', 0):,}  {it.get('full_name')}"
                    f"  [{it.get('language') or '-'}]\n   {desc}\n   {it.get('html_url')}"
                )
            else:
                repo = it.get("repository", {}).get("full_name", "")
                out.append(f"{it.get('path')}  ({repo})\n   {it.get('html_url')}")
        return ToolResult(success=True, output="\n\n".join(out))


class WebSearchFetchTool(Tool):
    name = "web_search_fetch"
    description = (
        "Busca na web E busca o conteúdo completo dos top resultados automaticamente. "
        "Use quando precisar de informação detalhada sem chamar fetch_url manualmente. "
        "Retorna conteúdo extraído de cada página (até 2000 chars por resultado)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query":       {"type": "string",  "description": "A query de busca."},
            "max_results": {"type": "integer", "description": "Número de resultados a buscar (default 3)."},
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 3) -> ToolResult:
        max_results = min(int(max_results) if str(max_results).isdigit() else 3, 5)
        results: list[tuple] = []
        for fn in (_search_ddg_html, _search_ddgs_lib):
            try:
                results = fn(query, max_results)
            except Exception:
                results = []
            if results:
                break

        if not results:
            return ToolResult(success=False, error="Nenhum resultado encontrado para a query.")

        combined = f"## Resultados para: {query}\n\n"
        for i, (title, url, snippet) in enumerate(results, 1):
            combined += f"### {i}. {title or '(sem título)'}\nFonte: {url}\n\n"
            try:
                resp = httpx.get(url, follow_redirects=True, timeout=15,
                                 headers={"User-Agent": _UA})
                if resp.status_code == 200:
                    text = _html_to_text(resp.text)
                    text = text[:2000] + "..." if len(text) > 2000 else text
                    combined += f"**Conteúdo:**\n{text}\n\n"
                else:
                    combined += f"*(status {resp.status_code} — snippet:)*\n{snippet}\n\n"
            except Exception as e:
                combined += f"*(Erro ao buscar: {e} — snippet:)*\n{snippet}\n\n"

        return ToolResult(success=True, output=combined)


__all__ = ["WebSearchTool", "FetchUrlTool", "SearchGithubTool", "WebSearchFetchTool"]
