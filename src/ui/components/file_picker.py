"""
File Picker - Seletor de arquivos interativo com busca fuzzy
"""

from pathlib import Path
from typing import List, Optional, Tuple
import fnmatch


class FilePicker:
    """Seletor de arquivos estilo fzf/ranger"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.files: List[Path] = []
        self.filtered: List[Path] = []
        self.selected_index = 0
        self.search_query = ""
        self.multi_select = False
        self.selected_items: List[Path] = []
    
    def scan(self, max_files: int = 1000, 
             extensions: Optional[List[str]] = None,
             exclude_patterns: Optional[List[str]] = None):
        """Escaneia diretório em busca de arquivos"""
        self.files = []
        
        exclude_patterns = exclude_patterns or [
            '__pycache__', '.git', 'node_modules', 
            '*.pyc', '*.so', '*.dll', '.env'
        ]
        
        for file_path in self.root_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Verifica exclusões
            skip = False
            rel_path = str(file_path.relative_to(self.root_path))
            
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(rel_path, f'*{pattern}*') or \
                   fnmatch.fnmatch(file_path.name, pattern):
                    skip = True
                    break
            
            if skip:
                continue
            
            # Filtra por extensão se especificado
            if extensions:
                if file_path.suffix not in extensions:
                    continue
            
            self.files.append(file_path)
            
            if len(self.files) >= max_files:
                break
        
        self.files.sort()
        self.filtered = self.files.copy()
        self.selected_index = 0
    
    def filter(self, query: str):
        """Filtra arquivos por query (fuzzy match simples)"""
        self.search_query = query.lower()
        
        if not query:
            self.filtered = self.files.copy()
            self.selected_index = min(self.selected_index, len(self.filtered) - 1)
            return
        
        self.filtered = []
        for file_path in self.files:
            rel_path = str(file_path.relative_to(self.root_path)).lower()
            filename = file_path.name.lower()
            
            # Match simples: query deve estar contida no path ou nome
            if self.search_query in rel_path or self.search_query in filename:
                self.filtered.append(file_path)
        
        self.selected_index = 0
    
    def move_up(self):
        """Move seleção para cima"""
        if self.selected_index > 0:
            self.selected_index -= 1
    
    def move_down(self):
        """Move seleção para baixo"""
        if self.selected_index < len(self.filtered) - 1:
            self.selected_index += 1
    
    def toggle_selection(self):
        """Toggle seleção do item atual (multi-select)"""
        current = self.filtered[self.selected_index] if self.filtered else None
        if current:
            if current in self.selected_items:
                self.selected_items.remove(current)
            else:
                self.selected_items.append(current)
    
    def get_selected(self) -> Optional[Path]:
        """Retorna arquivo selecionado atualmente"""
        if self.filtered and 0 <= self.selected_index < len(self.filtered):
            return self.filtered[self.selected_index]
        return None
    
    def render_list(self, height: int = 20, use_colors: bool = True) -> str:
        """Renderiza lista de arquivos"""
        lines = []
        
        # Header
        header = f"📁 {self.root_path}"
        if self.search_query:
            header += f" 🔍 '{self.search_query}'"
        header += f" ({len(self.filtered)}/{len(self.files)} arquivos)"
        
        lines.append(header)
        lines.append("─" * 60)
        
        # Calcula range visível
        start = max(0, self.selected_index - height // 2)
        end = min(start + height, len(self.filtered))
        
        if end - start < height and start > 0:
            start = max(0, end - height)
        
        # Renderiza itens
        for i in range(start, end):
            file_path = self.filtered[i]
            rel_path = str(file_path.relative_to(self.root_path))
            
            # Ícone baseado no tipo
            suffix = file_path.suffix.lower()
            if suffix in ['.py']:
                icon = "🐍"
            elif suffix in ['.js', '.ts', '.jsx', '.tsx']:
                icon = "📜"
            elif suffix in ['.md', '.txt', '.rst']:
                icon = "📄"
            elif suffix in ['.json', '.yaml', '.yml', '.toml']:
                icon = "⚙️"
            elif suffix in ['.html', '.css', '.scss']:
                icon = "🎨"
            else:
                icon = "📁"
            
            # Formata linha
            is_selected = i == self.selected_index
            is_multi_selected = file_path in self.selected_items
            
            prefix = "▸ " if is_selected else "  "
            marker = "✓ " if is_multi_selected else "  "
            
            if use_colors:
                if is_selected:
                    line = f"\033[97m\033[44m{prefix}{marker}{icon} {rel_path}\033[0m"
                else:
                    line = f"\033[2m{prefix}{marker}{icon} {rel_path}\033[0m"
            else:
                line = f"{prefix}{marker}{icon} {rel_path}"
            
            lines.append(line)
        
        # Footer
        lines.append("─" * 60)
        lines.append("↑↓ navegar | / buscar | espaço selecionar | enter confirmar | q cancelar")
        
        return '\n'.join(lines)
    
    def run_interactive(self) -> Optional[Path]:
        """
        Executa picker interativo (requer prompt_toolkit)
        Retorna o arquivo selecionado ou None se cancelado
        """
        try:
            from prompt_toolkit import Application
            from prompt_toolkit.layout import Layout, Window, HSplit
            from prompt_toolkit.layout.controls import FormattedTextControl
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.formatted_text import HTML
            
            kb = KeyBindings()
            
            @kb.add('up')
            def _(event):
                self.move_up()
                update_display()
            
            @kb.add('down')
            def _(event):
                self.move_down()
                update_display()
            
            @kb.add('space')
            def _(event):
                self.toggle_selection()
                update_display()
            
            @kb.add('enter')
            def _(event):
                event.app.exit(result=self.get_selected())
            
            @kb.add('q')
            @kb.add('c-c')
            def _(event):
                event.app.exit(result=None)
            
            text_control = FormattedTextControl(lambda: HTML(self.render_list(use_colors=False)))
            
            layout = Layout(HSplit([Window(content=text_control)]))
            
            app = Application(layout=layout, key_bindings=kb, full_screen=True)
            
            return app.run()
        except ImportError:
            # Fallback para versão simples sem prompt_toolkit
            print("\n⚠️  prompt_toolkit não disponível. Use versão CLI simples.")
            return self.get_selected()


# Função utilitária para uso rápido
def pick_file(root: str = ".", 
              extensions: Optional[List[str]] = None,
              multi: bool = False) -> Optional[Path]:
    """
    Abre picker de arquivos e retorna seleção
    
    Exemplo:
        file = pick_file(extensions=['.py', '.md'])
        if file:
            print(f"Selecionado: {file}")
    """
    picker = FilePicker(root)
    picker.scan(extensions=extensions)
    picker.multi_select = multi
    return picker.run_interactive()
