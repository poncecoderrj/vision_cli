"""
File manipulation tools
"""

from pathlib import Path
from typing import Optional, Dict, Any
import difflib

from src.tools import Tool, ToolResult


class ReadFileTool:
    """Lê o conteúdo de um arquivo de texto"""
    
    name = "read_file"
    description = "Lê um arquivo de texto. Use offset/limit para ler em chunks."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"},
            "offset": {"type": "integer", "description": "Linha inicial (0-based)"},
            "limit": {"type": "integer", "description": "Número máximo de linhas"}
        },
        "required": ["path"]
    }
    
    def execute(self, path: str, offset: int = 0, limit: Optional[int] = None) -> ToolResult:
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"Arquivo não encontrado: {path}")
        
        if not file_path.is_file():
            return ToolResult(success=False, output="", error=f"Não é um arquivo: {path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Aplica offset e limit
            if offset > 0:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]
            
            content = ''.join(lines)
            total_lines = len(lines)
            
            metadata = {
                "total_lines": total_lines,
                "offset": offset,
                "limit": limit,
                "file_size": file_path.stat().st_size
            }
            
            return ToolResult(
                success=True,
                output=content,
                metadata=metadata
            )
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="Arquivo binário ou codificação não suportada"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, path: str, **kwargs) -> bool:
        return bool(path)


class WriteFileTool:
    """Cria ou sobrescreve um arquivo"""
    
    name = "write_file"
    description = "Cria ou sobrescreve um arquivo com o conteúdo especificado"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"},
            "content": {"type": "string", "description": "Conteúdo a ser escrito"}
        },
        "required": ["path", "content"]
    }
    
    def execute(self, path: str, content: str) -> ToolResult:
        file_path = Path(path)
        
        # Cria diretórios intermediários se necessário
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            metadata = {
                "file_size": file_path.stat().st_size,
                "lines": content.count('\n') + 1
            }
            
            return ToolResult(
                success=True,
                output=f"Arquivo escrito: {path} ({metadata['lines']} linhas)",
                metadata=metadata
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, path: str, content: str, **kwargs) -> bool:
        return bool(path) and content is not None


class EditFileTool:
    """Edita um arquivo substituindo texto exato com fuzzy match"""
    
    name = "edit_file"
    description = "Substitui texto EXATO em um arquivo. Para melhor resultado, copie a indentação exata."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"},
            "old_string": {"type": "string", "description": "Texto original a ser substituído"},
            "new_string": {"type": "string", "description": "Novo texto"},
            "replace_all": {"type": "boolean", "description": "Substituir todas as ocorrências"}
        },
        "required": ["path", "old_string", "new_string"]
    }
    
    def __init__(self, fuzzy_threshold: float = 0.8):
        self.fuzzy_threshold = fuzzy_threshold
    
    def _find_match_fuzzy(self, content: str, old_string: str) -> tuple[int, int, str]:
        """Encontra correspondência usando fuzzy matching"""
        lines_content = content.split('\n')
        lines_old = old_string.split('\n')
        
        # Tenta match exato primeiro
        exact_start = content.find(old_string)
        if exact_start != -1:
            return exact_start, exact_start + len(old_string), old_string
        
        # Fuzzy match por linhas
        for i in range(len(lines_content) - len(lines_old) + 1):
            chunk = '\n'.join(lines_content[i:i + len(lines_old)])
            ratio = difflib.SequenceMatcher(None, chunk, old_string).ratio()
            
            if ratio >= self.fuzzy_threshold:
                start = sum(len(l) + 1 for l in lines_content[:i])
                end = start + len(chunk)
                return start, end, chunk
        
        return -1, -1, ""
    
    def generate_diff(self, old_content: str, new_content: str, filepath: str = "") -> str:
        """Gera um diff colorido no formato unified"""
        from difflib import unified_diff
        
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filepath}" if filepath else "",
            tofile=f"b/{filepath}" if filepath else "",
            lineterm='\n'
        )
        
        return ''.join(diff)
    
    def execute(self, path: str, old_string: str, new_string: str, 
                replace_all: bool = False, show_diff: bool = True) -> ToolResult:
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"Arquivo não encontrado: {path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            if replace_all:
                # Substituição global
                if old_string not in content:
                    # Tenta fuzzy match
                    start, end, matched = self._find_match_fuzzy(content, old_string)
                    if start == -1:
                        return ToolResult(
                            success=False,
                            output="",
                            error="Texto não encontrado (nem com fuzzy match)"
                        )
                    content = content[:start] + new_string + content[end:]
                else:
                    content = content.replace(old_string, new_string)
            else:
                # Substituição única
                start, end, matched = self._find_match_fuzzy(content, old_string)
                
                if start == -1:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Texto não encontrado. Verifique a indentação exata."
                    )
                
                content = content[:start] + new_string + content[end:]
            
            # Gera diff para preview
            diff_output = ""
            if show_diff and original_content != content:
                diff_output = self.generate_diff(original_content, content, path)
            
            # Escreve o arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            metadata = {
                "diff": diff_output,
                "old_size": len(original_content),
                "new_size": len(content),
                "changes": abs(len(content) - len(original_content))
            }
            
            return ToolResult(
                success=True,
                output=f"Arquivo editado: {path}\n\n{diff_output}",
                metadata=metadata
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, path: str, old_string: str, new_string: str, **kwargs) -> bool:
        return bool(path) and old_string is not None and new_string is not None


class DeleteFileTool:
    """Deleta um arquivo"""
    
    name = "delete_file"
    description = "Deleta um arquivo permanentemente"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do arquivo"}
        },
        "required": ["path"]
    }
    
    def execute(self, path: str) -> ToolResult:
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"Arquivo não encontrado: {path}")
        
        if not file_path.is_file():
            return ToolResult(success=False, output="", error=f"Não é um arquivo: {path}")
        
        try:
            file_path.unlink()
            return ToolResult(
                success=True,
                output=f"Arquivo deletado: {path}"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def validate(self, path: str, **kwargs) -> bool:
        return bool(path)


# Exporta as tools
read_file_tool = ReadFileTool()
write_file_tool = WriteFileTool()
edit_file_tool = EditFileTool()
delete_file_tool = DeleteFileTool()

FILE_TOOLS = [read_file_tool, write_file_tool, edit_file_tool, delete_file_tool]


# Funções getter para o registry
def get_read_file_tool():
    return read_file_tool

def get_write_file_tool():
    return write_file_tool

def get_edit_file_tool():
    return edit_file_tool

def get_delete_file_tool():
    return delete_file_tool
