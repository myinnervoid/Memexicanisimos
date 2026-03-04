"""
title: Memex Memory Governance
author: Memexicanisimos Team
version: 1.0.0
description: |
  Herramientas de gobernanza de memoria: ejecutar ciclo de limpieza,
  reportar salud del sistema, y mostrar entropy.
  Usa WAL mode y transacciones atómicas para seguridad.
requirements: pydantic
"""

import json
from typing import Callable, Any
from pydantic import BaseModel


class Tools:
    class Valves(BaseModel):
        db_path: str = "/app/backend/data/memex_memory.db"

    def __init__(self):
        self.valves = self.Valves()

    async def gc_memories(
        self,
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Ejecuta un ciclo completo de gobernanza de memoria:
        recalcula scores, archiva memorias irrelevantes, y compacta si hay exceso de entropy.
        Usa este comando cuando el usuario diga "limpia las memorias" o "ejecuta gobernanza".
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🧹 Ejecutando ciclo de gobernanza...", "done": False}
            })

        try:
            from memory_governor import MemoryGovernor
            gov = MemoryGovernor(self.valves.db_path)
            gov.migrate_schema()
            result = gov.run_cycle()

            report = (
                f"## 🧹 Gobernanza Completada\n\n"
                f"- **Memorias evaluadas:** {result['memories_scored']}\n"
                f"- **Memorias archivadas:** {result['memories_archived']}\n"
                f"- **Entropy:** {result['entropy'] if result['entropy'] is not None else 'N/A (<50 memorias)'}\n"
                f"- **Compactación:** {'Sí' if result['compacted'] else 'No'}\n"
                f"- **Duración:** {result['duration_seconds']}s\n"
            )

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "✅ Gobernanza completada", "done": True}
                })

            return report

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ Error: {e}", "done": True}
                })
            return f"❌ Error en gobernanza: {e}"

    async def memory_health_report(
        self,
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Genera un reporte detallado de salud de la memoria: distribución por tipo,
        scores promedio, riesgo de archivo, y estado de entropy.
        Usa este comando cuando el usuario diga "reporte de memoria" o "salud del sistema".
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "📊 Analizando salud de memoria...", "done": False}
            })

        try:
            from memory_governor import MemoryGovernor
            gov = MemoryGovernor(self.valves.db_path)
            gov.migrate_schema()
            report = gov.health_report()

            lines = [
                "## 📊 Reporte de Salud de Memoria\n",
                f"- **Total activas:** {report['total_active']}",
                f"- **Archivadas:** {report['total_archived']}",
                f"- **En riesgo (score bajo):** {report['low_scored_at_risk']}",
                f"- **Entropy:** {report['entropy'] if report['entropy'] is not None else 'N/A'}",
                f"- **Estado:** {report['entropy_status']}\n",
                "### Distribución por Tipo\n",
                "| Tipo | Cantidad | Score Promedio | Accesos Promedio |",
                "|------|----------|---------------|------------------|",
            ]

            for t in report["types"]:
                lines.append(
                    f"| {t['type']} | {t['count']} | {t['avg_score']} | {t['avg_access']} |"
                )

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "✅ Reporte generado", "done": True}
                })

            return "\n".join(lines)

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ Error: {e}", "done": True}
                })
            return f"❌ Error en reporte: {e}"
