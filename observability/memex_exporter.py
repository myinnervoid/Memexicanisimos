"""
Memex Prometheus Exporter v1.0
Expone métricas agregadas de Memexicanisimos OS en :9091/metrics

IMPORTANTE: request_id NO se usa como label en métricas.
Trazabilidad completa vía memex_traces.jsonl.
"""

import os
import sqlite3
import json
import time
import glob
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


MEMEX_DB_PATH = os.environ.get("MEMEX_DB_PATH", "/data/memex_memory.db")
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/data/workspace")
TELEMETRY_PATH = os.path.join(WORKSPACE_PATH, "memex_telemetry.jsonl")
GOVERNANCE_LOG = os.path.join(WORKSPACE_PATH, "governance_log.jsonl")
PORT = 9091


class MetricsCollector:
    """Recolecta métricas de los archivos internos de Memex."""

    def collect_memory_metrics(self):
        """Métricas de memoria desde SQLite."""
        metrics = {}
        if not os.path.exists(MEMEX_DB_PATH):
            return metrics
        try:
            conn = sqlite3.connect(MEMEX_DB_PATH, timeout=5)
            conn.row_factory = sqlite3.Row

            # Total memorias por tipo
            rows = conn.execute(
                "SELECT type, COUNT(*) as cnt FROM memories GROUP BY type"
            ).fetchall()
            for r in rows:
                metrics[f'memex_memory_count{{type="{r["type"]}"}}'] = r["cnt"]

            # Total general
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            metrics["memex_memory_total"] = total

            # Archived
            try:
                archived = conn.execute(
                    "SELECT COUNT(*) FROM memory_archive"
                ).fetchone()[0]
                metrics["memex_memory_archived_total"] = archived
            except sqlite3.OperationalError:
                pass

            # Score promedio
            try:
                avg_score = conn.execute(
                    "SELECT AVG(importance_score) FROM memories"
                ).fetchone()[0]
                metrics["memex_memory_avg_importance_score"] = round(avg_score or 0, 4)
            except sqlite3.OperationalError:
                pass

            conn.close()
        except Exception:
            pass
        return metrics

    def collect_telemetry_metrics(self):
        """Métricas de router desde telemetría JSONL (últimas 1000 líneas)."""
        metrics = {
            "memex_router_requests_total": 0,
            "memex_router_misprediction_total": 0,
        }
        model_tokens = {}
        tier_counts = {}
        confidence_sum = 0.0

        if not os.path.exists(TELEMETRY_PATH):
            return metrics

        try:
            with open(TELEMETRY_PATH, "r") as f:
                lines = f.readlines()[-1000:]

            for line in lines:
                try:
                    entry = json.loads(line.strip())
                except (json.JSONDecodeError, ValueError):
                    continue

                metrics["memex_router_requests_total"] += 1

                model = entry.get("model", "unknown")
                tokens = entry.get("actual_tokens", entry.get("predicted_cost", 0))
                model_tokens[model] = model_tokens.get(model, 0) + int(tokens or 0)

                tier = entry.get("tier_selected", entry.get("tier", "unknown"))
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

                if entry.get("mispredicted", False):
                    metrics["memex_router_misprediction_total"] += 1

                confidence_sum += float(entry.get("confidence_score", 0.5))

            # Tokens por modelo
            for model, total in model_tokens.items():
                safe = model.replace('"', '\\"')
                metrics[f'memex_tokens_total{{model="{safe}"}}'] = total

            # Requests por tier
            for tier, cnt in tier_counts.items():
                metrics[f'memex_router_tier_requests{{tier="{tier}"}}'] = cnt

            # Confidence promedio
            n = metrics["memex_router_requests_total"]
            if n > 0:
                metrics["memex_router_avg_confidence"] = round(confidence_sum / n, 4)
                metrics["memex_router_misprediction_rate"] = round(
                    metrics["memex_router_misprediction_total"] / n, 4
                )

        except Exception:
            pass
        return metrics

    def collect_governance_metrics(self):
        """Métricas del último ciclo de governance."""
        metrics = {}
        if not os.path.exists(GOVERNANCE_LOG):
            return metrics
        try:
            with open(GOVERNANCE_LOG, "r") as f:
                lines = f.readlines()
            # Último ciclo exitoso
            for line in reversed(lines):
                try:
                    entry = json.loads(line.strip())
                except (json.JSONDecodeError, ValueError):
                    continue
                if entry.get("action") == "governance_cycle" and "error" not in entry:
                    metrics["memex_governance_cycle_duration_seconds"] = entry.get("duration_seconds", 0)
                    metrics["memex_governance_purge_total"] = entry.get("memories_archived", 0)
                    metrics["memex_governance_memories_scored"] = entry.get("memories_scored", 0)
                    entropy = entry.get("entropy")
                    if entropy is not None:
                        metrics["memex_memory_entropy_score"] = round(entropy, 4)
                    break
        except Exception:
            pass
        return metrics

    def collect_all(self):
        """Combina todas las métricas."""
        all_metrics = {}
        all_metrics.update(self.collect_memory_metrics())
        all_metrics.update(self.collect_telemetry_metrics())
        all_metrics.update(self.collect_governance_metrics())
        return all_metrics


def format_prometheus(metrics: dict) -> str:
    """Formatea métricas en Prometheus exposition format."""
    lines = [
        "# HELP memex_memory_total Total active memories",
        "# TYPE memex_memory_total gauge",
        "# HELP memex_memory_count Memories by type",
        "# TYPE memex_memory_count gauge",
        "# HELP memex_tokens_total Tokens consumed by model",
        "# TYPE memex_tokens_total counter",
        "# HELP memex_router_requests_total Total router requests",
        "# TYPE memex_router_requests_total counter",
        "# HELP memex_router_misprediction_rate Router misprediction ratio",
        "# TYPE memex_router_misprediction_rate gauge",
        "# HELP memex_governance_cycle_duration_seconds Last governance cycle duration",
        "# TYPE memex_governance_cycle_duration_seconds gauge",
        "# HELP memex_memory_entropy_score Memory type distribution entropy",
        "# TYPE memex_memory_entropy_score gauge",
        "",
    ]
    for key, value in sorted(metrics.items()):
        lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"


collector = MetricsCollector()


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            metrics = collector.collect_all()
            body = format_prometheus(metrics).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silenciar logs de request


if __name__ == "__main__":
    print(f"🔭 Memex Exporter listening on :{PORT}/metrics")
    server = HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    server.serve_forever()
