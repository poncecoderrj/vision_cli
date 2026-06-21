# Backward-compat re-export. Logic lives in src/ui/.
from src.ui import (
    CORAL, GREEN, CYAN, GOLD, MUTED, DIMC, console,
    AgentMode, get_mode, cycle_mode, track_tool_call,
    print_header, print_user_message, print_agent_message,
    print_tool_result, print_system_message, print_error, print_session_stats,
    set_current_capture, prompt_command_approval, prompt_simple_approval, prompt_plan_approval,
    prompt_ask_user, prompt_ask_text, run_skill_wizard,
    get_user_input,
    AgentStream,
)
