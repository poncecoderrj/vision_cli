# Agente CLI (Estilo Claude CLI)

Uma interface de linha de comando baseada em inteligência artificial construída com foco em UI/UX e controle de segurança para execução de ferramentas no sistema local do usuário.

## Principais Funcionalidades

- **Experiência Visual Rica**: Utiliza `rich` para mostrar status de "pensamento", formatação em Markdown (tabelas, listas, código com cores) e layout organizado.
- **Sistema de Segurança de Comandos**: Antes de qualquer comando de shell (powershell, bash) ser executado no seu PC, um menu de aprovação aparecerá bloqueando a execução:
  - `[1] Permitir uma vez`: O comando roda, mas se o agente precisar usar o comando de novo, vai perguntar novamente.
  - `[2] Sempre permitir`: Cria uma *whitelist* e não pergunta mais sobre este exato comando.
  - `[3] Cancelar`: Intercepta o comando e o agente entende que não tem permissão para fazer aquilo.
- **Pesquisa Inteligente na Web**: Uma ferramenta gratuita baseada no DuckDuckGo para recuperar informações frescas.
- **Gerenciador de Tarefas Embutido**: O agente pode criar pequenas listas de tarefas localmente na memória para não se perder durante requisições muito longas e complexas.

## Configuração do Ambiente

Por padrão, esta CLI pode utilizar qualquer modelo da OpenAI ou modelos rodando localmente no seu computador (via Ollama, LM Studio, etc).

1. Na raiz deste projeto, você tem o arquivo de exemplo `.env`.
2. Altere o `.env` ou configure as seguintes variáveis:
   - Se for usar **OpenAI**: Defina `OPENAI_API_KEY=sk-...` e `MODEL_NAME=gpt-4o-mini`.
   - Se for usar **Ollama Local**: Defina `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama` e defina seu `MODEL_NAME` (ex: `llama3`, `mistral`).

## Como Iniciar

Este projeto requer as dependências que já estão instaladas no seu ambiente virtual. Para inicializar, certifique-se de ativar o ambiente:

### No Windows:
```powershell
.\.venv\Scripts\activate
python main.py
```

### No Linux/Mac:
```bash
source .venv/bin/activate
python main.py
```

## Como Testar
- Digite: `"O que está acontecendo nas notícias de IA hoje?"` (Para testar o *Spinner* rico na interface e a pesquisa web).
- Digite: `"Use o terminal para listar os arquivos do desktop."` (Para testar a segurança com as opções 1, 2 e 3).
