<!-- QUESTIONS
[
  {"id": "name",    "ask": "Qual o nome da API/projeto?",        "type": "text", "default": "minha-api",                                          "label": "Nome do projeto"},
  {"id": "stack",   "ask": "Qual stack?",                        "options": ["Python + FastAPI", "Python + Flask", "Node.js + Express", "Node.js + Fastify"], "label": "Stack"},
  {"id": "db",      "ask": "Banco de dados?",                    "options": ["SQLite (simples, local)", "PostgreSQL", "MongoDB", "Sem banco"],    "label": "Banco de dados"},
  {"id": "auth",    "ask": "Autenticação JWT?",                  "options": ["Sim", "Não"],                                                        "label": "Auth JWT"},
  {"id": "resource","ask": "Nome do recurso principal (ex: tasks, users, products)?", "type": "text", "default": "items",                         "label": "Recurso principal"}
]
-->

# SKILL: Criador de API REST

As configurações já foram coletadas. Execute os passos abaixo em ordem.

## PASSOS

### 1. Criar estrutura de pastas e instalar deps

**Python + FastAPI:**
```
mkdir {name} && cd {name}
pip install fastapi uvicorn[standard] python-dotenv pydantic
```
Se SQLite/PostgreSQL: `pip install sqlalchemy`
Se MongoDB: `pip install motor`
Se JWT: `pip install python-jose[cryptography] passlib[bcrypt]`

Estrutura:
```
{name}/
  main.py
  database.py
  models.py
  routers/{resource}.py
  requirements.txt
  .env
```

**Node.js + Express/Fastify:**
```
mkdir {name} && cd {name} && npm init -y
npm install express dotenv cors
```
Se JWT: `npm install jsonwebtoken bcryptjs`
Se Mongo: `npm install mongoose`
Se PostgreSQL: `npm install pg sequelize`

Estrutura:
```
{name}/
  src/
    index.js
    routes/{resource}.js
    controllers/{resource}Controller.js
    models/{resource}.js
    middleware/auth.js
  .env
  package.json
```

### 2. Implementar CRUD completo para `{resource}`
Criar os 5 endpoints:
- `GET /{resource}` → listar todos
- `GET /{resource}/:id` → buscar um
- `POST /{resource}` → criar
- `PUT /{resource}/:id` → atualizar
- `DELETE /{resource}/:id` → deletar

### 3. Configurar .env
```env
PORT=8000
DATABASE_URL=sqlite:///./database.db
SECRET_KEY=troque-isso-em-producao
```

### 4. Criar .gitignore
Incluir: `.env`, `__pycache__/`, `node_modules/`, `*.db`

### 5. Testar
FastAPI: `uvicorn main:app --reload` → http://localhost:8000/docs (Swagger automático)
Express: `node src/index.js` → testar os endpoints

### 6. Criar README com exemplos curl
Documentar cada endpoint com exemplos reais de chamadas.
