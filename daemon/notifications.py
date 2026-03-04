"""
Memex Daemon — Sistema de Notificaciones
Envía notificaciones a diferentes canales (Slack, Discord, archivo local).
Extensible: para añadir un nuevo canal, simplemente crea una función y regístrala.
"""

import os
import json
import time
import requests
from typing import Optional


# ==================== Canales de Notificación ====================

def _notify_file(title: str, message: str):
    """Guarda la notificación en un archivo local (siempre activo como fallback)."""
    log_path = os.environ.get("NOTIFICATION_FILE", "/app/workspace/daemon_notifications.md")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n---\n### {title}\n**{timestamp}**\n\n{message}\n")
    except Exception as e:
        print(f"[Notificación] Error escribiendo archivo: {e}")


def _notify_slack(title: str, message: str):
    """Envía notificación a Slack via webhook."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return

    payload = {
        "text": f"*{title}*\n{message[:3000]}"
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[Slack] Error: {response.status_code}")
    except Exception as e:
        print(f"[Slack] Error: {e}")


def _notify_discord(title: str, message: str):
    """Envía notificación a Discord via webhook."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return

    payload = {
        "content": f"**{title}**\n{message[:2000]}"
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code not in (200, 204):
            print(f"[Discord] Error: {response.status_code}")
    except Exception as e:
        print(f"[Discord] Error: {e}")


def _notify_generic_webhook(title: str, message: str):
    """Envía notificación a un webhook genérico (ej. n8n, Make, Zapier)."""
    webhook_url = os.environ.get("GENERIC_WEBHOOK_URL", "")
    if not webhook_url:
        return

    payload = {
        "title": title,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "memex-daemon"
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code not in (200, 201, 204):
            print(f"[Webhook] Error: {response.status_code}")
    except Exception as e:
        print(f"[Webhook] Error: {e}")


# ==================== Dispatcher ====================

# Registro de canales de notificación
NOTIFICATION_CHANNELS = {
    "file": _notify_file,
    "slack": _notify_slack,
    "discord": _notify_discord,
    "webhook": _notify_generic_webhook,
}


def send_notification(title: str, message: str, channels: Optional[list] = None):
    """
    Envía una notificación a todos los canales configurados.

    :param title: Título de la notificación.
    :param message: Cuerpo del mensaje.
    :param channels: Lista de canales a usar. Si es None, usa todos los configurados.
    """
    if channels is None:
        # Siempre usar archivo como fallback
        active_channels = ["file"]
        # Activar otros canales si tienen URL configurada
        if os.environ.get("SLACK_WEBHOOK_URL"):
            active_channels.append("slack")
        if os.environ.get("DISCORD_WEBHOOK_URL"):
            active_channels.append("discord")
        if os.environ.get("GENERIC_WEBHOOK_URL"):
            active_channels.append("webhook")
        channels = active_channels

    for channel in channels:
        handler = NOTIFICATION_CHANNELS.get(channel)
        if handler:
            try:
                handler(title, message)
                print(f"[Notificación] Enviada por '{channel}': {title}")
            except Exception as e:
                print(f"[Notificación] Error en '{channel}': {e}")
        else:
            print(f"[Notificación] Canal desconocido: {channel}")
