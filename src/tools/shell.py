"""
Shell execution tool: run_shell.
"""

import os
import subprocess
import threading

from rich.markup import escape as _escape

from .base import Tool, ToolResult


class RunShellTool(Tool):
    name = "run_shell"
    description = (
        "Execute a shell command with live output streaming. Use stdin_input to pre-fill "
        "interactive prompts (newline-separated answers). timeout in seconds (default 300)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command":     {"type": "string",  "description": "The command to execute."},
            "stdin_input": {"type": "string",  "description": "Newline-separated answers for interactive prompts."},
            "timeout":     {"type": "integer", "description": "Seconds before killing the process (default 300)."},
        },
        "required": ["command"],
    }

    def execute(self, command: str, stdin_input: str = "", timeout: int = 300) -> ToolResult:
        from ui import get_mode, AgentMode, prompt_command_approval, print_system_message
        from config import is_whitelisted, add_to_whitelist
        from ui import console

        if get_mode() == AgentMode.ACCEPT and not is_whitelisted(command):
            choice = prompt_command_approval(command)
            if isinstance(choice, str):
                msg = f"COMANDO_CANCELADO_COM_INSTRUCAO: {choice}"
                return ToolResult(success=False, output=msg, error=msg)
            if choice == 3 or choice is None:
                msg = ("ERRO_CRITICO: Usuário cancelou explicitamente a execução deste comando. "
                       "NÃO repita este comando. Analise o erro e tente uma abordagem completamente diferente.")
                return ToolResult(success=False, output=msg, error=msg)
            if choice == 2:
                add_to_whitelist(command)
                print_system_message("Comando adicionado à whitelist permanentemente.")
        elif is_whitelisted(command):
            print_system_message("Comando na whitelist. Executando automaticamente.")

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            msg = f"Erro ao iniciar comando: {e}"
            return ToolResult(success=False, output=msg, error=str(e))

        if stdin_input:
            try:
                answers = stdin_input if stdin_input.endswith("\n") else stdin_input + "\n"
                proc.stdin.write(answers)
                proc.stdin.flush()
            except Exception:
                pass
        try:
            proc.stdin.close()
        except Exception:
            pass

        output_lines: list[str] = []

        def _read():
            for raw_line in proc.stdout:
                line = raw_line.rstrip()
                output_lines.append(line)
                console.print(f"  [grey50]{_escape(line)}[/grey50]")

        reader = threading.Thread(target=_read, daemon=True)
        reader.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            reader.join(timeout=2)
            tail = "\n".join(output_lines[-20:])
            msg = f"Erro: comando excedeu {timeout}s.\n{tail}"
            return ToolResult(success=False, output=msg, error=f"Timeout após {timeout}s")

        reader.join(timeout=5)

        body = "\n".join(output_lines) if output_lines else "(sem saída)"
        output = f"exit={proc.returncode}\n{body}"
        return ToolResult(success=(proc.returncode == 0), output=output)


__all__ = ["RunShellTool"]
