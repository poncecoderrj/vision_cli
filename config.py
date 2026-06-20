import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path.home() / ".my_agent_cli"
CONFIG_DIR.mkdir(exist_ok=True)
WHITELIST_FILE = CONFIG_DIR / "command_whitelist.json"

def load_whitelist() -> list[str]:
    if WHITELIST_FILE.exists():
        try:
            with open(WHITELIST_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def add_to_whitelist(command: str):
    whitelist = load_whitelist()
    if command not in whitelist:
        whitelist.append(command)
        with open(WHITELIST_FILE, "w") as f:
            json.dump(whitelist, f, indent=4)

def is_whitelisted(command: str) -> bool:
    return command in load_whitelist()
