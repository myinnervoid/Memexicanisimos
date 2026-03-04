"""
Memex Daemon v5.0 — Agente en Segundo Plano
Monitorea repositorios Git, detecta cambios y actúa proactivamente.
Usa la API REST de Open WebUI para análisis y la base de datos de Memex para notificaciones.
Incluye el Protocolo Génesis para generar un agente autónomo en el workspace del host.
"""

import os
import time
import json
import requests
import schedule
from git_monitor import check_git_repos
from github_integration import check_github_issues
from notifications import send_notification
from genesis_protocol import trigger_genesis_creation

# Configuración desde variables de entorno
OPENWEBUI_API_URL = os.environ.get("OPENWEBUI_API_URL", "http://open-webui:8080/api")
OPENWEBUI_API_KEY = os.environ.get("OPENWEBUI_API_KEY", "")
WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/app/workspace")
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "10"))
GENESIS_DIR = os.path.join(WORKSPACE_PATH, "genesis_project")


def call_memex_api(prompt: str, model: str = "qwen2.5:7b") -> str:
    """
    Envía un prompt a la API de Open WebUI y retorna la respuesta.
    Usa la API de chat completions de Open WebUI.
    """
    headers = {
        "Content-Type": "application/json",
    }
    if OPENWEBUI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENWEBUI_API_KEY}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Eres Memex Daemon, un agente autónomo que analiza cambios en repositorios y sugiere mejoras. Responde en español de forma concisa."},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        response = requests.post(
            f"{OPENWEBUI_API_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "Sin respuesta.")
        else:
            return f"Error API ({response.status_code}): {response.text[:200]}"
    except Exception as e:
        return f"Error de conexión: {str(e)}"


def save_daemon_log(message: str):
    """Guarda un log del daemon en el workspace."""
    log_path = os.path.join(WORKSPACE_PATH, "daemon_logs.txt")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def job():
    """Trabajo principal del daemon. Se ejecuta periódicamente."""
    print(f"[Daemon] Ejecutando revisión programada...")
    save_daemon_log("Iniciando revisión programada.")

    # 1. Monitorear repositorios locales
    try:
        changes = check_git_repos(WORKSPACE_PATH)
        if changes:
            print(f"[Daemon] Detectados cambios en {len(changes)} repos.")
            save_daemon_log(f"Cambios detectados en {len(changes)} repos.")

            for repo_name, change_info in changes.items():
                prompt = (
                    f"Analiza los siguientes cambios en el repositorio '{repo_name}' "
                    f"y sugiere mejoras o identifica posibles problemas:\n\n{change_info}"
                )
                response = call_memex_api(prompt)
                save_daemon_log(f"Análisis de '{repo_name}': {response[:200]}...")

                send_notification(
                    title=f"🔄 Cambios en {repo_name}",
                    message=response
                )
        else:
            print("[Daemon] Sin cambios locales detectados.")
    except Exception as e:
        save_daemon_log(f"Error en monitoreo Git: {str(e)}")
        print(f"[Daemon] Error Git: {e}")

    # 2. Monitorear issues de GitHub
    try:
        github_token = os.environ.get("GITHUB_TOKEN", "")
        github_repos = os.environ.get("GITHUB_REPOS", "")  # formato: "user/repo1,user/repo2"

        if github_token and github_repos:
            repos_list = [r.strip() for r in github_repos.split(",") if r.strip()]
            new_issues = check_github_issues(github_token, repos_list)

            for issue in new_issues:
                prompt = (
                    f"Se ha detectado un nuevo issue en GitHub:\n"
                    f"Repositorio: {issue['repo']}\n"
                    f"Título: {issue['title']}\n"
                    f"Descripción: {issue['body']}\n\n"
                    f"Genera un plan de solución conciso."
                )
                response = call_memex_api(prompt)
                save_daemon_log(f"Issue #{issue['number']} en {issue['repo']}: {response[:200]}...")

                send_notification(
                    title=f"🐛 Nuevo Issue: {issue['title']}",
                    message=response
                )
    except Exception as e:
        save_daemon_log(f"Error en monitoreo GitHub: {str(e)}")
        print(f"[Daemon] Error GitHub: {e}")

    print("[Daemon] Revisión completada.")
    save_daemon_log("Revisión completada.")


if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Memex Daemon v5.0 — Agente en Segundo Plano")
    print(f"   Intervalo: cada {CHECK_INTERVAL_MINUTES} minutos")
    print(f"   Workspace: {WORKSPACE_PATH}")
    print(f"   API: {OPENWEBUI_API_URL}")
    print("=" * 50)

    save_daemon_log("Daemon v5.0 iniciado.")

    # ── Protocolo Génesis ──────────────────────────────────────────────
    if not os.path.exists(GENESIS_DIR):
        print("[Daemon] Proyecto Génesis no encontrado. Generando...")
        save_daemon_log("Generando Proyecto Génesis...")
        if trigger_genesis_creation():
            save_daemon_log(f"Proyecto Génesis creado en {GENESIS_DIR}")
            print("[Daemon] ✅ Proyecto Génesis generado.")
            print("[Daemon] 📋 El usuario debe ejecutar genesis_agent.py en el host.")
        else:
            save_daemon_log("Error al crear el Proyecto Génesis.")
            print("[Daemon] ❌ Error al crear el Proyecto Génesis.")
    else:
        print(f"[Daemon] Proyecto Génesis ya existe en {GENESIS_DIR}")
        save_daemon_log("Proyecto Génesis ya existe.")

    # Programar el job
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)

    # Ejecutar una primera vez al iniciar
    print("[Daemon] Ejecutando primera revisión...")
    job()

    # Bucle infinito
    while True:
        schedule.run_pending()
        time.sleep(60)

