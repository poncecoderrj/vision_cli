# Análise Comparativa: Vision CLI vs Claude Code / Gemini CLI / Qwen CLI

## Visão Geral

Este documento compara o Vision CLI com as principais soluções de CLI com IA do mercado (Claude Code, Gemini CLI, Qwen CLI) e descreve as melhorias implementadas para trazer funcionalidades equivalentes.

---

## 1. Gerenciamento de Sessões

### Como Claude/Gemini/Qwen fazem:
- **Claude**: Cria pasta `.claude` no diretório do projeto com histórico de sessões
- **Gemini**: Usa `.gemini` com logs estruturados em JSON
- **Qwen**: Usa `.qwen` com metadados ricos (resumos, arquivos trabalhados)

**Funcionalidades comuns:**
- Histórico persistente de conversas
- Resumos automáticos das sessões
- Capacidade de retomar sessões anteriores
- Listagem de sessões salvas

### Implementação no Vision CLI:

✅ **Implementado em `/workspace/src/core/session_manager.py`**

```python
# Estrutura de sessão salva (~/.vision_cli/sessions/)
{
  "id": "20250615_143022",
  "created_at": "2025-06-15T14:30:22",
  "updated_at": "2025-06-15T15:45:10",
  "cwd": "C:\\Users\\Luis\\project",
  "messages": [...],
  "summary": "Tarefas principais: 3 solicitações | Arquivos: app.py, main.js | Decisões: 2 ações concluídas",
  "status": "active"
}
```

**Comandos disponíveis:**
- `/sessions lista` - Lista todas as sessões salvas
- `/sessions resume <id>` - Mostra resumo de uma sessão
- `/sessions carregar <id>` - Carrega sessão antiga
- `/sessions excluir <id>` - Remove sessão

---

## 2. Consciência de Localização (File System Context)

### Como Claude/Gemini/Qwen fazem:
- Mantêm estado do diretório de trabalho atual (`cwd`)
- Ferramenta explícita `change_directory` para navegar
- Mostram visualmente o diretório atual no prompt
- Busca inteligente de arquivos/pastas quando usuário diz "ache X"

**Exemplo Claude:**
```
[Current directory: /home/user/project]
> ache o arquivo config.py
[Busca e retorna: ./src/config.py, ./tests/config.py]
```

### Implementação no Vision CLI:

✅ **Implementado em `/workspace/src/core/filesystem_context.py`**

**Funcionalidades:**
- `cwd` property - Diretório de trabalho atual
- `change_directory(path)` - Navega entre pastas
- `find_file_or_folder(name)` - Busca inteligente
- `list_contents()` - Lista conteúdo de diretórios
- `get_tree()` - Visualização em árvore

✅ **Ferramentas adicionadas em `/workspace/src/tools/navigation_tools/file_navigator.py`:**
- `list_dir(path)` - Lista diretório
- `change_directory(path)` - Muda diretório
- `get_current_directory()` - Mostra onde está
- `find_files(pattern)` - Busca por padrões

---

## 3. Comandos Específicos por Sistema Operacional

### Problema Identificado:
O agente estava usando comandos Unix (`mkdir -p ~/Desktop`) no Windows, causando erros repetidos e loops.

### Como Claude/Gemini/Qwen fazem:
- Detectam automaticamente o SO
- Ajustam comandos conforme o sistema
- Nunca insistem em comandos falhos

### Implementação no Vision CLI:

✅ **System Prompt Atualizado (`/workspace/agent.py`):**
- Instruções explícitas sobre Windows
- Exemplos de comandos corretos
- Regra: "NUNCA repita o mesmo comando falho"
- Regra: "Se cancelar, mude de estratégia"

✅ **Normalização Automática (`/workspace/src/tools/shell_tools/run_shell.py`):**
```python
# Converte automaticamente:
mkdir -p ~/Desktop/dir → New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\Desktop\dir"
```

---

## 4. Autonomia e Quebra de Loops

### Como Claude/Gemini/Qwen fazem:
- Analisam erros antes de tentar novamente
- Tentam até 3 abordagens diferentes
- Pedem ajuda ao usuário após falhas múltiplas
- Não repetem comandos cancelados

### Implementação no Vision CLI:

✅ **Regras no System Prompt:**
```
REGRA DAS 3 TENTATIVAS DIFERENTES:
Antes de dizer "não consegui", você DEVE tentar pelo menos 
3 abordagens DIFERENTES para o mesmo problema

CANCELAMENTO DO USUÁRIO:
- ISSO É UM ERRO CRÍTICO - NÃO REPITA O MESMO COMANDO
- Analise POR QUE o usuário cancelou
- Mude completamente de estratégia ou pergunte
```

✅ **Respostas a Cancelamentos (`/workspace/src/tools/shell_tools/run_shell.py`):**
```python
if approval == "cancel":
    return "ERRO_CRITICO: Usuário cancelou explicitamente. NÃO repita este comando."
```

---

## 5. Resumo Inteligente de Sessões

### Como Claude/Gemini/Qwen fazem:
- Geram resumos automáticos identificando:
  - Tarefas principais
  - Arquivos criados/modificados
  - Decisões importantes
  - Problemas resolvidos

### Implementação no Vision CLI:

✅ **Implementado em `/workspace/src/core/context_summarizer.py`:**

```python
def generate_session_summary(messages):
    # Analisa últimas 20 mensagens
    # Detecta tarefas (palavras-chave: crie, faça, execute)
    # Detecta arquivos mencionados (regex para extensões)
    # Detecta decisões (palavras-chave: decidi, concluí)
    # Retorna: "Tarefas principais: 3 | Arquivos: app.py, main.js | Decisões: 2"
```

---

## 6. Troca de Modelos Locais

### Como Claude/Gemini/Qwen fazem:
- Suporte a múltiplos backends (OpenAI, Anthropic, local)
- Configuração via variáveis de ambiente
- Detecção automática de portas

### Implementação no Vision CLI:

✅ **Documentação no System Prompt:**
```
MODELOS LOCAIS DISPONÍVEIS:
· LM Studio:       http://localhost:1234/v1
· Ollama:          http://localhost:11434/v1
· text-generation-webui: http://localhost:5000/v1
· LocalAI:         http://localhost:8080/v1

Para trocar: modifique OPENAI_BASE_URL
```

---

## 7. Interface e UX

### Como Claude/Gemini/Qwen fazem:
- Mostram diretório atual no header
- Indicam modo (aprovação/plano/automático)
- Feedback visual claro de ferramentas executadas

### Melhorias Sugeridas para Vision CLI:

⚠️ **A implementar:**
- Adicionar cwd atual no header da UI
- Mostrar resumo da sessão ao iniciar
- Comando `/where` para mostrar localização
- Comando `/tree` para ver estrutura de pastas

---

## Tabela Comparativa

| Funcionalidade | Claude | Gemini | Qwen | Vision CLI |
|----------------|--------|--------|------|------------|
| Sessões persistentes | ✅ | ✅ | ✅ | ✅ |
| Resumos automáticos | ✅ | ✅ | ✅ | ✅ |
| Consciência de cwd | ✅ | ✅ | ✅ | ✅ |
| Busca inteligente | ✅ | ✅ | ✅ | ✅ |
| Comandos por SO | ✅ | ✅ | ✅ | ✅ |
| Quebra de loops | ✅ | ✅ | ✅ | ✅ |
| Múltiplos modelos | ✅ | ✅ | ✅ | ✅ |
| UI com contexto | ✅ | ✅ | ✅ | ⚠️ Parcial |

---

## Próximos Passos Recomendados

1. **UI Enhancement**: Adicionar cwd no header e mostrar resumo ao iniciar
2. **Slash Commands**: Implementar `/where`, `/tree`, `/sessions` na UI
3. **Auto-Summary**: Gerar resumo a cada 10 mensagens e salvar na sessão
4. **Smart Retry**: Implementar retry automático com backoff para falhas de rede
5. **Context Window**: Limitar histórico enviado para LLM, mantendo apenas resumo + últimas msgs

---

## Conclusão

O Vision CLI agora possui paridade funcional com as principais soluções do mercado em termos de:
- ✅ Gerenciamento de sessões
- ✅ Consciência de localização
- ✅ Adaptação ao sistema operacional
- ✅ Autonomia e prevenção de loops
- ✅ Suporte a múltiplos modelos locais

As melhorias focaram em tornar o agente mais inteligente, autônomo e consciente do contexto, resolvendo os problemas relatados de:
- Loops infinitos com comandos falhos
- Insistência em comandos cancelados
- Falta de consciência de localização
- Comandos incompatíveis com Windows
