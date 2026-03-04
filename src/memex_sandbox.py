"""
title: Memex Pyodide Sandbox Guard
author: Memexicanisimos Team
version: 1.0.0
description: |
  Filtro de seguridad que intercepta bloques de código generados por el modelo
  ANTES de que Pyodide los ejecute. Bloquea imports peligrosos y aplica
  restricciones de seguridad. Capa adicional de defensa sobre el WebWorker.
requirements: pydantic
"""

import re
from typing import Optional

from pydantic import BaseModel, Field


# Módulos que nunca deben ejecutarse en Pyodide
BLOCKED_MODULES = [
    "os", "subprocess", "socket", "requests", "urllib",
    "http.client", "ftplib", "smtplib", "telnetlib",
    "shutil", "pathlib", "tempfile", "ctypes", "multiprocessing",
    "signal", "resource", "sys.exit",
]

# Patrones peligrosos en código
DANGEROUS_PATTERNS = [
    r"exec\s*\(",
    r"eval\s*\(",
    r"__import__\s*\(",
    r"compile\s*\(",
    r"globals\s*\(",
    r"locals\s*\(",
    r"getattr\s*\(.+,\s*['\"]__",
    r"open\s*\(['\"]\/",       # Abrir archivos del sistema
    r"while\s+True\s*:",       # Bucles infinitos
]


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=5, description="Prioridad del filtro (ejecutar después del router)."
        )
        enable_sandbox: bool = Field(
            default=True, description="Habilitar el guardia de sandbox."
        )
        blocked_modules: str = Field(
            default=",".join(BLOCKED_MODULES),
            description="Módulos bloqueados (separados por comas)."
        )
        max_code_length: int = Field(
            default=5000,
            description="Longitud máxima de un bloque de código (caracteres)."
        )
        warn_on_block: bool = Field(
            default=True,
            description="Añadir advertencia visible cuando se bloquea código."
        )

    def __init__(self):
        self.valves = self.Valves()

    def _extract_code_blocks(self, text: str) -> list:
        """Extrae todos los bloques de código (```...```) del mensaje."""
        pattern = r"```(?:\w+)?\n([\s\S]*?)```"
        return re.findall(pattern, text)

    def _check_imports(self, code: str) -> list:
        """Detecta imports de módulos bloqueados."""
        blocked = [m.strip() for m in self.valves.blocked_modules.split(",") if m.strip()]
        violations = []

        for module in blocked:
            # Detectar: import os, from os import, __import__('os')
            patterns = [
                rf"\bimport\s+{re.escape(module)}\b",
                rf"\bfrom\s+{re.escape(module)}\b",
                rf"__import__\s*\(\s*['\"]({re.escape(module)})['\"]",
            ]
            for p in patterns:
                if re.search(p, code):
                    violations.append(f"Import bloqueado: `{module}`")
                    break

        return violations

    def _check_dangerous_patterns(self, code: str) -> list:
        """Detecta patrones peligrosos en el código."""
        violations = []
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                violations.append(f"Patrón peligroso detectado: `{pattern}`")
        return violations

    def _sanitize_code_block(self, code: str) -> tuple:
        """
        Analiza un bloque de código y retorna (is_safe, violations).
        """
        violations = []

        # Verificar longitud
        if len(code) > self.valves.max_code_length:
            violations.append(f"Bloque excede {self.valves.max_code_length} caracteres")

        # Verificar imports
        violations.extend(self._check_imports(code))

        # Verificar patrones peligrosos
        violations.extend(self._check_dangerous_patterns(code))

        return (len(violations) == 0, violations)

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """Passthrough — no modificamos la entrada del usuario."""
        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        """
        Intercepta la respuesta del modelo ANTES de mostrarla.
        Si contiene bloques de código potencialmente peligrosos,
        añade una advertencia visible.
        """
        if not self.valves.enable_sandbox:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        # Verificar el último mensaje del asistente
        last_msg = messages[-1]
        if last_msg.get("role") != "assistant":
            return body

        content = last_msg.get("content", "")
        code_blocks = self._extract_code_blocks(content)

        if not code_blocks:
            return body

        all_violations = []
        for i, code in enumerate(code_blocks):
            is_safe, violations = self._sanitize_code_block(code)
            if not is_safe:
                all_violations.extend(
                    [f"Bloque {i+1}: {v}" for v in violations]
                )

        if all_violations and self.valves.warn_on_block:
            warning = (
                "\n\n---\n"
                "⚠️ **Memex Sandbox Guard** — Se detectaron operaciones potencialmente inseguras:\n"
            )
            for v in all_violations[:5]:  # Máximo 5 advertencias
                warning += f"- {v}\n"
            warning += (
                "\n> El código ha sido marcado para revisión. "
                "Si confías en la operación, puedes ejecutarlo manualmente.\n"
            )
            last_msg["content"] = content + warning

        return body
