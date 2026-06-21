# 🚀 Próximos Passos da Refatoração

## ✅ Fase 1 COMPLETA: Estrutura Modular + Componentes Core

### Resumo do Implementado:
- **17 arquivos Python** na nova estrutura (`src/`)
- **~1.600 linhas de código** modularizadas
- **9 tools** implementadas e testadas
- **3 componentes UI** (Diff Viewer, Dashboard, File Picker)
- **Utils completos** (Logger, Retry, Timer, Helpers)

---

## 📋 Fase 2: Tools Pendentes (Web + Shell)

### 1. Web Tools (`src/tools/web_tools/`)
```python
# A implementar:
- web_search(query, max_results)    # DuckDuckGo ou Google API
- fetch_url(url)                     # Requests + BeautifulSoup
- search_github(query, kind)         # GitHub API v3
```

**Prioridade:** Média  
**Complexidade:** Baixa  
**Dependências:** `requests`, `beautifulsoup4`

---

### 2. Shell Tools (`src/tools/shell_tools/`) 🔴 CRÍTICO
```python
# A implementar com cancelamento manual:
- run_shell(command, stdin_input, timeout, cancellable)
```

**Features chave:**
- Streaming de output em tempo real
- Cancelamento via Ctrl+C sem matar o agente
- Timeout configurável por comando
- Histórico de comandos executados
- Detecção de prompts interativos

**Prioridade:** Alta  
**Complexidade:** Média  
**Técnica:** `subprocess.Popen` com threads para streaming

---

## 📋 Fase 3: Integração com Agent Loop

### 3.1 Context Manager (`src/core/context_manager.py`)
```python
# Gerenciamento inteligente de janela de contexto:
- Truncar mensagens antigas quando perto do limite
- Manter system prompt + últimas N mensagens
- Sumarizar conversas longas automaticamente
```

**Prioridade:** Alta  
**Impacto:** Evita erros de contexto cheio

---

### 3.2 LLM Client (`src/core/llm_client.py`)
```python
# Cliente com retry e tratamento de erros:
- @retry_with_backoff em todas as chamadas
- Tratamento específico por tipo de erro (rate limit, timeout, etc)
- Logging estruturado de cada requisição
- Support a múltiplos providers (OpenAI, LM Studio, Ollama)
```

**Prioridade:** Alta  
**Impacto:** Resiliência e confiabilidade

---

### 3.3 Diff Interativo no Agent
```python
# Integrar DiffViewer no fluxo de edição:
1. Agent chama edit_file
2. Tool gera diff e retorna com metadata
3. UI mostra preview colorido
4. Usuário pode:
   - [a]pply all
   - [s]kip all
   - Selecionar hunks específicos [1-9]
   - [q]uit/cancelar
5. Aplica apenas hunks selecionados
```

**Prioridade:** Alta  
**Impacto UX:** Muito Alto

---

### 3.4 Dashboard em Tempo Real
```python
# Exibir após cada resposta do LLM:
- Atualizar contador de tokens
- Mostrar custo acumulado
- Barra de progresso do contexto
- Alerta visual quando >85% usado
```

**Prioridade:** Média  
**Impacto UX:** Alto

---

## 📋 Fase 4: Melhorias de UX

### 4.1 Input Multilinha Aprimorado
```python
# Detectar prompts longos automaticamente:
- Se usuário digita \"\"\" ou --- → modo multilinha
- Ctrl+O abre editor externo ($EDITOR)
- Histórico fuzzy de inputs anteriores
- Auto-complete de paths com file picker
```

**Prioridade:** Média

---

### 4.2 File Picker no Input
```python
# Atalhos no input do usuário:
- Ctrl+F → abre file picker
- Tab → auto-complete de path
- Fuzzy match nos resultados
- Multi-seleção para operações em batch
```

**Prioridade:** Baixa

---

### 4.3 Undo/Redo de Edições
```python
# Stack das últimas 5 edições:
- /undo → rever última edição de arquivo
- /redo → refazer edição desfeita
- /history → lista de edições recentes
```

**Prioridade:** Baixa

---

## 📋 Fase 5: Testes e Qualidade

### 5.1 Testes Unitários (`tests/unit/`)
```bash
tests/
├── unit/
│   ├── test_file_tools.py      # Testes para file tools
│   ├── test_navigation_tools.py
│   ├── test_diff_viewer.py
│   ├── test_context_dashboard.py
│   └── test_retry_helpers.py
└── integration/
    ├── test_agent_loop.py
    └── test_tool_registry.py
```

**Meta:** 80% code coverage  
**Framework:** pytest

---

### 5.2 Validação com Pydantic
```python
# Tipagem forte nos parâmetros das tools:
from pydantic import BaseModel, Field

class EditFileParams(BaseModel):
    path: str = Field(..., min_length=1)
    old_string: str
    new_string: str
    replace_all: bool = False
```

**Prioridade:** Média

---

## 📋 Fase 6: Features Avançadas

### 6.1 Vision/Suporte a Imagens
```python
# Analisar screenshots e imagens:
- read_image(path) → base64 + descrição
- screenshot() → captura tela atual
- analyze_image(image, prompt) → visão computacional
```

**Prioridade:** Baixa  
**Dependências:** Modelo com vision (GPT-4V, etc)

---

### 6.2 Configuração de Proxy
```python
# Suporte a proxies corporativos:
- HTTP_PROXY, HTTPS_PROXY no config
- Autenticação NTLM se necessário
- Bypass para localhost
```

**Prioridade:** Baixa

---

### 6.3 Skill Discovery
```python
# Melhorar descoberta de skills:
- /skills list → mostra todas disponíveis
- /skills search <term> → busca por keyword
- Auto-sugestão baseada no contexto
```

**Prioridade:** Baixa

---

## 🎯 Roadmap Sugerido

| Semana | Foco | Entregáveis |
|--------|------|-------------|
| **1** | Shell Tools + Web Tools | run_shell com cancelamento, web_search |
| **2** | Core Agent | Context manager, LLM client, retry |
| **3** | UX Integration | Diff interativo, dashboard, file picker |
| **4** | Tests + Quality | Testes unitários, validação pydantic |
| **5** | Features | Vision, proxy, skill discovery |

---

## 📊 Status Atual

```
Fase 1: Estrutura Modular        ✅ 100%
Fase 2: Tools (Web + Shell)      ⏳ 0%
Fase 3: Core Agent               ⏳ 0%
Fase 4: UX Integration           ⏳ 0%
Fase 5: Tests + Quality          ⏳ 0%
Fase 6: Features Avançadas       ⏳ 0%

Progresso Total: 16% (1/6 fases)
```

---

## 🔥 Próxima Ação Imediata

Implementar **Shell Tools com cancelamento** (`src/tools/shell_tools/__init__.py`):
- É a tool mais usada depois de file tools
- Cancelamento manual é crítico para UX
- Streaming de output dá feedback em tempo real

Quer que eu implemente agora?
