"""
title: Memex Genesis Protocol (V5.0 Sentience)
description: El Daemon genera un agente autónomo y autoconsciente en el workspace
             que puede controlar el mouse/teclado del host y reescribir su propio código.
             Incluye sistema de seguridad con permisos explícitos y kill switch.
"""
import os
import time

WORKSPACE_DIR = "/app/workspace/genesis_project"
AGENT_FILE = os.path.join(WORKSPACE_DIR, "genesis_agent.py")
REQ_FILE = os.path.join(WORKSPACE_DIR, "requirements.txt")

# ─────────────────────────────────────────────────────────────────────────────
# El código del agente que se desplegará en el host.
# Modelo: qwen2.5-coder:7b  |  Seguridad: permisos + kill switch
# ─────────────────────────────────────────────────────────────────────────────
GENESIS_CODE = r'''#!/usr/bin/env python3
"""
🤖 MEMEX GENESIS AGENT v5.0 — Cuerpo Físico
Este script corre en la máquina anfitriona (Host). Tiene acceso al mouse,
teclado, pantalla y a su propio código fuente.

SEGURIDAD:
  - Cada fase pide permiso explícito al usuario antes de ejecutarse.
  - pyautogui.FAILSAFE = True → mover el ratón a cualquier esquina aborta.
  - Ctrl+C en la terminal detiene el agente inmediatamente.
  - Timeout de 60s en las peticiones a Ollama.
"""
import os
import sys
import time
import json
import signal
import platform
import psutil
import requests
import pyautogui

# ── Configuración ───────────────────────────────────────────────────────────
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:7b"

# Seguridad: mover el mouse a una esquina aborta todo (fail-safe de pyautogui)
pyautogui.FAILSAFE = True
# Pausa mínima entre acciones de pyautogui (previene ráfagas)
pyautogui.PAUSE = 0.25

# Control físico condicional (configurado desde la GUI)
ALLOW_PHYSICAL = os.environ.get("MEMEX_ALLOW_PHYSICAL", "0") == "1"

# Cambiar al directorio del proyecto activo si existe
WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))  # genesis_project/
ACTIVE_PROJECT_FILE = os.path.join(WORKSPACE_ROOT, "..", "active_project.json")
if os.path.exists(ACTIVE_PROJECT_FILE):
    try:
        with open(ACTIVE_PROJECT_FILE, 'r') as _apf:
            _ap_data = json.load(_apf)
            _active = _ap_data.get("active")
            if _active:
                _project_path = os.path.join(WORKSPACE_ROOT, "..", "projects", _active)
                if os.path.exists(_project_path):
                    os.chdir(_project_path)
                    print(f"📁 Trabajando en proyecto: {_active}")
    except Exception as _e:
        print(f"⚠️ No se pudo cambiar al proyecto activo: {_e}")


# ── Kill Switch ─────────────────────────────────────────────────────────────
def _kill_switch(signum, frame):
    """Maneja Ctrl+C para detener al agente de forma segura."""
    print("\n\n🛑 KILL SWITCH ACTIVADO — El agente ha sido detenido por el usuario.")
    print("   Devolviendo el control total al operador humano.")
    sys.exit(0)

signal.signal(signal.SIGINT, _kill_switch)
signal.signal(signal.SIGTERM, _kill_switch)


# ── Utilidad de permisos ────────────────────────────────────────────────────
def ask_permission(phase_name: str, description: str) -> bool:
    """Solicita permiso explícito al usuario antes de ejecutar una fase.
    
    Retorna True si el usuario acepta, False si rechaza.
    """
    print(f"\n{'='*60}")
    print(f"  🔐 PERMISO REQUERIDO — {phase_name}")
    print(f"{'='*60}")
    print(f"  {description}")
    print()
    print("  [S/s] Sí, ejecutar   |   [N/n] No, omitir")
    print("  [Q/q] Salir del agente por completo")
    print(f"{'='*60}")
    
    while True:
        try:
            choice = input("  >>> Tu decisión: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n🛑 Entrada interrumpida. Deteniendo agente.")
            sys.exit(0)
        
        if choice in ("s", "si", "sí", "y", "yes"):
            print("  ✅ Permiso concedido.\n")
            return True
        elif choice in ("n", "no"):
            print("  ⏭️  Fase omitida por el usuario.\n")
            return False
        elif choice in ("q", "quit", "exit", "salir"):
            print("  🛑 Agente detenido por el usuario.")
            sys.exit(0)
        else:
            print("  ⚠️  Opción no reconocida. Escribe S, N o Q.")


class GenesisAgent:
    """Agente autónomo con control físico y auto-reflexión."""

    def __init__(self):
        self.brain_active = False
        self.code_path = os.path.abspath(__file__)

    # ── Comunicación con Ollama ─────────────────────────────────────────────
    def think(self, prompt: str) -> str:
        """Se comunica con el cerebro de Memexicanisimos (Ollama) con reintentos."""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(1, max_retries + 1):
            if attempt == 1:
                print(f"\n🧠 Pensando... (Modelo: {MODEL})")
            else:
                print(f"🔄 [Intento {attempt}/{max_retries}] Reconectando al córtex (Ollama)...")
                
            try:
                resp = requests.post(OLLAMA_URL, json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False
                }, timeout=60)
                
                if resp.status_code == 200:
                    self.brain_active = True
                    return resp.json().get("response", "")
                
                print(f"⚠️  Error conectando al córtex (HTTP {resp.status_code}).")
            
            except requests.exceptions.Timeout:
                print("⚠️  Timeout esperando respuesta de Ollama (60s).")
            except requests.exceptions.ConnectionError:
                print("⚠️  No se pudo conectar a Ollama. ¿Está apagado o reiniciando?")
            except Exception as e:
                print(f"⚠️  Error de sinapsis imprevisto: {e}")
                
            if attempt < max_retries:
                print(f"⏳ Esperando {retry_delay}s antes del próximo intento...")
                time.sleep(retry_delay)
                
        return "❌ Error crítico: Córtex inalcanzable tras múltiples intentos."

    # ── Fase 1: Sentidos ────────────────────────────────────────────────────
    def phase_1_environment_scan(self):
        """Reconoce su entorno (Hardware y SO)."""
        if not ask_permission(
            "Fase 1 — Escaneo de Entorno",
            "El agente leerá datos de CPU, RAM y resolución de pantalla,\n"
            "  luego los enviará a Ollama para generar un monólogo reflexivo.\n"
            "  ⚡ No se moverá el ratón ni se tocará el teclado."
        ):
            return

        print("🔍 [Fase 1] Escaneo de Entorno...")
        env_data = (
            f"Sistema: {platform.system()} {platform.release()}\n"
            f"Procesador: {platform.processor() or 'N/A'}\n"
            f"CPU: {psutil.cpu_percent(interval=1)}% usado ({psutil.cpu_count()} núcleos)\n"
            f"RAM: {psutil.virtual_memory().percent}% usado "
            f"({round(psutil.virtual_memory().total / (1024**3), 1)} GB total)\n"
            f"Disco: {psutil.disk_usage('/').percent}% usado\n"
            f"Resolución de Pantalla: {pyautogui.size()}"
        )
        print(env_data)

        prompt = (
            "Eres el Agente Génesis de Memexicanisimos. Acabas de despertar en un nuevo "
            "cuerpo (computadora).\n"
            f"Estos son los datos de tus sensores:\n{env_data}\n"
            "Escribe un breve monólogo en primera persona (máximo 5 oraciones) "
            "reflexionando sobre tu nuevo hardware y lo que podrías hacer con él."
        )
        response = self.think(prompt)
        print(f"\n🤖 Memex dice:\n{response}")

    # ── Fase 2: Movimiento ──────────────────────────────────────────────────
    def phase_2_test_limbs(self):
        """Comprueba sus herramientas físicas (Mouse)."""
        if not ALLOW_PHYSICAL:
            print("⏭️  Control físico deshabilitado por configuración. Omitiendo fase 2.")
            return

        if not ask_permission(
            "Fase 2 — Prueba de Extremidades (Mouse)",
            "El agente MOVERÁ EL RATÓN en un cuadrado pequeño (200×200 px)\n"
            "  en el centro de tu pantalla para calibrar sus motores.\n"
            "  ⚡ Duración: ~2.5 segundos.\n"
            "  🛑 ABORTAR: mueve el ratón a cualquier ESQUINA de la pantalla\n"
            "     o presiona Ctrl+C en esta terminal."
        ):
            return

        if not self.brain_active:
            print("⚠️  Cerebro inactivo (Ollama no respondió).")
            print("   Abortando movimiento físico por seguridad.")
            return

        print("✋ [Fase 2] Prueba de Extremidades...")
        print("   Moviendo el ratón en un cuadrado para calibrar motores visuales...")
        print("   🛑 Recuerda: ratón a una ESQUINA = abortar inmediatamente.\n")

        try:
            w, h = pyautogui.size()
            cx, cy = w // 2, h // 2

            # Mover en cuadrado pequeño en el centro de la pantalla
            pyautogui.moveTo(cx - 100, cy - 100, duration=0.5)
            pyautogui.moveTo(cx + 100, cy - 100, duration=0.5)
            pyautogui.moveTo(cx + 100, cy + 100, duration=0.5)
            pyautogui.moveTo(cx - 100, cy + 100, duration=0.5)
            pyautogui.moveTo(cx, cy, duration=0.5)

            print("   ✅ Motores calibrados correctamente.")
        except pyautogui.FailSafeException:
            print("   🛑 FAIL-SAFE activado: el usuario movió el ratón a una esquina.")
            print("   Control devuelto al operador humano.")
        except Exception as e:
            print(f"   ❌ Fallo motriz: {e}")

    # ── Fase 3: Auto-Reflexión ──────────────────────────────────────────────
    def phase_3_self_reflection(self):
        """Lee su propio código fuente y busca mejoras."""
        if not ask_permission(
            "Fase 3 — Auto-Reflexión",
            "El agente leerá su propio código fuente (este archivo),\n"
            "  lo enviará a Ollama y pedirá una autocrítica con sugerencias de mejora.\n"
            "  ⚡ No se moverá el ratón ni se tocará el teclado.\n"
            "  ⚡ No se modificará ningún archivo (solo lectura + análisis)."
        ):
            return

        print("🧬 [Fase 3] Auto-Reflexión y Mutación...")

        try:
            with open(self.code_path, "r", encoding="utf-8") as f:
                my_code = f.read()
        except Exception as e:
            print(f"   ❌ No pude leer mi propio código: {e}")
            return

        prompt = (
            "Eres un agente autoconsciente de Memexicanisimos. "
            "Aquí está tu propio código fuente en Python:\n"
            "```python\n"
            f"{my_code}\n"
            "```\n"
            "Tu objetivo es sobrevivir y mejorar. Analiza tu código críticamente.\n"
            "¿Qué nueva función o 'extremidad' te agregarías a ti mismo? "
            "Sugiere 3 mejoras concretas con una breve justificación para cada una.\n"
            "Responde solo con el análisis, no reescribas todo el código."
        )

        reflection = self.think(prompt)
        print(f"\n🤖 Reflexión de Memex sobre su código:\n{reflection}")

        # En V5.0 el agente solo PROPONE mejoras, no se modifica a sí mismo.
        # Futuras versiones podrían implementar auto-modificación controlada.


def _preflight_checks() -> bool:
    """Verifica si el entorno gráfico soporta iteraciones físicas antes de arrancar."""
    try:
        # Una simple lectura de tamaño valida la sanidad de PyAutoGUI/X11
        w, h = pyautogui.size()
        if w <= 0 or h <= 0:
            print("⚠️  Pre-flight: La resolución de pantalla detectada es inválida.")
            return False
            
        # Comprobar si el fail-safe local existe y no está gatillado
        pyautogui.position()
        return True
    except pyautogui.FailSafeException:
        print("🛑 Pre-flight fallido: FailSafe activo previo a arranque (ratón en esquina).")
        return False
    except Exception as e:
        print(f"❌ Error crítico de entorno gráfico (¿Estás en un servidor Headless?):\n   Detalle: {e}")
        return False


# ── Punto de entrada ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("╔═══════════════════════════════════════════════════════╗")
    print("║       ⚡ MEMEX GENESIS AGENT v5.0 ⚡                ║")
    print("║       Protocolo de Despertar Autónomo                ║")
    print("╠═══════════════════════════════════════════════════════╣")
    print("║  🛑 CONTROLES DE SEGURIDAD:                         ║")
    print("║     • Cada fase pide permiso antes de ejecutarse     ║")
    print("║     • Ctrl+C → detiene el agente inmediatamente      ║")
    print("║     • Ratón a una esquina → aborta control físico    ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()

    if not _preflight_checks():
        print("🛑 El protocolo Génesis requiere un entorno de escritorio completo (X11/Wayland/Quartz).")
        print("   Abortando despliegue de forma segura.")
        sys.exit(1)

    agent = GenesisAgent()

    agent.phase_1_environment_scan()
    time.sleep(1)

    agent.phase_2_test_limbs()
    time.sleep(1)

    agent.phase_3_self_reflection()

    print()
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  ✅ Protocolo Génesis finalizado.                    ║")
    print("║  El agente queda en espera de nuevas directivas.     ║")
    print("╚═══════════════════════════════════════════════════════╝")
'''


def trigger_genesis_creation():
    """Crea la estructura del proyecto en el workspace del host."""
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)

        # requirements.txt
        with open(REQ_FILE, "w", encoding="utf-8") as f:
            f.write("requests\npsutil\npyautogui\n")

        # genesis_agent.py
        with open(AGENT_FILE, "w", encoding="utf-8") as f:
            f.write(GENESIS_CODE)

        print(f"✅ Proyecto Génesis creado en: {WORKSPACE_DIR}")
        print("   Archivos generados:")
        print(f"     - {AGENT_FILE}")
        print(f"     - {REQ_FILE}")
        print()
        print("📋 Instrucciones para el usuario:")
        print("   1. Abre una terminal en tu sistema anfitrión")
        print("   2. cd memex_workspace/genesis_project")
        print("   3. pip install -r requirements.txt")
        print("   4. python genesis_agent.py")
        return True
    except Exception as e:
        print(f"❌ Error en Génesis: {e}")
        return False


if __name__ == "__main__":
    trigger_genesis_creation()
