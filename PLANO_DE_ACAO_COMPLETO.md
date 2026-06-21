# 🚀 Plano de Ação Completo: Refatoração e Melhorias do Agente

## 📋 Visão Geral

Este documento detalha **todas as melhorias** identificadas na análise, organizadas em fases lógicas para garantir uma evolução segura e modular do projeto.

---

## 🏗️ FASE 1: Fundação e Estrutura Modular (Dias 1-2)

### Objetivo
Criar a nova arquitetura de pastas sem quebrar a funcionalidade atual, permitindo crescimento futuro.

### 1.1 Nova Estrutura de Diretórios
```
src/
├── __init__.py
├── main.py                 # Entry point (movido da raiz)
├── core/
│   ├── __init__.py
│   ├── agent.py            # Loop principal e orquestração
│   ├── llm_client.py       # Cliente LLM (OpenAI/Anthropic) isolado
│   ├── context_manager.py  # Gerenciamento de janela de contexto
│   └── message_history.py  # Histórico com truncamento inteligente
├── tools/
│   ├── __init__.py
│   ├── registry.py         # Registro dinâmico de tools
│   ├── base.py             # Classe abstrata Tool
│   ├── file_tools/
│   │   ├── __init__.py
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   ├── edit_file.py    # Com fuzzy match + diff preview
│   │   └── list_files.py
│   ├── navigation_tools/
│   │   ├── __init__.py
│   │   ├── search_code.py
│   │   └── grep.py
│   ├── web_tools/
│   │   ├── __init__.py
│   │   ├── web_search.py
│   │   └── fetch_url.py
│   ├── shell_tools/
│   │   ├── __init__.py
│   │   ├── run_shell.py    # Com cancelamento
│   │   └── background_process.py
│   └── utility_tools/
│       ├── __init__.py
│       ├── ask_user.py
│       └── task_manager.py
├── ui/
│   ├── __init__.py
│   ├── theme.py            # Cores, estilos, ícones
│   ├── input_handler.py    # Prompt multilinha + editor externo
│   ├── stream_renderer.py  # Streaming de resposta + pensamento
│   ├── diff_viewer.py      # Visualizador de diff interativo
│   ├── context_dashboard.py# Dashboard de tokens/custo
│   └── file_picker.py      # Árvore de arquivos interativa
├── skills/
│   ├── __init__.py
│   ├── loader.py           # Carrega skills de Markdown
│   ├── parser.py           # Extrai metadata e passos
│   ├── wizard.py           # Wizard interativo aprimorado
│   └── executor.py         # Executa passos da skill
├── session/
│   ├── __init__.py
│   ├── storage.py          # Persistência JSON/SQLite
│   └── metadata.py         # Metadados da sessão
├── config/
│   ├── __init__.py
│   ├── settings.py         # Configurações globais
│   ├── whitelist.py        # Whitelist de comandos/arquivos
│   └── proxy.py            # Configuração de proxy
└── utils/
    ├── __init__.py
    ├── logger.py           # Logs estruturados (JSON)
    ├── retry.py            # Backoff exponencial
    ├── diff.py             # Utilitários de diff
    ├── fuzzy_match.py      # Algoritmo de fuzzy match
    └── vision.py           # Suporte a imagens (futuro)

tests/
├── __init__.py
├── test_tools/
│   ├── test_edit_file.py
│   └── test_shell.py
├── test_core/
│   ├── test_context_manager.py
│   └── test_agent.py
└── test_ui/
    └── test_diff_viewer.py

logs/                       # Logs estruturados por sessão
skills/templates/           # Templates de skills (mantido)
```

### 1.2 Tarefas Técnicas
- [ ] Criar estrutura de diretórios vazia
- [ ] Mover `agent.py`, `tools.py`, `ui.py` para novas localizações temporárias
- [ ] Criar `__init__.py` em todos os pacotes
- [ ] Implementar sistema de imports relativos
- [ ] Configurar `pytest` na raiz com `conftest.py`
- [ ] Atualizar `requirements.txt` com novas dependências

### Dependências Novas Sugeridas
```txt
rich>=13.0.0
prompt-toolkit>=3.0.40
pydantic>=2.0.0
structlog>=23.0.0  # Logs estruturados
tenacity>=8.2.0    # Retry com backoff
difflib            # Nativo do Python
fuzzywuzzy>=0.18.0 # Fuzzy match
python-Levenshtein # Otimização para fuzzy
```

---

## 🛠️ FASE 2: Modularização das Tools (Dias 3-5)

### Objetivo
Quebrar `tools.py` (528 linhas) em modules independentes e registráveis.

### 2.1 Implementar Base Tool e Registry
**Arquivo:** `src/tools/base.py`
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ToolResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class BaseTool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
    
    def validate(self, **kwargs) -> bool:
        # Validação comum
        pass
```

**Arquivo:** `src/tools/registry.py`
```python
class ToolRegistry:
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)
    
    @classmethod
    def list_tools(cls) -> List[Dict]:
        # Retorna schema para o LLM
        pass
```

### 2.2 Extrair Tools por Categoria
- [ ] **File Tools**: `read_file`, `write_file`, `edit_file`, `list_files`
- [ ] **Navigation Tools**: `search_code`, `grep`
- [ ] **Web Tools**: `web_search`, `fetch_url`
- [ ] **Shell Tools**: `run_shell` (com cancelamento)
- [ ] **Utility Tools**: `ask_user`, `task_manager`

### 2.3 Melhorias Específicas por Tool

#### 🔹 `edit_file` com Fuzzy Match + Diff Preview
**Problema atual:** Exige linha exata, erro se não encontrar.
**Solução:**
1. Usar `fuzzywuzzy` para encontrar linha mais próxima (threshold 80%)
2. Mostrar diff antes de aplicar
3. Permitir edição de múltiplos blocos em uma chamada

**Fluxo:**
```
1. Usuário pede edição
2. Agente encontra linha com fuzzy match
3. UI mostra diff colorido (verde/vermelho)
4. Usuário confirma com [Y/n] ou edita manualmente
5. Aplica mudança atômica
```

#### 🔹 `run_shell` com Cancelamento
**Problema atual:** Commandos longos travam a sessão.
**Solução:**
1. Executar em subprocesso com PID rastreável
2. Mostrar `[Ctrl+C para cancelar]` na UI
3. Capturar SIGINT e matar processo filho
4. Mostrar output parcial até o cancelamento

#### 🔹 Multi-file Edit Atômico
**Problema atual:** Edita um arquivo por vez.
**Solução:**
1. Agrupar edições por arquivo
2. Mostrar diff consolidado de todos os arquivos
3. Aplicar em transação (ou rollback se falhar)

---

## 🎨 FASE 3: Revolução da UI/UX (Dias 6-9)

### Objetivo
Transformar a experiência do usuário com componentes visuais interativos.

### 3.1 Diff Visual Interativo (`src/ui/diff_viewer.py`)
**Implementação:**
```python
from rich.panel import Panel
from rich.syntax import Syntax
import difflib

class DiffViewer:
    def render_diff(self, old_content: str, new_content: str, filename: str):
        diff = difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            lineterm='',
            fromfile=f'a/{filename}',
            tofile=f'b/{filename}'
        )
        
        # Colorir linhas
        # - Vermelhas (removidas)
        # + Verdes (adicionadas)
        # Contexto em cinza
        
        # Opções interativas:
        # [A]plicar tudo
        # [S]kip (pular)
        # [E]ditar manualmente
        # [B]lock (aplicar apenas blocos selecionados)
```

**Recursos:**
- ✅ Syntax highlighting por linguagem
- ✅ Navegação com setas para blocos
- ✅ Seleção de blocos individuais
- ✅ Preview em tempo real
- ✅ Atalhos: `a` (apply), `s` (skip), `e` (edit), `q` (quit)

### 3.2 Input Multilinha Aprimorado (`src/ui/input_handler.py`)
**Recursos:**
1. **Detecção automática de multilinha:**
   - Se usuário digita `"""` ou `---` → ativa modo editor
   - Mostra contador de linhas e caracteres
   
2. **Editor externo:**
   - `Ctrl+O` abre `$EDITOR` (vim, nano, code)
   - Salva e retorna conteúdo automaticamente

3. **Histórico de prompts:**
   - `↑` / `↓` navega no histórico
   - Busca fuzzy no histórico com `Ctrl+R`

4. **Validação em tempo real:**
   - Highlight de sintaxe enquanto digita
   - Alerta se comando shell parecer perigoso

### 3.3 Dashboard de Contexto em Tempo Real (`src/ui/context_dashboard.py`)
**Localização:** Barra inferior ou lateral direita

**Informações exibidas:**
```
┌─ Contexto ─────────────┐
│ Tokens: 45.2k / 128k   │
│ Custo: $0.23 (estimado)│
│ Janela: 65% livre      │
│ Arquivos: 3 abertos    │
│ Tools usadas: 12       │
└────────────────────────┘
```

**Recursos:**
- Atualização a cada mensagem
- Barra de progresso visual
- Alerta quando >80% da janela usada
- Botão `[C]omprimir` para resumir histórico

### 3.4 Árvore de Arquivos Interativa (`src/ui/file_picker.py`)
**Inspiração:** `fzf` + `ranger`

**Recursos:**
- Navegação com setas
- Busca fuzzy integrada (`/padrao`)
- Multi-seleção com `Space`
- Preview de conteúdo ao lado
- Ações rápidas: `o` (open), `e` (edit), `d` (delete)

**Exemplo de uso:**
```
Usuário: "Edite os arquivos de config"
Agente: [Abre file picker]
  [x] src/config/settings.py
  [x] src/config/database.py
  [ ] src/config/cache.py
Confirma seleção? [Y/n]
```

### 3.5 Streaming de Pensamento (`src/ui/stream_renderer.py`)
**Problema atual:** Usuário vê apenas resposta final.
**Solução:** Mostrar Chain of Thought em tempo real.

**Implementação:**
```python
def stream_with_thought(response_stream):
    for chunk in response_stream:
        if chunk.type == 'thought':
            render_thought(chunk.content)  # Cinza, itálico
        elif chunk.type == 'response':
            render_response(chunk.content) # Normal
```

**UI:**
```
🤔 Pensando...
  ├─ Analisando estrutura do projeto
  ├─ Identificando arquivos relevantes
  └─ Planejando edição em 3 passos

✅ Resposta:
Vou editar os seguintes arquivos...
```

### 3.6 Cancelamento e Desfazer Melhorados
**Cancelamento Granular:**
- `Ctrl+C` na ferramenta atual (não mata sessão)
- Menu: `[C]ancelar tool atual` | `[Q]uit sessão`

**Desfazer (Undo):**
- Manter stack de últimas 5 edições
- Comando `/undo` reverte última mudança
- Mostrar diff reverso antes de aplicar

---

## ⚙️ FASE 4: Core Agent e Gerenciamento (Dias 10-12)

### 4.1 Context Window Management (`src/core/context_manager.py`)
**Problema:** Histórico cresce infinitamente, estoura token limit.

**Estratégias:**
1. **Truncamento Inteligente:**
   - Manter primeiras 2 mensagens (contexto inicial)
   - Manter últimas 10 mensagens
   - Resumir meio do histórico com LLM

2. **Compressão de Mensagens:**
   - Remover outputs longos de tools (manter apenas resumo)
   - Colapsar mensagens consecutivas do mesmo tipo

3. **Priorização:**
   - Mensagens com `!importante` nunca são removidas
   - Arquivos mencionados recentemente têm prioridade

**Algoritmo:**
```python
def truncate_history(messages, max_tokens=100000):
    current_tokens = count_tokens(messages)
    
    while current_tokens > max_tokens:
        # Remove mensagens do meio (não as primeiras nem últimas)
        mid_index = len(messages) // 2
        removed = summarize_message(messages[mid_index])
        messages[mid_index] = removed
        current_tokens = count_tokens(messages)
    
    return messages
```

### 4.2 LLM Client Isolado (`src/core/llm_client.py`)
**Responsabilidades:**
- Abstrair provedor (OpenAI, Anthropic, Local)
- Gerenciar retries com backoff
- Logging de requests/responses
- Contagem de tokens precisa

**Retry com Backoff Exponencial:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True
)
async def chat_completion(messages, model):
    # Lógica de chamada API
    pass
```

### 4.3 Logs Estruturados (`src/utils/logger.py`)
**Formato JSON:**
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "session_id": "abc123",
  "event": "tool_executed",
  "tool_name": "edit_file",
  "duration_ms": 234,
  "tokens_used": 1500,
  "success": true
}
```

**Recursos:**
- Logs por sessão em `logs/session_<id>.jsonl`
- Filtros por nível (DEBUG, INFO, WARN, ERROR)
- Integração com ferramentas de observabilidade (ELK, Datadog)

---

## 🧪 FASE 5: Qualidade e Testes (Dias 13-15)

### 5.1 Testes Unitários
**Estrutura:**
```
tests/
├── test_tools/
│   ├── test_edit_file.py       # Fuzzy match, diff preview
│   ├── test_shell.py           # Cancelamento, timeout
│   └── test_registry.py        # Registro de tools
├── test_core/
│   ├── test_context_manager.py # Truncamento, compressão
│   ├── test_llm_client.py      # Retry, error handling
│   └── test_agent.py           # Loop principal
└── test_ui/
    ├── test_diff_viewer.py     # Renderização de diff
    └── test_input_handler.py   # Multilinha, editor externo
```

**Cobertura Mínima:**
- 80% das tools críticas
- 70% do core agent
- 60% da UI

### 5.2 Tratamento de Erros Específico
**Problema atual:** `try/except Exception` genérico.

**Solução:** Exceptions tipadas por domínio
```python
class ToolError(Exception): pass
class FileNotFound(ToolError): pass
class PermissionDenied(ToolError): pass
class ShellTimeout(ToolError): pass
class ContextWindowExceeded(Exception): pass
class RateLimitExceeded(Exception): pass

# Uso específico
try:
    await tool.execute()
except FileNotFound as e:
    logger.warning(f"Arquivo não encontrado: {e.path}")
    return suggest_similar_files(e.path)
except ShellTimeout as e:
    logger.error(f"Commando demorou muito: {e.command}")
    return offer_cancel_option()
```

### 5.3 Validação e Schema de Tools
**Usando Pydantic:**
```python
class EditFileParams(BaseModel):
    file_path: str
    old_text: str
    new_text: str
    use_fuzzy: bool = True
    fuzzy_threshold: int = 80
    
    @validator('file_path')
    def validate_path(cls, v):
        if not Path(v).exists():
            raise ValueError(f"Arquivo não existe: {v}")
        return v
```

---

## 🚀 FASE 6: Features Avançadas (Dias 16-20)

### 6.1 Suporte a Imagens/Vision (`src/utils/vision.py`)
**Preparação para modelos multimodais:**
- Detectar se modelo suporta vision
- Upload de imagens como contexto
- OCR em screenshots de erros
- Análise de diagramas e fluxogramas

### 6.2 Configuração de Proxy (`src/config/proxy.py`)
**Para ambientes corporativos:**
```python
class ProxyConfig:
    http_proxy: Optional[str]
    https_proxy: Optional[str]
    no_proxy: List[str]
    
    def apply_to_session(self, session):
        # Configura proxies nas requests HTTP
        pass
```

### 6.3 Skill Discovery Melhorado
**Problema atual:** Skills estáticas em templates.

**Solução:**
- Scan automático de skills em `~/.agent/skills/`
- Hot-reload: detectar novos arquivos sem reiniciar
- Marketplace: baixar skills de repositórios Git
- Validação de schema antes de carregar

### 6.4 Multi-Agent Collaboration (Futuro)
**Visão:**
- Agente especialista em código
- Agente especialista em testes
- Agente especialista em deploy
- Orchestrador coordena entre eles

---

## 📊 Cronograma Resumido

| Fase | Duração | Entregáveis Principais |
|------|---------|------------------------|
| **1. Fundação** | 2 dias | Estrutura de pastas, imports, pytest setup |
| **2. Tools** | 3 dias | 13 tools modulares, fuzzy match, cancelamento |
| **3. UI/UX** | 4 dias | Diff viewer, dashboard, file picker, streaming |
| **4. Core** | 3 dias | Context manager, LLM client, logs estruturados |
| **5. Qualidade** | 3 dias | Testes (80% coverage), errors tipados |
| **6. Features** | 5 dias | Vision, proxy, skill discovery |

**Total Estimado:** 20 dias úteis (1 mês calendário)

---

## 🎯 Métricas de Sucesso

Após implementação completa:

1. **Modularidade:**
   - Nenhum arquivo >300 linhas
   - Tools adicionáveis sem modificar core
   - Cobertura de testes >80%

2. **UX:**
   - Tempo médio de edição reduzido em 40%
   - Erros de "linha não encontrada" reduzidos em 90%
   - NPS interno >8/10

3. **Performance:**
   - Latência de tool execution <500ms (p95)
   - Memory usage estável <500MB
   - Context window nunca estoura

4. **Confiabilidade:**
   - Zero crashes não tratados
   - Retry automático em 95% dos erros de rede
   - Logs estruturados para 100% das ações

---

## 🔧 Próximos Passos Imediatos

1. **Hoje:** Aprovar este plano
2. **Dia 1:** Criar estrutura de pastas (Fase 1)
3. **Dia 2-4:** Implementar Diff Viewer + Fuzzy Match (prioridade máxima de UX)
4. **Dia 5-7:** Context Manager + Retry (prioridade máxima de estabilidade)
5. **Dia 8+:** Iterar nas demais features

---

## 📝 Notas de Implementação

- **Branch Strategy:** Criar branch `refactor/modularization` para não quebrar `main`
- **Commits:** Seguir Conventional Commits (`feat:`, `fix:`, `refactor:`)
- **Review:** Cada fase requer PR review antes de merge
- **Rollback:** Manter backup da versão atual até Fase 3 completa

---

**Autor:** Agente de Análise  
**Data:** 2025-01-15  
**Versão:** 1.0
