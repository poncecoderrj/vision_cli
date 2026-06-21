<!-- QUESTIONS
[
  {"id": "scope",    "ask": "O que quer refatorar?",          "options": ["Um arquivo específico", "Uma função/classe", "O projeto inteiro", "Remover código morto"],       "label": "Escopo"},
  {"id": "language", "ask": "Linguagem principal?",            "options": ["Python", "JavaScript", "TypeScript", "Outra"],                                                  "label": "Linguagem"},
  {"id": "tests",    "ask": "Existem testes automatizados?",   "options": ["Sim (pytest / jest / etc)", "Não"],                                                             "label": "Testes"},
  {"id": "target",   "ask": "Arquivo ou pasta alvo?",          "type": "text", "default": ".",                                                                             "label": "Caminho alvo"}
]
-->

# SKILL: Refatoração de Código

As configurações já foram coletadas. Execute os passos abaixo **em ordem, sem pular**.

## PASSOS

### 1. Mapear o estado atual
```
list_dir("{target}")
glob_files("**/*.py", "{target}")   (ou *.js, *.ts)
```

### 2. Ler o código alvo completo
```
read_file("{target}")
```
**Não edite ainda** — leia tudo primeiro.

### 3. Identificar problemas com search_code
```
search_code("def .*:", "{target}")       # funções longas/duplicadas
search_code("TODO|FIXME|HACK", "{target}")
search_code("import ", "{target}")       # imports não usados
```

### 4. Planejar com manage_tasks
Registre CADA mudança planejada antes de executar:
```
manage_tasks("add", "Extrair função X de Y")
manage_tasks("add", "Renomear variável a → user_id")
manage_tasks("list")
```

### 5. Refatorar uma mudança por vez
- `read_file` → ver trecho exato
- `edit_file` → corrigir com `old_string` preciso
- Rodar testes depois de cada mudança:
  - Sim: `run_shell("pytest -x")` ou `run_shell("npm test -- --bail")`
  - Não: rodar o arquivo principal e confirmar sem erro
- `manage_tasks("complete", "nome-da-tarefa")`

### 6. Revisão final
```
manage_tasks("list")   → confirmar todas completas
run_shell("pytest -v") ou npm test completo
```
Mostre ao usuário: lista de arquivos modificados + resumo das mudanças.

## REGRAS INVIOLÁVEIS
- Nunca mude comportamento e nome ao mesmo tempo
- Se não há testes, avise o usuário antes de refatorar
- Prefira código mais simples ao mais "elegante"
