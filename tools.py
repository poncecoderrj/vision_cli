import os
import re
import html as _html
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    from ddgs import DDGS            # pacote novo (usado só como fallback)
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

import httpx

from ui import (
    console,
    prompt_command_approval,
    prompt_simple_approval,
    prompt_ask_user,
    print_system_message,
    get_mode,
    AgentMode,
)
from rich.markup import escape as _escape
from config import is_whitelisted, add_to_whitelist

# ── Limits & ignore rules ────────────────────────────────────────────────────

MAX_READ_CHARS = 60_000           # protege o contexto do modelo
MAX_GREP_RESULTS = 60
MAX_GLOB_RESULTS = 200
IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".idea", ".mypy_cache", ".pytest_cache", ".next",
}


def _resolve(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _approval_needed() -> bool:
    """File mutations need approval only in ACCEPT mode.
    AUTO = sem perguntar; PLAN = já confirmado no plano."""
    return get_mode() == AgentMode.ACCEPT


def _ask(title: str, detail: str) -> "str | None":
    """Run the approval dialog. Returns None to proceed, or an error/instruction string."""
    if not _approval_needed():
        return None
    decision = prompt_simple_approval(title, detail)
    if decision is True:
        return None
    if isinstance(decision, str):
        return f"Usuário não aprovou e pediu em vez disso: {decision}"
    return "Operação cancelada pelo usuário."


# ── Read-only tools ──────────────────────────────────────────────────────────

def read_file(path: str, offset: int = 0, limit: int = 0) -> str:
    """Read a text file. offset/limit are 1-based line ranges (0 = from start / all)."""
    p = _resolve(path)
    if not p.exists():
        return f"Erro: arquivo não encontrado: {p}"
    if p.is_dir():
        return f"Erro: '{p}' é um diretório. Use list_dir."
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Erro: '{p}' parece ser um arquivo binário (não é texto)."
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"

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
    return f"{header}\n{'─' * 40}\n{chunk}{note}"


def list_dir(path: str = ".") -> str:
    """List the contents of a directory (folders first)."""
    p = _resolve(path)
    if not p.exists():
        return f"Erro: diretório não encontrado: {p}"
    if not p.is_dir():
        return f"Erro: '{p}' não é um diretório."
    try:
        entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except Exception as e:
        return f"Erro ao listar diretório: {e}"

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
    return "\n".join(lines)


def glob_files(pattern: str, path: str = ".") -> str:
    """Find files by glob pattern (ex: '**/*.py', 'src/*.js')."""
    base = _resolve(path)
    if not base.exists():
        return f"Erro: diretório base não encontrado: {base}"
    try:
        matches = [
            m for m in base.glob(pattern)
            if not any(part in IGNORE_DIRS for part in m.parts)
        ]
    except Exception as e:
        return f"Erro no glob: {e}"

    matches = sorted(matches, key=lambda m: m.stat().st_mtime if m.exists() else 0, reverse=True)
    if not matches:
        return f"Nenhum arquivo corresponde a '{pattern}' em {base}."

    shown = matches[:MAX_GLOB_RESULTS]
    out = [str(m) for m in shown]
    if len(matches) > MAX_GLOB_RESULTS:
        out.append(f"... (+{len(matches) - MAX_GLOB_RESULTS} arquivos)")
    return "\n".join(out)


def search_code(pattern: str, path: str = ".", glob: str = "*") -> str:
    """Search file contents by regex. Returns 'file:line: text' matches."""
    base = _resolve(path)
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Erro: regex inválida: {e}"
    if not base.exists():
        return f"Erro: caminho não encontrado: {base}"

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
                            return "\n".join(results)
        except (OSError, UnicodeError):
            continue

    return "\n".join(results) if results else f"Nenhuma ocorrência de '{pattern}'."


_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgenteCLI/1.0"


def _unwrap_ddg(href: str) -> str:
    """DDG às vezes embrulha URLs em /l/?uddg=... — desembrulha."""
    if "uddg=" in href:
        qs = parse_qs(urlparse(href).query)
        if qs.get("uddg"):
            return qs["uddg"][0]
    if href.startswith("//"):
        return "https:" + href
    return href


def _strip_tags(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _search_ddg_html(query: str, max_results: int) -> list[tuple]:
    """Busca confiável via httpx direto no endpoint HTML do DuckDuckGo."""
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
    """Fallback: biblioteca ddgs."""
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


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web. Reliable: scrapes DuckDuckGo HTML via httpx, lib as fallback.

    Dica: para focar uma fonte use 'site:' na query, ex:
      'site:github.com fastapi auth', 'site:stackoverflow.com pandas merge'.
    """
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
        return ("Nenhum resultado encontrado."
                + (f" (erro: {err})" if err else "")
                + "\nDica: tente reformular a query, ou use fetch_url se já tiver a URL.")

    out = []
    for i, (title, url, snippet) in enumerate(results, 1):
        out.append(f"{i}. {title or '(sem título)'}\n   {snippet}\n   {url}")
    return "\n\n".join(out)


def _html_to_text(raw: str) -> str:
    """Lightweight HTML → readable text (no external deps)."""
    raw = re.sub(r"(?is)<(script|style|noscript|svg|head|nav|footer)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/h[1-6]|/li|/tr|/section)\s*/?>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = _html.unescape(raw)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def fetch_url(url: str, max_chars: int = 8000) -> str:
    """Download a web page and return its readable text content."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=20,
                         headers={"User-Agent": _UA})
        resp.raise_for_status()
    except Exception as e:
        return (f"Erro ao buscar URL ({e}). NÃO desista: tente outra URL dos "
                f"resultados, ou faça um novo web_search e abra outro link.")

    ctype = resp.headers.get("content-type", "")
    text = _html_to_text(resp.text) if "html" in ctype else resp.text
    truncated = len(text) > max_chars
    text = text[:max_chars]
    note = "\n\n[... conteúdo truncado ...]" if truncated else ""
    return f"{url}\n{'─' * 40}\n{text}{note}"


def search_github(query: str, kind: str = "repositories", max_results: int = 5) -> str:
    """Search GitHub. kind: 'repositories' (default) or 'code' (requer GITHUB_TOKEN)."""
    kind = kind if kind in ("repositories", "code") else "repositories"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AgenteCLI"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if kind == "code" and not token:
        return ("Busca de código no GitHub exige GITHUB_TOKEN no .env. "
                "Use kind='repositories' ou configure o token.")
    try:
        resp = httpx.get(
            f"https://api.github.com/search/{kind}",
            params={"q": query, "per_page": max_results},
            headers=headers, timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        return f"Erro na busca GitHub: {e}"

    items = resp.json().get("items", [])
    if not items:
        return ("Nenhum resultado no GitHub. Tente termos diferentes/mais simples, "
                "ou use web_search com 'site:github.com ...'.")
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
    return "\n\n".join(out)


# ── Mutating tools (need approval in ACCEPT mode) ────────────────────────────

def write_file(path: str, content: str) -> str:
    """Create a new file or overwrite an existing one."""
    p = _resolve(path)
    exists = p.exists()
    action = "Sobrescrever arquivo" if exists else "Criar arquivo"
    n_lines = content.count("\n") + 1
    detail = f"{p}\n\n{n_lines} linhas · {len(content):,} caracteres"

    blocked = _ask(f"⚠ {action}", detail)
    if blocked:
        return blocked
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"Erro ao escrever arquivo: {e}"
    return f"{'Sobrescrito' if exists else 'Criado'}: {p} ({n_lines} linhas)"


def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Replace an exact string in a file. old_string must be unique unless replace_all."""
    p = _resolve(path)
    if not p.exists():
        return f"Erro: arquivo não encontrado: {p}"
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"

    count = text.count(old_string)
    if count == 0:
        return "Erro: old_string não encontrado no arquivo. Verifique espaços/indentação exatos."
    if count > 1 and not replace_all:
        return (f"Erro: old_string aparece {count}× — não é único. "
                f"Inclua mais contexto ou use replace_all=true.")

    preview_old = (old_string[:120] + "…") if len(old_string) > 120 else old_string
    preview_new = (new_string[:120] + "…") if len(new_string) > 120 else new_string
    detail = f"{p}\n\n- {preview_old}\n+ {preview_new}"
    if replace_all:
        detail += f"\n\n(substituindo {count} ocorrências)"

    blocked = _ask("⚠ Editar arquivo", detail)
    if blocked:
        return blocked

    new_text = text.replace(old_string, new_string) if replace_all \
        else text.replace(old_string, new_string, 1)
    try:
        p.write_text(new_text, encoding="utf-8")
    except Exception as e:
        return f"Erro ao salvar arquivo: {e}"
    n = count if replace_all else 1
    return f"Editado: {p} ({n} substituição{'ões' if n > 1 else ''})"


def delete_file(path: str) -> str:
    """Delete a file (não deleta diretórios)."""
    p = _resolve(path)
    if not p.exists():
        return f"Erro: arquivo não encontrado: {p}"
    if p.is_dir():
        return f"Erro: '{p}' é um diretório. Por segurança, delete diretórios via run_shell explicitamente."

    blocked = _ask("⚠ Deletar arquivo", str(p))
    if blocked:
        return blocked
    try:
        p.unlink()
    except Exception as e:
        return f"Erro ao deletar: {e}"
    return f"Deletado: {p}"


def run_shell(command: str, stdin_input: str = "", timeout: int = 300) -> str:
    """Execute a shell command with live output streaming.

    stdin_input: newline-separated answers for interactive prompts, e.g. "myapp\\nreact\\n".
    timeout: seconds before killing the process (default 300 — enough for npm install).
    """
    if get_mode() == AgentMode.ACCEPT and not is_whitelisted(command):
        choice = prompt_command_approval(command)
        if isinstance(choice, str):
            return f"Usuário não aprovou e pediu em vez disso: {choice}"
        if choice == 3 or choice is None:
            return "User cancelled the execution of this command."
        if choice == 2:
            add_to_whitelist(command)
            print_system_message("Comando adicionado à whitelist permanentemente.")
    elif is_whitelisted(command):
        print_system_message("Comando na whitelist. Executando automaticamente.")

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr → single stream, no deadlock
            cwd=os.getcwd(),
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        return f"Erro ao iniciar comando: {e}"

    # Feed stdin answers (for interactive CLIs that ask questions)
    if stdin_input:
        try:
            answers = stdin_input if stdin_input.endswith("\n") else stdin_input + "\n"
            proc.stdin.write(answers)
            proc.stdin.flush()
        except Exception:
            pass
    try:
        proc.stdin.close()
    except Exception:
        pass

    # Stream each output line to the terminal in real-time
    output_lines: list[str] = []

    def _read():
        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            output_lines.append(line)
            console.print(f"  [grey50]{_escape(line)}[/grey50]")

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        reader.join(timeout=2)
        tail = "\n".join(output_lines[-20:])
        return f"Erro: comando excedeu {timeout}s.\n{tail}"

    reader.join(timeout=5)

    body = "\n".join(output_lines) if output_lines else "(sem saída)"
    return f"exit={proc.returncode}\n{body}"


# ── User decision tool ───────────────────────────────────────────────────────

def ask_user(question: str, options: list) -> str:
    """Present a decision to the user and return their chosen option."""
    if not options or not isinstance(options, list):
        return "Erro: 'options' deve ser uma lista não-vazia de strings."
    choice = prompt_ask_user(question, [str(o) for o in options])
    return f"Usuário escolheu: {choice}"


# ── In-memory task tracker ───────────────────────────────────────────────────

_tasks: list[dict] = []


def manage_tasks(action: str, task_name: str = "") -> str:
    global _tasks
    if action == "add":
        _tasks.append({"name": task_name, "status": "pending"})
        return f"Tarefa adicionada: '{task_name}'."
    if action == "list":
        if not _tasks:
            return "Nenhuma tarefa."
        return "\n".join(
            f"{i+1}. [{'x' if t['status'] == 'completed' else ' '}] {t['name']}"
            for i, t in enumerate(_tasks)
        )
    if action == "complete":
        for t in _tasks:
            if t["name"] == task_name:
                t["status"] = "completed"
                return f"Tarefa concluída: '{task_name}'."
        return f"Tarefa não encontrada: '{task_name}'."
    return "Ação inválida. Use add, list ou complete."


# ── Registry ─────────────────────────────────────────────────────────────────

AVAILABLE_TOOLS = {
    "read_file":     read_file,
    "list_dir":      list_dir,
    "glob_files":    glob_files,
    "search_code":   search_code,
    "web_search":    web_search,
    "fetch_url":     fetch_url,
    "search_github": search_github,
    "write_file":    write_file,
    "edit_file":     edit_file,
    "delete_file":   delete_file,
    "run_shell":     run_shell,
    "manage_tasks":  manage_tasks,
    "ask_user":      ask_user,
}
