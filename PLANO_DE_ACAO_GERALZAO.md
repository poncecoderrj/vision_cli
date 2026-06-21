# 🚀 PLANO DE AÇÃO GERALZÃO - AGENTE WINDOWS ESPECIALISTA

## 📋 VISÃO GERAL

**Objetivo:** Transformar o agente em um **especialista em Windows** com navegabilidade ultra-inteligente, tools de pesquisa/web robustas e UX de nível production (estilo Claude CLI/Cursor).

**Duração Estimada:** 25-30 dias úteis  
**Prioridade Máxima:** Navegação Windows + Web Search Inteligente + Terminal Interativo

---

## 🎯 FASE 0: FUNDAÇÃO E ESTRUTURA (JÁ INICIADA)

### ✅ Concluído
- [x] Nova estrutura de pastas (`src/core`, `src/tools/*`, `src/ui/*`)
- [x] File tools modulares (read, write, edit com fuzzy match, delete)
- [x] Navigation tools (list_dir, glob_files, search_code)
- [x] Utility tools (ask_user, manage_tasks melhorado)
- [x] Utilitários (logger, retry, fuzzy_match, diff)

### 🔴 Pendente Crítico
- [ ] Shell tools (run_shell com terminal interativo)
- [ ] Web tools (web_search, fetch_url, search_github inteligentes)
- [ ] GitHub Skills especializadas
- [ ] Integração completa no agent.py

---

## 🔨 FASE 1: TOOLS DE NAVEGAÇÃO WINDOWS ULTRA-INTELIGENTES

### 1.1 `list_dir` - Navegabilidade Perfeita em Windows
**Problema Atual:** Agente se perde facilmente ao navegar.

**Melhorias:**
```python
class ListDirTool:
    def execute(self, path: str, depth: int = 1, show_hidden: bool = False):
        # ✅ SEMPRE retornar caminho absoluto normalizado
        # ✅ Detectar automaticamente se é Windows/Linux
        # ✅ Retornar árvore visual clara com ícones
        # ✅ Incluir metadata: tipo, tamanho, data modificação
        # ✅ Limitar profundidade automática baseada no conteúdo
        # ✅ Detectar padrões comuns (.git, node_modules, venv) e sugerir ignorar
        # ✅ Cache de diretórios recentes para navegação rápida
        # ✅ Hint automático: "Você está em C:\Projects\myapp\src"
```

**Critérios de Qualidade:**
- [ ] Nunca perder o contexto do diretório atual
- [ ] Mostrar breadcrumbs claros: `C:\> Users > Documents > Project > src`
- [ ] Detectar automaticamente estruturas de projeto (React, Python, Node)
- [ ] Sugerir próximos passos: "Quer ver o package.json ou requirements.txt?"

---

### 1.2 `glob_files` - O Mais Inteligente Possível
**Problema Atual:** Buscas genéricas retornam muitos falsos positivos.

**Melhorias:**
```python
class GlobFilesTool:
    def execute(self, pattern: str, path: str = None, smart: bool = True):
        # ✅ Auto-expandir padrões comuns: "*.py" → "**/*.py"
        # ✅ Sugestão inteligente de padrões baseada no pedido
        # ✅ Filtrar automaticamente: node_modules, .git, __pycache__, dist, build
        # ✅ Priorizar arquivos relevantes ao contexto da conversa
        # ✅ Retornar resultados ranqueados por relevância
        # ✅ Agrupar por tipo/diretório para facilitar leitura
        # ✅ Limitar a X resultados mais relevantes (não 1000 arquivos)
        # ✅ Detectar intenção: "achar arquivo de config" → buscar *.json, *.yaml, *.toml
```

**Exemplos de Inteligência:**
- Usuário: "onde tá o arquivo de rotas?" → Buscar: `**/routes.*`, `**/router.*`, `**/*routes*`
- Usuário: "preciso do main" → Buscar: `main.*`, `index.*`, `app.*`, `__main__.*`
- Usuário: "config do projeto" → Buscar: `package.json`, `pyproject.toml`, `setup.cfg`, `.env*`

---

### 1.3 `search_code` - Search Code Cirúrgico
**Problema Atual:** Regex simples não captura contexto semântico.

**Melhorias:**
```python
class SearchCodeTool:
    def execute(self, query: str, path: str = None, file_pattern: str = None, context_lines: int = 3):
        # ✅ Busca semântica + regex combinados
        # ✅ Expandir query automaticamente:
        #    - "função de login" → buscar: def login, function login, login(, auth
        #    - "classe user" → buscar: class User, classuser, UserModel, user_dict
        # ✅ Retornar contexto completo (N linhas antes/depois)
        # ✅ Highlight dos matches no resultado
        # ✅ Agrupar por arquivo e ordenar por relevância
        # ✅ Ignorar comentários e strings (opcional)
        # ✅ Suporte a busca por tipo: "def", "class", "import", "const"
        # ✅ Cache de buscas frequentes
```

**Features Avançadas:**
- [ ] Busca fuzzy: "funcao de autenticacao" → encontra `authenticate_user`
- [ ] Busca por assinatura: "função que recebe email e senha" → `def login(email, password)`
- [ ] Detecção de padrões: "todos os endpoints GET" → `@app.get`, `router.get`, `GET /`

---

### 1.4 `run_shell` - Bash/PowerShell de Qualidade Máxima + Terminal Interativo
**Problema Atual:** Comandos longos não têm controle, não há terminal interativo.

**Melhorias:**
```python
class RunShellTool:
    def execute(self, command: str, cwd: str = None, interactive: bool = False, timeout: int = 60):
        # ✅ Detectar automaticamente Windows (PowerShell/CMD) vs Linux (bash)
        # ✅ Streaming em tempo real com cores preservadas
        # ✅ Cancelamento granular (Ctrl+C mata comando, não sessão)
        # ✅ Timeout configurável por tipo de comando
        # ✅ Histórico de comandos executados na sessão
        # ✅ Variáveis de ambiente isoladas por sessão
        # ✅ Detecção automática de processos em loop (npm run dev, server)
        
        # 🆕 FEATURE CLONE DO GEMINI CLI:
        # ✅ Se comando inicia servidor/loop → avisar: "Servidor rodando na porta 3000"
        # ✅ Permitir Ctrl+R para entrar no terminal interativo
        # ✅ No terminal: Ctrl+C mata processo, não o agente
        # ✅ Voltar ao agente com Ctrl+D ou comando /exit
```

**Terminal Interativo (Feature Gemini CLI):**
```
🖥️ Servidor rodando em http://localhost:3000
💡 Pressione Ctrl+R para entrar no terminal interativo
   (Ctrl+C encerra o servidor, não a sessão do agente)

[Usuário aperta Ctrl+R]
┌─────────────────────────────────────┐
│ TERMINAL INTERATIVO (Ctrl+D sai)    │
│ $ npm run dev                       │
│ > listening on port 3000            │
│ [output stream...]                  │
│ $                                   │
└─────────────────────────────────────┘
```

**Segurança:**
- [ ] Whitelist de comandos perigosos (rm -rf, del /F, format)
- [ ] Aprovação para comandos fora da whitelist
- [ ] Sandbox para comandos não confiáveis (future)

---

## 🌐 FASE 2: WEB SEARCH INTELIGENTE E REALISTA

### 2.1 `web_search` - Pesquisa Real com Validação
**Problema Crítico:** Retorna lixo, IA não valida qualidade, continua mesmo com info inútil.

**Melhorias:**
```python
class WebSearchTool:
    def execute(self, query: str, max_results: int = 5, validate: bool = True, max_retries: int = 3):
        # ✅ Múltiplas fontes: DuckDuckGo, Bing API, Google Custom Search (opcional)
        # ✅ Scraping inteligente do HTML → texto limpo
        # ✅ VALIDAÇÃO DE QUALIDADE:
        #    - Remover resultados de baixa qualidade (SEO spam, conteúdoraso)
        #    - Verificar se o conteúdo realmente responde a query
        #    - Score de relevância (0-10) para cada resultado
        # ✅ RE-PESQUISA AUTOMÁTICA:
        #    - Se todos os resultados têm score < 5 → reformular query
        #    - Tentar sinônimos, termos mais específicos
        #    - Máximo de 3 tentativas antes de admitir falha
        # ✅ LEITURA PROFUNDA:
        #    - Fetch completo das URLs promissoras
        #    - Extrair apenas conteúdo relevante (remover nav, footer, ads)
        #    - Resumir em bullets points com citações
        # ✅ TRANSPARÊNCIA:
        #    - Se não achar nada útil → dizer claramente: "Não encontrei informações confiáveis sobre X"
        #    - Sugerir alternativas: "Tente pesquisar por Y ou Z"
        #    - Nunca inventar informações
```

**Fluxo Inteligente:**
```
1. Pesquisa inicial: "como configurar webpack com React"
2. Analisa 10 resultados → 8 são SEO spam, 2 são medianos (score 4/10)
3. Reformula: "webpack React configuration tutorial 2024 site:github.com OR site:medium.com"
4. Analisa novos resultados → 5 bons (score 7+/10)
5. Fetch das 3 melhores URLs
6. Extrai conteúdo relevante
7. Retorna: "Encontrei 3 guias confiáveis: [resumo com links]"
   OU
   "Não encontrei informações atualizadas. Encontrei apenas tutoriais de 2020 que podem estar desatualizados."
```

**Fontes Prioritárias:**
- Documentação oficial (.dev, .org, docs.*)
- GitHub (issues, README, discussions)
- StackOverflow (respostas votadas)
- Medium/Dev.to (apenas autores verificados)
- Reddit (subs técnicos: r/programming, r/webdev)

---

### 2.2 `fetch_url` - Leitura Profunda de URLs
**Problema:** Baixa URL mas não extrai conteúdo útil.

**Melhorias:**
```python
class FetchURLTool:
    def execute(self, url: str, extract_type: str = "auto"):
        # ✅ Detecção automática de tipo de conteúdo:
        #    - Documentação → extrair títulos, código, exemplos
        #    - Artigo → título, autor, data, conteúdo principal
        #    - GitHub → README, issues recentes, stars
        #    - API docs → endpoints, parâmetros, exemplos
        # ✅ Remover ruído: menus, footers, ads, comentários
        # ✅ Preservar formatação de código
        # ✅ Extrair metadata: author, date, last_updated
        # ✅ Validar se conteúdo é relevante para o contexto atual
        # ✅ Timeout inteligente (páginas pesadas → abortar após 10s)
        # ✅ Cache de URLs já visitadas na sessão
```

---

### 2.3 `search_github` + GitHub Skills Especializadas
**Problema:** Só pesquisa, não gerencia projetos.

**Melhorias:**

#### Tool Base: `search_github`
```python
class SearchGitHubTool:
    def execute(self, query: str, search_type: str = "repo", language: str = None, sort: str = "stars"):
        # ✅ Busca repositórios, código, issues, PRs
        # ✅ Autenticação opcional (token aumenta limites)
        # ✅ Filtros inteligentes: stars, updated, forks, language
        # ✅ Retornar: nome, descrição, stars, última atualização, link
        # ✅ Preview do README para os top 3 resultados
```

#### 🆕 SKILLS ESPECIALIZADAS EM GITHUB:

**Skill 1: `github_clone_setup`**
```markdown
Nome: github_clone_setup
Descrição: Clona repositório, instala dependências, configura ambiente
Passos:
1. Perguntar URL do repo ou buscar no GitHub
2. Clonar em diretório apropriado
3. Detectar tipo de projeto (package.json, requirements.txt, Cargo.toml)
4. Instalar dependências automaticamente
5. Configurar .env se necessário
6. Rodar testes iniciais
7. Reportar status: "✅ Projeto pronto em C:\Projects\myapp"
```

**Skill 2: `github_commit_push`**
```markdown
Nome: github_commit_push
Descrição: Gerencia commits e push para GitHub
Passos:
1. git status para ver mudanças
2. git diff para revisar
3. Perguntar mensagem de commit (ou sugerir baseada nas mudanças)
4. git add, git commit, git push
5. Lidar com autenticação (SSH vs HTTPS)
6. Criar branch se necessário
```

**Skill 3: `github_pr_creator`**
```markdown
Nome: github_pr_creator
Descrição: Cria Pull Request no GitHub
Passos:
1. Verificar branch atual e últimas mudanças
2. Buscar issues relacionadas (se houver)
3. Gerar descrição de PR baseada nos commits
4. Usar GitHub CLI ou API para criar PR
5. Linkar issues, adicionar labels, reviewers
```

**Skill 4: `github_project_manager`**
```markdown
Nome: github_project_manager
Descrição: Gerencia projetos GitHub (issues, milestones, projects)
Passos:
1. Listar issues abertas/fechadas
2. Criar nova issue com template
3. Atualizar status de issues
4. Gerenciar milestones
5. Integrar com GitHub Projects (kanban)
```

---

## 📝 FASE 3: TOOLS DE ARQUIVO CIRÚRGICAS

### 3.1 `write_file` - Escrita de Documentos Inteligente
**Análise:** Já funciona bem, mas pode melhorar.

**Melhorias:**
```python
class WriteFileTool:
    def execute(self, path: str, content: str, create_dirs: bool = True):
        # ✅ Criar diretórios pais automaticamente
        # ✅ Detectar encoding apropriado (UTF-8 padrão)
        # ✅ Backup automático de arquivos existentes (.bak)
        # ✅ Validação de sintaxe para linguagens conhecidas
        #    - JSON → validar estrutura
        #    - YAML → validar indentação
        #    - Python → syntax check
        # ✅ Template detection:
        #    - Se escrever .md → sugerir estrutura (títulos, seções)
        #    - Se escrever .py → adicionar shebang, docstrings
        # ✅ Aprovação em camadas:
        #    - Arquivos críticos (.env, config, database) → aprovação explícita
        #    - Código → mostrar diff antes de escrever
```

---

### 3.2 `edit_file` - Edição Cirúrgica com Diff Visual
**Problema:** Replace exato é frágil, não mostra diff visual.

**Melhorias:**
```python
class EditFileTool:
    def execute(self, path: str, edits: List[EditOperation], dry_run: bool = False):
        # ✅ FUZZY MATCH para encontrar linhas (já implementado)
        # ✅ MÚLTIPLAS EDIÇÕES EM UM ARQUIVO
        # ✅ LOOPS DE VALIDAÇÃO:
        #    1. Encontrar linhas candidatas (fuzzy match)
        #    2. Mostrar contexto de cada match
        #    3. Confirmar qual match editar (ou editar todos)
        #    4. Aplicar edição em staging
        #    5. Validar sintaxe após edição
        #    6. Mostrar DIFF VISUAL INTERATIVO
        
        # 🆕 DIFF VISUAL INTERATIVO (Estilo Claude):
        # ┌─────────────────────────────────────────────┐
        # 📄 Arquivo: C:\Projects\app\src\utils.py      │
        #                                                  │
        # 🔴 REMOVIDO (linha 42):                         │
        #   def calculate_total(items):                   │
        #     total = 0                                   │
        #     for item in items:                          │
        #       total += item.price                       │
        #                                                  │
        # 🟢 ADICIONADO (linha 42):                       │
        #   def calculate_total(items, tax_rate=0.1):     │
        #     subtotal = sum(item.price for item in items)│
        #     tax = subtotal * tax_rate                   │
        #     return subtotal + tax                       │
        #                                                  │
        # [a]plicar  [r]ejeitar  [e]ditar manual  [q]uit │
        # └─────────────────────────────────────────────┘
```

**Fluxo de Validação:**
1. Usuário pede: "adiciona imposto na função calculate_total"
2. Tool encontra 3 funções similares com fuzzy match
3. Mostra contexto de cada uma e pergunta: "Qual destas você quer editar?"
4. Usuário seleciona → aplica edição em staging
5. Valida sintaxe Python → OK
6. Mostra diff visual interativo
7. Usuário aperta 'a' → aplica
8. Confirma: "✅ Editado C:\Projects\app\src\utils.py (linha 42-46)"

---

### 3.3 `delete_file` - Deleção Segura e Precisa
**Problema:** Pode deletar arquivo errado se navegação falhar.

**Melhorias:**
```python
class DeleteFileTool:
    def execute(self, path: str, recursive: bool = False, dry_run: bool = True):
        # ✅ SEMPRE confirmar caminho absoluto antes de deletar
        # ✅ Dry run por padrão: mostrar o que seria deletado
        # ✅ Backup automático antes de deletar (lixeira ou .deleted/)
        # ✅ Detecção de arquivos críticos:
        #    - .git/, node_modules/, venv/ → alertar "Tem certeza?"
        #    - Arquivos com < 24h de criação → alertar "Recém-criado"
        # ✅ Contagem de impacto: "Isso deletará 15 arquivos (123 KB)"
        # ✅ Aprovação em camadas:
        #    - 1 arquivo → aprovação simples
        #    - >5 arquivos ou >1MB → aprovação explícita com lista
        #    - Diretórios inteiros → aprovação muito explícita
```

---

## 🤖 FASE 4: CORE AGENT MELHORIAS

### 4.1 Context Window Management
```python
class ContextManager:
    # ✅ Limitar histórico de mensagens (últimas 20 exchanges)
    # ✅ Sumarizar conversas antigas automaticamente
    # ✅ Manter apenas contexto relevante (arquivos mencionados recentemente)
    # ✅ Compression de tokens quando >80% da janela
    # ✅ Priorizar: system prompt > arquivos abertos > histórico recente
```

### 4.2 Retry com Backoff Exponencial
```python
@retry_with_backoff(max_retries=3, backoff_factor=2)
def call_llm(prompt):
    # ✅ Retry automático para erros de rede (5xx, timeout)
    # ✅ Backoff exponencial: 2s, 4s, 8s entre tentativas
    # ✅ Fallback para modelo alternativo se principal falhar
    # ✅ Log estruturado de todas as tentativas
```

### 4.3 Logs Estruturados
```python
# ✅ Logger separado por módulos (tools, ui, core)
# ✅ Níveis: DEBUG, INFO, WARNING, ERROR
# ✅ Output em arquivo (logs/agent_YYYY-MM-DD.log)
# ✅ Logs JSON para análise posterior
# ✅ Correlação de IDs para tracear fluxos completos
```

---

## 🧩 FASE 5: MANAGE_TASKS EM LOOP INTELIGENTE

### 5.1 `manage_tasks` - Task Tracker em Loop
**Problema:** In-memory, básico, não persiste.

**Melhorias:**
```python
class ManageTasksTool:
    def execute(self, action: str, task_data: dict = None):
        # ✅ Persistência em arquivo (.tasks.json na raiz do projeto)
        # ✅ Estados: pending, in_progress, blocked, done
        # ✅ Dependências entre tasks
        # ✅ Loop automático:
        #    1. Completar task atual
        #    2. Marcar como done
        #    3. Selecionar próxima task (por prioridade/dependência)
        #    4. Reportar progresso
        # ✅ Integração com GitHub Issues (opcional)
        # ✅ Dashboard visual:
        #    ████████░░ 60% concluído (6/10 tasks)
        # ✅ Estimativa de tempo restante baseada no histórico
```

**Comandos:**
- `/task add "Implementar login"`
- `/task list` → mostra todas com status
- `/task start 3` → marca task 3 como in_progress
- `/task done 3` → marca como done e sugere próxima
- `/task loop` → entra em modo automático (completa uma por uma)

---

## 🎨 FASE 6: UI/UX AVANÇADA

### 6.1 Diff Visual Interativo (Já descrito no edit_file)
### 6.2 Dashboard de Contexto em Tempo Real
```
┌─────────────────────────────────────────────┐
│ 📊 CONTEXTO                                 │
│ Tokens: 8,432 / 32,000 (26%) ████░░░░░░░░  │
│ Custo estimado: $0.04                       │
│ Arquivos abertos: 3                         │
│ Tools usadas: 12                            │
│ Tempo de sessão: 23min                      │
└─────────────────────────────────────────────┘
```

### 6.3 File Picker Interativo (Estilo fzf)
```
🔍 Buscar arquivo: [utils____________]

> src/utils/helpers.py       (2.3 KB, modificado há 2h)
  src/utils/auth.py          (1.8 KB, modificado há 1d)
  src/utils/database.py      (4.1 KB, modificado há 3d)
  tests/test_utils.py        (900 B, modificado há 1w)

[↑↓] navegar  [/] buscar  [Tab] multi-seleção  [Enter] abrir
```

### 6.4 Streaming de Pensamento
```
🤔 Pensando...
├─ Analisando pedido do usuário
├─ Buscando arquivos relevantes com glob_files
├─ Lendo src/config.py para entender estrutura
├─ Planejando edição em 3 etapas
└─ Pronto para executar

✅ Plano definido. Posso prosseguir? [y/n]
```

---

## 📅 CRONOGRAMA DETALHADO

| Fase | Duração | Entregáveis Principais | Prioridade |
|------|---------|------------------------|------------|
| **Fase 1** | 4 dias | list_dir, glob_files, search_code, run_shell (terminal interativo) | 🔴 CRÍTICA |
| **Fase 2** | 5 dias | web_search (validação), fetch_url, search_github + 4 GitHub Skills | 🔴 CRÍTICA |
| **Fase 3** | 3 dias | write_file (validação), edit_file (diff visual), delete_file (seguro) | 🟡 ALTA |
| **Fase 4** | 3 dias | Context manager, retry, logs estruturados | 🟡 ALTA |
| **Fase 5** | 2 dias | manage_tasks em loop com persistência | 🟢 MÉDIA |
| **Fase 6** | 5 dias | Dashboard, file picker, streaming pensamento, UI refinada | 🟢 MÉDIA |
| **Integração** | 3 dias | Testes end-to-end, bugs fixes, performance | 🟡 ALTA |
| **Total** | **25 dias** | | |

---

## 🎯 MÉTRICAS DE SUCESSO

### Navegação Windows
- [ ] Agente nunca se perde em projetos >10k arquivos
- [ ] 95% de precisão em buscas de arquivos ("onde tá X?")
- [ ] <2 segundos para listar diretórios grandes

### Web Search
- [ ] 80% dos searches retornam informação útil (score >6/10)
- [ ] Máximo de 2 reformulações automáticas antes de admitir falha
- [ ] Zero alucinações (informações inventadas)

### Terminal Interativo
- [ ] Ctrl+R entra no terminal sem matar sessão
- [ ] Ctrl+C mata processo, não o agente
- [ ] Detecção automática de servidores em loop

### Edição de Arquivos
- [ ] 90% de precisão no fuzzy match (encontra linha certa)
- [ ] Diff visual em 100% das edições
- [ ] Zero edições acidentais em arquivos errados

### GitHub Skills
- [ ] Clone + setup funcionando em 5 tipos de projetos (Node, Python, Rust, Go, Java)
- [ ] Commit/push com autenticação SSH e HTTPS
- [ ] Criação de PR com descrição automática

---

## 🚀 PRÓXIMOS PASSOS IMEDIATOS

1. **Hoje:** Implementar `run_shell` com terminal interativo (Feature Gemini CLI)
2. **Amanhã:** Reescrever `web_search` com validação e re-pesquisa
3. **Dia 3:** Criar GitHub Skills especializadas
4. **Dia 4:** Implementar diff visual no `edit_file`
5. **Dia 5:** Testes end-to-end das tools críticas

---

## ⚠️ RISCOS E MITIGAÇÕES

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Web search ainda retorna lixo | Alto | Limitar fontes, validar score, admitir falha cedo |
| Terminal interativo buga no Windows | Médio | Testar extensivamente em PowerShell e CMD |
| Fuzzy match edita arquivo errado | Alto | Sempre mostrar diff e pedir confirmação |
| GitHub Skills requerem token | Baixo | Funcionalidade básica sem token, premium com token |
| Performance cai com muitas tools | Médio | Lazy loading de tools, cache agressivo |

---

**STATUS:** Plano aprovado e detalhado. Pronto para implementação!
