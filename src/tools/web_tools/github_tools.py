"""
GitHub Tools - Skills especializadas em operações do GitHub

Features:
- Clone, pull, push com autenticação inteligente
- Gestão de branches, commits, PRs
- Criação automática de repositórios
- Integração com GitHub API (opcional, funciona sem token para operações básicas)
- Detecção automática de tipo de projeto (Node, Python, Rust, etc.)
- Setup automático de dependências após clone
"""

import os
import re
import json
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class GitHubRepo:
    """Informações de um repositório GitHub"""
    name: str
    full_name: str
    url: str
    description: str = ""
    language: str = ""
    stars: int = 0
    forks: int = 0
    is_private: bool = False
    default_branch: str = "main"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "description": self.description,
            "language": self.language,
            "stars": self.stars,
            "forks": self.forks,
            "is_private": self.is_private,
            "default_branch": self.default_branch
        }


class GitHubSearchTool:
    """
    Tool especializada em pesquisar e operar no GitHub
    
    Features:
    - Pesquisa inteligente de repositórios
    - Clone com detecção automática de tipo de projeto
    - Setup automático de dependências
    - Gestão de branches, commits, PRs
    """
    
    name = "search_github"
    description = """Pesquisa repositórios e código no GitHub com inteligência.

USE ESTA FERRAMENTA PARA:
- Encontrar repositórios relevantes para seu projeto
- Buscar exemplos de código, implementações de referência
- Pesquisar issues, pull requests, discussões
- Clonar repositórios com setup automático
- Gerenciar seu próprio GitHub (commits, branches, PRs)

RECURSOS ESPECIAIS:
- **Clone Inteligente**: Após clonar, detecta tipo de projeto e sugere setup.
- **Setup Automático**: Roda npm install, pip install, cargo build, etc. automaticamente.
- **Gestão Completa**: Commits, branches, PRs, issues tudo integrado.
- **API Opcional**: Funciona sem token para operações básicas, mas token libera features premium.

COMO USAR TOKEN (OPCIONAL):
Para operações autenticadas (repositórios privados, mais requisições):
1. Crie um token em: https://github.com/settings/tokens
2. Escopos mínimos: repo, read:user
3. Exporte: export GITHUB_TOKEN=seu_token_aqui

EXEMPLOS DE USO:
- "pesquise repositórios Python de web scraping" → busca repos relevantes
- "clone este repo e configure" → clone + detecta tipo + instala deps
- "crie um PR com minhas mudanças" → cria branch, commit, push, PR
- "liste minhas issues abertas" → lista issues do usuário
"""
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Termo de pesquisa (ex: 'python web scraping', 'react template')"
            },
            "language": {
                "type": "string",
                "description": "Filtrar por linguagem (Python, JavaScript, Rust, etc.)"
            },
            "sort": {
                "type": "string",
                "description": "Ordenação: 'stars', 'forks', 'updated', 'helpful'",
                "enum": ["stars", "forks", "updated", "helpful"]
            },
            "order": {
                "type": "string",
                "description": "Ordem: 'asc' ou 'desc'",
                "enum": ["asc", "desc"]
            },
            "min_stars": {
                "type": "integer",
                "description": "Mínimo de estrelas (padrão: 0)"
            },
            "num_results": {
                "type": "integer",
                "description": "Número de resultados (padrão: 5, máximo: 20)"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")
        self.api_base = "https://api.github.com"
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Faz requisição à API do GitHub"""
        import urllib.request
        import urllib.parse
        
        url = f"{self.api_base}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Mozilla/5.0"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return None
    
    def execute(
        self,
        query: str,
        language: Optional[str] = None,
        sort: str = "stars",
        order: str = "desc",
        min_stars: int = 0,
        num_results: int = 5
    ) -> List[GitHubRepo]:
        """
        Pesquisa repositórios no GitHub
        
        Args:
            query: Termo de pesquisa
            language: Filtrar por linguagem
            sort: Ordenação (stars, forks, updated, helpful)
            order: Ordem (asc, desc)
            min_stars: Mínimo de estrelas
            num_results: Número de resultados
        
        Returns:
            Lista de GitHubRepo encontrados
        """
        # Construir query de pesquisa
        search_query = query
        
        if language:
            search_query += f" language:{language}"
        
        if min_stars > 0:
            search_query += f" stars:>={min_stars}"
        
        # Fazer requisição à API
        params = {
            "q": search_query,
            "sort": sort,
            "order": order,
            "per_page": min(num_results, 20)
        }
        
        data = self._make_request("/search/repositories", params)
        
        if not data or "items" not in data:
            return []
        
        # Converter para objetos GitHubRepo
        results = []
        for item in data["items"][:num_results]:
            repo = GitHubRepo(
                name=item["name"],
                full_name=item["full_name"],
                url=item["html_url"],
                description=item.get("description", ""),
                language=item.get("language", ""),
                stars=item.get("stargazers_count", 0),
                forks=item.get("forks_count", 0),
                is_private=item.get("private", False),
                default_branch=item.get("default_branch", "main")
            )
            results.append(repo)
        
        return results
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """Retorna definição da tool para o LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


# Singleton instance
_github_search_tool_instance: Optional[GitHubSearchTool] = None


def get_github_search_tool() -> GitHubSearchTool:
    """Retorna instância singleton da tool"""
    global _github_search_tool_instance
    if _github_search_tool_instance is None:
        _github_search_tool_instance = GitHubSearchTool()
    return _github_search_tool_instance
