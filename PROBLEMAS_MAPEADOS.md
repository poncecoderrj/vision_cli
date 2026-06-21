# 🔍 PROBLEMAS MAPEADOS - AGENTE CLI

## 📋 RESUMO EXECUTIVO

Foram identificados **3 problemas críticos** que impedem a UX adequada do agente:

1. **Auto-complete '/' não aparece ao digitar** ❌
2. **Auto-complete '@' não cita arquivos** ❌  
3. **Terminal interativo para servidores não tem foco granular com Shift** ❌

---

## 🐛 PROBLEMA 1: Auto-complete '/' Não Aparece

### Sintoma
Quando o usuário digita `/` no input, o menu de auto-complete **não aparece**, mesmo com `complete_while_typing=True`.

### Causa Raiz
Após análise do código em `/workspace/ui.py`:

```python
class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        
        # Regex atual:
        m = re.search(r"(?:^|\s)/(\w*)$", text_before)
        if m is None:
            return  # ❌ PROBLEMA: Se não match, retorna sem yield
        
        partial = m.group(1).lower()
        # ... lógica de completions
```

**Problemas identificados:**

1. **Regex muito restritivo**: O pattern `(?:^|\s)/(\w*)$` exige que `/` esteja no início OU após whitespace, mas o `$` no final pode não casar corretamente dependendo do estado do buffer.

2. **Falta de debug/logging**: Não há como saber se o completer está sendo chamado.

3. **ThreadedCompleter pode estar causando race condition**: O `ThreadedCompleter` executa em thread separada e pode não estar disparando no timing correto.

4. **complete_while_typing=True pode não ser suficiente**: Prompt_toolkit às vezes requer configuração adicional para mostrar o menu automaticamente.

### Evidências de Teste
```bash
# Teste manual mostrou que a lógica FUNCIONA:
Text: '/' -> Slash match: '' (partial vazio, todos os commands aparecem)
Text: '/s' -> Slash match: 's' (filtra por 's')
```

Mas na UI real, o menu **não aparece**.

### Solução Proposta

#### Opção A: Forçar exibição do menu
Adicionar configuração explícita para sempre mostrar menu quando houver trigger:

```python
def _build_input_app(buf: Buffer) -> Application:
    # ... existing code ...
    
    @kb.add('tab')
    def _(event):
        # Força mostrar completion menu
        b = event.app.current_buffer
        if b.complete_state is None:
            b.start_completion()
        else:
            b.complete_next()
    
    return Application(
        layout=Layout(body, focused_element=input_window),
        key_bindings=kb,
        style=_PT_STYLE,
        full_screen=False,
        mouse_support=False,
        erase_when_done=True,
    )
```

#### Opção B: Usar FuzzyMatcher para melhor matching
```python
from prompt_toolkit.completion import FuzzyMatcher

class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        
        # Regex mais permissivo
        m = re.search(r"/(\w*)$", text_before)
        if m is None:
            return

        partial = m.group(1).lower()
        
        # ... rest of logic ...
        
        # Usar fuzzy matcher para melhor experiência
        matcher = FuzzyMatcher()
        for name, description in all_options:
            if matcher.match(name.lower(), partial):
                yield Completion(...)
```

#### Opção C: Adicionar logging para debug
```python
import logging
logger = logging.getLogger(__name__)

class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        logger.debug(f"get_completions called! text={repr(document.text)}, cursor={document.cursor_position}")
        logger.debug(f"text_before_cursor={repr(document.text_before_cursor)}")
        
        # ... rest of logic ...
        
        if m is None:
            logger.debug("No regex match!")
            return
        
        logger.debug(f"Match found! partial={partial}")
```

---

## 🐛 PROBLEMA 2: Auto-complete '@' Não Cita Arquivos

### Sintoma
Quando o usuário digita `@` no input, espera-se que apareçam sugestões de arquivos/diretórios, mas **nada aparece**.

### Causa Raiz

```python
class AtMentionCompleter(Completer):
    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        
        # Regex atual:
        m = re.search(r"(?:^|(?<=\s))@(\S*)$", text_before)
        if m is None:
            return
        
        partial = m.group(1)
        # ... lógica de busca de arquivos
```

**Problemas identificados:**

1. **Lookbehind assertion `(?<=\s)` pode falhar**: Em alguns casos, o lookbehind não funciona como esperado no prompt_toolkit.

2. **Base path sempre usa cwd**: Se o usuário estiver em diretório sem muitos arquivos, poucas sugestões aparecem.

3. **Mesmo problema do ThreadedCompleter**: Pode não estar disparando corretamente.

4. **Falta de fallback**: Se não encontrar arquivos no cwd, não busca em lugares comuns.

### Evidências de Teste
```bash
# Teste manual mostrou que a lógica FUNCIONA:
Text: '@' -> MATCH! partial='' -> YIELDING: skills/, src/, agent.py...
Text: '@f' -> MATCH! partial='f' -> Results count: 0 (nenhum arquivo começa com 'f')
```

Mas na UI real, o menu **não aparece**.

### Solução Proposta

#### Opção A: Simplificar regex
```python
# Regex atual (complexo):
m = re.search(r"(?:^|(?<=\s))@(\S*)$", text_before)

# Regex simplificado:
m = re.search(r"(?:^|\s)@(\S*)$", text_before)
```

#### Opção B: Adicionar busca em múltiplos diretórios
```python
class AtMentionCompleter(Completer):
    _SEARCH_DIRS = [".", "src", "docs", "tests", ".."]
    
    def get_completions(self, document, complete_event):
        # ... existing logic ...
        
        # Se não achar no cwd, buscar em outros diretórios
        if not base.exists():
            for search_dir in self._SEARCH_DIRS:
                search_path = Path.cwd() / search_dir
                if search_path.exists():
                    # buscar arquivos lá
                    pass
```

#### Opção C: Adicionar caching para performance
```python
from functools import lru_cache

class AtMentionCompleter(Completer):
    @lru_cache(maxsize=100)
    def _get_file_suggestions(self, dir_path: str, prefix: str):
        # Cache de sugestões por diretório + prefixo
        pass
```

---

## 🐛 PROBLEMA 3: Terminal Interativo Sem Foco Granular

### Sintoma
Quando o agente roda um servidor (ex: `npm run dev`), o usuário quer:
- Ver o output em tempo real
- Poder cancelar APENAS aquele terminal (com Shift+C ou similar)
- Não cancelar o agente inteiro

Atualmente:
- Ou o comando roda e bloqueia tudo
- Ou Ctrl+C mata o agente inteiro

### Causa Raiz

Analisando `/workspace/src/tools/shell_tools/run_shell.py`:

```python
def execute_interactive(self, command: str, ...) -> Generator[Dict, None, ShellExecutionResult]:
    # Cria subprocess com pipes
    process = subprocess.Popen(
        shell_cmd + [command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        ...
    )
    
    # Lê output em loop
    while True:
        retcode = process.poll()
        if retcode is not None:
            break
        
        # Lê stdout/stderr
        # ...
        
        # Checa se deve parar
        if self._stop_event.is_set():
            process.terminate()
            break
        
        time.sleep(0.1)  # ❌ Problema: polling ineficiente
```

**Problemas identificados:**

1. **Não há integração com UI para foco granular**: O terminal roda, mas não há como o usuário "entrar" nele com Shift+algo.

2. **Polling ineficiente**: `time.sleep(0.1)` consome CPU e tem latency.

3. **Sem controle de janela de terminal**: Deveria abrir uma janela/painel separado que pode receber foco.

4. **Prompt_toolkit não suporta múltiplos focos nativamente**: Precisaria de arquitetura diferente.

### Solução Proposta

#### Arquitetura Recomendada (baseada em CLIs modernos como Gemini CLI, Cursor):

```
┌─────────────────────────────────────┐
│  AGENTE CLI (prompt principal)      │
│  > user typing here...              │
└─────────────────────────────────────┘

[Servidor iniciado]

┌─────────────────────────────────────┐
│  AGENTE CLI                         │
│  > ...                              │
├─────────────────────────────────────┤
│  🖥️ TERMINAL (npm run dev)          │ ← Foco secundário
│  $ npm run dev                      │
│  > listening on port 3000           │
│  [Ctrl+C mata só este terminal]     │
│  [Shift+Tab volta pro agente]       │
└─────────────────────────────────────┘
```

#### Implementação:

1. **Criar painel de terminal dedicado**:
```python
from prompt_toolkit.layout import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

class TerminalPanel:
    def __init__(self):
        self.output_buffer = []
        self.control = FormattedTextControl(self._get_text)
        self.window = Window(
            content=self.control,
            height=D(weight=1),
        )
    
    def append_output(self, text: str):
        self.output_buffer.append(text)
        self.control.invalidate()
    
    def _get_text(self):
        return "\n".join(self.output_buffer[-50:])  # Last 50 lines
```

2. **Key bindings para foco**:
```python
@kb.add('s-c')  # Shift+C
def _(event):
    # Cancela apenas o processo em execução
    shell_tool.stop_current()

@kb.add('s-tab')  # Shift+Tab
def _(event):
    # Alterna foco entre input e terminal
    toggle_focus()
```

3. **Usar select() em vez de polling**:
```python
import select

def stream_output(self, process):
    # Usa select para I/O eficiente
    streams = [process.stdout, process.stderr]
    
    while True:
        ready, _, _ = select.select(streams, [], [], timeout=0.1)
        for stream in ready:
            line = stream.readline()
            if line:
                yield line
```

---

## 📊 PESQUISA: Como CLIs Inteligentes Agem

### Gemini CLI (Google)
- ✅ **Auto-complete**: Mostra menu automaticamente ao digitar `/` ou `@`
- ✅ **Terminal interativo**: Abre painel separado para processos em loop
- ✅ **Foco granular**: Ctrl+C mata processo, não o CLI
- ✅ **Streaming**: Output em tempo real com cores

### Cursor IDE
- ✅ **Inline suggestions**: Completions aparecem inline (fantasma)
- ✅ **Popup menu**: Tab completa, setas navegam
- ✅ **Terminal integrado**: Painel inferior para comandos longos
- ✅ **Cancelamento**: Escape cancela operação atual

### Claude CLI (Anthropic)
- ✅ **Smart completions**: Context-aware (sugere arquivos relevantes)
- ✅ **Multi-pane**: Separa output do agente vs terminal
- ✅ **Undo/Redo**: Ctrl+Z desfaz última ação

### tldr; Features Essenciais:
1. **Completions sempre visíveis** quando há trigger (`/`, `@`)
2. **Terminal em painel separado** para processos em loop
3. **Controle granular** de cancelamento (só processo, não agente)
4. **Streaming eficiente** (select/async, não polling)

---

## 🎯 PLANO DE AÇÃO PRIORIZADO

### Fase 1: Corrigir Auto-complete (CRÍTICO - 2 dias)

#### Dia 1: Debug e diagnóstico
- [ ] Adicionar logging extensivo nos completers
- [ ] Testar com `ThreadedCompleter` vs `Completer` simples
- [ ] Verificar se `complete_while_typing` está funcionando
- [ ] Testar em diferentes terminais (Windows Terminal, bash, zsh)

#### Dia 2: Implementar fixes
- [ ] **Fix 1**: Simplificar regex dos completers
- [ ] **Fix 2**: Adicionar keybinding Tab para forçar completion
- [ ] **Fix 3**: Configurar `complete_while_typing` corretamente
- [ ] **Fix 4**: Adicionar fallback para busca de arquivos

### Fase 2: Terminal Interativo (ALTA - 3 dias)

#### Dia 3: Arquitetura
- [ ] Criar classe `TerminalPanel` com output streaming
- [ ] Integrar com `run_shell` tool
- [ ] Implementar detecção automática de servidores

#### Dia 4: Controles
- [ ] Keybinding Shift+C para cancelar processo
- [ ] Keybinding Shift+Tab para alternar foco
- [ ] Implementar `select()` para I/O eficiente

#### Dia 5: UX
- [ ] Adicionar indicadores visuais (🔴 vivo, 🟢 terminado)
- [ ] Mostrar PID e porta do servidor
- [ ] Permitir interação direta (digitar no terminal)

### Fase 3: Skills e Processos (MÉDIA - 2 dias)

#### Dia 6: Mapear skills existentes
- [ ] Listar todas as skills em `/skills/*.md`
- [ ] Criar registry centralizado
- [ ] Adicionar metadata (autor, versão, tags)

#### Dia 7: Fluxo de trabalho padronizado
- [ ] Definir template padrão para novas skills
- [ ] Criar wizard de configuração interativo
- [ ] Documentar processo de criação de skills

---

## 📝 SKILLS MAPEADAS

Atualmente em `/workspace/skills/`:

| Skill | Descrição | Status |
|-------|-----------|--------|
| `api.md` | Criador de API REST | ✅ Pronto |
| `debug.md` | Debug assistido | ✅ Pronto |
| `react.md` | Projetos React | ✅ Pronto |
| `refactor.md` | Refatoração de código | ✅ Pronto |
| `scraper.md` | Web scraper | ✅ Pronto |

### Skills Sugeridas (para adicionar):
- [ ] `git.md` - Gestão de repositórios Git
- [ ] `docker.md` - Containerização
- [ ] `test.md` - Geração de testes
- [ ] `deploy.md` - Deploy automatizado
- [ ] `database.md` - Modelagem de banco de dados

---

## 🔧 RECOMENDAÇÕES TÉCNICAS

### 1. Para Auto-complete
```python
# Usar esta configuração no Buffer:
buf = Buffer(
    multiline=True,
    completer=CombinedCompleter(),  # Sem ThreadedCompleter inicialmente
    complete_while_typing=True,
    enable_history_search=True,
    validate_while_typing=False,
)

# E adicionar keybinding explícito:
@kb.add('tab')
def _(event):
    buf = event.app.current_buffer
    if buf.complete_state:
        buf.complete_next()
    else:
        buf.start_completion()
```

### 2. Para Terminal Interativo
```python
# Usar asyncio para I/O não-bloqueante:
import asyncio

async def stream_process(process):
    stdout = asyncio.StreamReader()
    stderr = asyncio.StreamReader()
    
    await asyncio.gather(
        read_stream(stdout, callback),
        read_stream(stderr, callback)
    )
```

### 3. Para Skills
```python
# Registry pattern:
class SkillRegistry:
    def __init__(self):
        self.skills = {}
        self.load_from_dir("skills")
    
    def load_from_dir(self, path: str):
        for file in Path(path).glob("*.md"):
            skill = self.parse_skill(file)
            self.skills[skill.name] = skill
    
    def get_skill(self, name: str) -> Skill:
        return self.skills.get(name)
```

---

## ✅ CRITÉRIOS DE ACEITE

### Auto-complete Funcional
- [ ] Digitar `/` → Menu aparece instantaneamente
- [ ] Digitar `/sk` → Filtra para `skills`
- [ ] Digitar `@` → Lista arquivos do diretório
- [ ] Digitar `@src/` → Lista arquivos dentro de `src/`
- [ ] Pressionar Tab → Completa seleção
- [ ] Pressionar Enter → Usa seleção

### Terminal Interativo Funcional
- [ ] Rodar `npm run dev` → Output em tempo real
- [ ] Pressionar Shift+C → Mata processo, agente continua
- [ ] Pressionar Shift+Tab → Alterna foco input/terminal
- [ ] Servidor detectado → Avisa porta e URL

### Skills Padronizadas
- [ ] Todas skills seguem template padrão
- [ ] Wizard de configuração funciona
- [ ] Skills listadas via `/skills`

---

**Documento criado:** Hoje  
**Próxima ação:** Iniciar Fase 1 - Debug do auto-complete
