import subprocess
import requests
from .logger import MemexLogger

logger = MemexLogger.get_logger()


class AIController:
    """
    Controlador exclusivo para la operación de Inteligencia Artificial (Ollama).
    Desacopla la lógica de red/contenedores de la interfaz gráfica.
    """

    @staticmethod
    def get_installed_models() -> list[str]:
        """Obtiene la lista de modelos instalados en el motor local (Ollama)."""
        installed = []
        try:
            result = subprocess.run(
                ['docker', 'exec', 'memex-ollama', 'ollama', 'list'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n')[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            installed.append(parts[0])
        except subprocess.TimeoutExpired:
            logger.error("[AIController] Timeout listando modelos (Daemon sobrecargado).")
        except FileNotFoundError:
            logger.error("[AIController] Docker no está en PATH.")
        except Exception as e:
            logger.error(f"[AIController] Error listando modelos: {e}")
            
        return installed

    @staticmethod
    def is_alive(host: str = "http://localhost:11434") -> bool:
        """Verifica si la API de Ollama está respondiendo."""
        try:
            response = requests.get(f"{host}/api/tags", timeout=3)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    @staticmethod
    def verify_docker_network(target: str = "ollama") -> tuple[bool, str]:
        """
        Diagnostica si los contenedores de Open WebUI alcanzan internamente a Ollama
        a través del bridge network de Docker Compose.
        """
        try:
            # Ejecutamos curl -f http://ollama:11434 dentro de webui
            cmd = [
                'docker', 'exec', 'memex-webui', 
                'curl', '-s', '-f', f'http://{target}:11434'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, f"✅ Conexión interna WebUI ↔ {target.capitalize()} DOCKER OK."
            else:
                return False, f"❌ Fallo Red: WebUI no alcanza a {target}. ¿Firewall o Red muerta?\nDetalle: {result.stderr or result.stdout}"
        except subprocess.TimeoutExpired:
            return False, f"⌛ Timeout: La red virtual hacia {target} no respondió a tiempo."
        except Exception as e:
            return False, f"⚠️ Error del demonio o contenedor apagado: {e}"
