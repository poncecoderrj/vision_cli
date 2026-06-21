"""
Command whitelist configuration — persisted to ~/.my_agent_cli/command_whitelist.json
"""

import fnmatch
import json
from pathlib import Path

CONFIG_DIR    = Path.home() / ".my_agent_cli"
CONFIG_DIR.mkdir(exist_ok=True)
WHITELIST_FILE = CONFIG_DIR / "command_whitelist.json"


def load_whitelist() -> list[str]:
    if WHITELIST_FILE.exists():
        try:
            return json.loads(WHITELIST_FILE.read_text())
        except Exception:
            return []
    return []


def add_to_whitelist(command: str):
    whitelist = load_whitelist()
    if command not in whitelist:
        whitelist.append(command)
        WHITELIST_FILE.write_text(json.dumps(whitelist, indent=4))


def is_whitelisted(command: str) -> bool:
    return any(fnmatch.fnmatch(command, pattern) for pattern in load_whitelist())


__all__ = ["load_whitelist", "add_to_whitelist", "is_whitelisted"]
