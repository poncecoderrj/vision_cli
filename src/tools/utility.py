"""
Utility tools: manage_tasks, ask_user.
"""

from .base import Tool, ToolResult

_tasks: list[dict] = []


class ManageTasksTool(Tool):
    name = "manage_tasks"
    description = "Track a todo list for long, multi-step goals."
    parameters = {
        "type": "object",
        "properties": {
            "action":    {"type": "string", "enum": ["add", "list", "complete"]},
            "task_name": {"type": "string", "description": "Required for add/complete."},
        },
        "required": ["action"],
    }

    def execute(self, action: str, task_name: str = "") -> ToolResult:
        global _tasks
        if action == "add":
            _tasks.append({"name": task_name, "status": "pending"})
            return ToolResult(success=True, output=f"Tarefa adicionada: '{task_name}'.")
        if action == "list":
            if not _tasks:
                return ToolResult(success=True, output="Nenhuma tarefa.")
            lines = "\n".join(
                f"{i+1}. [{'x' if t['status'] == 'completed' else ' '}] {t['name']}"
                for i, t in enumerate(_tasks)
            )
            return ToolResult(success=True, output=lines)
        if action == "complete":
            for t in _tasks:
                if t["name"] == task_name:
                    t["status"] = "completed"
                    return ToolResult(success=True, output=f"Tarefa concluída: '{task_name}'.")
            msg = f"Tarefa não encontrada: '{task_name}'."
            return ToolResult(success=False, output=msg, error=msg)
        msg = "Ação inválida. Use add, list ou complete."
        return ToolResult(success=False, output=msg, error=msg)


class AskUserTool(Tool):
    name = "ask_user"
    description = (
        "Ask the user to choose between options when a decision is needed — e.g., which stack, "
        "approach, architecture, or plan to follow. Always use this instead of guessing or assuming."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The decision question to present to the user."},
            "options":  {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of 2–5 options for the user to choose from.",
            },
        },
        "required": ["question", "options"],
    }

    def execute(self, question: str, options: list) -> ToolResult:
        if not options or not isinstance(options, list):
            msg = "Erro: 'options' deve ser uma lista não-vazia de strings."
            return ToolResult(success=False, output=msg, error=msg)
        from ui import prompt_ask_user
        choice = prompt_ask_user(question, [str(o) for o in options])
        return ToolResult(success=True, output=f"Usuário escolheu: {choice}")


__all__ = ["ManageTasksTool", "AskUserTool"]
