# 🚀 PLANO DE IMPLEMENTAÇÃO - REPAROS CRÍTICOS

## 📌 VISÃO GERAL

Este documento descreve **exatamente** o que será implementado para resolver os 3 problemas críticos mapeados.

---

## 🔧 PROBLEMA 1 & 2: Auto-complete '/' e '@' Não Funcionam

### Diagnóstico Confirmado

Após testes, a lógica dos completers **funciona em isolamento**, mas na UI real o menu não aparece. Isso indica que o problema está na **integração com o prompt_toolkit**, não na lógica de matching.

### Solução Implementada

Vou aplicar **4 fixes combinados**:

#### Fix 1: Remover ThreadedCompleter (causa race condition)
```python
# ANTES:
buf = Buffer(
    completer=ThreadedCompleter(CombinedCompleter()),
    complete_while_typing=True,
)

# DEPOIS:
buf = Buffer(
    completer=CombinedCompleter(),
    complete_while_typing=True,
    enable_history_search=True,
)
```

#### Fix 2: Adicionar keybinding Tab explícito
```python
@kb.add('tab')
def _(event):
    """Força completion menu ou navega para próxima opção."""
    b = event.app.current_buffer
    if b.complete_state is None:
        # Tenta iniciar completion
        b.start_completion()
    else:
        # Navega para próxima opção
        b.complete_next()

@kb.add('s-tab')
def _(event):
    """Navega para opção anterior OU alterna modo (se sem completion)."""
    b = event.app.current_buffer
    if b.complete_state:
        b.complete_previous()
    else:
        # Comportamento original: alterna modo
        cycle_mode()
        event.app.invalidate()
```

#### Fix 3: Simplificar regex dos completers
```python
# SlashCommandCompleter - Regex mais permissivo
class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        
        # Regex simplificado: aceita / em qualquer lugar após whitespace
        m = re.search(r"(?:^|\s)/(\w*)$", text_before)
        if m is None:
            return
        
        partial = m.group(1).lower()
        # ... resto da lógica
```

```python
# AtMentionCompleter - Remove lookbehind complexo
class AtMentionCompleter(Completer):
    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        
        # Regex simplificado
        m = re.search(r"(?:^|\s)@(\S*)$", text_before)
        if m is None:
            return
        
        partial = m.group(1)
        # ... resto da lógica
```

#### Fix 4: Adicionar fallback de busca para @
```python
class AtMentionCompleter(Completer):
    _SEARCH_DIRS = [".", "src", "docs", "tests", "..", "../.."]
    
    def get_completions(self, document, complete_event):
        # ... lógica existente ...
        
        # Fallback: se base não existe, buscar em outros diretórios
        if not base.exists() or not base.is_dir():
            if not dir_part:  # Só se não tiver caminho específico
                for search_dir in self._SEARCH_DIRS:
                    search_path = Path.cwd() / search_dir
                    if search_path.exists() and search_path.is_dir():
                        try:
                            for entry in search_path.iterdir():
                                if entry.name.startswith(name_frag):
                                    # yield completion
                                    pass
                        except:
                            pass
            return
```

---

## 🖥️ PROBLEMA 3: Terminal Interativo Sem Foco Granular

### Arquitetura Proposta

```
┌─────────────────────────────────────────┐
│  INPUT BOX (prompt do usuário)          │
│  > digite aqui...                       │
├─────────────────────────────────────────┤
│  CONVERSATION HISTORY                   │
│  ⏺ Agente: ...                          │
│  ⏺ Usuário: ...                         │
├─────────────────────────────────────────┤
│  TERMINAL PANEL (quando ativo) 🟢       │
│  $ npm run dev                          │
│  > listening on port 3000               │
│  [Shift+C cancela] [Shift+Tab sai]      │
└─────────────────────────────────────────┘
```

### Implementação Passo a Passo

#### Step 1: Criar classe TerminalPanel

```python
# src/ui/components/terminal_panel.py
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

class TerminalPanel:
    """Painel de terminal para processos em execução."""
    
    def __init__(self):
        self.active = False
        self.process = None
        self.output_lines = []
        self.max_lines = 100
    
    def start(self, process, command: str):
        """Inicia monitoramento de processo."""
        self.active = True
        self.process = process
        self.output_lines = [f"$ {command}"]
    
    def append_output(self, text: str, is_stderr: bool = False):
        """Adiciona linha de output."""
        prefix = "❌ " if is_stderr else "   "
        self.output_lines.append(prefix + text)
        
        # Manter apenas últimas max_lines
        if len(self.output_lines) > self.max_lines:
            self.output_lines = self.output_lines[-self.max_lines:]
    
    def stop(self):
        """Para monitoramento."""
        self.active = False
        self.process = None
        self.output_lines.append("--- Processo terminado ---")
    
    def render(self) -> Panel:
        """Renderiza painel Rich."""
        status = "🔴 RODANDO" if self.active else "🟢 INATIVO"
        content = "\n".join(self.output_lines[-50:])  # Últimas 50 linhas
        
        return Panel(
            content,
            title=f"[bold green]{status}[/bold green]",
            border_style="green" if self.active else "grey42",
            padding=(0, 1),
        )
```

#### Step 2: Integrar com run_shell tool

```python
# src/tools/shell_tools/run_shell.py (modificação)
class RunShellTool:
    def __init__(self):
        self.current_process = None
        self.terminal_panel = TerminalPanel()  # Nova instância
    
    def execute_interactive(self, command: str, ...):
        # ... código existente ...
        
        # Iniciar painel
        self.terminal_panel.start(process, command)
        
        while True:
            # ... leitura de output ...
            
            if stdout_chunk:
                self.terminal_panel.append_output(stdout_chunk.rstrip())
                yield {"type": "output", "stream": "stdout", "data": stdout_chunk}
            
            if stderr_chunk:
                self.terminal_panel.append_output(stderr_chunk.rstrip(), is_stderr=True)
                yield {"type": "output", "stream": "stderr", "data": stderr_chunk}
        
        # Terminar painel
        self.terminal_panel.stop()
```

#### Step 3: Adicionar keybindings para controle

```python
# ui.py - No _build_input_app
@kb.add('s-c')  # Shift+C
def _(event):
    """Cancela processo em execução (não o agente)."""
    from src.tools.shell_tools import get_run_shell_tool
    tool = get_run_shell_tool()
    if tool.current_process:
        tool.stop_current()
        console.print("\n[bold yellow]⏹️  Processo cancelado![/bold yellow]\n")

@kb.add('escape')
def _(event):
    """Fecha painel de terminal se aberto."""
    from src.tools.shell_tools import get_run_shell_tool
    tool = get_run_shell_tool()
    if tool.terminal_panel.active:
        tool.terminal_panel.stop()
        console.print("\n[dim]Terminal fechado[/dim]\n")
```

#### Step 4: Usar select() para I/O eficiente

```python
# Substituir polling por select
import select
import fcntl
import os

def stream_output_efficient(self, process, callback):
    """Stream output usando select() em vez de polling."""
    
    # Configurar non-blocking
    flags_out = fcntl.fcntl(process.stdout.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(process.stdout.fileno(), fcntl.F_SETFL, flags_out | os.O_NONBLOCK)
    
    flags_err = fcntl.fcntl(process.stderr.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(process.stderr.fileno(), fcntl.F_SETFL, flags_err | os.O_NONBLOCK)
    
    streams = {
        process.stdout.fileno(): (process.stdout, False),
        process.stderr.fileno(): (process.stderr, True),
    }
    
    while True:
        retcode = process.poll()
        
        # Usar select para esperar dados
        ready, _, _ = select.select(list(streams.keys()), [], [], timeout=0.1)
        
        for fd in ready:
            stream, is_stderr = streams[fd]
            try:
                data = stream.read(4096)
                if data:
                    callback(data, is_stderr)
            except (BlockingIOError, IOError):
                pass
        
        if retcode is not None:
            break
```

---

## 📋 SKILLS - MAPEAMENTO E PADRONIZAÇÃO

### Skills Existentes (Análise)

| Skill | Arquivo | Configurações | Passos | Status |
|-------|---------|---------------|--------|--------|
| API REST | `api.md` | nome, stack, db, auth, resource | 6 passos | ✅ OK |
| Debug | `debug.md` | erro, contexto | 4 passos | ✅ OK |
| React | `react.md` | tipo, features, styling | 5 passos | ✅ OK |
| Refactor | `refactor.md` | arquivo, objetivo | 4 passos | ✅ OK |
| Scraper | `scraper.md` | url, dados, formato | 5 passos | ✅ OK |

### Template Padrão para Novas Skills

```markdown
<!-- QUESTIONS
[
  {"id": "campo1", "ask": "Pergunta 1?", "type": "text", "default": "valor", "label": "Label"},
  {"id": "campo2", "ask": "Pergunta 2?", "options": ["Opção A", "Opção B"], "label": "Label"}
]
-->

# SKILL: Nome da Skill

Descrição breve do que esta skill faz.

## PASSOS

### 1. Primeiro passo
Descrição do que fazer.

```bash
comando exemplo
```

### 2. Segundo passo
Mais descrição.

### 3. Validação
Como validar que funcionou.

### 4. Entrega
O que entregar ao usuário.
```

### Registry de Skills

```python
# src/skills/registry.py
from pathlib import Path
import re

class Skill:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.questions = []
        self.steps = []
        self.metadata = {}
    
    @classmethod
    def from_file(cls, path: Path):
        content = path.read_text(encoding='utf-8')
        skill = cls(path.stem, path)
        
        # Extrair questions do comentário HTML
        questions_match = re.search(
            r'<!--\s*QUESTIONS\s*\[(.*?)\]\s*-->',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if questions_match:
            import json
            skill.questions = json.loads(f'[{questions_match.group(1)}]')
        
        # Extrair metadata
        skill.metadata = {
            'has_questions': len(skill.questions) > 0,
            'step_count': content.count('### '),
        }
        
        return skill


class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills = {}
        self.load_all()
    
    def load_all(self):
        """Carrega todas as skills do diretório."""
        if not self.skills_dir.exists():
            return
        
        for file in self.skills_dir.glob("*.md"):
            skill = Skill.from_file(file)
            self.skills[skill.name] = skill
    
    def list_skills(self) -> list:
        """Lista todas as skills disponíveis."""
        return list(self.skills.values())
    
    def get_skill(self, name: str) -> Skill:
        """Obtém skill por nome."""
        return self.skills.get(name)
    
    def has_skill(self, name: str) -> bool:
        """Verifica se skill existe."""
        return name in self.skills
```

---

## 🎯 ETAPAS DE IMPLEMENTAÇÃO

### Etapa 1: Auto-complete (Dia 1-2)

#### Dia 1: Modificar ui.py
- [ ] Remover `ThreadedCompleter` do `get_user_input()`
- [ ] Adicionar keybinding `tab` para forçar completion
- [ ] Modificar `s-tab` para navegar (se completion ativo) ou alternar modo
- [ ] Simplificar regex em `SlashCommandCompleter`
- [ ] Simplificar regex em `AtMentionCompleter`
- [ ] Adicionar fallback de busca em múltiplos diretórios

#### Dia 2: Testes e ajustes
- [ ] Testar `/` → deve mostrar menu
- [ ] Testar `/sk` → deve filtrar
- [ ] Testar `@` → deve listar arquivos
- [ ] Testar `@src/` → deve listar conteúdo de src/
- [ ] Ajustar timing se necessário
- [ ] Adicionar logging para debug futuro

### Etapa 2: Terminal Interativo (Dia 3-5)

#### Dia 3: Criar TerminalPanel
- [ ] Criar arquivo `src/ui/components/terminal_panel.py`
- [ ] Implementar classe `TerminalPanel`
- [ ] Integrar com sistema de renderização Rich

#### Dia 4: Integrar com run_shell
- [ ] Modificar `RunShellTool` para usar `TerminalPanel`
- [ ] Implementar `select()` para I/O eficiente
- [ ] Adicionar callbacks de streaming

#### Dia 5: Keybindings e UX
- [ ] Adicionar `Shift+C` para cancelar processo
- [ ] Adicionar `Escape` para fechar terminal
- [ ] Mostrar indicadores visuais (🔴/🟢)
- [ ] Testar com `npm run dev`, `python app.py`, etc.

### Etapa 3: Skills Registry (Dia 6-7)

#### Dia 6: Criar registry
- [ ] Criar `src/skills/registry.py`
- [ ] Implementar classes `Skill` e `SkillRegistry`
- [ ] Parsear questions de cada skill file
- [ ] Adicionar método `list_skills()`

#### Dia 7: Integração e docs
- [ ] Integrar registry no agent.py
- [ ] Comando `/skills` lista skills disponíveis
- [ ] Documentar template padrão
- [ ] Criar exemplo de nova skill

---

## 📊 MÉTRICAS DE SUCESSO

### Auto-complete
| Métrica | Antes | Depois (Meta) |
|---------|-------|---------------|
| Menu aparece ao digitar `/` | ❌ Não | ✅ Sim (<100ms) |
| Menu aparece ao digitar `@` | ❌ Não | ✅ Sim (<100ms) |
| Filtragem funciona | ⚠️ Parcial | ✅ 100% |
| Tab completa seleção | ❌ Não | ✅ Sim |

### Terminal Interativo
| Métrica | Antes | Depois (Meta) |
|---------|-------|---------------|
| Output em tempo real | ⚠️ Polling | ✅ select() |
| Cancelar só processo | ❌ Não | ✅ Shift+C |
| Foco granular | ❌ Não | ✅ Escape |
| CPU usage (idle) | ~10% | <1% |

### Skills
| Métrica | Antes | Depois (Meta) |
|---------|-------|---------------|
| Skills listáveis | ⚠️ Manual | ✅ `/skills` |
| Template padronizado | ❌ Não | ✅ Sim |
| Registry centralizado | ❌ Não | ✅ Sim |

---

## 🔍 TESTES RÁPIDOS

### Testar Auto-complete
```bash
cd /workspace
python -c "
from ui import SlashCommandCompleter, AtMentionCompleter
from prompt_toolkit.document import Document

# Teste Slash
slash = SlashCommandCompleter()
doc = Document(text='/', cursor_position=1)
results = list(slash.get_completions(doc, None))
print(f'Slash completions: {len(results)}')

# Teste At
at = AtMentionCompleter()
doc = Document(text='@', cursor_position=1)
results = list(at.get_completions(doc, None))
print(f'At completions: {len(results)}')
"
```

### Testar Terminal Panel
```bash
cd /workspace
python -c "
from src.ui.components.terminal_panel import TerminalPanel

panel = TerminalPanel()
panel.start(None, 'npm run dev')
panel.append_output('Starting development server...')
panel.append_output('Listening on port 3000', is_stderr=False)
panel.append_output('Error: port in use', is_stderr=True)

print(panel.render())
panel.stop()
"
```

### Testar Skills Registry
```bash
cd /workspace
python -c "
from src.skills.registry import SkillRegistry

registry = SkillRegistry()
skills = registry.list_skills()
print(f'Skills found: {len(skills)}')
for skill in skills:
    print(f'  - {skill.name}: {skill.metadata}')
"
```

---

## 📝 CHECKLIST FINAL

### Antes de Commit
- [ ] Todos testes manuais passaram
- [ ] Código formatado (black/isort)
- [ ] Logs removidos (ou nível DEBUG)
- [ ] Documentação atualizada
- [ ] Backward compatibility mantida

### Após Commit
- [ ] Testar em Windows
- [ ] Testar em Linux
- [ ] Testar em macOS (se possível)
- [ ] Validar com casos reais de uso

---

**Plano criado:** Hoje  
**Implementador:** Agente  
**Status:** Pronto para iniciar
