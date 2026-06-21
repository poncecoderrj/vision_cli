"""
InteractionLogger: grava turnos e métricas em JSONL para análise posterior.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class InteractionLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.session_file = os.path.join(
            log_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        self.stats_file = os.path.join(log_dir, "stats.jsonl")

    def log_turn(self, turn_data: Dict[str, Any]) -> None:
        """Grava um turno completo (user → assistant → tool result)."""
        turn_data = dict(turn_data)
        turn_data["timestamp"] = datetime.now().isoformat()
        try:
            with open(self.session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(turn_data, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def log_metric(self, metric: str, value: Any, context: Optional[Dict] = None) -> None:
        """Grava uma métrica pontual (ex: tool_repaired, fallback_triggered)."""
        entry = {
            "metric": metric,
            "value": value,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }
        try:
            with open(self.stats_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


__all__ = ["InteractionLogger"]
