"""
Navigation tools - list_dir, glob_files, search_code
"""

from pathlib import Path
from typing import Optional, List
import fnmatch
import re

from src.tools import Tool, ToolResult


class ListDirTool:
    """Lista o conteúdo de um diretório"""
    
    name = "list_dir"
    description = "Lista arquivos e subdiretórios em um caminho"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do diretório"}
        },
        "required": ["path"]
    }
    
    def execute(self, path: str) -> ToolResult:
        dir_path = Path(path)
        
        if not dir_path.exists():
            return ToolResult(success=False, output="", error=f"Diretório não encontrado: {path}")
        
        if not dir_path.is_dir():
            return ToolResult(success=False, output="", error=f"Não é um diretório: {path}")
        
        try:
            items = []
            for item in sorted(dir_path.iterdir()):
                item_type = "dir" if item.is_dir() else "file"
                size = item.stat().st_size if item.is_file() else 0
                items.append({
                    "name": item.name,
                    "type": item_type,
                    "size": size,
                    "path": str(item)
                })
            
            # Formata output
            output_lines = []
            for item in items:
                icon = "📁" if item["type"] == "dir" else "📄"
                size_str = f" ({item['size']:,} bytes)" if item["size"] > 0 else ""
                output_lines.append(f"{icon} {item['name']}{size_str}")
            
            metadata = {
                "total_items": len(items),
                "dirs": sum(1 for i in items if i["type"] == "dir"),
                "files": sum(1 for i in items if i["type"] == "file")
            }
            
            return ToolResult(
                success=True,
                output='\n'.join(output_lines),
                metadata=metadata
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, path: str, **kwargs) -> bool:
        return bool(path)


class GlobFilesTool:
    """Encontra arquivos por padrão glob"""
    
    name = "glob_files"
    description = "Encontra arquivos correspondendo a um padrão (ex: '**/*.py')"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Padrão glob (ex: '**/*.py', '*.md')"},
            "path": {"type": "string", "description": "Diretório base (padrão: .)"}
        },
        "required": ["pattern"]
    }
    
    def execute(self, pattern: str, path: str = ".") -> ToolResult:
        base_path = Path(path)
        
        if not base_path.exists():
            return ToolResult(success=False, output="", error=f"Caminho não encontrado: {path}")
        
        try:
            # Usa glob recursivo se tiver **
            recursive = "**" in pattern
            
            if recursive:
                matches = list(base_path.rglob(pattern.replace("**/", "")))
            else:
                matches = list(base_path.glob(pattern))
            
            # Limita a 100 resultados
            matches = matches[:100]
            
            output_lines = [str(m.relative_to(base_path)) for m in matches]
            
            metadata = {
                "total_matches": len(matches),
                "pattern": pattern,
                "base_path": str(base_path)
            }
            
            return ToolResult(
                success=True,
                output='\n'.join(output_lines) if output_lines else "Nenhum arquivo encontrado",
                metadata=metadata
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, pattern: str, **kwargs) -> bool:
        return bool(pattern)


class SearchCodeTool:
    """Busca por regex no conteúdo dos arquivos (grep)"""
    
    name = "search_code"
    description = "Busca por padrão regex no conteúdo de arquivos. Similar ao grep."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Padrão regex para buscar"},
            "path": {"type": "string", "description": "Diretório base (padrão: .)"},
            "glob": {"type": "string", "description": "Filtro glob para arquivos (ex: '*.py')"}
        },
        "required": ["pattern"]
    }
    
    def execute(self, pattern: str, path: str = ".", 
                glob: Optional[str] = None) -> ToolResult:
        base_path = Path(path)
        
        if not base_path.exists():
            return ToolResult(success=False, output="", error=f"Caminho não encontrado: {path}")
        
        try:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            results = []
            
            # Determina quais arquivos buscar
            if glob:
                files = list(base_path.rglob(glob.replace("**/", "")))
            else:
                # Busca em todos os arquivos de texto comuns
                files = []
                for ext in ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx', '*.md', 
                           '*.txt', '*.json', '*.yaml', '*.yml', '*.html', '*.css']:
                    files.extend(base_path.rglob(ext))
            
            # Limita a 500 arquivos
            files = files[:500]
            
            matches_count = 0
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    matches = regex.finditer(content)
                    for match in matches:
                        # Pega linha do match
                        start_pos = match.start()
                        line_start = content.rfind('\n', 0, start_pos) + 1
                        line_end = content.find('\n', start_pos)
                        if line_end == -1:
                            line_end = len(content)
                        
                        line_num = content[:start_pos].count('\n') + 1
                        line_content = content[line_start:line_end].strip()
                        
                        results.append({
                            "file": str(file_path.relative_to(base_path)),
                            "line": line_num,
                            "content": line_content
                        })
                        
                        matches_count += 1
                        
                        # Limita a 50 matches
                        if matches_count >= 50:
                            break
                    
                    if matches_count >= 50:
                        break
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            # Formata output
            output_lines = []
            for r in results:
                output_lines.append(f"{r['file']}:{r['line']}: {r['content']}")
            
            metadata = {
                "total_matches": matches_count,
                "pattern": pattern,
                "files_searched": len(files)
            }
            
            return ToolResult(
                success=True,
                output='\n'.join(output_lines) if output_lines else "Nenhuma correspondência encontrada",
                metadata=metadata
            )
        except re.error as e:
            return ToolResult(success=False, output="", error=f"Regex inválido: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, pattern: str, **kwargs) -> bool:
        return bool(pattern)


# Exporta as tools
list_dir_tool = ListDirTool()
glob_files_tool = GlobFilesTool()
search_code_tool = SearchCodeTool()

NAVIGATION_TOOLS = [list_dir_tool, glob_files_tool, search_code_tool]


# Funções getter para o registry
def get_list_dir_tool():
    return list_dir_tool

def get_glob_files_tool():
    return glob_files_tool

def get_search_code_tool():
    return search_code_tool
