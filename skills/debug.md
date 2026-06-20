<!-- QUESTIONS
[
  {"id": "error_type", "ask": "Qual tipo de problema?",           "options": ["Erro de execução (tem mensagem de erro)", "Comportamento errado (sem erro)", "Testes falhando", "Performance lenta"],  "label": "Tipo de problema"},
  {"id": "language",   "ask": "Qual linguagem/ambiente?",          "options": ["Python", "JavaScript/Node.js", "TypeScript", "Outro"],                                                                "label": "Linguagem"},
  {"id": "scope",      "ask": "Onde está o problema?",            "options": ["Sei o arquivo/função", "Não sei onde está", "É um erro de instalação/ambiente"],                                       "label": "Escopo"}
]
-->

# SKILL: Debug e Correção de Código

As configurações já foram coletadas. Execute os passos abaixo em ordem.

## PASSOS

### 1. Mapear o projeto
```
list_dir(".")
glob_files("**/*.py")   (ou *.js, *.ts conforme a linguagem)
```

### 2. Localizar o problema
Se o usuário indicou arquivo/função:
```
read_file("arquivo_indicado")
search_code("nome_da_função_ou_erro")
```
Se não sabe onde está:
```
search_code("error|Error|exception|Exception")
search_code("TODO|FIXME|HACK")
```

### 3. Reproduzir o erro
```
run_shell("python arquivo.py")    (Python)
run_shell("node src/index.js")    (Node)
run_shell("pytest -x")            (testes Python)
run_shell("npm test -- --bail")   (testes JS)
```
Leia o stderr completo para entender o stack trace.

### 4. Analisar e corrigir
- Leia o arquivo completo antes de qualquer edição
- Faça UMA correção por vez com edit_file
- Após cada mudança, rode o código/testes de novo
- Se falhar ainda, leia o novo erro e ajuste

### 5. Se não encontrar sozinho
```
web_search("erro exato + linguagem + versão")
search_github("erro similar")
```

### 6. Confirmar a correção
Rode os testes/comando completo uma última vez para confirmar que está OK.
Mostre ao usuário o que foi corrigido e por quê estava errado.
