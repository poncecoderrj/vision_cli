"""
Base classes for tools - Classes base para todas as tools
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Resultado padronizado de uma tool"""
    success: bool
    output: str = ""
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata or {}
        }


class Tool:
    """
    Classe base para todas as tools
    
    Todas as tools devem herdar desta classe e implementar:
    - name: Nome da tool
    - description: Descrição detalhada
    - parameters: Schema JSON dos parâmetros
    - execute(): Método principal de execução
    """
    
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Executa a tool com os parâmetros fornecidos
        
        Returns:
            ToolResult com sucesso/falha e output
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """Retorna definição da tool para o LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


__all__ = ["Tool", "ToolResult"]
