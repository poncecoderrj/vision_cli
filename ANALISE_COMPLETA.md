# 📋 Análise Completa do Projeto - Agente CLI

## 1. O Que Entendi

### Visão Geral
Projeto é um **agente de programação autônomo CLI** (estilo Claude CLI/Cursor) que permite LLMs executarem ações reais no sistema via ferramentas controladas.

### Arquitetura Atual
- **6 arquivos Python principais** (~2.2k linhas totais)
- **5 skills templates** em Markdown com wizard interativo
- **3 modos de operação**: ACCEPT (aprovação), PLAN (revisar plano), AUTO (automático)
- **13 ferramentas** registradas: arquivo, navegação, web search, shell, tasks, ask_user

### Fluxo Principal
```
main.py → run_agent_loop() → [get_user_input → _stream_llm → _execute_tool] → loop
```

---

## 2. Estrutura Atual vs. Proposta

### ❌ Estrutura Atual (Plana)
```
/workspace/
├── main.py              (17 linhas) - entry point
├── agent.py             (649 linhas) - loop principal + LLM streaming + skills
├── tools.py             (528 linhas) - TODAS as ferramentas + approval logic
├── ui.py                (807 linhas) - TUDO de UI: rich, prompt_toolkit, prompts
├── session.py           (111 linhas) - persistência de sessões
├── config.py            (29 linhas) - whitelist e config básica
├── input_queue.py       (84 linhas) - captura de input Windows (msvcrt)
├── requirements.txt
├── README.md
└── skills/
    ├── api.md
    ├── debug.md
    ├── react.md
    ├── refactor.md
    └── scraper.md
```

**Problemas:**
- `agent.py` monolítico (649 linhas) mistura: loop, streaming, skills, tool execution
- `tools.py` gigante (528 linhas) com todas as ferramentas em um só arquivo
- `ui.py` enorme (807 linhas) misturando: tema, input box, prompts, stream rendering
- Zero separação por responsabilidade
- Difícil adicionar novas tools sem poluir arquivos gigantes
- Testabilidade quase impossível

---

### ✅ Estrutura Proposta (Modular)

```
/workspace/
├── main.py                          # Entry point (inalterado)
├── requirements.txt
├── README.md
├── .env.example
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                        # Núcleo do agente
│   │   ├── __init__.py
│   │   ├── agent.py                 # Loop principal + coordenação
│   │   ├── llm_client.py            # OpenAI client + streaming
│   │   ├── message_history.py       # Gerenciamento de contexto/mensagens
│   │   └── context_manager.py       # Context window management
│   │
│   ├── tools/                       # Tools modulares
│   │   ├── __init__.py              # Registry das tools
│   │   ├── base.py                  # BaseTool class + decorators
│   │   ├── registry.py              # Tool discovery + schema generation
│   │   │
│   │   ├── file_tools/              # Ferramentas de arquivo
│   │   │   ├── __init__.py
│   │   │   ├── read_file.py
│   │   │   ├── write_file.py
│   │   │   ├── edit_file.py         # + fuzzy match future
│   │   │   └── delete_file.py
│   │   │
│   │   ├── navigation_tools/        # Navegação local
│   │   │   ├── __init__.py
│   │   │   ├── list_dir.py
│   │   │   ├── glob_files.py
│   │   │   └── search_code.py
│   │   │
│   │   ├── web_tools/               # Web search/fetch
│   │   │   ├── __init__.py
│   │   │   ├── web_search.py        # + retry/backoff
│   │   │   ├── fetch_url.py
│   │   │   └── search_github.py
│   │   │
│   │   ├── shell_tools/             # Shell commands
│   │   │   ├── __init__.py
│   │   │   ├── run_shell.py         # + cancelamento
│   │   │   └── process_monitor.py   # Novo: monitorar processos
│   │   │
│   │   └── utility_tools/           # Utils
│   │       ├── __init__.py
│   │       ├── manage_tasks.py
│   │       └── ask_user.py
│   │
│   ├── ui/                          # Interface
│   │   ├── __init__.py
│   │   ├── theme.py                 # Cores, estilos, constants
│   │   ├── console_output.py        # Rich panels, messages, stats
│   │   ├── input_box.py             # Prompt toolkit input
│   │   ├── completers.py            # Auto-complete (@mentions, /commands)
│   │   ├── prompts.py               # Approval dialogs, ask_user, wizards
│   │   ├── stream_renderer.py       # AgentStream class
│   │   └── key_bindings.py          # Atalhos customizados
│   │
│   ├── skills/                      # Skills system
│   │   ├── __init__.py
│   │   ├── loader.py                # Carregar .md files
│   │   ├── parser.py                # Parse QUESTIONS block
│   │   ├── wizard.py                # Interactive wizard
│   │   └── executor.py              # Run skill steps
│   │
│   ├── session/                     # Session management
│   │   ├── __init__.py
│   │   ├── storage.py               # Save/load sessions
│   │   └── metadata.py              # Stats, turns, tokens
│   │
│   ├── config/                      # Configuração
│   │   ├── __init__.py
│   │   ├── settings.py              # Env vars, defaults
│   │   ├── whitelist.py             # Command whitelist
│   │   └── proxy.py                 # Futuro: proxy support
│   │
│   └── utils/                       # Utilitários
│       ├── __init__.py
│       ├── logging_config.py        # Logs estruturados
│       ├── retry.py                 # Retry with backoff
│       ├── text_diff.py             # Diff preview
│       └── vision.py                # Futuro: image support
│
├── tests/                           # Testes unitários
│   ├── __init__.py
│   ├── test_tools/
│   │   ├── test_read_file.py
│   │   ├── test_edit_file.py
│   │   └── ...
│   ├── test_ui/
│   │   ├── test_prompts.py
│   │   └── ...
│   └── conftest.py
│
├── skills/                          # Skill templates (mantido)
│   ├── api.md
│   ├── debug.md
│   ├── react.md
│   ├── refactor.md
│   └── scraper.md
│
└── logs/                            # Logs estruturados (gitignored)
    └── agent.log
```

---

## 3. Melhorias Identificadas (Priorizadas)

### 🔴 Críticas (Segurança/Estabilidade)
1. **Context window management** - Limitar histórico para não estourar tokens
2. **Retry com backoff exponencial** - Resiliência de rede (web_search, fetch_url)
3. **Tratamento de erros específico** - Menos `except Exception` genérico
4. **Cancelamento de shell commands** - Ctrl+C para matar processo em execução

### 🟡 Alta Prioridade (UX/Developer Experience)
5. **Fuzzy match no edit_file** - Não exigir string exata (tolerância a whitespace)
6. **Diff preview antes de editar** - Mostrar diff colorido antes de aprovar
7. **Logs estruturados** - Debugabilidade com níveis (DEBUG, INFO, ERROR)
8. **Testes unitários** - Cobrir tools críticas (read_file, edit_file, run_shell)

### 🟢 Média Prioridade (Features)
9. **Multi-file edit atômico** - Transações: ou tudo aplica ou nada
10. **Suporte a imagens/vision** - Upload e análise de screenshots
11. **Configuração de proxy** - Corporate environments
12. **Skill discovery melhorado** - Listar skills com descrição/tags

---

## 4. Benefícios da Nova Estrutura

### Para Crescimento de Tools
- ✅ Adicionar nova tool = criar 1 arquivo em `tools/<category>/`
- ✅ Auto-discovery via registry
- ✅ Schema generation automático
- ✅ Testes isolados por tool

### Para Manutenção
- ✅ Separação clara de responsabilidades
- ✅ Arquivos menores (<200 linhas cada)
- ✅ Imports explícitos
- ✅ Fácil refatorar sem quebrar tudo

### Para Testabilidade
- ✅ Mock de dependencies (LLM client, file system)
- ✅ Tests unitários por módulo
- ✅ CI/CD ready

### Para Novos Contribuidores
- ✅ Estrutura intuitiva
- ✅ Documentação por módulo
- ✅ Exemplos claros

---

## 5. Plano de Refatoração (Fases)

### Fase 1: Fundação (Sem quebrar nada)
- [ ] Criar estrutura de pastas `src/`
- [ ] Mover `config.py` → `src/config/settings.py` + `whitelist.py`
- [ ] Mover `session.py` → `src/session/storage.py`
- [ ] Mover `input_queue.py` → `src/utils/input_capture.py`
- [ ] Criar `src/tools/base.py` com `BaseTool` class

### Fase 2: Modularizar Tools
- [ ] Extrair file tools para `src/tools/file_tools/`
- [ ] Extrair navigation tools para `src/tools/navigation_tools/`
- [ ] Extrair web tools para `src/tools/web_tools/`
- [ ] Extrair shell tools para `src/tools/shell_tools/`
- [ ] Criar `src/tools/registry.py` com auto-discovery
- [ ] Adicionar retry decorator com backoff

### Fase 3: Modularizar UI
- [ ] Separar theme/constants → `src/ui/theme.py`
- [ ] Separar input box → `src/ui/input_box.py`
- [ ] Separar prompts → `src/ui/prompts.py`
- [ ] Separar stream renderer → `src/ui/stream_renderer.py`
- [ ] Adicionar logs estruturados

### Fase 4: Core Agent
- [ ] Extrair LLM client → `src/core/llm_client.py`
- [ ] Extrair message history → `src/core/message_history.py`
- [ ] Adicionar context window management
- [ ] Melhorar tratamento de erros

### Fase 5: Qualidade
- [ ] Adicionar testes unitários (50%+ coverage)
- [ ] Adicionar diff preview no edit_file
- [ ] Adicionar fuzzy match no edit_file
- [ ] Documentar módulos

---

## 6. Próximos Passos Imediatos

**Quer que eu implemente:**

A) **Refatoração completa** da estrutura de pastas (todas as fases)?
B) **Uma melhoria específica** primeiro (ex: retry, logs, tests)?
C) **Criar apenas a estrutura** vazia para você preencher?
D) **Outra prioridade** que você definir?

---

**Resumo:** Projeto está funcional mas precisa de modularização para escalar. A estrutura proposta segue best practices (separation of concerns, single responsibility) e prepara o terreno para crescimento sustentável.
