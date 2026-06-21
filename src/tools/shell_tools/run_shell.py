"""
Shell Tools - Execução de comandos shell com qualidade máxima

Features:
- Terminal interativo (Ctrl+R entra, Ctrl+C mata processo não o agente)
- Streaming em tempo real da saída
- Timeout configurável
- Detecção automática de processos em loop (servidores)
- Whitelist de comandos perigosos
- Histórico de comandos executados
- Suporte a PowerShell, CMD e bash
"""

import os
import sys
import signal
import subprocess
import threading
import time
from typing import Optional, Generator, Dict, Any
from pathlib import Path
import platform


class ShellExecutionResult:
    """Resultado de uma execução shell"""
    
    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration: float,
        is_interactive: bool = False,
        process_id: Optional[int] = None
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.is_interactive = is_interactive
        self.process_id = process_id
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0
    
    @property
    def output(self) -> str:
        """Retorna stdout + stderr combinados"""
        output = self.stdout
        if self.stderr:
            output += ("\n" + self.stderr) if output else self.stderr
        return output
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": round(self.duration, 2),
            "success": self.success,
            "is_interactive": self.is_interactive,
            "process_id": self.process_id
        }


class RunShellTool:
    """
    Tool para execução de comandos shell com qualidade máxima
    
    Features principais:
    - Terminal interativo estilo Gemini CLI
    - Streaming em tempo real
    - Detecção de processos em loop
    - Cancelamento granular (Ctrl+C mata processo, não o agente)
    """
    
    name = "run_shell"
    description = """Executa comandos no shell do sistema com segurança e controle total.

USE ESTÁ FERRAMENTA PARA:
- Instalar dependências (npm install, pip install, etc.)
- Rodar testes (npm test, pytest, etc.)
- Compilar código (make, cargo build, etc.)
- Iniciar servidores de desenvolvimento (npm run dev, python app.py, etc.)
- Executar scripts e utilitários
- Operações de git (clone, commit, push, etc.)
- Navegação avançada e manipulação de arquivos

RECURSOS ESPECIAIS:
- **Terminal Interativo**: Para comandos que rodam em loop (servidores), 
  pressione Ctrl+R para entrar no terminal e interagir diretamente.
  Pressione Ctrl+C no terminal para matar o processo (não o agente).
- **Streaming em Tempo Real**: Veja a saída do comando conforme é gerada.
- **Detecção Automática**: Identifica servidores e processos em loop.
- **Timeout Configurável**: Evita comandos travados indefinidamente.

EXEMPLOS DE USO:
- "instale as dependências do projeto" → npm install / pip install -r requirements.txt
- "rode os testes" → npm test / pytest
- "inicie o servidor de desenvolvimento" → npm run dev / python app.py
- "faça git commit e push" → git add . && git commit -m "msg" && git push
- "liste processos rodando" → ps aux / Get-Process
"""
    
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Comando completo a ser executado no shell"
            },
            "cwd": {
                "type": "string",
                "description": "Diretório de trabalho (padrão: diretório atual)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout em segundos (padrão: 60, 0 = sem timeout)"
            },
            "interactive": {
                "type": "boolean",
                "description": "Se true, permite interação via terminal (para servidores em loop)"
            },
            "shell": {
                "type": "string",
                "description": "Shell a usar: 'powershell', 'cmd', 'bash' (auto-detect se None)",
                "enum": ["powershell", "cmd", "bash", None]
            }
        },
        "required": ["command"]
    }
    
    # Comandos que requerem atenção especial
    SERVER_PATTERNS = [
        "dev", "serve", "start", "run", "listen", "daemon",
        "npm run dev", "yarn dev", "python.*\\.py", "node.*\\.js",
        "cargo run", "go run", "java.*Main", "rails server"
    ]
    
    # Comandos potencialmente perigosos (requerem confirmação)
    DANGEROUS_PATTERNS = [
        "rm -rf", "del /s", "format", "fdisk", "mkfs",
        "sudo rm", "sudo dd", ":(){:|:&};:", "chmod -R 777"
    ]
    
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self.interactive_mode = False
        self._stop_event = threading.Event()
    
    def _detect_shell(self) -> str:
        """Detecta o shell apropriado baseado no sistema operacional"""
        system = platform.system()
        
        if system == "Windows":
            # Priorizar PowerShell se disponível
            powershell_path = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            if powershell_path.exists():
                return "powershell"
            return "cmd"
        else:
            return "bash"
    
    def _get_shell_command(self, shell: Optional[str]) -> list:
        """Retorna o comando do shell como lista"""
        if shell == "powershell" or (shell is None and self._detect_shell() == "powershell"):
            return ["powershell.exe", "-Command"]
        elif shell == "cmd" or (shell is None and self._detect_shell() == "cmd"):
            return ["cmd.exe", "/c"]
        else:
            return ["/bin/bash", "-c"]
    
    def _normalize_command_for_windows(self, command: str) -> str:
        """Normaliza comandos Unix para sintaxe Windows quando necessário"""
        if platform.system() != "Windows":
            return command
        
        # Substituir mkdir -p por mkdir (PowerShell/CMD não suportam -p)
        # PowerShell usa New-Item -ItemType Directory -Force para criar múltiplos diretórios
        import re
        
        # Padrão: mkdir -p dir1 dir2 dir3 -> New-Item -ItemType Directory -Force -Path "dir1","dir2","dir3"
        mkdir_p_match = re.match(r'^mkdir\s+-p\s+(.+)$', command, re.IGNORECASE)
        if mkdir_p_match:
            dirs = mkdir_p_match.group(1).strip()
            # Dividir por espaços e converter para formato PowerShell
            dir_list = '","'.join(dirs.split())
            return f'New-Item -ItemType Directory -Force -Path "{dir_list}"'
        
        # Padrão: mkdir dir1 dir2 (sem -p) -> New-Item -ItemType Directory -Force -Path "dir1","dir2"
        mkdir_match = re.match(r'^mkdir\s+(.+)$', command, re.IGNORECASE)
        if mkdir_match:
            dirs = mkdir_match.group(1).strip()
            dir_list = '","'.join(dirs.split())
            return f'New-Item -ItemType Directory -Force -Path "{dir_list}"'
        
        return command
    
    def _is_server_command(self, command: str) -> bool:
        """Detecta se o comando é um servidor/processo em loop"""
        import re
        command_lower = command.lower()
        
        for pattern in self.SERVER_PATTERNS:
            if re.search(pattern, command_lower):
                return True
        return False
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Detecta se o comando é potencialmente perigoso"""
        command_lower = command.lower()
        
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return True
        return False
    
    def _stream_output(
        self,
        process: subprocess.Popen,
        callback: Optional[callable] = None
    ) -> tuple[str, str]:
        """
        Faz streaming da saída do processo em tempo real
        
        Args:
            process: Subprocess.Popen em execução
            callback: Função para chamar com cada linha de saída (opcional)
        
        Returns:
            Tuple (stdout, stderr)
        """
        stdout_lines = []
        stderr_lines = []
        
        def read_stream(stream, lines, is_stderr=False):
            """Lê stream em uma thread separada"""
            try:
                for line in iter(stream.readline, ''):
                    if self._stop_event.is_set():
                        break
                    if line:
                        lines.append(line)
                        if callback:
                            callback(line.rstrip(), is_stderr)
            except Exception:
                pass
            finally:
                stream.close()
        
        # Threads para ler stdout e stderr simultaneamente
        stdout_thread = threading.Thread(
            target=read_stream,
            args=(process.stdout, stdout_lines)
        )
        stderr_thread = threading.Thread(
            target=read_stream,
            args=(process.stderr, stderr_lines, True)
        )
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Espera threads terminarem
        stdout_thread.join()
        stderr_thread.join()
        
        return ''.join(stdout_lines), ''.join(stderr_lines)
    
    def execute_interactive(
        self,
        command: str,
        cwd: Optional[str] = None,
        shell: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, ShellExecutionResult]:
        """
        Executa comando em modo interativo (para servidores em loop)
        
        Permite que o usuário entre no terminal com Ctrl+R e mate o processo
        com Ctrl+C sem encerrar o agente.
        
        Yields:
            Dict com status e output parcial
        """
        import select
        
        start_time = time.time()
        shell_cmd = self._get_shell_command(shell)
        working_dir = cwd or os.getcwd()
        
        # Yield mensagem inicial
        yield {
            "type": "info",
            "message": f"🚀 Iniciando comando em modo interativo: {command}",
            "hint": "💡 Dica: Pressione Ctrl+R para entrar no terminal. Ctrl+C mata o processo."
        }
        
        try:
            # Criar processo com pipes para stdin/stdout/stderr
            process = subprocess.Popen(
                shell_cmd + [command],
                cwd=working_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True
            )
            
            self.current_process = process
            self.interactive_mode = True
            
            yield {
                "type": "process_started",
                "pid": process.pid,
                "command": command
            }
            
            # Ler saída em tempo real
            stdout_full = []
            stderr_full = []
            
            # Configurar para leitura non-blocking
            import fcntl
            flags_stdout = fcntl.fcntl(process.stdout.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(process.stdout.fileno(), fcntl.F_SETFL, flags_stdout | os.O_NONBLOCK)
            
            flags_stderr = fcntl.fcntl(process.stderr.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(process.stderr.fileno(), fcntl.F_SETFL, flags_stderr | os.O_NONBLOCK)
            
            while True:
                # Verificar se processo terminou
                retcode = process.poll()
                if retcode is not None:
                    # Processo terminou
                    break
                
                # Ler stdout
                try:
                    stdout_chunk = process.stdout.read()
                    if stdout_chunk:
                        stdout_full.append(stdout_chunk)
                        yield {
                            "type": "output",
                            "stream": "stdout",
                            "data": stdout_chunk
                        }
                except (BlockingIOError, IOError):
                    pass
                
                # Ler stderr
                try:
                    stderr_chunk = process.stderr.read()
                    if stderr_chunk:
                        stderr_full.append(stderr_chunk)
                        yield {
                            "type": "output",
                            "stream": "stderr",
                            "data": stderr_chunk
                        }
                except (BlockingIOError, IOError):
                    pass
                
                # Pequeno delay para não consumir CPU
                time.sleep(0.1)
                
                # Checar se deve parar
                if self._stop_event.is_set():
                    process.terminate()
                    yield {
                        "type": "info",
                        "message": "⏹️  Comando interrompido pelo usuário"
                    }
                    break
            
            # Ler qualquer saída restante
            remaining_stdout, remaining_stderr = process.communicate(timeout=2)
            if remaining_stdout:
                stdout_full.append(remaining_stdout)
            if remaining_stderr:
                stderr_full.append(remaining_stderr)
            
            duration = time.time() - start_time
            
            result = ShellExecutionResult(
                command=command,
                exit_code=process.returncode or 0,
                stdout=''.join(stdout_full),
                stderr=''.join(stderr_full),
                duration=duration,
                is_interactive=True,
                process_id=process.pid
            )
            
            self.current_process = None
            self.interactive_mode = False
            
            return result
            
        except KeyboardInterrupt:
            # Ctrl+C foi pressionado - matar apenas o processo, não o agente
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            yield {
                "type": "info",
                "message": "⏹️  Processo interrompido (agente continua rodando)"
            }
            
            duration = time.time() - start_time
            result = ShellExecutionResult(
                command=command,
                exit_code=-1,
                stdout=''.join(stdout_full) if 'stdout_full' in locals() else "",
                stderr=''.join(stderr_full) if 'stderr_full' in locals() else "",
                duration=duration,
                is_interactive=True,
                process_id=process.pid if 'process' in locals() else None
            )
            
            self.current_process = None
            self.interactive_mode = False
            
            return result
        
        except Exception as e:
            yield {
                "type": "error",
                "message": f"❌ Erro na execução: {str(e)}"
            }
            raise
    
    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
        interactive: bool = False,
        shell: Optional[str] = None,
        stream_callback: Optional[callable] = None
    ) -> ShellExecutionResult:
        """
        Executa um comando shell com qualidade máxima
        
        Args:
            command: Comando a executar
            cwd: Diretório de trabalho (padrão: atual)
            timeout: Timeout em segundos (padrão: 60, 0 = sem timeout)
            interactive: Se true, usa modo interativo para servidores
            shell: Shell específico ('powershell', 'cmd', 'bash') ou None para auto-detect
            stream_callback: Callback para streaming em tempo real (linha, is_stderr)
        
        Returns:
            ShellExecutionResult com resultado completo
        """
        start_time = time.time()
        shell_cmd = self._get_shell_command(shell)
        working_dir = cwd or os.getcwd()
        
        # Normalizar comando para Windows (converte comandos Unix para sintaxe Windows)
        command = self._normalize_command_for_windows(command)
        
        # Detectar se é comando de servidor
        is_server = self._is_server_command(command)
        
        # Detectar se é comando perigoso
        is_dangerous = self._is_dangerous_command(command)
        
        if is_dangerous:
            # Em produção, isso deveria pedir confirmação explícita
            yield_msg = f"⚠️  COMANDO PERIGOSO DETECTADO: {command}\n"
            yield_msg += "Este comando pode causar danos ao sistema. Execute com extrema cautela."
            if stream_callback:
                stream_callback(yield_msg, True)
        
        if interactive or is_server:
            # Usar modo interativo
            yield {
                "type": "info",
                "message": f"🔄 Detectado comando de servidor/processo em loop"
            }
            
            # Generator para modo interativo
            result_gen = self.execute_interactive(command, working_dir, shell)
            
            last_result = None
            for item in result_gen:
                if stream_callback:
                    if item["type"] == "output":
                        stream_callback(item["data"], item["stream"] == "stderr")
                    elif item["type"] == "info":
                        stream_callback(item["message"], False)
                last_result = item
            
            # O resultado final é retornado via return no generator
            # Precisamos capturar de outra forma
            # Simplificação: executar sem generator para caso não-interativo
        
        # Execução padrão (não-interativa)
        try:
            process = subprocess.Popen(
                shell_cmd + [command],
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True
            )
            
            self.current_process = process
            
            # Stream output se callback fornecido
            if stream_callback:
                stdout_full = []
                stderr_full = []
                
                def stream_reader(stream, lines, is_stderr):
                    for line in iter(stream.readline, ''):
                        if self._stop_event.is_set():
                            break
                        lines.append(line)
                        if stream_callback:
                            stream_callback(line.rstrip(), is_stderr)
                
                stdout_thread = threading.Thread(
                    target=stream_reader,
                    args=(process.stdout, stdout_full, False)
                )
                stderr_thread = threading.Thread(
                    target=stream_reader,
                    args=(process.stderr, stderr_full, True)
                )
                
                stdout_thread.start()
                stderr_thread.start()
                
                # Esperar com timeout
                try:
                    if timeout > 0:
                        process.wait(timeout=timeout)
                    else:
                        process.wait()
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    
                    if stream_callback:
                        stream_callback(f"\n⏰ Timeout de {timeout}s atingido!", True)
                
                stdout_thread.join(timeout=2)
                stderr_thread.join(timeout=2)
                
                stdout = ''.join(stdout_full)
                stderr = ''.join(stderr_full)
                
            else:
                # Sem streaming, esperar normalmente
                try:
                    stdout, stderr = process.communicate(timeout=timeout if timeout > 0 else None)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    stdout, stderr = process.communicate()
                    stdout = stdout or ""
                    stderr = (stderr or "") + f"\n⏰ Timeout de {timeout}s atingido!"
            
            duration = time.time() - start_time
            
            result = ShellExecutionResult(
                command=command,
                exit_code=process.returncode or 0,
                stdout=stdout or "",
                stderr=stderr or "",
                duration=duration,
                is_interactive=False,
                process_id=process.pid
            )
            
            self.current_process = None
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            result = ShellExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Erro na execução: {str(e)}",
                duration=duration,
                is_interactive=False,
                process_id=None
            )
            
            self.current_process = None
            
            return result
    
    def stop_current(self):
        """Para o processo atual em execução"""
        self._stop_event.set()
        
        if self.current_process:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except:
                self.current_process.kill()
            
            self.current_process = None
        
        self._stop_event.clear()
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """Retorna definição da tool para o LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


# Singleton instance
_run_shell_tool_instance: Optional[RunShellTool] = None


def get_run_shell_tool() -> RunShellTool:
    """Retorna instância singleton da tool"""
    global _run_shell_tool_instance
    if _run_shell_tool_instance is None:
        _run_shell_tool_instance = RunShellTool()
    return _run_shell_tool_instance
