"""
title: Memex Context Optimizer (Skill)
author: Memexicanisimos Team
version: 1.0.0
description: |
  Mitiga el efecto 'lost-in-the-middle' y evita OOM (Out of Memory).
  Monitorea la longitud de la conversación y compacta el historial intermedio
  de forma transparente antes de enviarlo al LLM.
requirements: pydantic
"""

from pydantic import BaseModel, Field
from typing import Optional

class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=2, description="Prioridad del filtro (mayor que el Router para actuar antes)."
        )
        max_estimated_tokens: int = Field(
            default=6000, description="Límite seguro de tokens antes de activar la compresión (Contexto total es 8192)."
        )
        messages_to_keep: int = Field(
            default=6, description="Número de mensajes recientes a conservar intactos."
        )

    def __init__(self):
        self.valves = self.Valves()

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Intercepta el payload de mensajes. Si el historial es muy largo,
        comprime los mensajes intermedios para salvar RAM y mejorar la atención del LLM.
        """
        messages = body.get("messages", [])
        if len(messages) <= self.valves.messages_to_keep + 2:
            return body

        # Estimación cruda de tokens (1 palabra ~ 1.3 tokens)
        total_words = sum(len(m.get("content", "").split()) for m in messages)
        estimated_tokens = int(total_words * 1.3)

        if estimated_tokens > self.valves.max_estimated_tokens:
            print(f"[Skill: Context Optimizer] Contexto saturado ({estimated_tokens} tokens). Iniciando compresión...")
            
            # Separar el prompt del sistema (siempre debe ser el índice 0)
            system_msgs = [m for m in messages if m.get("role") == "system"]
            non_system_msgs = [m for m in messages if m.get("role") != "system"]

            if len(non_system_msgs) > self.valves.messages_to_keep:
                # Conservar los N mensajes más recientes
                recent_msgs = non_system_msgs[-self.valves.messages_to_keep:]
                
                # Los mensajes del medio se "archivan"
                archived_count = len(non_system_msgs) - self.valves.messages_to_keep
                
                # Crear un mensaje de compresión que el LLM pueda leer
                compression_notice = {
                    "role": "user",
                    "content": f"[Memex Context Skill: {archived_count} mensajes intermedios han sido archivados para liberar RAM y optimizar la ventana de contexto. El contexto reciente se mantiene a continuación.]"
                }

                # Reconstruir el body de mensajes para el LLM
                body["messages"] = system_msgs + [compression_notice] + recent_msgs
                print(f"[Skill: Context Optimizer] Compresión exitosa. Mensajes reducidos a {len(body['messages'])}.")

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        return body
