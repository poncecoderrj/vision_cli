import os
import json
from pathlib import Path
from typing import List, Dict, Optional

class FileSystemContext:
    """Gerencia o contexto do sistema de arquivos e localização atual."""
    
    def __init__(self):
        self._cwd = os.getcwd()
        self._history = [self._cwd]
    
    @property
    def cwd(self) -> str:
        """Retorna o diretório de trabalho atual."""
        return self._cwd
    
    @cwd.setter
    def cwd(self, path: str):
        """Define um novo diretório de trabalho."""
        if os.path.isdir(path):
            self._cwd = os.path.abspath(path)
            self._history.append(self._cwd)
        else:
            raise ValueError(f"Diretório não existe: {path}")
    
    def change_directory(self, path: str) -> bool:
        """Muda o diretório de trabalho (suporta caminhos relativos e absolutos)."""
        try:
            # Se for caminho relativo, combina com o cwd atual
            if not os.path.isabs(path):
                target_path = os.path.join(self._cwd, path)
            else:
                target_path = path
            
            target_path = os.path.normpath(target_path)
            
            if os.path.isdir(target_path):
                self._cwd = target_path
                self._history.append(self._cwd)
                return True
            else:
                return False
        except Exception:
            return False
    
    def get_relative_path(self, absolute_path: str) -> str:
        """Converte um caminho absoluto para relativo ao cwd atual."""
        try:
            return os.path.relpath(absolute_path, self._cwd)
        except ValueError:
            # Caminhos em drives diferentes no Windows
            return absolute_path
    
    def resolve_path(self, path: str) -> str:
        """Resolve um caminho (relativo ou absoluto) para absoluto baseado no cwd."""
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self._cwd, path))
    
    def find_file_or_folder(self, name: str, max_depth: int = 5) -> List[str]:
        """
        Busca inteligente por arquivos ou pastas com o nome dado.
        Retorna lista de caminhos absolutos encontrados.
        """
        results = []
        search_root = self._cwd
        
        for root, dirs, files in os.walk(search_root):
            # Calcula profundidade relativa ao cwd
            rel_path = os.path.relpath(root, search_root)
            depth = rel_path.count(os.sep) + 1 if rel_path != '.' else 0
            
            if depth > max_depth:
                continue
            
            # Verifica pastas
            if name in dirs:
                results.append(os.path.join(root, name))
            
            # Verifica arquivos
            if name in files:
                results.append(os.path.join(root, name))
        
        return results
    
    def list_contents(self, path: Optional[str] = None, show_hidden: bool = False) -> List[Dict]:
        """Lista o conteúdo de um diretório (padrão: cwd atual)."""
        target_path = path if path else self._cwd
        
        if not os.path.isdir(target_path):
            return []
        
        contents = []
        try:
            for entry in os.scandir(target_path):
                if not show_hidden and entry.name.startswith('.'):
                    continue
                
                entry_info = {
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir(),
                    "is_file": entry.is_file()
                }
                
                if entry.is_file():
                    try:
                        entry_info["size"] = entry.stat().st_size
                    except Exception:
                        entry_info["size"] = 0
                
                contents.append(entry_info)
        except PermissionError:
            pass
        
        # Ordena: pastas primeiro, depois arquivos, ambos alfabeticamente
        contents.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return contents
    
    def get_tree(self, path: Optional[str] = None, max_depth: int = 3, current_depth: int = 0) -> str:
        """Gera uma representação em árvore do diretório."""
        target_path = path if path else self._cwd
        
        if not os.path.isdir(target_path) or current_depth > max_depth:
            return ""
        
        tree_lines = []
        indent = "  " * current_depth
        
        try:
            entries = sorted(os.scandir(target_path), key=lambda e: e.name.lower())
            for entry in entries:
                if entry.name.startswith('.'):
                    continue
                
                if entry.is_dir():
                    tree_lines.append(f"{indent}📁 {entry.name}/")
                    subtree = self.get_tree(entry.path, max_depth, current_depth + 1)
                    if subtree:
                        tree_lines.append(subtree)
                elif entry.is_file():
                    tree_lines.append(f"{indent}📄 {entry.name}")
        except PermissionError:
            tree_lines.append(f"{indent}🔒 [Sem permissão]")
        
        return "\n".join(tree_lines)
    
    def get_context_summary(self) -> Dict:
        """Retorna um resumo do contexto atual do sistema de arquivos."""
        return {
            "cwd": self._cwd,
            "cwd_display": self._cwd.replace(os.path.expanduser("~"), "~"),
            "history_length": len(self._history),
            "last_5_dirs": self._history[-5:] if len(self._history) > 5 else self._history
        }
