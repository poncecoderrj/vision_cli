"""
InteractionLogger: grava turnos e métricas em JSONL para análise posterior.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Optional


class InteractionLogger:
    def __init__(self, log_dir: str = "logs", max_size_mb: int = 10, keep_files: int = 3):
        self.log_dir = log_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.keep_files = keep_files
        os.makedirs(log_dir, exist_ok=True)
        self.session_file = os.path.join(
            log_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        self.stats_file = os.path.join(log_dir, "stats.jsonl")

    def _rotate_if_needed(self, filepath: str) -> None:
        """Rotaciona o arquivo quando ultrapassa max_size_bytes, mantendo keep_files cópias."""
        if not os.path.exists(filepath):
            return
        if os.path.getsize(filepath) <= self.max_size_bytes:
            return
        base, ext = os.path.splitext(filepath)
        for i in range(self.keep_files - 1, 0, -1):
            src = f"{base}.{i}{ext}"
            dst = f"{base}.{i + 1}{ext}"
            if os.path.exists(src):
                shutil.move(src, dst)
        shutil.move(filepath, f"{base}.1{ext}")
        open(filepath, "w").close()

    def log_turn(self, turn_data: Dict[str, Any]) -> None:
        """Grava um turno completo (user → assistant → tool result)."""
        turn_data = dict(turn_data)
        turn_data["timestamp"] = datetime.now().isoformat()
        try:
            self._rotate_if_needed(self.session_file)
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
            self._rotate_if_needed(self.stats_file)
            with open(self.stats_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


__all__ = ["InteractionLogger"]
