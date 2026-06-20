import os
import re
import json
from datetime import datetime
from pathlib import Path

_VISIONS_DIR = ".visions"
_CURRENT_FILE = "session_current.json"


def _visions_dir() -> Path:
    d = Path(os.getcwd()) / _VISIONS_DIR
    d.mkdir(exist_ok=True)
    return d


def _clean(messages: list) -> list:
    """Strip internal keys (starting with '_') before persisting."""
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in messages]


def save_current_session(messages: list, model: str, base_url: str) -> None:
    """Auto-save after each completed turn. Silent on any error."""
    try:
        clean = _clean(messages)
        turns = sum(1 for m in clean if m.get("role") == "user")
        data = {
            "version": 1,
            "model": model,
            "base_url": base_url,
            "saved_at": datetime.now().isoformat(),
            "cwd": os.getcwd(),
            "turns": turns,
            "messages": clean,
        }
        (_visions_dir() / _CURRENT_FILE).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def save_named_session(messages: list, name: str, model: str, base_url: str) -> str:
    """Save a named snapshot to .visions/<name>.json. Returns path or error string."""
    try:
        safe = re.sub(r"[^\w\-]", "-", name)[:64]
        clean = _clean(messages)
        turns = sum(1 for m in clean if m.get("role") == "user")
        data = {
            "version": 1,
            "model": model,
            "base_url": base_url,
            "saved_at": datetime.now().isoformat(),
            "cwd": os.getcwd(),
            "turns": turns,
            "messages": clean,
        }
        path = _visions_dir() / f"{safe}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
    except Exception as e:
        return f"Erro ao salvar: {e}"


def load_session(name: str = "") -> "dict | None":
    """Load session_current (name='') or .visions/<name>.json. Returns dict or None."""
    try:
        vd = Path(os.getcwd()) / _VISIONS_DIR
        fname = _CURRENT_FILE if not name else f"{name}.json"
        f = vd / fname
        if not f.exists():
            return None
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_sessions() -> list:
    """Return metadata for all sessions, sorted by saved_at descending."""
    try:
        vd = Path(os.getcwd()) / _VISIONS_DIR
        if not vd.exists():
            return []
        results = []
        for f in vd.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append({
                    "name": f.stem,
                    "turns": data.get("turns", "?"),
                    "saved_at": data.get("saved_at", ""),
                    "model": data.get("model", "?"),
                })
            except Exception:
                continue
        results.sort(key=lambda x: x["saved_at"], reverse=True)
        return results
    except Exception:
        return []


def has_current_session() -> bool:
    """True if .visions/session_current.json exists with at least 1 user turn."""
    try:
        f = Path(os.getcwd()) / _VISIONS_DIR / _CURRENT_FILE
        if not f.exists():
            return False
        data = json.loads(f.read_text(encoding="utf-8"))
        return data.get("turns", 0) > 0
    except Exception:
        return False
