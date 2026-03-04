"""
title: Memex Auto-Router v2.0 (Orchestrator)
author: Memexicanisimos Team
version: 2.0.0
description: |
  Filtro inteligente con enrutamiento dinámico basado en señales múltiples.
  3 tiers: light → medium → heavy. Incluye control de concurrencia
  (ResourceManager) y telemetría en outlet (memex_telemetry.jsonl).
  Funciona como Filter nativo de Open WebUI — 0 RAM extra.
requirements: pydantic
"""

import json
import os
import re
import time
import requests
from threading import Semaphore
from typing import Optional

from pydantic import BaseModel, Field

TELEMETRY_PATH = "/app/backend/data/workspace/memex_telemetry.jsonl"
OLLAMA_API_BASE = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="Prioridad del filtro (0 = más alta)."
        )
        light_model: str = Field(
            default="qwen2.5:1.5b",
            description="Modelo para saludos, charlas cortas y traducción (~1.2 GB)."
        )
        medium_model: str = Field(
            default="qwen2.5:7b",
            description="Modelo intermedio para tareas de complejidad media (~4.7 GB)."
        )
        heavy_model: str = Field(
            default="deepseek-r1:7b",
            description="Modelo para código, razonamiento profundo y análisis (~5.1 GB)."
        )
        complexity_threshold_medium: float = Field(
            default=0.3,
            description="Score mínimo (0-1) para enrutar al modelo medio."
        )
        complexity_threshold_heavy: float = Field(
            default=0.6,
            description="Score mínimo (0-1) para enrutar al modelo pesado."
        )
        long_prompt_threshold: int = Field(
            default=150,
            description="Longitud mínima del prompt para considerarlo 'largo'."
        )
        deep_conversation_threshold: int = Field(
            default=5,
            description="Número de mensajes en la conversación para considerarla 'profunda'."
        )
        max_concurrent_heavy: int = Field(
            default=2,
            description="Máximo de peticiones concurrentes al modelo pesado."
        )
        enable_telemetry: bool = Field(
            default=True,
            description="Registrar uso de modelos en memex_telemetry.jsonl."
        )
        code_keywords: str = Field(
            default="código,python,javascript,typescript,bash,shell,script,function,class,import,def ,return,variable,loop,array,json,api,http,sql,docker,git,deploy,ci/cd,pipeline,debug,refactor,test,pytest",
            description="Keywords que indican tarea de código (peso: 0.4)."
        )
        reasoning_keywords: str = Field(
            default="analiza,compara,evalúa,arquitectura,diseño,estrategia,plan,optimiza,resumen,documento,investiga,explica por qué,pros y cons,trade-off",
            description="Keywords que indican razonamiento profundo (peso: 0.3)."
        )
        tool_keywords: str = Field(
            default="memoria,recuerda,guarda,workspace,archivo,busca en,herramienta,ejecuta,comando,git status,git commit",
            description="Keywords que indican uso de herramientas (peso: 0.2)."
        )

    def __init__(self):
        self.valves = self.Valves()
        self._semaphore = None
        self._request_meta = {}  # Store metadata per request for outlet

    def _get_semaphore(self) -> Semaphore:
        """Lazy init del semáforo (se recrea si cambia el Valve)."""
        if self._semaphore is None or self._semaphore._value != self.valves.max_concurrent_heavy:
            self._semaphore = Semaphore(self.valves.max_concurrent_heavy)
        return self._semaphore

    def _parse_keywords(self, valve_str: str) -> list:
        """Parsea keywords de un Valve string."""
        return [k.strip().lower() for k in valve_str.split(",") if k.strip()]

    def _compute_complexity_score(self, message: str, messages: list) -> dict:
        """
        Calcula un score de complejidad (0-1) basado en señales múltiples.
        Retorna dict con score total y desglose por señal.
        """
        msg_lower = message.lower()

        # Señal 1: Keywords de código (peso 0.4)
        code_kws = self._parse_keywords(self.valves.code_keywords)
        has_code = any(kw in msg_lower for kw in code_kws)
        # Bonus: detectar bloques de código con regex
        has_code_block = bool(re.search(r'```[\s\S]*```|`[^`]+`', message))
        code_score = 0.4 if (has_code or has_code_block) else 0.0

        # Señal 2: Keywords de razonamiento (peso 0.3)
        reasoning_kws = self._parse_keywords(self.valves.reasoning_keywords)
        has_reasoning = any(kw in msg_lower for kw in reasoning_kws)
        reasoning_score = 0.3 if has_reasoning else 0.0

        # Señal 3: Uso de herramientas (peso 0.2)
        tool_kws = self._parse_keywords(self.valves.tool_keywords)
        has_tools = any(kw in msg_lower for kw in tool_kws)
        tool_score = 0.2 if has_tools else 0.0

        # Señal 4: Longitud del prompt (peso 0.1)
        is_long = len(message) > self.valves.long_prompt_threshold
        length_score = 0.1 if is_long else 0.0

        # Señal 5: Profundidad de conversación (bonus 0.1)
        conversation_depth = len(messages)
        depth_bonus = 0.1 if conversation_depth > self.valves.deep_conversation_threshold else 0.0

        total = min(1.0, code_score + reasoning_score + tool_score + length_score + depth_bonus)

        return {
            "total": round(total, 2),
            "code": code_score,
            "reasoning": reasoning_score,
            "tools": tool_score,
            "length": length_score,
            "depth": depth_bonus,
        }

    def _select_tier(self, score: float) -> str:
        """Selecciona el tier basado en el score de complejidad."""
        if score >= self.valves.complexity_threshold_heavy:
            return "heavy"
        elif score >= self.valves.complexity_threshold_medium:
            return "medium"
        else:
            return "light"

    def _get_model_for_tier(self, tier: str) -> str:
        """Retorna el modelo correspondiente al tier."""
        return {
            "light": self.valves.light_model,
            "medium": self.valves.medium_model,
            "heavy": self.valves.heavy_model,
        }[tier]

    def _ensure_model_exists(self, model_name: str):
        """
        Verifica si el modelo existe en la base de Ollama.
        Si no existe, intenta mandar la señal de pull para evitar
        que el pipeline colapse y de falsos timeouts.
        """
        try:
            # 1. Comprobar si existe localmente
            check_url = f"{OLLAMA_API_BASE}/api/show"
            resp = requests.post(check_url, json={"name": model_name}, timeout=5)
            if resp.status_code == 200:
                return # El modelo existe
            
            # 2. Si llegamos aquí, el modelo no existe. Intentar Pull (non-blocking)
            print(f"[Memex Router] ⚠️ Modelo '{model_name}' no existe localmente. Intentando Pull en background...")
            pull_url = f"{OLLAMA_API_BASE}/api/pull"
            # Mandamos stream=False para no colgar, aunque un modelo pesado tomará tiempo.
            # En v2, pasaremos la responsabilidad al Daemon, pero esto evita crasheos puros.
            requests.post(pull_url, json={"name": model_name, "stream": False}, timeout=1)
        except requests.exceptions.Timeout:
            pass # Ignoramos timeout intencional del request de pull
        except Exception as e:
            print(f"[Memex Router] Error en _ensure_model_exists para {model_name}: {e}")

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Intercepta la petición ANTES de que llegue al LLM.
        Analiza con señales múltiples y enruta a 1 de 3 tiers.
        """
        messages = body.get("messages", [])
        if not messages:
            return body

        original_model = body.get("model", "")

        # Solo actuar en el sabor Memex Auto
        if "memex-auto" not in original_model.lower():
            return body

        last_message = messages[-1].get("content", "").strip()
        if not last_message:
            return body

        # Calcular complejidad
        analysis = self._compute_complexity_score(last_message, messages)
        tier = self._select_tier(analysis["total"])

        # ResourceManager: si el tier es heavy, verificar semáforo
        if tier == "heavy":
            sem = self._get_semaphore()
            if not sem.acquire(blocking=False):
                # Sistema saturado → degradar a medium
                tier = "medium"
                print(f"[Memex Router] ⚠️ Recursos saturados. Degradando de heavy → medium.")

        target_model = self._get_model_for_tier(tier)

        print(f"[Memex Router] Score: {analysis['total']} → Tier: {tier} → Modelo: {target_model}")
        print(f"  Señales: code={analysis['code']}, reasoning={analysis['reasoning']}, "
              f"tools={analysis['tools']}, length={analysis['length']}, depth={analysis['depth']}")

        # Validamos que el modelo exista, o disparamos un pull proactivo
        self._ensure_model_exists(target_model)

        body["model"] = target_model

        # Guardar metadata para telemetría en outlet
        user_id = "unknown"
        if __user__ and isinstance(__user__, dict):
            user_id = __user__.get("id", __user__.get("email", "unknown"))

        self._request_meta[id(body)] = {
            "ts": time.time(),
            "user": user_id,
            "model": target_model,
            "tier": tier,
            "score": analysis["total"],
            "msg_len": len(last_message),
            "original_model": original_model,
        }

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Post-procesamiento: registrar telemetría y liberar semáforo.
        """
        # Liberar semáforo si fue adquirido
        meta = self._request_meta.pop(id(body), None)

        if meta and meta.get("tier") == "heavy":
            try:
                self._get_semaphore().release()
            except ValueError:
                pass  # Ya liberado

        # Registrar telemetría
        if meta and self.valves.enable_telemetry:
            meta["latency_ms"] = round((time.time() - meta["ts"]) * 1000)
            meta["ts"] = int(meta["ts"])
            try:
                os.makedirs(os.path.dirname(TELEMETRY_PATH), exist_ok=True)
                with open(TELEMETRY_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[Memex Router] Error escribiendo telemetría: {e}")

        return body
