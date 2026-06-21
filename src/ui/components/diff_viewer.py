"""
Diff Viewer - Visualização interativa de diffs com cores e seleção de blocos
"""

from typing import List, Tuple, Optional
from difflib import unified_diff
import re


class DiffViewer:
    """Visualizador de diffs com suporte a cores e seleção de blocos"""
    
    def __init__(self):
        self.diff_lines: List[str] = []
        self.hunks: List[dict] = []
    
    def generate_diff(self, old_content: str, new_content: str, 
                     from_file: str = "", to_file: str = "") -> str:
        """Gera diff no formato unified"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Garante que todas as linhas terminam com \n
        if old_lines and not old_lines[-1].endswith('\n'):
            old_lines[-1] += '\n'
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        
        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile=from_file,
            tofile=to_file,
            lineterm='\n'
        )
        
        self.diff_lines = list(diff)
        self._parse_hunks()
        
        return ''.join(self.diff_lines)
    
    def _parse_hunks(self):
        """Parse dos hunks do diff para seleção individual"""
        self.hunks = []
        current_hunk = None
        
        for line in self.diff_lines:
            if line.startswith('@@'):
                if current_hunk:
                    self.hunks.append(current_hunk)
                
                # Parse @@ -old_start,old_count +new_start,new_count @@
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    current_hunk = {
                        'header': line,
                        'old_start': int(match.group(1)),
                        'old_count': int(match.group(2)) if match.group(2) else 1,
                        'new_start': int(match.group(3)),
                        'new_count': int(match.group(4)) if match.group(4) else 1,
                        'lines': [line]
                    }
            elif current_hunk:
                current_hunk['lines'].append(line)
        
        if current_hunk:
            self.hunks.append(current_hunk)
    
    def format_colored(self, use_rich: bool = True) -> str:
        """Formata o diff com cores"""
        if use_rich:
            try:
                from rich.text import Text
                from rich.panel import Panel
                
                text = Text()
                for line in self.diff_lines:
                    if line.startswith('+') and not line.startswith('+++'):
                        text.append(line, style="green")
                    elif line.startswith('-') and not line.startswith('---'):
                        text.append(line, style="red")
                    elif line.startswith('@'):
                        text.append(line, style="cyan bold")
                    elif line.startswith(' '):
                        text.append(line, style="dim")
                    else:
                        text.append(line, style="yellow")
                
                return text
            except ImportError:
                pass
        
        # Fallback para texto simples com ANSI
        output = []
        for line in self.diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                output.append(f"\033[92m{line}\033[0m")
            elif line.startswith('-') and not line.startswith('---'):
                output.append(f"\033[91m{line}\033[0m")
            elif line.startswith('@'):
                output.append(f"\033[96m\033[1m{line}\033[0m")
            elif line.startswith(' '):
                output.append(f"\033[2m{line}\033[0m")
            else:
                output.append(f"\033[93m{line}\033[0m")
        
        return ''.join(output)
    
    def get_hunk_summary(self) -> str:
        """Retorna resumo dos hunks"""
        if not self.hunks:
            return "Nenhuma mudança detectada"
        
        lines = [f"{len(self.hunks)} bloco(s) de mudanças:", ""]
        for i, hunk in enumerate(self.hunks, 1):
            lines.append(
                f"  [{i}] Linhas {hunk['old_start']}-{hunk['old_start'] + hunk['old_count']} "
                f"→ {hunk['new_start']}-{hunk['new_start'] + hunk['new_count']}"
            )
        
        return '\n'.join(lines)
    
    def apply_selected_hunks(self, old_content: str, hunk_indices: List[int]) -> str:
        """Aplica apenas hunks selecionados ao conteúdo original"""
        if not hunk_indices:
            return old_content
        
        lines = old_content.splitlines(keepends=True)
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        
        # Ordena índices em ordem decrescente para aplicar do fim para o início
        for idx in sorted(hunk_indices, reverse=True):
            if idx < 1 or idx > len(self.hunks):
                continue
            
            hunk = self.hunks[idx - 1]
            old_start = hunk['old_start'] - 1  # Convert para 0-based
            
            # Extrai linhas novas do hunk
            new_lines = []
            for line in hunk['lines'][1:]:  # Pula header
                if line.startswith('+'):
                    new_lines.append(line[1:])
                elif not line.startswith('-') and not line.startswith('\\'):
                    new_lines.append(line[1:])
            
            # Substitui linhas antigas pelas novas
            lines[old_start:old_start + hunk['old_count']] = new_lines
        
        return ''.join(lines)
    
    def render_interactive(self) -> str:
        """Renderiza view interativa para seleção de hunks"""
        output = []
        output.append("\n" + "="*60)
        output.append("📝 DIFF PREVIEW - Selecione os blocos para aplicar")
        output.append("="*60 + "\n")
        
        for i, hunk in enumerate(self.hunks, 1):
            output.append(f"\033[96m\033[1m[Hunk {i}]\033[0m")
            output.append(f"  Linhas {hunk['old_start']}-{hunk['old_start'] + hunk['old_count']} → "
                         f"{hunk['new_start']}-{hunk['new_start'] + hunk['new_count']}")
            
            for line in hunk['lines'][1:]:  # Pula header
                if line.startswith('+'):
                    output.append(f"\033[92m{line}\033[0m", end='')
                elif line.startswith('-'):
                    output.append(f"\033[91m{line}\033[0m", end='')
                elif line.startswith(' '):
                    output.append(f"\033[2m{line}\033[0m", end='')
                else:
                    output.append(line, end='')
            output.append("")
        
        output.append("\n" + "="*60)
        output.append("Comandos:")
        output.append("  [a]pply all   - Aplica todos os hunks")
        output.append("  [s]kip all    - Pula todos (não aplica nada)")
        output.append("  [1], [2], ... - Toggle hunk específico")
        output.append("  [q]uit        - Cancelar edição")
        output.append("="*60 + "\n")
        
        return '\n'.join(output)


# Singleton global
diff_viewer = DiffViewer()
