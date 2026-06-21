"""
Utility tools - ask_user, manage_tasks
"""

from typing import List, Optional, Dict
from datetime import datetime

from src.tools import Tool, ToolResult


class AskUserTool:
    """Faz uma pergunta ao usuário com opções"""
    
    name = "ask_user"
    description = "Apresenta uma pergunta com opções para o usuário escolher"
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Pergunta a ser feita"},
            "options": {"type": "array", "items": {"type": "string"}, "description": "Lista de opções"}
        },
        "required": ["question", "options"]
    }
    
    def __init__(self, input_func=None):
        self.input_func = input_func
    
    def execute(self, question: str, options: List[str]) -> ToolResult:
        if not options:
            return ToolResult(
                success=False,
                output="",
                error="Opções não podem estar vazias"
            )
        
        # Formata a pergunta
        output_lines = [question, ""]
        for i, option in enumerate(options, 1):
            output_lines.append(f"  {i}. {option}")
        output_lines.append("")
        output_lines.append("Digite o número da opção:")
        
        # Se tiver função de input, usa (para integração com UI)
        if self.input_func:
            try:
                response = self.input_func('\n'.join(output_lines))
                idx = int(response.strip()) - 1
                if 0 <= idx < len(options):
                    return ToolResult(
                        success=True,
                        output=options[idx],
                        metadata={"selected_index": idx, "options": options}
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Opção inválida"
                    )
            except ValueError:
                return ToolResult(
                    success=False,
                    output="",
                    error="Resposta deve ser um número"
                )
        
        # Sem função de input, retorna as opções para a UI processar
        return ToolResult(
            success=True,
            output='\n'.join(output_lines),
            metadata={"requires_input": True, "options": options}
        )
    
    def validate(self, question: str, options: list, **kwargs) -> bool:
        return bool(question) and isinstance(options, list) and len(options) > 0


class ManageTasksTool:
    """Gerencia uma lista de tarefas para trabalhos longos"""
    
    name = "manage_tasks"
    description = "Adiciona, remove ou lista tarefas em andamento"
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "remove", "list", "complete"], 
                      "description": "Ação a realizar"},
            "task_name": {"type": "string", "description": "Nome da tarefa"}
        },
        "required": ["action"]
    }
    
    def __init__(self):
        self._tasks: Dict[str, dict] = {}
    
    def execute(self, action: str, task_name: Optional[str] = None) -> ToolResult:
        timestamp = datetime.now().isoformat()
        
        if action == "add":
            if not task_name:
                return ToolResult(
                    success=False,
                    output="",
                    error="Nome da tarefa é obrigatório para adicionar"
                )
            
            self._tasks[task_name] = {
                "created": timestamp,
                "status": "pending"
            }
            
            return ToolResult(
                success=True,
                output=f"Tarefa adicionada: {task_name}",
                metadata={"task": task_name, "status": "pending"}
            )
        
        elif action == "complete":
            if not task_name or task_name not in self._tasks:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Tarefa não encontrada: {task_name}"
                )
            
            self._tasks[task_name]["status"] = "completed"
            self._tasks[task_name]["completed"] = timestamp
            
            return ToolResult(
                success=True,
                output=f"Tarefa completada: {task_name}",
                metadata={"task": task_name, "status": "completed"}
            )
        
        elif action == "remove":
            if not task_name or task_name not in self._tasks:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Tarefa não encontrada: {task_name}"
                )
            
            del self._tasks[task_name]
            
            return ToolResult(
                success=True,
                output=f"Tarefa removida: {task_name}"
            )
        
        elif action == "list":
            if not self._tasks:
                return ToolResult(
                    success=True,
                    output="Nenhuma tarefa pendente"
                )
            
            output_lines = ["Tarefas:", ""]
            for name, info in self._tasks.items():
                status_icon = "✅" if info["status"] == "completed" else "⏳"
                output_lines.append(f"  {status_icon} {name}")
            
            metadata = {
                "total": len(self._tasks),
                "completed": sum(1 for t in self._tasks.values() if t["status"] == "completed"),
                "pending": sum(1 for t in self._tasks.values() if t["status"] == "pending")
            }
            
            return ToolResult(
                success=True,
                output='\n'.join(output_lines),
                metadata=metadata
            )
        
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Ação inválida: {action}. Use: add, remove, complete, list"
            )
    
    def validate(self, action: str, **kwargs) -> bool:
        return action in ["add", "remove", "complete", "list"]


# Exporta as tools
def create_ask_user_tool(input_func=None):
    return AskUserTool(input_func=input_func)

manage_tasks_tool = ManageTasksTool()

UTILITY_TOOLS = [create_ask_user_tool(), manage_tasks_tool]


# Funções getter para o registry
def get_ask_user_tool():
    from . import create_ask_user_tool
    return create_ask_user_tool()

def get_manage_tasks_tool():
    return manage_tasks_tool
