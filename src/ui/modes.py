"""
Agent mode state (ACCEPT / PLAN / AUTO) and session token stats.
"""

import time
from enum import Enum

from .theme import CYAN, GOLD, GREEN


class AgentMode(Enum):
    ACCEPT = "accept"
    PLAN   = "plan"
    AUTO   = "auto"


_state = {"mode": AgentMode.ACCEPT}

MODE_DISPLAY = {
    AgentMode.ACCEPT: ("class:mode.accept", "modo aprovação"),
    AgentMode.PLAN:   ("class:mode.plan",   "modo plano"),
    AgentMode.AUTO:   ("class:mode.auto",   "modo automático"),
}


def get_mode() -> AgentMode:
    return _state["mode"]


def cycle_mode() -> AgentMode:
    modes = list(AgentMode)
    _state["mode"] = modes[(modes.index(_state["mode"]) + 1) % len(modes)]
    return _state["mode"]


# Session-wide token / tool stats
_stats = {"tokens_in": 0, "tokens_out": 0, "tool_calls": 0, "start": time.perf_counter()}


def track_tool_call():
    _stats["tool_calls"] += 1


__all__ = ["AgentMode", "get_mode", "cycle_mode", "MODE_DISPLAY", "_stats", "track_tool_call"]
