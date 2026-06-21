"""
Public UI API — re-exported for agent.py and ui.py compatibility.
"""

from .theme import CORAL, GREEN, CYAN, GOLD, MUTED, DIMC, console, PT_STYLE
from .modes import AgentMode, get_mode, cycle_mode, track_tool_call, _stats
from .output import (
    print_header, print_user_message, print_agent_message,
    print_tool_result, print_system_message, print_error, print_session_stats,
)
from .approvals import (
    set_current_capture,
    prompt_command_approval,
    prompt_simple_approval,
    prompt_plan_approval,
)
from .wizard import prompt_ask_user, prompt_ask_text, run_skill_wizard
from .input_box import get_user_input
from .stream_display import AgentStream

__all__ = [
    # theme
    "CORAL", "GREEN", "CYAN", "GOLD", "MUTED", "DIMC", "console",
    # modes
    "AgentMode", "get_mode", "cycle_mode", "track_tool_call",
    # output
    "print_header", "print_user_message", "print_agent_message",
    "print_tool_result", "print_system_message", "print_error", "print_session_stats",
    # approvals
    "set_current_capture", "prompt_command_approval",
    "prompt_simple_approval", "prompt_plan_approval",
    # wizard
    "prompt_ask_user", "prompt_ask_text", "run_skill_wizard",
    # input
    "get_user_input",
    # stream
    "AgentStream",
]
