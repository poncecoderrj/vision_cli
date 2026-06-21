# 🚀 Refatoração do Agente de Programação Autônomo

## ✅ Fase 1 Concluída: Estrutura Modular Criada

### Nova Estrutura de Pastas:
```
src/
├── core/                    # Loop principal, LLM client, context manager
│   └── __init__.py
├── tools/                   # Tools modulares por categoria
│   ├── __init__.py         # Registry e classes base
│   ├── file_tools/         # read_file, write_file, edit_file, delete_file
│   ├── navigation_tools/   # list_dir, glob_files, search_code
│   ├── web_tools/          # web_search, fetch_url, search_github (TODO)
│   ├── shell_tools/        # run_shell com cancelamento (TODO)
│   └── utility_tools/      # ask_user, manage_tasks
├── ui/
│   ├── __init__.py
│   └── components/
│       ├── diff_viewer.py       # ✅ Diff visual interativo
│       ├── context_dashboard.py # ✅ Dashboard de tokens/custo
│       └── file_picker.py       # ✅ Seletor de arquivos estilo fzf
├── utils/
│   ├── __init__.py
│   └── helpers.py         # Logger, retry com backoff, fuzzy match
├── session/               # Gerenciamento de sessões
├── skills/                # Sistema de skills
└── config/                # Configurações e whitelist
```

### 📦 Componentes Implementados:

#### 1. **Tools Registry** (`src/tools/__init__.py`)
- Interface `Tool` padronizada
- Classe `ToolResult` para resultados consistentes
- `ToolRegistry` centralizado para registro e execução

#### 2. **File Tools** (`src/tools/file_tools/__init__.py`)
- ✅ `ReadFileTool` - Leitura com offset/limit
- ✅ `WriteFileTool` - Escrita com criação de diretórios
- ✅ `EditFileTool` - **Fuzzy match + Diff preview**
- ✅ `DeleteFileTool` - Deleção segura

**Melhoria chave:** `EditFileTool` agora tem:
- Fuzzy matching (80% threshold) para encontrar texto mesmo com indentação ligeiramente diferente
- Geração automática de diff no formato unified
- Metadata com tamanho das mudanças

#### 3. **Navigation Tools** (`src/tools/navigation_tools/__init__.py`)
- ✅ `ListDirTool` - Lista com ícones e tamanhos
- ✅ `GlobFilesTool` - Busca por padrão glob
- ✅ `SearchCodeTool` - Grep com regex, limitação de resultados

#### 4. **Utility Tools** (`src/tools/utility_tools/__init__.py`)
- ✅ `AskUserTool` - Perguntas com opções múltiplas
- ✅ `ManageTasksTool` - Gestão de tarefas com timestamps

#### 5. **UI Components**

##### Diff Viewer (`src/ui/components/diff_viewer.py`)
- Geração de diff no formato unified
- Parse de hunks individuais
- Formatação colorida (Rich ou ANSI)
- **Seleção interativa de hunks** para aplicar parcialmente
- Renderização com comandos: `[a]pply`, `[s]kip`, `[1-9]`, `[q]uit`

##### Context Dashboard (`src/ui/components/context_dashboard.py`)
- Tracking de tokens em tempo real
- Cálculo de custo estimado
- Barra de progresso da janela de contexto
- Contagem de tools usadas
- Tempo de sessão decorrido
- Alerta quando perto do limite (85%)

##### File Picker (`src/ui/components/file_picker.py`)
- Navegação estilo fzf/ranger
- Busca fuzzy por nome/path
- Multi-seleção com Space
- Ícones por tipo de arquivo
- Integração com prompt_toolkit para UI full-screen

#### 6. **Utils Helpers** (`src/utils/helpers.py`)
- ✅ `setup_logger()` - Logger estruturado com arquivo opcional
- ✅ `@retry_with_backoff()` - Decorator com backoff exponencial + jitter
- ✅ `fuzzy_match()` - Algoritmo de matching simples
- ✅ `truncate_text()`, `format_bytes()`, `format_duration()`
- ✅ `Timer` - Context manager para profiling

---

## 🔄 Próximos Passos (Fase 2):

### Tools Pendentes:
1. **Web Tools** (`src/tools/web_tools/`)
   - `web_search()` com integração DuckDuckGo/Google
   - `fetch_url()` com parsing de HTML
   - `search_github()` via API do GitHub

2. **Shell Tools** (`src/tools/shell_tools/`)
   - `run_shell()` com **cancelamento manual** (Ctrl+C na tool)
   - Timeout configurável por comando
   - Streaming de output em tempo real
   - Histórico de comandos executados

3. **Integração com Registry**
   - Registrar todas as tools no `ToolRegistry`
   - Exportar lista formatada para o system prompt
   - Validar parâmetros antes de executar

### Melhorias de UX Prioritárias:
1. **Diff Interativo no Agent Loop**
   - Integrar `DiffViewer` no fluxo de `edit_file`
   - Mostrar preview antes de aplicar
   - Permitir seleção de hunks

2. **Dashboard em Tempo Real**
   - Exibir após cada resposta do LLM
   - Atualizar contador de tokens
   - Alertar quando contexto estiver cheio

3. **File Picker no Input**
   - Atalho `Ctrl+F` para abrir picker
   - Auto-complete de paths com fuzzy match
   - Histórico de arquivos acessados

---

## 📊 Métricas de Melhoria:

| Categoria | Antes | Depois | Ganho |
|-----------|-------|--------|-------|
| **Modularidade** | 3 arquivos monolíticos | 15+ módulos separados | ⬆️ 400% |
| **Tools** | 13 tools em 1 arquivo | Tools categorizadas por domínio | ⬆️ Organização |
| **UX - Diff** | Texto plano | Visual colorido + seleção | ⬆️ Impacto Alto |
| **UX - Contexto** | Sem tracking | Dashboard completo | ⬆️ Transparência |
| **Resiliência** | Sem retry | Backoff exponencial | ⬆️ Confiabilidade |
| **Debug** | Print statements | Logger estruturado | ⬆️ Debugabilidade |

---

## 🎯 Como Usar os Novos Componentes:

### Exemplo: Tool Registry
```python
from src.tools import registry
from src.tools.file_tools import FILE_TOOLS

# Registra todas as file tools
for tool in FILE_TOOLS:
    registry.register(tool)

# Executa uma tool
result = registry.execute("read_file", path="main.py")
if result.success:
    print(result.output)
```

### Exemplo: Retry com Backoff
```python
from src.utils.helpers import retry_with_backoff

@retry_with_backoff(max_attempts=5, base_delay=0.5)
def call_llm_api(prompt):
    # Sua chamada de API aqui
    pass
```

### Exemplo: Diff Viewer
```python
from src.ui.components.diff_viewer import diff_viewer

old = "def hello():\n    pass"
new = "def hello():\n    print('Hello!')"

diff = diff_viewer.generate_diff(old, new, "test.py")
print(diff_viewer.format_colored())
print(diff_viewer.get_hunk_summary())
```

### Exemplo: Context Dashboard
```python
from src.ui.components.context_dashboard import dashboard

dashboard.record_tokens(prompt_tokens=1500, completion_tokens=500)
dashboard.record_tool_call("edit_file")
print(dashboard.render_dashboard())
```

---

## 📝 Arquivos Originais Mantidos:
Os arquivos originais (`agent.py`, `tools.py`, `ui.py`, etc.) **não foram modificados** para garantir que o sistema continue funcionando durante a transição. A próxima fase migrará gradualmente para a nova estrutura.
