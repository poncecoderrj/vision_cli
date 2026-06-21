"""
Context Dashboard - Monitoramento em tempo real de tokens, custo e contexto
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenStats:
    """Estatísticas de uso de tokens"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    
    def add(self, prompt: int, completion: int):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.requests += 1


@dataclass
class ContextWindow:
    """Gerenciamento da janela de contexto"""
    max_tokens: int = 128000  # Padrão para modelos grandes
    used_tokens: int = 0
    messages_count: int = 0
    
    @property
    def available_tokens(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)
    
    @property
    def usage_percentage(self) -> float:
        if self.max_tokens == 0:
            return 0.0
        return min(100.0, (self.used_tokens / self.max_tokens) * 100)
    
    def is_near_limit(self, threshold: float = 0.85) -> bool:
        return self.usage_percentage >= (threshold * 100)


class ContextDashboard:
    """Dashboard de contexto em tempo real"""
    
    def __init__(self, model_name: str = "gpt-4", 
                 max_tokens: int = 128000,
                 cost_per_1k_input: float = 0.03,
                 cost_per_1k_output: float = 0.06):
        self.model_name = model_name
        self.context = ContextWindow(max_tokens=max_tokens)
        self.token_stats = TokenStats()
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.start_time = datetime.now()
        self.tools_called: Dict[str, int] = {}
    
    def record_tokens(self, prompt_tokens: int, completion_tokens: int):
        """Registra uso de tokens de uma requisição"""
        self.token_stats.add(prompt_tokens, completion_tokens)
        self.context.used_tokens = self.token_stats.total_tokens
        self.context.messages_count = self.token_stats.requests
    
    def record_tool_call(self, tool_name: str):
        """Registra chamada de tool"""
        self.tools_called[tool_name] = self.tools_called.get(tool_name, 0) + 1
    
    def estimate_cost(self) -> float:
        """Estima custo atual baseado nos tokens usados"""
        input_cost = (self.token_stats.prompt_tokens / 1000) * self.cost_per_1k_input
        output_cost = (self.token_stats.completion_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost
    
    def get_elapsed_time(self) -> str:
        """Retorna tempo decorrido desde o início"""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def render_dashboard(self, use_rich: bool = True) -> str:
        """Renderiza o dashboard formatado"""
        if use_rich:
            try:
                from rich.panel import Panel
                from rich.text import Text
                from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
                
                # Cria texto do dashboard
                text = Text()
                
                # Header
                text.append(f"🤖 {self.model_name}\n", style="bold blue")
                text.append(f"⏱️  Sessão: {self.get_elapsed_time()}\n\n", style="dim")
                
                # Tokens
                text.append("📊 TOKENS:\n", style="bold")
                text.append(f"  Prompt:     {self.token_stats.prompt_tokens:,}\n", style="cyan")
                text.append(f"  Completion: {self.token_stats.completion_tokens:,}\n", style="green")
                text.append(f"  Total:      {self.token_stats.total_tokens:,}\n", style="yellow")
                text.append(f"  Requests:   {self.token_stats.requests}\n\n", style="dim")
                
                # Context Window
                text.append("🪟 CONTEXT WINDOW:\n", style="bold")
                usage_pct = self.context.usage_percentage
                color = "green" if usage_pct < 50 else "yellow" if usage_pct < 80 else "red"
                text.append(f"  Usado: {self.context.used_tokens:,} / {self.context.max_tokens:,}\n", style=color)
                text.append(f"  Disponível: {self.context.available_tokens:,}\n", style="dim")
                
                # Barra de progresso ASCII
                bar_width = 30
                filled = int((usage_pct / 100) * bar_width)
                bar = "█" * filled + "░" * (bar_width - filled)
                text.append(f"  [{bar}] {usage_pct:.1f}%\n\n", style=color)
                
                # Custo
                text.append("💰 CUSTO ESTIMADO:\n", style="bold")
                text.append(f"  ${self.estimate_cost():.4f}\n\n", style="gold")
                
                # Tools
                if self.tools_called:
                    text.append("🛠️ TOOLS USADAS:\n", style="bold")
                    for tool, count in sorted(self.tools_called.items(), 
                                             key=lambda x: x[1], reverse=True)[:5]:
                        text.append(f"  {tool}: {count}\n", style="dim")
                
                return text
            except ImportError:
                pass
        
        # Fallback para texto simples
        lines = [
            f"🤖 {self.model_name} | ⏱️  {self.get_elapsed_time()}",
            "",
            "📊 TOKENS:",
            f"  Prompt: {self.token_stats.prompt_tokens:,}",
            f"  Completion: {self.token_stats.completion_tokens:,}",
            f"  Total: {self.token_stats.total_tokens:,}",
            f"  Requests: {self.token_stats.requests}",
            "",
            "🪟 CONTEXT WINDOW:",
            f"  {self.context.used_tokens:,} / {self.context.max_tokens:,} "
            f"({self.context.usage_percentage:.1f}%)",
            f"  Disponível: {self.context.available_tokens:,}",
            "",
            f"💰 CUSTO: ${self.estimate_cost():.4f}",
        ]
        
        if self.tools_called:
            lines.append("")
            lines.append("🛠️ TOOLS:")
            for tool, count in list(self.tools_called.items())[:5]:
                lines.append(f"  {tool}: {count}")
        
        return '\n'.join(lines)
    
    def reset(self):
        """Reseta todas as estatísticas"""
        self.token_stats = TokenStats()
        self.context.used_tokens = 0
        self.context.messages_count = 0
        self.tools_called = {}
        self.start_time = datetime.now()


# Singleton global
dashboard = ContextDashboard()
