<!-- QUESTIONS
[
  {"id": "name",      "ask": "Qual o nome do projeto?",        "type": "text", "default": "meu-app", "label": "Nome do projeto"},
  {"id": "framework", "ask": "Qual framework?",                "options": ["React", "Vue", "Svelte"],                           "label": "Framework"},
  {"id": "language",  "ask": "TypeScript ou JavaScript?",      "options": ["TypeScript (recomendado)", "JavaScript"],           "label": "Linguagem"},
  {"id": "tailwind",  "ask": "Quer Tailwind CSS?",             "options": ["Sim", "Não"],                                       "label": "Tailwind CSS"},
  {"id": "router",    "ask": "Quer React Router?",             "options": ["Sim", "Não"], "if": "framework=React",             "label": "React Router"},
  {"id": "extras",    "ask": "Algum extra?",                   "options": ["Nenhum", "Axios (HTTP)", "Zustand (estado)", "React Query"], "label": "Extras"}
]
-->

# SKILL: Criador de App React/Vite

⚠️  RODANDO NO WINDOWS - Use comandos Windows!

As configurações já foram coletadas. Execute os passos abaixo em ordem.

## PASSOS

### 1. Criar o projeto com Vite (não-interativo)
Monte o `--template` com base nas configurações:
- React + TypeScript → `--template react-ts`
- React + JavaScript → `--template react`
- Vue + TypeScript   → `--template vue-ts`
- Vue + JavaScript   → `--template vue`
- Svelte + TypeScript → `--template svelte-ts`
- Svelte + JavaScript → `--template svelte`

Comando: `npm create vite@latest {name} -- --template {template}`

⚠️  Se falhar, tente com stdin_input: `run_shell("npm create vite@latest", stdin_input="{name}\n\n{template}\n")`

### 2. Instalar dependências base
```
cd {name} && npm install
```
- Se React Router: `npm install react-router-dom`
- Se Axios:        `npm install axios`
- Se Zustand:      `npm install zustand`
- Se React Query:  `npm install @tanstack/react-query`

⚠️  Se `cd` falhar, use paths absolutos ou tente: `run_shell("npm install", cwd="{name}")`

### 3. Configurar Tailwind (se Sim)
```
cd {name}
npm install -D tailwindcss postcss autoprefixer
```

**IMPORTANTE PARA WINDOWS:** O comando `npx tailwindcss init -p` pode falhar no Windows. Se falhar, CRIE MANUALMENTE os arquivos:

**tailwind.config.js** (na raiz do projeto):
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

**postcss.config.js** (na raiz do projeto):
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

Adicionar no topo de `{name}/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 4. Criar estrutura de pastas
**IMPORTANTE PARA WINDOWS:** Não use `mkdir` diretamente! Use a ferramenta `write_file` para criar arquivos `.gitkeep` dentro das pastas desejadas - isso criará as pastas automaticamente.

Crie um arquivo `.gitkeep` vazio em cada uma destas pastas (use o caminho COMPLETO):
```
{name}/src/components/.gitkeep
{name}/src/pages/.gitkeep       (só se router=Sim)
{name}/src/hooks/.gitkeep
{name}/src/services/.gitkeep
{name}/src/assets/.gitkeep
```

Exemplo: Se o projeto se chama "petshop-local", use caminhos como:
- `petshop-local/src/components/.gitkeep`
- `petshop-local/src/hooks/.gitkeep`

NUNCA use comandos shell `mkdir` no Windows - sempre use write_file!

### 5. Limpar boilerplate
- Substituir `{name}/src/App.tsx` (ou `.jsx`) por um componente limpo básico
- Limpar `{name}/src/index.css` (manter só diretivas Tailwind se ativado, ou zerar)
- Remover `{name}/src/App.css`

NOTA: Sempre use o caminho completo `{name}/src/...` para evitar criar arquivos no diretório errado!

### 6. Confirmar e mostrar próximos passos
Rode: `cd {name} && npm run dev` — confirme que sobe sem erro.
Mostre ao usuário:
- URL de dev: http://localhost:5173
- Comandos: `npm run dev`, `npm run build`, `npm run preview`
