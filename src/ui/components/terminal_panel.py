"""
Terminal Panel - Componente Rich para exibição de terminal em tempo real

Features:
- Streaming eficiente usando select() ao invés de polling
- Painel dedicado com bordas e título
- Controle granular de foco (Shift+C cancela, Escape fecha)
- Suporte a múltiplos terminais simultâneos
- Integração com Rich Live para atualização em tempo real
"""

import os
import sys
import select
import subprocess
import threading
import time
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.style import Style
from rich import box


class TerminalSession:
    """Representa uma sessão de terminal ativa"""
    
    def __init__(self, session_id: str, command: str, process: subprocess.Popen):
        self.session_id = session_id
        self.command = command
        self.process = process
        self.stdout_buffer: List[str] = []
        self.stderr_buffer: List[str] = []
        self.start_time = time.time()
        self.is_active = True
        self.is_focused = False
        self.output_lines: List[str] = []
        self.max_lines = 500  # Limite de linhas no buffer
    
    def add_output(self, line: str, is_stderr: bool = False):
        """Adiciona linha de saída ao buffer"""
        timestamp = f"{time.time() - self.start_time:6.2f}s"
        prefix = "❯" if not is_stderr else "✗"
        formatted = f"[{timestamp}] {prefix} {line}"
        
        self.output_lines.append(formatted)
        
        # Manter buffer dentro do limite
        if len(self.output_lines) > self.max_lines:
            self.output_lines = self.output_lines[-self.max_lines:]
    
    def get_duration(self) -> float:
        """Retorna duração atual da sessão"""
        return time.time() - self.start_time
    
    def render(self, width: int) -> RenderableType:
        """Renderiza a sessão como um painel Rich"""
        content = "\n".join(self.output_lines[-100:])  # Mostrar últimas 100 linhas
        
        status = "🟢 RODANDO" if self.is_active else "🔴 FINALIZADO"
        focus_indicator = " ⭐ FOCO" if self.is_focused else ""
        
        header = Text()
        header.append(f"{status}", style="bold green" if self.is_active else "bold red")
        header.append(f" | PID: {self.process.pid}", style="dim")
        header.append(f" | {self.get_duration():.1f}s", style="dim")
        header.append(focus_indicator, style="bold yellow")
        
        return Panel(
            content if content else "[dim]Aguardando saída...[/dim]",
            title=f"Terminal: {self.command[:40]}...",
            subtitle=header,
            border_style="green" if self.is_active else "red",
            box=box.ROUNDED,
            padding=(0, 1),
            width=width,
        )


class TerminalPanel:
    """
    Gerenciador de painéis de terminal com streaming eficiente
    
    Uso:
        panel = TerminalPanel(console)
        
        # Iniciar processo
        session = panel.spawn("npm run dev")
        
        # Stream com select() (eficiente)
        for output in panel.stream(session):
            console.print(output)
        
        # Cancelar processo específico
        panel.cancel(session)
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.sessions: Dict[str, TerminalSession] = {}
        self.focused_session: Optional[str] = None
        self._lock = threading.Lock()
        self._stop_all = threading.Event()
    
    def spawn(
        self,
        command: str,
        cwd: Optional[str] = None,
        shell: str = "/bin/bash",
        env: Optional[Dict[str, str]] = None
    ) -> TerminalSession:
        """
        Spawn um novo processo de terminal
        
        Args:
            command: Comando a executar
            cwd: Diretório de trabalho
            shell: Shell a usar
            env: Variáveis de ambiente
        
        Returns:
            TerminalSession criada
        """
        session_id = f"term_{len(self.sessions)}_{int(time.time())}"
        working_dir = cwd or os.getcwd()
        
        # Configurar ambiente
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        # Criar processo
        process = subprocess.Popen(
            [shell, "-c", command],
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            bufsize=0,  # Binary mode for select
            universal_newlines=False,
            env=full_env
        )
        
        session = TerminalSession(session_id, command, process)
        
        with self._lock:
            self.sessions[session_id] = session
            
            # Focar automaticamente na nova sessão
            self.focused_session = session_id
            session.is_focused = True
        
        return session
    
    def stream(self, session: TerminalSession, callback: Optional[Callable[[str, bool], None]] = None):
        """
        Stream da saída do processo usando select() para eficiência
        
        Args:
            session: Sessão para stream
            callback: Função opcional para chamar com cada linha (linha, is_stderr)
        
        Yields:
            Linhas de saída formatadas
        """
        if not self.console.is_terminal:
            # Modo não-interativo, apenas esperar
            stdout, stderr = process.communicate()
            if stdout:
                for line in stdout.decode('utf-8', errors='replace').splitlines():
                    session.add_output(line, False)
                    yield line
            if stderr:
                for line in stderr.decode('utf-8', errors='replace').splitlines():
                    session.add_output(line, True)
                    yield f"[red]{line}[/red]"
            return
        
        process = session.process
        
        # Usar select para I/O eficiente (sem polling)
        while session.is_active and process.poll() is None:
            # Verificar se deve parar
            if self._stop_all.is_set():
                break
            
            # Usar select para aguardar dados disponíveis
            try:
                readable, _, _ = select.select(
                    [process.stdout, process.stderr],
                    [],
                    [],
                    0.5  # Timeout curto para permitir verificação de stop
                )
            except (ValueError, OSError):
                # Pipes podem fechar
                break
            
            for stream in readable:
                try:
                    # Ler dados disponíveis
                    data = os.read(stream.fileno(), 4096)
                    if not data:
                        # EOF
                        continue
                    
                    text = data.decode('utf-8', errors='replace')
                    lines = text.splitlines()
                    
                    is_stderr = stream == process.stderr
                    
                    for line in lines:
                        session.add_output(line, is_stderr)
                        
                        if callback:
                            callback(line, is_stderr)
                        
                        # Yield para display imediato
                        if is_stderr:
                            yield f"[red]{line}[/red]"
                        else:
                            yield line
                
                except (BlockingIOError, OSError):
                    continue
            
            # Verificar se processo terminou
            retcode = process.poll()
            if retcode is not None:
                session.is_active = False
                break
        
        # Ler qualquer saída restante
        try:
            remaining_stdout, remaining_stderr = process.communicate(timeout=2)
            if remaining_stdout:
                for line in remaining_stdout.decode('utf-8', errors='replace').splitlines():
                    session.add_output(line, False)
                    yield line
            if remaining_stderr:
                for line in remaining_stderr.decode('utf-8', errors='replace').splitlines():
                    session.add_output(line, True)
                    yield f"[red]{line}[/red]"
        except (subprocess.TimeoutExpired, Exception):
            pass
    
    def focus(self, session_id: str):
        """Focar em uma sessão específica"""
        with self._lock:
            # Remover foco de todas
            for sess in self.sessions.values():
                sess.is_focused = False
            
            # Focar na selecionada
            if session_id in self.sessions:
                self.sessions[session_id].is_focused = True
                self.focused_session = session_id
    
    def cancel(self, session_id: str) -> bool:
        """
        Cancelar um processo específico
        
        Args:
            session_id: ID da sessão para cancelar
        
        Returns:
            True se cancelado com sucesso
        """
        with self._lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            
            if not session.is_active:
                return False
            
            # Tentar terminate primeiro
            try:
                session.process.terminate()
                session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Forçar kill
                session.process.kill()
                session.process.wait(timeout=2)
            except Exception:
                pass
            
            session.is_active = False
            session.add_output(f"[yellow]Processo cancelado pelo usuário[/yellow]")
            
            # Remover foco se estava focado
            if self.focused_session == session_id:
                self.focused_session = None
            
            return True
    
    def cancel_focused(self) -> bool:
        """Cancelar o processo atualmente em foco"""
        if self.focused_session:
            return self.cancel(self.focused_session)
        return False
    
    def close(self, session_id: str) -> bool:
        """Fechar e remover uma sessão"""
        with self._lock:
            if session_id not in self.sessions:
                return False
            
            # Cancelar se ainda ativo
            if self.sessions[session_id].is_active:
                self.cancel(session_id)
            
            del self.sessions[session_id]
            
            if self.focused_session == session_id:
                self.focused_session = None
            
            return True
    
    def stop_all(self):
        """Parar todos os processos ativos"""
        self._stop_all.set()
        
        with self._lock:
            for session in self.sessions.values():
                if session.is_active:
                    try:
                        session.process.terminate()
                    except:
                        session.process.kill()
        
        self._stop_all.clear()
    
    def render_all(self, width: Optional[int] = None) -> List[RenderableType]:
        """Renderizar todas as sessões como painéis"""
        if width is None:
            width = self.console.width
        
        renderables = []
        for session_id, session in self.sessions.items():
            renderables.append(session.render(width))
        
        return renderables
    
    def get_status_table(self) -> RenderableType:
        """Retornar tabela de status de todas as sessões"""
        from rich.table import Table
        
        table = Table(title="📟 Terminais Ativos", box=box.SIMPLE)
        table.add_column("ID", style="cyan")
        table.add_column("Comando", style="white")
        table.add_column("PID", style="dim")
        table.add_column("Tempo", style="dim")
        table.add_column("Status", style="green")
        table.add_column("Foco", justify="center")
        
        for session_id, session in self.sessions.items():
            focus_icon = "⭐" if session.is_focused else ""
            status = "🟢" if session.is_active else "🔴"
            
            table.add_row(
                session_id,
                session.command[:30] + "..." if len(session.command) > 30 else session.command,
                str(session.process.pid),
                f"{session.get_duration():.1f}s",
                status,
                focus_icon
            )
        
        return table


# Singleton para uso global
_terminal_panel: Optional[TerminalPanel] = None


def get_terminal_panel(console: Optional[Console] = None) -> TerminalPanel:
    """Retorna instância singleton do TerminalPanel"""
    global _terminal_panel
    if _terminal_panel is None:
        if console is None:
            console = Console()
        _terminal_panel = TerminalPanel(console)
    return _terminal_panel
