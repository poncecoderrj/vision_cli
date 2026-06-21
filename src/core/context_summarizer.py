from typing import List, Dict, Any
import json

def generate_session_summary(messages: List[Dict[str, str]]) -> str:
    """
    Gera um resumo inteligente da sessão baseado nas mensagens.
    Identifica tarefas principais, arquivos trabalhados e decisões importantes.
    """
    if not messages:
        return "Sessão vazia"
    
    # Análise simples baseada em padrões de texto
    tasks = []
    files_mentioned = set()
    decisions = []
    
    for msg in messages[-20:]:  # Analisa últimas 20 mensagens
        content = msg.get("content", "")
        role = msg.get("role", "")
        
        # Detecta tarefas (comandos do usuário)
        if role == "user":
            if any(kw in content.lower() for kw in ["crie", "criar", "faça", "fazer", "execute", "roda", "inicie"]):
                tasks.append(content[:100])
        
        # Detecta arquivos mencionados
        import re
        file_patterns = [
            r'[\w\-\.]+\.(py|js|ts|jsx|tsx|html|css|json|md|txt|bat|sh)',
            r'[\/\\][\w\-\.]+[\/\\][\w\-\.]+'
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            files_mentioned.update(matches)
        
        # Detecta decisões importantes
        if role == "assistant":
            if any(kw in content.lower() for kw in ["decidi", "escolhi", "optei", "concluí", "finalizado"]):
                decisions.append(content[:100])
    
    # Constrói resumo
    summary_parts = []
    
    if tasks:
        summary_parts.append(f"Tarefas principais: {len(tasks)} solicitações")
    
    if files_mentioned:
        files_list = ", ".join(list(files_mentioned)[:5])
        summary_parts.append(f"Arquivos: {files_list}")
    
    if decisions:
        summary_parts.append(f"Decisões: {len(decisions)} ações concluídas")
    
    if not summary_parts:
        return f"Sessão com {len(messages)} mensagens"
    
    return " | ".join(summary_parts)


def format_context_for_prompt(cwd: str, recent_files: List[str] = None, session_summary: str = "") -> str:
    """Formata o contexto para ser injetado no prompt do sistema."""
    
    context = f"""
## CONTEXTO ATUAL
- **Diretório de Trabalho**: {cwd}
- **Sistema Operacional**: Windows (use comandos PowerShell/CMD)
"""
    
    if session_summary:
        context += f"- **Resumo da Sessão**: {session_summary}\n"
    
    if recent_files and len(recent_files) > 0:
        context += f"- **Arquivos Recentes**: {', '.join(recent_files[:5])}\n"
    
    context += """
## REGRAS DE LOCALIZAÇÃO
1. Sempre verifique o diretório atual antes de executar comandos que criam/modificam arquivos
2. Use caminhos absolutos ou relativos ao cwd explicitamente
3. Se o usuário pedir para 'achar' algo, use a ferramenta de busca antes de agir
4. Ao criar projetos, confirme o local de criação com o usuário se houver ambiguidade
"""
    
    return context
