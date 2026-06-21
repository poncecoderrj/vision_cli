"""
MetricsAnalyzer: lê os logs JSONL e gera relatórios e sugestões de melhoria.
"""

import json
import os
from collections import defaultdict
from typing import Dict


class MetricsAnalyzer:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir

    def analyze_stats(self) -> Dict:
        stats_file = os.path.join(self.log_dir, "stats.jsonl")
        if not os.path.exists(stats_file):
            return {"erro": "Arquivo de estatísticas não encontrado. Execute algumas sessões primeiro."}

        metrics = defaultdict(list)
        with open(stats_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    metric = entry.get("metric")
                    if metric:
                        metrics[metric].append(entry.get("value"))
                except Exception:
                    continue

        report: Dict = {}

        if "tool_validation_error" in metrics:
            report["erros_validacao"] = len(metrics["tool_validation_error"])

        if "tool_repaired" in metrics:
            values = metrics["tool_repaired"]
            success = sum(1 for v in values if v is True)
            total = len(values)
            pct = f"{success / total * 100:.1f}%" if total else "0%"
            report["taxa_reparo"] = f"{success}/{total} ({pct})"

        if "fallback_triggered" in metrics:
            values = metrics["fallback_triggered"]
            success = sum(1 for v in values if v is True)
            total = len(values)
            pct = f"{success / total * 100:.1f}%" if total else "0%"
            report["taxa_fallback"] = f"{success}/{total} ({pct})"

        # Ferramentas mais usadas — lê últimos 5 arquivos de sessão
        tool_usage: Dict[str, int] = defaultdict(int)
        try:
            session_files = sorted(
                [f for f in os.listdir(self.log_dir) if f.startswith("session_") and f.endswith(".jsonl")],
                reverse=True,
            )[:5]
            for sf in session_files:
                with open(os.path.join(self.log_dir, sf), "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            tc = data.get("tool_call", {})
                            if tc and tc.get("name"):
                                tool_usage[tc["name"]] += 1
                        except Exception:
                            continue
        except Exception:
            pass

        if tool_usage:
            report["ferramentas_mais_usadas"] = dict(
                sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            )

        return report

    def generate_prompt_boost(self) -> str:
        """Sugestões para melhorar o system prompt com base nos logs."""
        report = self.analyze_stats()
        if "erro" in report:
            return report["erro"]

        suggestions = []

        taxa_fallback = report.get("taxa_fallback", "")
        if taxa_fallback:
            try:
                pct = float(taxa_fallback.split("(")[1].rstrip("%)"))
                if pct > 30:
                    suggestions.append(
                        "- Alto uso de fallback (>30%). Adicione exemplos de tool calls no system prompt."
                    )
            except Exception:
                pass

        taxa_reparo = report.get("taxa_reparo", "")
        if taxa_reparo:
            try:
                pct = float(taxa_reparo.split("(")[1].rstrip("%)"))
                if pct < 50:
                    suggestions.append(
                        "- Baixa taxa de reparo (<50%). Considere usar um modelo maior ou ampliar a heurística."
                    )
            except Exception:
                pass

        erros = report.get("erros_validacao", 0)
        if erros > 10:
            suggestions.append(
                f"- {erros} erros de validação encontrados. Verifique se o modelo está gerando tool calls corretas."
            )

        if not suggestions:
            suggestions.append("- Sistema estável. Continue monitorando.")

        return "\n".join(suggestions)


__all__ = ["MetricsAnalyzer"]
