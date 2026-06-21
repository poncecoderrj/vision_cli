from typing import Any, Callable, Dict, List, Optional
import json
import re


def _rule_based_summary(messages: List[Dict[str, Any]]) -> str:
    """Sumarização por regras — extrai tool calls e erros sem usar LLM."""
    events = []
    for msg in messages:
        role = msg.get("role", "")
        content = str(msg.get("content") or "")
        tool_calls = msg.get("tool_calls", [])

        if role == "user":
            text = content[:80] + "..." if len(content) > 80 else content
            events.append(f"Usuário: {text}")
        elif role == "assistant":
            if tool_calls:
                names = [tc.get("function", {}).get("name", tc.get("name", "?")) for tc in tool_calls]
                events.append(f"Assistente usou: {', '.join(names)}")
            elif content:
                first = content.split(".")[0] if "." in content else content[:60]
                events.append(f"Assistente: {first}")
        elif role == "tool":
            lower = content.lower()
            if "erro" in lower or "error" in lower:
                m = re.search(r'(?:erro|error)[\s:]+(.+?)(?:\n|$)', content, re.I)
                snippet = m.group(1)[:80] if m else content[:60]
                events.append(f"Erro: {snippet}")
            else:
                events.append(f"Resultado: OK ({content[:40]}...)" if len(content) > 40 else f"Resultado: {content}")

    return "\n".join(events[-10:]) if events else "Sem eventos registrados."


def summarize_with_llm(
    messages: List[Dict[str, Any]],
    client: Any,
    model_name: str,
) -> str:
    """Usa o LLM para gerar um resumo conciso da conversa."""
    if not messages:
        return "Nenhuma conversa anterior."

    conversation_text = ""
    for msg in messages[-20:]:
        role = msg.get("role", "?")
        content = str(msg.get("content") or "")
        reasoning = msg.get("reasoning", "")
        if reasoning:
            content += f" [raciocínio: {reasoning[:100]}]"
        conversation_text += f"[{role}]: {content[:300]}\n"

    prompt = (
        "Você é um assistente que resume conversas de um agente de IA. "
        "Resuma os pontos principais abaixo (máx. 200 palavras), mantendo: "
        "arquivos lidos/escritos, comandos executados, decisões, erros resolvidos.\n\n"
        f"CONVERSA:\n{conversation_text}\n\nRESUMO:"
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            max_tokens=300,
        )
        text = response.choices[0].message.content or ""
        return text.strip() or "Resumo não disponível."
    except Exception:
        # Tenta resumo por regras primeiro (preserva tool calls); só usa keyword se falhar
        rule_summary = _rule_based_summary(messages)
        return rule_summary if rule_summary != "Sem eventos registrados." else generate_session_summary(messages)


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
