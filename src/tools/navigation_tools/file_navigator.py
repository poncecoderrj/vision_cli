"""Ferramentas de navegação no sistema de arquivos."""

from typing import Optional, List, Dict, Any
import os
from pathlib import Path

# Importa o contexto do sistema de arquivos
try:
    from src.core.filesystem_context import FileSystemContext
    fs_context = FileSystemContext()
except ImportError:
    # Fallback para instância simples se não estiver no módulo core
    class SimpleFSContext:
        def __init__(self):
            self._cwd = os.getcwd()
        
        @property
        def cwd(self) -> str:
            return self._cwd
        
        def change_directory(self, path: str) -> bool:
            try:
                if not os.path.isabs(path):
                    target_path = os.path.join(self._cwd, path)
                else:
                    target_path = path
                
                if os.path.isdir(target_path):
                    self._cwd = os.path.abspath(target_path)
                    return True
                return False
            except Exception:
                return False
        
        def resolve_path(self, path: str) -> str:
            if os.path.isabs(path):
                return os.path.normpath(path)
            return os.path.normpath(os.path.join(self._cwd, path))
    
    fs_context = SimpleFSContext()


def list_dir(path: Optional[str] = None) -> str:
    """Lista o conteúdo de um diretório (padrão: diretório atual)."""
    try:
        target_path = path if path else fs_context.cwd
        
        if not os.path.exists(target_path):
            return f"Erro: Diretório não existe: {target_path}"
        
        if not os.path.isdir(target_path):
            return f"Erro: Não é um diretório: {target_path}"
        
        contents = []
        try:
            for entry in os.scandir(target_path):
                if entry.name.startswith('.'):
                    continue
                
                if entry.is_dir():
                    contents.append(f"📁 {entry.name}/")
                else:
                    size = entry.stat().st_size
                    size_str = _format_size(size)
                    contents.append(f"📄 {entry.name} ({size_str})")
        except PermissionError:
            return f"Erro: Sem permissão para acessar: {target_path}"
        
        # Ordena: pastas primeiro, depois arquivos
        contents.sort(key=lambda x: (not x.startswith("📁"), x.lower()))
        
        result = [f"Conteúdo de {target_path}:", "=" * 50]
        result.extend(contents)
        
        if not contents:
            result.append("(diretório vazio)")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Erro ao listar diretório: {str(e)}"


def change_directory(path: str) -> str:
    """Muda o diretório de trabalho atual."""
    try:
        if not path:
            return f"Diretório atual: {fs_context.cwd}"
        
        success = fs_context.change_directory(path)
        
        if success:
            return f"Mudou para: {fs_context.cwd}"
        else:
            return f"Erro: Diretório não existe: {path}"
    
    except Exception as e:
        return f"Erro ao mudar diretório: {str(e)}"


def get_current_directory() -> str:
    """Retorna o diretório de trabalho atual."""
    return f"Diretório atual: {fs_context.cwd}"


def find_files(pattern: str, max_results: int = 20) -> str:
    """Busca arquivos por padrão (glob-like)."""
    try:
        results = []
        search_root = fs_context.cwd
        
        # Converte padrão simples para busca
        # Ex: "*.py" → busca todos .py
        # Ex: "**/*.js" → busca recursivo
        
        recursive = "**" in pattern
        clean_pattern = pattern.replace("**/", "").replace("*/", "")
        
        for root, dirs, files in os.walk(search_root):
            # Limita profundidade se não for recursivo
            if not recursive:
                depth = os.path.relpath(root, search_root).count(os.sep)
                if depth > 0:
                    continue
            
            for file in files:
                if _matches_pattern(file, clean_pattern):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, search_root)
                    results.append(rel_path)
                
                if len(results) >= max_results:
                    break
            
            if len(results) >= max_results:
                break
        
        if not results:
            return f"Nenhum arquivo encontrado para o padrão: {pattern}"
        
        result_lines = [f"Arquivos encontrados ({len(results)}):", "=" * 50]
        result_lines.extend(results)
        
        return "\n".join(result_lines)
    
    except Exception as e:
        return f"Erro na busca: {str(e)}"


def _format_size(size: int) -> str:
    """Formata tamanho de arquivo em KB/MB."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _matches_pattern(filename: str, pattern: str) -> bool:
    """Verifica se nome do arquivo corresponde ao padrão."""
    import fnmatch
    
    if pattern.startswith("*."):
        ext = pattern[1:]  # ".py"
        return filename.endswith(ext)
    elif "*" in pattern:
        return fnmatch.fnmatch(filename, pattern)
    else:
        return filename == pattern


# Registro das ferramentas disponíveis
AVAILABLE_NAVIGATION_TOOLS = {
    "list_dir": {
        "function": list_dir,
        "description": "Lista o conteúdo de um diretório. Use para saber onde está antes de criar/modificar arquivos.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho do diretório (opcional, padrão: diretório atual)"
                }
            },
            "required": []
        }
    },
    "change_directory": {
        "function": change_directory,
        "description": "Muda o diretório de trabalho atual. Útil para navegar entre pastas.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho para o diretório (relativo ou absoluto)"
                }
            },
            "required": ["path"]
        }
    },
    "get_current_directory": {
        "function": get_current_directory,
        "description": "Retorna o diretório de trabalho atual.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "find_files": {
        "function": find_files,
        "description": "Busca arquivos por padrão (ex: '*.py', '**/*.js').",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Padrão de busca (ex: '*.py', 'test_*.js')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 20)"
                }
            },
            "required": ["pattern"]
        }
    }
}
