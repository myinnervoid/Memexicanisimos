"""
title: Memex LLM-as-Judge (Skill)
author: Memexicanisimos Team
version: 1.0.0
description: |
  Skill de evaluación. Permite al agente principal usar un modelo secundario 
  para evaluar, auditar o puntuar un fragmento de código o texto según criterios.
requirements: pydantic, requests
"""

import requests
from pydantic import BaseModel, Field
from typing import Callable, Any

class Tools:
    class Valves(BaseModel):
        ollama_url: str = Field(
            default="http://ollama:11434", description="URL interna del motor Ollama."
        )
        judge_model: str = Field(
            default="qwen2.5:7b", description="El modelo que actuará como juez."
        )

    def __init__(self):
        self.valves = self.Valves()

    async def evaluate_output(self, subject_to_evaluate: str, criteria: str, __event_emitter__: Callable[[dict], Any] = None) -> str:
        """
        Actúa como un LLM-as-Judge. Usa esta herramienta para autoevaluar tu propio código
        o evaluar un texto externo en base a criterios estrictos.
        
        :param subject_to_evaluate: El código, texto o plan que necesita ser calificado.
        :param criteria: Criterios de evaluación (ej. "Seguridad, Rendimiento, Legibilidad").
        """
        
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "⚖️ Invocando al Juez Cognitivo...", "done": False}
            })

        prompt = (
            f"Eres un Juez Evaluador Imparcial.\n"
            f"Evalúa el siguiente contenido basándote ESTRICTAMENTE en estos criterios: {criteria}.\n"
            f"Asigna una puntuación del 1 al 10 y da un feedback conciso.\n\n"
            f"CONTENIDO A EVALUAR:\n{subject_to_evaluate}"
        )

        schema = {
            "type": "object",
            "properties": {
                "aprobado": {"type": "boolean"},
                "puntuacion": {"type": "integer"},
                "feedback": {"type": "string"},
                "errores": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["aprobado", "puntuacion", "feedback", "errores"]
        }

        payload = {
            "model": self.valves.judge_model,
            "prompt": prompt,
            "stream": False,
            "format": schema
        }

        try:
            import json
            response = requests.post(f"{self.valves.ollama_url}/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            
            # El motor asegura 100% JSON estricto
            raw_response = response.json().get("response", "{}")
            
            try:
                evaluation_data = json.loads(raw_response)
                
                html_response = (
                    f"### ⚖️ Resultado de la Evaluación (Juez: {self.valves.judge_model})\n\n"
                    f"**Puntuación:** {evaluation_data.get('puntuacion', '?')}/10 | "
                    f"**Decisión:** {'✅ Aprobado' if evaluation_data.get('aprobado') else '❌ Rechazado'}\n\n"
                    f"**Feedback:**\n{evaluation_data.get('feedback', 'Sin feedback')}\n\n"
                )
                
                if evaluation_data.get("errores"):
                    html_response += "**Errores Detectados:**\n"
                    for error in evaluation_data.get("errores"):
                        html_response += f"- {error}\n"
                        
                result_text = html_response
                
            except json.JSONDecodeError:
                result_text = f"### ⚖️ Resultado de la Evaluación\nError de parseo del JSON del Juez:\n{raw_response}"
            
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "✅ Evaluación completada.", "done": True}
                })
                
            return result_text
            
        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": "❌ Error al invocar al juez.", "done": True}
                })
            return f"Error en el sistema de evaluación: {str(e)}"
