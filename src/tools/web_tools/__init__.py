"""Web Tools - Pesquisa e navegação web inteligente"""

from .web_search import WebSearchTool, get_web_search_tool, SearchResponse, SearchResult
from .github_tools import GitHubSearchTool, get_github_search_tool, GitHubRepo

__all__ = [
    "WebSearchTool",
    "get_web_search_tool",
    "SearchResponse",
    "SearchResult",
    "GitHubSearchTool",
    "get_github_search_tool",
    "GitHubRepo"
]
