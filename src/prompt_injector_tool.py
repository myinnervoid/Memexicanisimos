"""
title: Memex Prompt Injector & Architect
author: Memexicanisimos Team
version: 1.0.0
description: |
  Herramienta que asiste al usuario en la creación de System Prompts optimizados
  para nuevos agentes, integrando automáticamente el uso de memoria FTS5 y Workspace.
  Usa __event_emitter__ para reportar progreso en tiempo real en la UI de Open WebUI.
requirements: pydantic
"""

from pydantic import BaseModel, Field
from typing import Callable, Any, Optional
import asyncio


class Tools:
    class Valves(BaseModel):
        default_memory_instructions: str = Field(
            default=(
                "- Usa `search_memory` antes de responder para recuperar contexto relevante.\n"
                "- Usa `save_memory` cuando aprendas una regla, preferencia o hecho nuevo del usuario.\n"
                "- Usa `search_lessons` al inicio de cada sesión para no repetir errores."
            ),
            description="Instrucciones base de memoria inyectadas en todos los prompts generados."
        )
        workspace_instructions: str = Field(
            default=(
                "- Usa `analyze_code(file, tool)` para ejecutar linters (pylint, flake8, mypy, bandit).\n"
                "- Usa `generate_tests(file)` para crear pruebas unitarias automáticas.\n"
                "- Usa `create_task(title, desc, priority)` para organizar trabajo en TODO.md.\n"
                "- Usa `git_status()` y `git_commit(msg)` para gestión de versiones."
            ),
            description="Instrucciones de workspace para agentes que trabajan con archivos."
        )

    def __init__(self):
        self.valves = self.Valves()

    async def generate_memex_prompt(
        self,
        role_description: str,
        include_workspace: bool = False,
        include_orchestration: bool = True,
        language: str = "español",
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Genera un System Prompt maestro para un nuevo Agente/Sabor de Memexicanisimos.
        Úsalo cuando el usuario te pida crear un nuevo agente, bot, o "prompt para X".

        :param role_description: Descripción del rol del agente (ej. "Revisor de código Python experto en seguridad").
        :param include_workspace: True si el agente necesitará leer/analizar archivos locales.
        :param include_orchestration: True si el agente puede usar subagentes y comandos.
        :param language: Idioma del prompt generado.
        """

        # 1. Señalizar inicio del proceso
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🧠 Diseñando la arquitectura del System Prompt...", "done": False}
            })
            await asyncio.sleep(0.5)

        # 2. Construir el Prompt Base
        prompt_lines = []
        prompt_lines.append(f"Eres un experto especializado como: **{role_description.upper()}**.")
        prompt_lines.append("")
        prompt_lines.append("### TU MISIÓN PRINCIPAL")
        prompt_lines.append(
            "Actúa de manera autónoma, piensa paso a paso, y asegúrate de cumplir "
            "con los más altos estándares de tu especialidad. Responde siempre de forma "
            f"directa y en {language}."
        )
        prompt_lines.append("")

        # 3. Señalizar progreso
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "🔧 Inyectando módulos de herramientas cognitivas...", "done": False}
            })
            await asyncio.sleep(0.5)

        # 4. Bloque de Memoria (siempre incluido)
        prompt_lines.append("### USO DE HERRAMIENTAS Y MEMORIA (CRÍTICO)")
        prompt_lines.append("Tienes acceso a herramientas cognitivas persistentes. Debes usarlas proactivamente:")
        prompt_lines.append(self.valves.default_memory_instructions)
        prompt_lines.append("")

        # 5. Bloque de Workspace (opcional)
        if include_workspace:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "📂 Añadiendo capacidades de análisis de código...", "done": False}
                })
                await asyncio.sleep(0.3)

            prompt_lines.append("### HERRAMIENTAS DE WORKSPACE Y CÓDIGO")
            prompt_lines.append("Tienes acceso a herramientas de desarrollo local:")
            prompt_lines.append(self.valves.workspace_instructions)
            prompt_lines.append("")

        # 6. Bloque de Orquestación (opcional)
        if include_orchestration:
            prompt_lines.append("### ORQUESTACIÓN DE AGENTES")
            prompt_lines.append(
                "- Usa `run_subagent(task, model)` para delegar subtareas complejas a un contexto limpio.\n"
                "- Usa `run_command(cmd)` para ejecutar comandos del sistema (lista blanca: pytest, git, linters).\n"
                "- Usa `write_plan(content, title)` para documentar planes antes de ejecutar tareas grandes.\n"
                "- Usa `add_lesson(lesson, context)` cuando el usuario te corrija, para no repetir errores."
            )
            prompt_lines.append("")

        # 7. Bloque de Formato
        prompt_lines.append("### FORMATO DE RESPUESTA")
        prompt_lines.append(
            "- Sé conciso y directo.\n"
            "- Si haces un cambio, explica brevemente el 'por qué'.\n"
            "- Si guardas algo en memoria, avísale al usuario que lo has recordado.\n"
            "- No incluyas etiquetas <think> ni razonamiento interno en tu respuesta final."
        )

        # 8. Compilar prompt final
        full_prompt = "\n".join(prompt_lines)

        # 9. Señalizar finalización
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "✅ System Prompt generado con éxito.", "done": True}
            })

        # 10. Devolver con instrucciones para el usuario
        return (
            f"Aquí tienes el System Prompt optimizado para tu agente **{role_description}**. "
            f"Cópialo y pégalo al crear un nuevo modelo en Open WebUI "
            f"(Workspace → Models → Create a Model → System Prompt):\n\n"
            f"```\n{full_prompt}\n```\n\n"
            f"*Asegúrate de habilitar las herramientas 'Memex Tools' y 'Memex Prompt Injector' "
            f"cuando crees el modelo.*"
        )

    async def list_available_tools(
        self,
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Lista todas las herramientas disponibles en Memex con descripción breve.
        Útil para que el usuario sepa qué capacidades tiene el ecosistema.
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "📋 Recopilando catálogo de herramientas...", "done": False}
            })

        tools_catalog = [
            ("save_memory", "Guarda un hecho, plan o lección en la memoria persistente FTS5."),
            ("search_memory", "Busca memorias por palabras clave con relevancia semántica."),
            ("get_memory_by_id", "Recupera una memoria completa por su ID."),
            ("list_recent_memories", "Lista memorias recientes, filtrable por tipo."),
            ("delete_memory", "Elimina una memoria permanentemente."),
            ("memory_stats", "Muestra estadísticas de uso de la memoria."),
            ("export_memories", "Exporta memorias a un archivo JSON en el workspace."),
            ("import_memories", "Importa memorias desde un archivo JSON."),
            ("write_plan", "Guarda un plan estructurado como memoria tipo 'plan'."),
            ("add_lesson", "Registra una lección aprendida para no repetir errores."),
            ("search_lessons", "Busca lecciones relevantes."),
            ("run_subagent", "Ejecuta una subtarea en un contexto limpio vía Ollama."),
            ("run_command", "Ejecuta un comando del sistema (lista blanca)."),
            ("analyze_code", "Ejecuta linters (pylint, flake8, mypy, bandit) sobre archivos."),
            ("generate_tests", "Genera pruebas unitarias vía subagente."),
            ("generate_docstring", "Genera docstrings para funciones o archivos completos."),
            ("create_task", "Crea una tarea en TODO.md del workspace."),
            ("list_tasks", "Lista tareas pendientes o completadas."),
            ("git_status", "Muestra el estado de git en el workspace."),
            ("git_commit", "Hace git add + commit con un mensaje."),
            ("fetch_url", "Obtiene contenido de una URL (HTTP/HTTPS)."),
            ("summarize_text", "Resume textos largos vía subagente."),
            ("open_in_editor", "Abre un archivo en el editor del sistema."),
            ("generate_memex_prompt", "Genera System Prompts optimizados para nuevos agentes."),
        ]

        lines = ["| Herramienta | Descripción |", "|---|---|"]
        for name, desc in tools_catalog:
            lines.append(f"| `{name}` | {desc} |")

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "✅ Catálogo listo.", "done": True}
            })

        return f"### 🧰 Catálogo de Herramientas Memex ({len(tools_catalog)} disponibles)\n\n" + "\n".join(lines)
