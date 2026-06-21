# 🔍 ANÁLISE PROFUNDA DO CÓDIGO - Vision CLI Agent

## 📊 VISÃO GERAL DO PROJETO

**Total de arquivos Python:** 29  
**Arquivos principais (root):** 7 (main.py, agent.py, tools.py, ui.py, config.py, session.py, input_queue.py)  
**Arquivos em src/:** 22 (organizados em módulos)  
**Linhas de código totais:** ~3.500+ LOC

---

## 🚨 PROBLEMAS CRÍTICOS ENCONTRADOS

### 1. **DUPLICAÇÃO DE CÓDIGO MASSIVA** ⚠️⚠️⚠️

**Problema:** O projeto tem DUAS implementações completas das mesmas tools:

#### A. Tools na raiz (`tools.py` - 554 linhas):
- `read_file()`, `write_file()`, `edit_file()`, `delete_file()`
- `list_dir()`, `glob_files()`, `search_code()`
- `web_search()`, `fetch_url()`, `search_github()`
- `run_shell()`, `manage_tasks()`

#### B. Tools em `src/tools/` (módulos separados):
- `src/tools/file_tools/__init__.py`: `ReadFileTool`, `WriteFileTool`, `EditFileTool`, `DeleteFileTool`
- `src/tools/web_tools/`: `WebSearchTool`, `GitHubSearchTool`
- `src/tools/shell_tools/`: `RunShellTool`
- `src/tools/navigation_tools/`: (vazio)

**Impacto:**
- Código duplicado = 2x manutenção
- Risco de inconsistência (bugs corrigidos em um lugar, não no outro)
- Confusão sobre qual implementação usar
- **O `agent.py` usa as funções de `tools.py` da raiz, ignorando completamente a estrutura em `src/`**

**Solução Recomendada:**
```python
# REMOVER: tools.py da raiz (ou mover para src/)
# CONSOLIDAR: Toda lógica em src/tools/ com classes bem definidas
# IMPORTAR: from src.tools import ToolsRegistry
```

---

### 2. **MONOLITO NO `agent.py`** ⚠️⚠️

**Problema:** `agent.py` tem **659 linhas** com responsabilidades misturadas:
- Definição de schema de tools (linhas 120-253)
- Streaming do LLM (linhas 267-340)
- Skills system (linhas 348-420)
- Slash commands (linhas 424-534)
- Execução de tools (linhas 536-565)
- Loop principal (linhas 566-659)

**Violações de SRP (Single Responsibility Principle):**
```python
# Mistura no mesmo arquivo:
- Configuração do cliente OpenAI
- System prompt hardcoded (98 linhas!)
- Parsing de <think> tags
- Gerenciamento de skills (.md files)
- Execução de tools
- UI calls (print_error, print_tool_result)
```

**Solução Recomendada:**
```
agent.py → src/core/agent.py (orquestração apenas)
├── src/core/llm_client.py (streaming, client OpenAI)
├── src/core/tool_executor.py (_execute_tool)
├── src/core/skill_manager.py (skills .md)
└── src/core/prompt_builder.py (system prompt)
```

---

### 3. **SYSTEM PROMPT HARDCODED** ⚠️

**Problema:** 98 linhas de system prompt hardcoded no `agent.py` (linhas 47-118):

```python
SYSTEM_PROMPT = """Você é um agente de programação autônomo...
[98 linhas de texto]
"""
```

**Riscos:**
- Difícil de manter e versionar
- Não pode ser customizado sem editar código
- Sem validação de sintaxe
- Mistura configuração com lógica

**Solução Recomendada:**
```python
# Mover para arquivo separado
src/prompts/system_prompt.md ou .txt
# OU
src/config/prompts.py com templates

# Carregar dinamicamente
def load_system_prompt() -> str:
    return (Path(__file__).parent / "prompts" / "system.txt").read_text()
```

---

### 4. **VALIDAÇÃO FRÁGIL DE ARGUMENTOS** ⚠️⚠️

**Problema identificado no erro reportado:**
```python
TypeError: edit_file() missing 1 required positional argument: 'old_string'
```

**Causa raiz:** No `agent.py`, linha 540-542:
```python
try:
    fn_args = json.loads(tc["arguments"]) if tc["arguments"].strip() else {}
except json.JSONDecodeError:
    fn_args = {}  # ← Dicionário vazio se JSON inválido!
```

Se o LLM retorna argumentos malformados ou incompletos, o código tenta chamar a função com args faltantes.

**Validação atual (apenas para edit_file):**
```python
if fn_name == "edit_file":
    required = ["path", "old_string", "new_string"]
    missing = [arg for arg in required if arg not in fn_args or not fn_args[arg]]
    if missing:
        return f"Erro: edit_file requer argumentos: {', '.join(required)}..."
```

**Problemas:**
- Só valida `edit_file`, ignora outras tools
- Validação feita DEPOIS de tentar parse (poderia ser antes)
- Não previne `TypeError`, só captura depois

**Solução Recomendada:**
```python
# Em src/tools/base.py
class Tool:
    def validate_args(self, **kwargs) -> tuple[bool, str]:
        """Valida argumentos antes de executar"""
        for req in self.required_params:
            if req not in kwargs or not kwargs[req]:
                return False, f"Parâmetro obrigatório faltando: {req}"
        return True, ""

# No executor
def _execute_tool(tc: dict) -> str:
    fn = AVAILABLE_TOOLS.get(fn_name)
    
    # Validar ANTES de executar
    is_valid, error_msg = fn.validate_args(**fn_args)
    if not is_valid:
        return f"Erro de validação: {error_msg}"
    
    result = fn.execute(**fn_args)
```

---

### 5. **MÓDULOS ÓRFÃOS EM `src/`** ⚠️

**Problema:** A estrutura em `src/` foi criada mas **NÃO É USADA**:

```
src/
├── tools/           ← Criado mas NÃO importado pelo agent.py
│   ├── base.py      ← Classes Tool, ToolResult (boas!)
│   ├── file_tools/  ← ReadFileTool, etc (duplicado!)
│   ├── web_tools/   ← WebSearchTool, GitHubSearchTool
│   └── shell_tools/ ← RunShellTool
├── ui/              ← Vazio (só __init__.py)
│   └── components/
│       ├── diff_viewer.py      ← Não usado
│       ├── terminal_panel.py   ← Não usado
│       ├── file_picker.py      ← Não usado
│       └── context_dashboard.py ← Não usado
├── skills/          ← Vazio
├── config/          ← Vazio
└── core/            ← Vazio
```

**Impacto:**
- 40% do código em `src/` está morto
- Esforço de refatoração desperdiçado
- Confusão para novos desenvolvedores

**Decisão necessária:**
- **Opção A:** Completar migração para `src/` (recomendado)
- **Opção B:** Remover `src/` e consolidar na raiz

---

### 6. `ui.py` GIGANTE (982 linhas)** ⚠️

**Problema:** `ui.py` concentra toda UI em um arquivo enorme:
- Definição de tema/cores
- Agent modes
- Session stats
- Prompt toolkit input box (completer, processor, layout)
- Print functions (header, error, tool_result)
- Approval prompts
- Skill wizard
- Terminal streaming panel

**Falta de separação:**
```python
# Tudo no mesmo arquivo:
- Estilos Rich
- Lógica prompt_toolkit
- Funções de print
- Components complexos (TerminalPanel, StreamInputCapture)
```

**Solução Recomendada:**
```
ui.py → src/ui/
├── src/ui/theme.py         ← Cores, estilos Rich
├── src/ui/components/
│   ├── input_box.py        ← PromptSession, completer
│   ├── panels.py           ← TerminalPanel, HeaderPanel
│   └── dialogs.py          ← Approval prompts
├── src/ui/printers.py      ← print_error, print_tool_result, etc
└── src/ui/modes.py         ← AgentMode enum, cycle_mode
```

---

### 7. **GERENCIAMENTO DE ERROS INCONSISTENTE** ⚠️

**Padrões diferentes em lugares diferentes:**

```python
# tools.py - Retorna strings de erro
def read_file(path: str, ...) -> str:
    if not p.exists():
        return f"Erro: arquivo não encontrado: {p}"

# src/tools/file_tools/__init__.py - Usa ToolResult
def execute(self, path: str, ...) -> ToolResult:
    if not file_path.exists():
        return ToolResult(success=False, output="", error="Arquivo não encontrado")

# agent.py - Try/except genérico
try:
    result = fn(**fn_args)
except TypeError as e:
    return f"Erro ao executar {fn_name}: {e}"
```

**Problemas:**
- Inconsistência dificulta tratamento uniforme de erros
- Strings de erro não estruturadas dificultam parsing
- `ToolResult` é melhor padrão mas não usado consistentemente

**Solução Recomendada:**
```python
# Padronizar TODAS as tools com ToolResult
# Criar helper para converter ToolResult → string formatada
def format_tool_result(result: ToolResult) -> str:
    if result.success:
        return result.output
    else:
        return f"❌ Erro: {result.error}"
```

---

### 8. **DEPENDÊNCIAS CÍCLICAS EM POTENCIAL** ⚠️

**Fluxo atual:**
```
main.py → agent.py → tools.py → ui.py → agent.py (?)
                    ↑                    │
                    └────────────────────┘
```

**Risco:** `tools.py` importa de `ui.py`:
```python
from ui import (
    console,
    prompt_command_approval,
    prompt_simple_approval,
    prompt_ask_user,
    print_system_message,
    get_mode,
    AgentMode,
)
```

E `ui.py` pode precisar de `tools.py` no futuro (ex: mostrar preview de tool).

**Solução:** Injeção de dependência ou events:
```python
# Em vez de importar direto, usar callback
class ToolExecutor:
    def __init__(self, approval_callback=None):
        self.approval_callback = approval_callback
    
    def execute(self, tool_name, args):
        if self.approval_callback:
            approved = self.approval_callback(tool_name, args)
```

---

### 9. **FALTA DE TESTES** ❌

**Problema crítico:** Zero testes no projeto!

```bash
$ find /workspace -name "*test*.py"
(nenhum resultado)
```

**Riscos:**
- Refatorações são feitas no escuro
- Bugs de regressão não detectados
- Impossível validar fixes automaticamente
- Dificulta onboarding de novos devs

**Estrutura recomendada:**
```
tests/
├── unit/
│   ├── test_tools.py
│   ├── test_agent.py
│   └── test_ui.py
├── integration/
│   ├── test_session_management.py
│   └── test_tool_execution.py
└── fixtures/
    └── sample_files/
```

---

### 10. **CONFIGURAÇÃO ESPALHADA** ⚠️

**Config em múltiplos lugares:**
```python
# main.py
sys.stdout = io.TextIOWrapper(..., encoding="utf-8")

# agent.py
LM_STUDIO_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
MODEL_NAME    = os.getenv("MODEL_NAME", "gemma-2b-it")

# config.py
CONFIG_DIR = Path.home() / ".my_agent_cli"
WHITELIST_FILE = CONFIG_DIR / "command_whitelist.json"

# tools.py
MAX_READ_CHARS = 60_000
MAX_GREP_RESULTS = 60
IGNORE_DIRS = {...}
```

**Problemas:**
- Constants mágicas espalhadas
- Sem validação de config
- Difícil sobrescrever comportamento

**Solução:**
```python
# src/config/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    openai_base_url: str = "http://localhost:1234/v1"
    model_name: str = "gemma-2b-it"
    max_read_chars: int = 60000
    ignore_dirs: set[str] = {"node_modules", ".git", ...}
    
    class Config:
        env_prefix = "VISION_"
        env_file = ".env"

settings = Settings()
```

---

## ✅ PONTOS FORTES DO PROJETO

### 1. **Streaming eficiente do LLM** ✓
```python
# agent.py linhas 292-333
for chunk in response:
    delta = chunk.choices[0].delta
    # Processamento incremental inteligente
    # Separação reasoning_content vs answer
```

### 2. **Sistema de Skills (.md files)** ✓
```python
# agent.py linhas 348-420
_SKILLS_DIR = Path(__file__).parent / "skills"
def _list_skills() -> dict[str, Path]:
    return {p.stem: p for p in sorted(_SKILLS_DIR.glob("*.md"))}
```

### 3. **Whitelist de comandos shell** ✓
```python
# config.py
def is_whitelisted(command: str) -> bool:
    return command in load_whitelist()
```

### 4. **Persistência de sessão** ✓
```python
# session.py
def save_current_session(messages: list, model: str, base_url: str):
    # Auto-save após cada turno
    # Sessions nomeadas em .visions/
```

### 5. **UI rica com Rich + prompt_toolkit** ✓
```python
# ui.py
console = Console(safe_box=False)
# Input box estilo Claude com rounded corners
# Completion menu para slash commands
```

---

## 📋 PLANO DE REFACTORY PRIORITIZADO

### Fase 1: Crítico (1-2 semanas)
1. **Consolidar tools** - Escolher `tools.py` OU `src/tools/`, eliminar duplicação
2. **Adicionar validação robusta** - Prevenir `TypeError` em todas as tools
3. **Criar testes básicos** - Cobrir ferramentas principais
4. **Extrair system prompt** - Mover para arquivo separado

### Fase 2: Estrutural (2-3 semanas)
5. **Quebrar agent.py** - Separar em módulos menores (core/, llm/, tools/)
6. **Refatorar ui.py** - Separar componentes, printers, modes
7. **Padronizar erros** - Usar `ToolResult` consistentemente
8. **Config centralizada** - Pydantic settings

### Fase 3: Qualidade (contínuo)
9. **Completar migração src/** - Ou remover se não for usar
10. **Documentação** - README, docstrings, type hints
11. **CI/CD** - GitHub Actions para rodar testes
12. **Logging** - Substituir prints por logging estruturado

---

## 🎯 RECOMENDAÇÕES IMEDIATAS

### Para o erro específico reportado (`edit_file missing old_string`):

**Fix rápido em `agent.py`:**
```python
def _execute_tool(tc: dict) -> str:
    fn_name = tc["name"]
    try:
        fn_args = json.loads(tc["arguments"]) if tc["arguments"].strip() else {}
    except json.JSONDecodeError:
        return f"Erro: argumentos JSON inválidos para {fn_name}"
    
    fn = AVAILABLE_TOOLS.get(fn_name)
    if fn is None:
        return f"Tool '{fn_name}' não encontrada."
    
    # Validação GENÉRICA baseada no signature da função
    import inspect
    sig = inspect.signature(fn)
    required_params = {
        name for name, param in sig.parameters.items()
        if param.default is inspect.Parameter.empty
    }
    missing = required_params - set(fn_args.keys())
    if missing:
        return f"Erro: {fn_name} requer parâmetros: {', '.join(missing)}"
    
    track_tool_call()
    t0 = time.perf_counter()
    try:
        result = fn(**fn_args)
    except Exception as e:  # Capturar TODAS exceptions, não só TypeError
        return f"Erro ao executar {fn_name}: {type(e).__name__}: {e}"
    
    duration = time.perf_counter() - t0
    print_tool_result(fn_name, fn_args, str(result), duration)
    return str(result)
```

### Para UX durante instalação/espera:

**Melhoria no `print_tool_result`:**
```python
def print_tool_result(tool_name: str, fn_args: dict, result: str, duration: float):
    # Detectar erros de forma mais robusta
    is_error = (
        result.strip().startswith(("Erro:", "Error:", "❌")) or
        "Traceback" in result or
        "Exception" in result
    )
    
    if is_error:
        # Mostrar erro COMPLETO, não só primeiras 5 linhas
        console.print(Panel(
            result,
            title=f"❌ Erro em {tool_name}",
            border_style="red",
            padding=(1, 2)
        ))
    else:
        # Sucesso - mostrar resumo elegante
        console.print(f"[green]✓[/green] {tool_name} ({duration:.1f}s)")
```

---

## 📈 MÉTRICAS DE QUALIDADE ATUAIS

| Métrica | Valor | Ideal | Status |
|---------|-------|-------|--------|
| Arquivos Python | 29 | 15-20 | ⚠️ Fragmentado |
| Maior arquivo (ui.py) | 982 LOC | <300 | ❌ Muito grande |
| Segundo maior (agent.py) | 659 LOC | <300 | ❌ Muito grande |
| Tools duplicadas | 2x | 1x | ❌ Duplicação |
| Cobertura de testes | 0% | >80% | ❌ Crítico |
| Type hints | ~30% | >90% | ⚠️ Baixo |
| Docstrings | ~40% | >90% | ⚠️ Baixo |
| Módulos órfãos | 8+ | 0 | ❌ Código morto |

---

## 🔧 ARQUIVOS QUE PRECISAM DE ATENÇÃO IMEDIATA

1. **`agent.py`** - Quebrar em 4-5 módulos menores
2. **`tools.py`** vs **`src/tools/`** - Decidir e consolidar
3. **`ui.py`** - Extrair componentes para `src/ui/components/`
4. **`vision.bat` / `iniciar.bat`** - Adicionar BOM UTF-8 (já feito)
5. **`requirements.txt`** - Adicionar `pytest`, `pydantic`, `black`

---

## 💡 CONCLUSÃO

O projeto tem **boa arquitetura conceitual** mas sofre de:
1. **Duplicação massiva** de código (tools em 2 lugares)
2. **Arquivos monolíticos** (agent.py, ui.py, tools.py)
3. **Falta de testes** (risco alto de regressão)
4. **Validação frágil** (causa errors como o reportado)
5. **Código morto** em `src/` (40% do projeto não é usado)

**Prioridade máxima:**
1. Fix de validação de argumentos (evita crashes)
2. Consolidar tools (eliminar duplicação)
3. Adicionar testes básicos
4. Quebrar agent.py e ui.py

Com essas melhorias, o projeto terá base sólida para crescer de forma sustentável.
