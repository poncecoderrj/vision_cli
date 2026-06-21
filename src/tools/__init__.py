"""
Tools Registry - Registro centralizado de todas as tools do agente

Este módulo fornece um registry unificado para todas as tools, permitindo
que o agent.py descubra e use as tools de forma dinâmica.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import base classes primeiro
from .base import Tool, ToolResult


@dataclass
class ToolInfo:
    """Informações sobre uma tool registrada"""
    name: str
    category: str
    instance: Any
    description: str
    parameters: Dict[str, Any]


class ToolsRegistry:
    """
    Registry centralizado de tools
    
    Uso:
        registry = ToolsRegistry()
        registry.register_tool("file_tools", "read_file", ReadFileTool())
        
        # Obter todas as tools
        all_tools = registry.get_all_tools()
        
        # Obter tool específica
        read_tool = registry.get_tool("read_file")
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolInfo] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register_tool(
        self,
        category: str,
        name: str,
        instance: Any,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Registra uma tool no registry"""
        
        # Extrair descrição e parâmetros da instância se não fornecidos
        if description is None:
            description = getattr(instance, "description", "Sem descrição")
        
        if parameters is None:
            parameters = getattr(instance, "parameters", {})
        
        tool_info = ToolInfo(
            name=name,
            category=category,
            instance=instance,
            description=description,
            parameters=parameters
        )
        
        self._tools[name] = tool_info
        
        # Adicionar à categoria
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Obtém instância de uma tool pelo nome"""
        tool_info = self._tools.get(name)
        return tool_info.instance if tool_info else None
    
    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """Obtém informações de uma tool pelo nome"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Retorna dict com todas as tools (nome -> instância)"""
        return {name: info.instance for name, info in self._tools.items()}
    
    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Retorna definições de todas as tools para o LLM"""
        definitions = []
        
        for name, info in self._tools.items():
            # Tentar obter definição da própria tool
            if hasattr(info.instance, "to_tool_definition"):
                definitions.append(info.instance.to_tool_definition())
            else:
                definitions.append({
                    "name": name,
                    "description": info.description,
                    "parameters": info.parameters
                })
        
        return definitions
    
    def get_tools_by_category(self, category: str) -> Dict[str, Any]:
        """Retorna tools de uma categoria específica"""
        tool_names = self._categories.get(category, [])
        return {name: self._tools[name].instance for name in tool_names if name in self._tools}
    
    def list_categories(self) -> List[str]:
        """Lista todas as categorias registradas"""
        return list(self._categories.keys())
    
    def list_tools(self) -> List[str]:
        """Lista todos os nomes de tools registrados"""
        return list(self._tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Verifica se uma tool está registrada"""
        return name in self._tools


# Singleton global
_registry_instance: Optional[ToolsRegistry] = None


def get_registry() -> ToolsRegistry:
    """Retorna instância singleton do registry"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolsRegistry()
    return _registry_instance


def initialize_default_tools():
    """
    Inicializa o registry com todas as tools padrão
    
    Deve ser chamado uma vez no início da aplicação.
    """
    registry = get_registry()
    
    # File Tools
    try:
        from .file_tools import (
            get_read_file_tool,
            get_write_file_tool,
            get_edit_file_tool,
            get_delete_file_tool
        )
        
        registry.register_tool("file", "read_file", get_read_file_tool())
        registry.register_tool("file", "write_file", get_write_file_tool())
        registry.register_tool("file", "edit_file", get_edit_file_tool())
        registry.register_tool("file", "delete_file", get_delete_file_tool())
    except ImportError as e:
        print(f"⚠️  Warning: Could not load file tools: {e}")
    
    # Navigation Tools
    try:
        from .navigation_tools import (
            get_list_dir_tool,
            get_glob_files_tool,
            get_search_code_tool
        )
        
        registry.register_tool("navigation", "list_dir", get_list_dir_tool())
        registry.register_tool("navigation", "glob_files", get_glob_files_tool())
        registry.register_tool("navigation", "search_code", get_search_code_tool())
    except ImportError as e:
        print(f"⚠️  Warning: Could not load navigation tools: {e}")
    
    # Shell Tools
    try:
        from .shell_tools import get_run_shell_tool
        
        registry.register_tool("shell", "run_shell", get_run_shell_tool())
    except ImportError as e:
        print(f"⚠️  Warning: Could not load shell tools: {e}")
    
    # Web Tools
    try:
        from .web_tools import (
            get_web_search_tool,
            get_github_search_tool
        )
        
        registry.register_tool("web", "web_search", get_web_search_tool())
        registry.register_tool("web", "search_github", get_github_search_tool())
    except ImportError as e:
        print(f"⚠️  Warning: Could not load web tools: {e}")
    
    # Utility Tools
    try:
        from .utility_tools import (
            get_ask_user_tool,
            get_manage_tasks_tool
        )
        
        registry.register_tool("utility", "ask_user", get_ask_user_tool())
        registry.register_tool("utility", "manage_tasks", get_manage_tasks_tool())
    except ImportError as e:
        print(f"⚠️  Warning: Could not load utility tools: {e}")
    
    return registry


__all__ = [
    "ToolsRegistry",
    "ToolInfo",
    "get_registry",
    "initialize_default_tools"
]
