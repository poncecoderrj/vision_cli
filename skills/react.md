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

### 2. Instalar dependências base
```
cd {name} && npm install
```
- Se React Router: `npm install react-router-dom`
- Se Axios:        `npm install axios`
- Se Zustand:      `npm install zustand`
- Se React Query:  `npm install @tanstack/react-query`

### 3. Configurar Tailwind (se Sim)
```
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```
Editar `tailwind.config.js` → content: `["./index.html","./src/**/*.{js,ts,jsx,tsx}"]`
Adicionar no topo de `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 4. Criar estrutura de pastas
Use write_file para criar um `.gitkeep` em cada pasta:
```
src/components/
src/pages/       (só se router=Sim)
src/hooks/
src/services/
src/assets/
```

### 5. Limpar boilerplate
- Substituir `src/App.tsx` (ou `.jsx`) por um componente limpo básico
- Limpar `src/index.css` (manter só diretivas Tailwind se ativado, ou zerar)
- Remover `src/App.css`

### 6. Confirmar e mostrar próximos passos
Rode: `cd {name} && npm run dev` — confirme que sobe sem erro.
Mostre ao usuário:
- URL de dev: http://localhost:5173
- Comandos: `npm run dev`, `npm run build`, `npm run preview`
