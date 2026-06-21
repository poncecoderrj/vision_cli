# Como Iniciar o Agente CLI

## Método Rápido (Recomendado)

Basta clicar duas vezes no arquivo **`vision.bat`** na pasta do projeto.

O script fará automaticamente:
1. ✅ Verificar se o Python está instalado
2. ✅ Criar ambiente virtual (.venv) se não existir
3. ✅ Instalar/atualizar todas as dependências
4. ✅ Iniciar o agente CLI

## Requisitos

- **Python 3.8 ou superior**
- Windows 10/11

## Comandos Úteis

### Atalhos no Agente

| Tecla | Ação |
|-------|------|
| `/` + Tab | Menu de comandos e skills |
| `@` + Tab | Menu de arquivos e pastas |
| Shift+Tab | Alternar modo (aprovação/plano/automático) |
| Enter | Enviar mensagem |
| Ctrl+C | Sair do agente |

### Skills Disponíveis

- `/react` - Criar projeto React/Vite
- `/api` - Criar API
- `/debug` - Debuggar código
- `/refactor` - Refatorar código
- `/scraper` - Criar scraper

## Solução de Problemas

### "Python não encontrado"
Instale o Python em: https://python.org/downloads/

### Erro ao criar ambiente virtual
Execute manualmente:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Dependências desatualizadas
Delete a pasta `.venv` e execute o `vision.bat` novamente.
