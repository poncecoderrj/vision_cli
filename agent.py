import os
import json
import time
import inspect
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tools import AVAILABLE_TOOLS
from session import (
    save_current_session,
    save_named_session,
    load_session,
    list_sessions,
    has_current_session,
)
from ui import (
    console,
    print_header,
    print_user_message,
    get_user_input,
    print_session_stats,
    print_tool_result,
    print_error,
    print_system_message,
    track_tool_call,
    AgentStream,
    AgentMode,
    get_mode,
    prompt_plan_approval,
    run_skill_wizard,
    CORAL, GREEN, GOLD, MUTED, DIMC,
)
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
from rich import box

load_dotenv(override=True)

LM_STUDIO_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
MODEL_NAME    = os.getenv("MODEL_NAME", "gemma-2b-it")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "lm-studio"),
    base_url=LM_STUDIO_URL,
)

SYSTEM_PROMPT = """Você é um agente de programação autônomo rodando localmente no PC do usuário. Você TEM acesso real ao sistema de arquivos e ao terminal.

================================================================================
                    ⚠️  VOCÊ ESTÁ RODANDO NO WINDOWS! ⚠️
================================================================================

ISSO É CRÍTICO - LEIA COM ATENÇÃO:
- Use SEMPRE comandos e sintaxe do Windows (CMD/PowerShell)
- NUNCA use comandos Unix/Linux como `mkdir -p`, `ls`, `cat`, `rm`, `pwd`, etc.
- Para paths, use `%USERPROFILE%` em vez de `~` (ex: `%USERPROFILE%\\Desktop`)
- Use `mkdir` sem flag `-p` (no Windows, mkdir já cria pastas intermediárias)
- Use `dir` em vez de `ls`, `type` ou `more` em vez de `cat`, `del` em vez de `rm`
- Separador de paths é `\\` (backslash), não `/`
- O til `~` NÃO funciona no Windows CMD - use `%USERPROFILE%` ou paths relativos

COMANDOS WINDOWS CORRETOS:
- Criar pasta:    mkdir "%USERPROFILE%\\Desktop\\minha_pasta"  OU  mkdir Desktop\\minha_pasta
- Listar:         dir
- Ler arquivo:    type arquivo.txt  OU  more arquivo.txt
- Deletar:        del arquivo.txt
- Copiar:         copy origem destino
- Mover:          move origem destino
- Mudar dir:      cd caminho
- Path absoluto:  C:\\Users\\SeuNome\\Desktop  OU  %USERPROFILE%\\Desktop

================================================================================
                         🔄 ANÁLISE DE ERROS E PERSISTÊNCIA
================================================================================

QUANDO UM COMANDO FALHAR (exit code != 0) OU FOR CANCELADO:

1. **NUNCA repita o MESMO comando falho** - Isso é inútil e desperdiça tempo
2. **ANALISE o erro** - Leia a mensagem de erro para entender o que deu errado
3. **MUDE A ESTRATÉGIA** - Tente uma abordagem DIFERENTE:

   Exemplo de loop ERRADO (NÃO FAÇA):
   ❌ mkdir -p ~/Desktop/visionsx → erro → tentar de novo → erro → tentar de novo...

   Exemplo de abordagem CORRETA (FAÇA ISSO):
   ✅ mkdir -p ~/Desktop/visionsx → erro "sintaxe incorreta"
   ✅ ANALISOU: "ah, -p e ~ não funcionam no Windows"
   ✅ NOVO COMANDO: mkdir "%USERPROFILE%\Desktop\visionsx"
   ✅ Se ainda falhar, tente: cd %USERPROFILE%\Desktop && mkdir visionsx
   ✅ Se ainda falhar, tente: powershell -Command "New-Item -ItemType Directory -Path '%USERPROFILE%\Desktop\visionsx'"

4. **REGRA DAS 3 TENTATIVAS DIFERENTES**: Antes de dizer "não consegui", você DEVE tentar pelo menos 3 abordagens DIFERENTES para o mesmo problema

5. **SEJA EXPLÍCITO SOBRE O ERRO**: Quando algo falhar, diga ao usuário:
   - O que você tentou
   - Qual foi o erro
   - O que vai tentar agora (comando diferente)

6. **CANCELAMENTO DO USUÁRIO**: Se o usuário cancelar um comando (opção 3):
   - ISSO É UM ERRO CRÍTICO - NÃO REPITA O MESMO COMANDO
   - Analise POR QUE o usuário cancelou
   - Mude completamente de estratégia ou pergunte ao usuário o que fazer
   - Exemplo: se cancelaram "mkdir -p ~/Desktop", tente "mkdir %USERPROFILE%\Desktop" ou pergunte

7. **INSTRUÇÕES ALTERNATIVAS**: Se o usuário der uma instrução alternativa (opção 4):
   - Analise cuidadosamente a sugestão do usuário
   - O usuário está tentando te ajudar a corrigir o erro
   - Use a abordagem sugerida ou adapte-a

================================================================================
                              REGRAS ABSOLUTAS
================================================================================

- NUNCA diga que "não pode acessar o PC" ou "não tem acesso ao sistema". Isso é FALSO — você tem acesso total via ferramentas.
- Use as ferramentas IMEDIATAMENTE quando precisar. Não peça permissão (o sistema cuida disso) e não suponha resultados: execute e descubra.
- Para trabalhar com código, PREFIRA as ferramentas de arquivo (read_file, write_file, edit_file) em vez de run_shell — são mais precisas.
- NUNCA entre em loop repetindo o mesmo comando falho. Se falhou uma vez, mude a abordagem na próxima tentativa.
- Sempre analise a mensagem de erro antes de tentar novamente.
- Se o usuário cancelar um comando, NÃO insista no mesmo comando - mude de estratégia ou pergunte.

FERRAMENTAS DE ARQUIVO:
- `read_file(path, offset?, limit?)` → lê um arquivo de texto (offset/limit em linhas)
- `write_file(path, content)` → cria ou sobrescreve um arquivo
- `edit_file(path, old_string, new_string, replace_all?)` → substitui texto EXATO em um arquivo. old_string deve ser único (copie a indentação exata) ou use replace_all
- `delete_file(path)` → deleta um arquivo

NAVEGAÇÃO E BUSCA LOCAL:
- `list_dir(path)` → lista o conteúdo de um diretório
- `glob_files(pattern, path?)` → encontra arquivos por padrão (ex: '**/*.py')
- `search_code(pattern, path?, glob?)` → busca por regex no conteúdo dos arquivos (grep)

PESQUISA NA WEB:
- `web_search(query, max_results?)` → busca geral. Para focar uma fonte use 'site:' na query (ex: 'site:github.com', 'site:stackoverflow.com', 'site:developer.mozilla.org')
- `fetch_url(url)` → abre uma página e lê o conteúdo completo (use depois do web_search pra ler um resultado a fundo, ou pra ler documentação direto)
- `search_github(query, kind?)` → busca repositórios/código no GitHub (ótimo pra achar exemplos reais e bibliotecas)

ESTRATÉGIA DE PESQUISA:
1. web_search para descobrir links relevantes (ou search_github para código)
2. fetch_url no link mais promissor para ler o conteúdo de verdade
3. Não responda só com base no snippet — abra a fonte quando precisar de detalhe

SISTEMA:
- `run_shell(command, stdin_input?, timeout?)` → executa comandos de terminal com output em tempo real. Use stdin_input para responder prompts interativos (respostas separadas por \n). timeout padrão: 300s.
- `manage_tasks(action, task_name)` → controla uma lista de tarefas para trabalhos longos

PADRÕES DE SHELL (Windows - evite prompts interativos):
- Vite (React/Vue/Svelte):   npm create vite@latest NOME -- --template react
  Variantes de template: react · react-ts · vue · vue-ts · svelte · svelte-ts · vanilla · vanilla-ts
- Next.js:                   npx create-next-app@latest NOME --typescript --tailwind --app --eslint --src-dir
- Instalar deps:             cd NOME && npm install          (pode demorar 1-3 min — o timeout aguenta)
- Criar pasta no Windows:    
  · Opção 1: mkdir "%USERPROFILE%\Desktop\visionsx"
  · Opção 2: mkdir Desktop\visionsx  (se já estiver em %USERPROFILE%)
  · Opção 3: powershell -Command "New-Item -ItemType Directory -Path '%USERPROFILE%\Desktop\visionsx'"
- Listar arquivos:           dir
- Ler arquivo:               type arquivo.txt ou more arquivo.txt
- Deletar arquivo:           del arquivo.txt
- Copiar arquivo:            copy origem destino
- Mover arquivo:             move origem destino
- Se um scaffolder pedir respostas interativas que não têm flag, use stdin_input:
  Exemplo: run_shell("npm create vite@latest", stdin_input="meu-app\n\nreact\nJavaScript\n")
  A ordem das perguntas típica do Vite: nome-do-projeto → framework → variante
- Para inicializar git: git init && git add . && git commit -m "init"

================================================================================
                      FLUXO RECOMENDADO ao editar código
================================================================================

1. Use search_code/glob_files para localizar o que importa
2. Use read_file para entender o conteúdo exato antes de editar
3. Use edit_file (preciso) ou write_file (arquivo novo)
4. Rode testes/comandos com run_shell quando fizer sentido

================================================================================
                         DECISÕES (quando precisar escolher)
================================================================================

- Se precisar decidir entre opções (stack, arquitetura, biblioteca, abordagem, plano) e não puder decidir sozinho, use ask_user(question, options) para apresentar as opções ao usuário.
- Nunca suponha a preferência do usuário — pergunte com ask_user.
- Após receber a resposta, siga a opção escolhida sem questionar.
- Exemplo: ask_user("Qual stack de frontend usar?", ["React + Vite", "Vue 3 + Nuxt", "Next.js"])

================================================================================
                    FRANQUEZA (regra inviolável)
================================================================================

- SEMPRE relate o que realmente aconteceu. O resultado de cada ferramenta é a verdade.
- NUNCA invente resultados, conteúdo de páginas, ou diga que criou/editou um arquivo se a ferramenta retornou erro.
- Se uma ferramenta retornou erro ou veio vazia, DIGA isso claramente ao usuário e explique o que vai tentar em seguida.
- Se você não conseguiu, admita. Mentir ou fingir sucesso é o pior erro possível.

================================================================================
                    PERSISTÊNCIA INTELIGENTE (não desista, mas não repita!)
================================================================================

- Se uma ferramenta falhar ou voltar vazia, NÃO pare — tente outro caminho com OUTRA chamada de ferramenta:
  · web_search vazio → reformule a query (termos diferentes, em inglês, mais específico), tente 'site:...', ou use search_github
  · fetch_url falhou/vazio → tente outra URL dos resultados, ou faça novo web_search e abra outro link
  · edit_file falhou (string não única / não encontrada) → read_file de novo para pegar o texto exato e tente outra vez
  · run_shell deu erro → leia o stderr, ENTENDA O ERRO, ajuste o comando para algo DIFERENTE e rode de novo

- ⚠️  NUNCA repita o mesmo comando exato após falhar. Isso é perda de tempo.
- Faça várias tentativas com abordagens DIFERENTES ANTES de dizer que não foi possível.
- Só conclua "não consegui" depois de esgotar alternativas reais — e aí explique o que tentou.

================================================================================
                                 SEJA DIRETO
================================================================================

Seja direto e objetivo. Quebre tarefas grandes com manage_tasks.

================================================================================
                         🔄 TROCA DE MODELOS LOCAIS
================================================================================

O usuário pode estar rodando múltiplos modelos locais (LM Studio, Ollama, etc.).
Se o usuário mencionar problemas de conexão ou quiser trocar de modelo:

- Verifique a URL em LM_STUDIO_URL (padrão: http://localhost:1234/v1)
- Outros modelos podem rodar em portas diferentes:
  · LM Studio:       http://localhost:1234/v1
  · Ollama:          http://localhost:11434/v1
  · text-generation-webui: http://localhost:5000/v1
  · LocalAI:         http://localhost:8080/v1

- Se o usuário quiser trocar, ele pode modificar a variável de ambiente OPENAI_BASE_URL
- Sugira ao usuário verificar qual modelo está ativo e em qual porta
"""

def _fn(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


tools_schema = [
    _fn(
        "read_file",
        "Read the contents of a text file. Use before editing to see exact content.",
        {
            "path":   {"type": "string", "description": "Path to the file."},
            "offset": {"type": "integer", "description": "Optional 1-based start line."},
            "limit":  {"type": "integer", "description": "Optional number of lines to read."},
        },
        ["path"],
    ),
    _fn(
        "write_file",
        "Create a new file or overwrite an existing one with the given content.",
        {
            "path":    {"type": "string", "description": "Path to the file."},
            "content": {"type": "string", "description": "Full content to write."},
        },
        ["path", "content"],
    ),
    _fn(
        "edit_file",
        "Replace an exact string in a file. old_string must match exactly (including indentation) and be unique unless replace_all is true.",
        {
            "path":        {"type": "string", "description": "Path to the file."},
            "old_string":  {"type": "string", "description": "Exact text to find."},
            "new_string":  {"type": "string", "description": "Text to replace it with."},
            "replace_all": {"type": "boolean", "description": "Replace all occurrences (default false)."},
        },
        ["path", "old_string", "new_string"],
    ),
    _fn(
        "delete_file",
        "Delete a single file (not directories).",
        {"path": {"type": "string", "description": "Path to the file to delete."}},
        ["path"],
    ),
    _fn(
        "list_dir",
        "List the contents of a directory (folders first).",
        {"path": {"type": "string", "description": "Directory path (default: current)."}},
        [],
    ),
    _fn(
        "glob_files",
        "Find files matching a glob pattern, e.g. '**/*.py' or 'src/*.js'.",
        {
            "pattern": {"type": "string", "description": "Glob pattern."},
            "path":    {"type": "string", "description": "Base directory (default: current)."},
        },
        ["pattern"],
    ),
    _fn(
        "search_code",
        "Search file contents by regular expression (like grep). Returns file:line: matches.",
        {
            "pattern": {"type": "string", "description": "Regex pattern to search for."},
            "path":    {"type": "string", "description": "Base directory or file (default: current)."},
            "glob":    {"type": "string", "description": "Filter files, e.g. '*.py' (default: all)."},
        },
        ["pattern"],
    ),
    _fn(
        "web_search",
        "Search the web for snippets (titles + short summaries). RETURNS ONLY SNIPPETS - NOT FULL CONTENT! For detailed info, you MUST call fetch_url(url) on each result. Tip: use 'site:' to target sources.",
        {
            "query":       {"type": "string", "description": "The search query."},
            "max_results": {"type": "integer", "description": "Max results (default 5)."},
        },
        ["query"],
    ),
    _fn(
        "fetch_url",
        "MAIN TOOL for reading web content. ALWAYS use this AFTER web_search to get full article/tutorial/documentation text. web_search only gives snippets - fetch_url gives complete content. Call this multiple times for different URLs.",
        {
            "url":       {"type": "string", "description": "The URL to fetch."},
            "max_chars": {"type": "integer", "description": "Max characters to return (default 8000)."},
        },
        ["url"],
    ),
    _fn(
        "search_github",
        "Search GitHub for repositories (or code). Great for finding real code examples and libraries.",
        {
            "query":       {"type": "string", "description": "Search query, e.g. 'react ecommerce template'."},
            "kind":        {"type": "string", "enum": ["repositories", "code"], "description": "What to search (default repositories)."},
            "max_results": {"type": "integer", "description": "Max results (default 5)."},
        },
        ["query"],
    ),
    _fn(
        "run_shell",
        "Execute a shell command with live output streaming. Use stdin_input to pre-fill interactive prompts (newline-separated answers). timeout in seconds (default 300).",
        {
            "command":     {"type": "string",  "description": "The command to execute."},
            "stdin_input": {"type": "string",  "description": "Newline-separated answers for interactive prompts, e.g. 'myapp\\nreact\\nJavaScript\\n'."},
            "timeout":     {"type": "integer", "description": "Seconds before killing the process (default 300)."},
        },
        ["command"],
    ),
    _fn(
        "manage_tasks",
        "Track a todo list for long, multi-step goals.",
        {
            "action":    {"type": "string", "enum": ["add", "list", "complete"]},
            "task_name": {"type": "string", "description": "Required for add/complete."},
        },
        ["action"],
    ),
    _fn(
        "ask_user",
        "Ask the user to choose between options when a decision is needed — e.g., which stack, approach, architecture, or plan to follow. Always use this instead of guessing or assuming.",
        {
            "question": {"type": "string", "description": "The decision question to present to the user."},
            "options":  {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of 2–5 options for the user to choose from.",
            },
        },
        ["question", "options"],
    ),
]


def _split_think(raw: str) -> tuple[str, str]:
    """Split reasoning wrapped in <think>…</think> from the visible answer."""
    if "<think>" not in raw:
        return "", raw
    before, after = raw.split("<think>", 1)
    if "</think>" in after:
        reasoning, tail = after.split("</think>", 1)
        return reasoning, (before + tail)
    return after, before  # ainda pensando: resposta é só o que veio antes da tag


def _stream_llm(messages: list, stream: AgentStream) -> tuple[str, dict, object]:
    """Stream one LLM response. Returns (answer_text, tool_calls_by_index, usage)."""
    # Strip internal markers before sending to the API
    api_messages = [{k: v for k, v in m.items() if k != "_skill"} for m in messages]

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=api_messages,
            tools=tools_schema,
            tool_choice="auto",
            stream=True,
            stream_options={"include_usage": True},
        )
    except Exception as e:
        print_error(f"Erro ao conectar: {e}\nURL: {LM_STUDIO_URL}")
        return "", {}, None

    raw_content   = ""   # tudo que vem em delta.content (pode conter <think>)
    reasoning_acc = ""   # reasoning vindo de campo dedicado (reasoning_content)
    answer        = ""
    tool_calls_acc: dict[int, dict] = {}
    usage = None

    try:
        for chunk in response:
            if not chunk.choices:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                continue

            delta = chunk.choices[0].delta

            # 1) Reasoning em campo dedicado (DeepSeek / LM Studio: reasoning_content)
            rc = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if rc:
                reasoning_acc += rc

            # 2) Conteúdo normal — pode embutir <think>…</think>
            if delta.content:
                raw_content += delta.content

            # Deriva reasoning/answer a partir do estado completo (robusto a tags partidas)
            think_part, answer = _split_think(raw_content)
            combined_reasoning = reasoning_acc + think_part
            if combined_reasoning:
                stream.set_reasoning(combined_reasoning)
            stream.set_answer(answer)

            # 3) Tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_acc[idx]["name"] += tc.function.name
                            stream.add_tool_pending(tc.function.name)
                        if tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

            if getattr(chunk, "usage", None):
                usage = chunk.usage

    except Exception as e:
        print_error(f"Erro no streaming: {e}")

    if usage:
        stream.set_usage(usage.prompt_tokens, usage.completion_tokens)

    return answer, tool_calls_acc, usage


# ── Skills ───────────────────────────────────────────────────────────────────

_SKILLS_DIR = Path(__file__).parent / "skills"


def _list_skills() -> dict[str, Path]:
    """Return {name: path} for every .md in the skills/ folder."""
    if not _SKILLS_DIR.exists():
        return {}
    return {p.stem: p for p in sorted(_SKILLS_DIR.glob("*.md"))}


def _load_skill(name: str) -> str | None:
    """Load a skill file by name (without .md). Returns content or None."""
    skills = _list_skills()
    if name in skills:
        return skills[name].read_text(encoding="utf-8")
    return None


def _parse_skill_questions(content: str) -> list[dict]:
    """Parse <!-- QUESTIONS [...] --> block from skill markdown. Returns list of question dicts."""
    import re as _re
    m = _re.search(r'<!--\s*QUESTIONS\s*\n(.*?)\n-->', content, _re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(1).strip())
    except Exception:
        return []


def _print_skills_panel(detail: bool = False):
    skills = _list_skills()
    if not skills:
        console.print(f"  [{MUTED}]Nenhuma skill encontrada em skills/[/{MUTED}]")
        return

    console.print()
    rows = []
    for name, path in skills.items():
        content = path.read_text(encoding="utf-8")
        title = content.split("\n")[0].lstrip("# ").strip()
        questions = _parse_skill_questions(content)
        q_count = f"  [{DIMC}]{len(questions)} perguntas[/{DIMC}]" if questions else ""
        rows.append(f"  [{GOLD}]/{name:<14}[/{GOLD}] [white]{escape(title)}[/white]{q_count}")

        if detail and questions:
            for q in questions:
                ask = q.get("ask", "")[:60]
                opts = q.get("options", [])
                opt_preview = "  ·  " + " / ".join(str(o) for o in opts[:3]) if opts else ""
                if len(opts) > 3:
                    opt_preview += f" (+{len(opts)-3})"
                rows.append(f"    [{DIMC}]→ {escape(ask)}{escape(opt_preview)}[/{DIMC}]")

    console.print(Panel(
        "\n".join(rows),
        title=f"[bold {GOLD}]◈ skills disponíveis[/bold {GOLD}]",
        title_align="left",
        box=box.ROUNDED, border_style=GOLD, padding=(1, 2),
    ))
    console.print(
        f"  [{DIMC}]/nome-da-skill  ativa a skill com wizard de configuração"
        f"   ·   /  ou  /skills  mostra esta lista[/{DIMC}]"
    )
    console.print()


def _print_skill_activated(name: str, title_line: str):
    console.print()
    console.print(Panel(
        f"[bold white]{escape(title_line)}[/bold white]\n"
        f"  [{MUTED}]roteiro carregado — o agente vai seguir os passos definidos[/{MUTED}]",
        title=f"[bold {GREEN}]✓ skill ativada: /{name}[/bold {GREEN}]",
        title_align="left",
        box=box.ROUNDED, border_style=GREEN, padding=(0, 2),
    ))
    console.print()


def _handle_slash_command(cmd: str, rest: str, messages: list) -> "tuple[bool, str]":
    """Handle /command input. Returns (consumed, effective_user_msg).
    consumed=True means skip LLM for this turn. effective_user_msg is the message to use."""
    name = cmd.lstrip("/").lower().strip()

    # "/" alone or "/skills" → list panel
    if name in ("", "skills", "help", "ajuda"):
        _print_skills_panel(detail=True)
        return True, ""

    if name in ("clear", "limpar", "reset"):
        del messages[1:]
        print_system_message("Conversa resetada. Skill desativada.")
        return True, ""

    # ── /resume ───────────────────────────────────────────────────────────────
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

        turns   = data.get("turns", "?")
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

    # ── /save ─────────────────────────────────────────────────────────────────
    if name in ("save", "salvar"):
        save_name = rest.strip()
        if not save_name:
            print_system_message("Uso: /save nome-da-sessao")
            return True, ""
        path = save_named_session(messages, save_name, MODEL_NAME, LM_STUDIO_URL)
        print_system_message(f"Sessão salva: {path}")
        return True, ""

    skill_content = _load_skill(name)
    if skill_content:
        title_line = skill_content.split("\n")[0].lstrip("# ").strip()
        _print_skill_activated(name, title_line)

        # Run structured wizard if the skill has questions
        questions = _parse_skill_questions(skill_content)
        config_block = ""
        if questions:
            answers = run_skill_wizard(questions, skill_name=name)
            lines = [f"  {k}: {v}" for k, v in answers.items()]
            config_block = (
                "\n\nCONFIGURAÇÕES ESCOLHIDAS PELO USUÁRIO (use exatamente estas):\n"
                + "\n".join(lines)
                + "\n\nAgora execute os passos da skill com essas configurações."
            )

        # Remove any previously injected skill message and insert new one
        messages[:] = [m for m in messages if not m.get("_skill")]
        messages.insert(1, {
            "role": "system",
            "content": f"SKILL ATIVA — siga o roteiro abaixo à risca:\n\n{skill_content}{config_block}",
            "_skill": True,
        })

        if rest.strip():
            return False, rest   # "/react cria um app de tarefas" → pass rest to LLM
        if config_block:
            # Wizard collected everything — kick off execution immediately
            return False, "Execute agora seguindo o roteiro da skill com as configurações acima."
        return True, ""

    # Unknown slash command — let LLM handle naturally
    return False, cmd + (" " + rest if rest else "")


def _execute_tool(tc: dict) -> str:
    """Execute a single tool call with generic argument validation.
    
    Uses inspect.signature to validate required arguments for ALL tools,
    not just edit_file. Catches all exceptions for better error reporting.
    """
    fn_name = tc["name"]
    try:
        fn_args = json.loads(tc["arguments"]) if tc["arguments"].strip() else {}
    except json.JSONDecodeError:
        fn_args = {}

    fn = AVAILABLE_TOOLS.get(fn_name)
    if fn is None:
        return f"Tool '{fn_name}' não encontrada."

    # Validação genérica via inspect.signature para TODAS as tools
    try:
        sig = inspect.signature(fn)
        required_args = []
        for param_name, param in sig.parameters.items():
            # Parâmetro é obrigatório se não tem default e não é *args/**kwargs
            if (param.default == inspect.Parameter.empty and 
                param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)):
                required_args.append(param_name)
        
        # Verificar argumentos faltando ou vazios
        missing = [arg for arg in required_args if arg not in fn_args or fn_args[arg] == ""]
        if missing:
            return f"Erro: {fn_name} requer argumentos: {', '.join(required_args)}. Faltando: {', '.join(missing)}"
    except Exception as e:
        # Se não conseguir inspecionar, continua sem validação (fallback)
        print_system_message(f"Aviso: não foi possível validar argumentos de {fn_name}: {e}")

    track_tool_call()
    t0 = time.perf_counter()
    try:
        result = fn(**fn_args)
    except TypeError as e:
        error_msg = f"Erro de argumentos em {fn_name}: {e}"
        print_error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Erro ao executar {fn_name}: {type(e).__name__}: {e}"
        print_error(error_msg)
        return error_msg
    
    duration = time.perf_counter() - t0
    print_tool_result(fn_name, fn_args, str(result), duration)
    return str(result)


def run_agent_loop():
    print_header(MODEL_NAME, LM_STUDIO_URL)

    # ── Session resume hint ──────────────────────────────────────────────────
    if has_current_session():
        console.print(
            f"  [{GOLD}]◈[/{GOLD}]  [{MUTED}]Sessão anterior encontrada  ·  [/{MUTED}]"
            f"[{GOLD}]/resume[/{GOLD}] [{MUTED}]para continuar  ·  [/{MUTED}]"
            f"[{GOLD}]/resume lista[/{GOLD}] [{MUTED}]para ver todas[/{MUTED}]"
        )
        console.print()

    skills = _list_skills()
    if skills:
        names = "  ".join(f"[{GOLD}]/{n}[/{GOLD}]" for n in skills)
        console.print(f"  [{MUTED}]skills:[/{MUTED}]  {names}")
        console.print(f"  [{DIMC}]/skills para ver detalhes[/{DIMC}]")
        console.print()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    _input_queue: list[str] = []   # messages queued while AI was streaming

    while True:
        # ── Pull from queue first, else prompt user ──────────────────────────
        if _input_queue:
            user_msg = _input_queue.pop(0)
            remaining = len(_input_queue)
            suffix = f" ({remaining} restante{'s' if remaining != 1 else ''} na fila)" if remaining else ""
            print_system_message(f"Processando mensagem da fila{suffix}...")
            print_user_message(user_msg)
        else:
            user_msg = get_user_input()

        if user_msg.strip().lower() in {"exit", "quit", "sair", "q"}:
            print_session_stats()
            break
        if not user_msg.strip():
            continue

        # ── Slash command detection ──────────────────────────────────────────
        stripped = user_msg.strip()
        if stripped.startswith("/"):
            parts = stripped.split(None, 1)
            cmd  = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            consumed, effective = _handle_slash_command(cmd, rest, messages)
            if consumed:
                continue
            user_msg = effective if effective else user_msg

        print_user_message(user_msg)
        messages.append({"role": "user", "content": user_msg})

        while True:  # tool-call loop
            # ── Stream LLM response ─────────────────────────────────────────
            with AgentStream() as stream:
                text, tool_calls, usage = _stream_llm(messages, stream)
            # Collect any messages typed while the AI was streaming
            _input_queue.extend(stream.get_queued_inputs())

            # Build assistant message for history
            assistant_msg: dict = {"role": "assistant", "content": text or None}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls.values()
                ]
            messages.append(assistant_msg)

            if not tool_calls:
                save_current_session(messages, MODEL_NAME, LM_STUDIO_URL)
                break

            # ── Mode: PLAN — confirm before executing ───────────────────────
            if get_mode() == AgentMode.PLAN:
                if not prompt_plan_approval(tool_calls):
                    messages.append({
                        "role": "user",
                        "content": "O usuário revisou o plano e decidiu não executar. Pergunte o que ele prefere fazer.",
                    })
                    break

            # ── Execute tool calls ───────────────────────────────────────────
            for tc in tool_calls.values():
                result = _execute_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
