"""
Color constants, prompt_toolkit style, and shared Rich console.
"""

from rich.console import Console
from prompt_toolkit.styles import Style as PTStyle

CORAL = "#d97757"
GREEN = "#7fae5f"
CYAN  = "#56b6c2"
GOLD  = "#e5c07b"
MUTED = "#9a9a9a"
DIMC  = "grey42"

console = Console(safe_box=False)

PT_STYLE = PTStyle.from_dict({
    "box":         CORAL,
    "prompt":      f"{CORAL} bold",
    "input":       "",
    "placeholder": "#6b6b6b",
    "hint":        "#6b6b6b",
    "tokens":      "#6b6b6b",
    "tokens.hi":   "#9a9a9a",
    "mode.accept": f"{CYAN} bold",
    "mode.plan":   f"{GOLD} bold",
    "mode.auto":   f"{GREEN} bold",
    "completion-menu":                     "bg:#2a2a2a #cccccc",
    "completion-menu.completion":          "bg:#2a2a2a #cccccc",
    "completion-menu.completion.current":  f"bg:{CORAL} #ffffff bold",
    "completion-menu.meta.completion":     "bg:#333333 #888888",
    "completion-menu.meta.completion.current": f"bg:{CORAL} #dddddd",
    "scrollbar.background":                "bg:#3a3a3a",
    "scrollbar.button":                    f"bg:{CORAL}",
})

__all__ = ["CORAL", "GREEN", "CYAN", "GOLD", "MUTED", "DIMC", "console", "PT_STYLE"]
