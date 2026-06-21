import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

SESSIONS_DIR = Path.home() / ".vision_cli" / "sessions"

class SessionManager:
    def __init__(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, session_id: str) -> Path:
        return SESSIONS_DIR / f"{session_id}.json"

    def create_session(self, session_id: str, initial_cwd: str) -> Dict:
        """Cria uma nova sessão vazia."""
        session_data = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "cwd": initial_cwd,
            "messages": [],
            "summary": "",
            "status": "active"
        }
        self.save_session(session_data)
        return session_data

    def load_session(self, session_id: str) -> Optional[Dict]:
        """Carrega uma sessão existente."""
        path = self.get_session_path(session_id)
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_session(self, session_data: Dict):
        """Salva o estado atual da sessão."""
        session_data["updated_at"] = datetime.now().isoformat()
        path = self.get_session_path(session_data["id"])
        
        # Garante encoding UTF-8 e indentação para legibilidade
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

    def list_sessions(self) -> List[Dict]:
        """Lista todas as sessões salvas, ordenadas por atualização."""
        sessions = []
        if not SESSIONS_DIR.exists():
            return sessions

        for file in SESSIONS_DIR.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append(data)
            except Exception:
                continue
        
        # Ordena pela mais recente primeiro
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def add_message(self, session_id: str, role: str, content: str):
        """Adiciona uma mensagem ao histórico da sessão."""
        session = self.load_session(session_id)
        if not session:
            return

        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limita o histórico direto no arquivo para não ficar gigante (mantém últimos 50 msgs)
        # O contexto completo para a IA é gerenciado pelo agent, aqui guardamos log persistente
        if len(session["messages"]) > 100:
            session["messages"] = session["messages"][-50:]
            
        self.save_session(session)

    def update_summary(self, session_id: str, summary: str):
        """Atualiza o resumo inteligente da sessão."""
        session = self.load_session(session_id)
        if session:
            session["summary"] = summary
            self.save_session(session)

    def delete_session(self, session_id: str) -> bool:
        """Deleta uma sessão."""
        path = self.get_session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def generate_session_id(self) -> str:
        """Gera um ID único para a sessão baseado no timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
