import time
import os
import subprocess
from .logger import MemexLogger
from .config import ConfigManager
from .docker_utils import DockerUtils

logger = MemexLogger.get_logger()

class InstallerCore:
    def __init__(self, workspace_path: str = "memex_workspace"):
        self.workspace_path = workspace_path
        self.cfg_mgr = ConfigManager(workspace_path)

    def prepare_environment(self, ram_gb: float, use_gpu: bool, port: int, flavors_dict: dict):
        """Genera .env y flavors_config.json."""
        logger.info("[*] Preparando entorno de instalación...")
        self.cfg_mgr.generate_env(ram_gb=ram_gb, use_gpu=use_gpu, custom_port=port)
        self.cfg_mgr.save_flavors_config(flavors_dict)
        self.cfg_mgr.save_state({
            "ram_gb": ram_gb,
            "use_gpu": use_gpu,
            "port": port,
            "flavors": flavors_dict,
            "installed_at": time.time()
        })
        logger.info("[+] Entorno preparado.")

    def ensure_docker(self) -> bool:
        """Intenta instalar Docker en sistemas Debian/Ubuntu si no existe."""
        logger.info("[*] Asegurando presencia de Docker...")
        result = subprocess.run(["which", "docker"], stdout=subprocess.PIPE)
        if result.returncode == 0:
            logger.info("   Docker ya está instalado.")
            return True
        
        logger.info("   Instalando Docker vía script oficial (requiere sudo)...")
        try:
            curl_res = subprocess.run("curl -fsSL https://get.docker.com -o get-docker.sh", shell=True)
            if curl_res.returncode != 0:
                return False
            
            sh_res = subprocess.run("sudo sh get-docker.sh", shell=True)
            if sh_res.returncode != 0:
                return False
            
            user = os.environ.get("USER", "root")
            subprocess.run(f"sudo usermod -aG docker {user}", shell=True)
            logger.info(f"[+] Docker instalado exitosamente. Se añadió '{user}' al grupo docker.")
            return True
        except Exception as e:
            logger.error(f"Error instalando Docker: {e}")
            return False

    def docker_compose_up(self) -> bool:
        """Reinicia el stack unificado."""
        logger.info("[*] Limpiando contenedores previos...")
        DockerUtils.down()
        logger.info("[*] Levantando Docker Compose en modo detached...")
        return DockerUtils.up()

    def pull_models(self, models: list) -> bool:
        """Obliga la descarga de modelos base configurados."""
        success_all = True
        unique_models = list(set(models)) # Eliminar duplicados
        for model in unique_models:
            success = DockerUtils.pull_model(model)
            if not success:
                logger.error(f"[!] Aviso: No se pudo descargar completamente el modelo {model}.")
                success_all = False
        return success_all

    def wait_for_health(self, port: int = 3000, timeout: int = 120) -> bool:
        """Espera a que Open WebUI responda al healthcheck nativo de Docker."""
        logger.info(f"[*] Esperando a que el contenedor 'memex-webui' esté saludable (timeout {timeout}s)...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format='{{json .State.Health.Status}}'", "memex-webui"],
                    capture_output=True, text=True, timeout=5
                )
                status = result.stdout.strip().strip("'\"")
                if status == "healthy":
                    logger.info("[+] Contenedor memex-webui está reportando 'healthy'.")
                    return True
                elif status == "unhealthy":
                    logger.warning("[!] Contenedor memex-webui reporta 'unhealthy'.")
                    # might recover, keeping the loop
            except Exception as e:
                pass
            time.sleep(3)
        logger.error(f"[!] memex-webui no alcanzó estado saludable en {timeout}s.")
        return False

    def wait_for_flavors(self, port: int = 3000, expected_flavors: list = None, timeout: int = 120) -> bool:
        """
        Espera activamente a que los Sabores (modelos custom) aparezcan en la API de Open WebUI.
        Consulta GET /api/models hasta que los IDs esperados estén presentes o se agote el timeout.
        """
        import requests
        if expected_flavors is None:
            expected_flavors = ["memex-coder", "memex-marketer", "memex-researcher", "memex-editor"]

        url = f"http://localhost:{port}/api/models"
        logger.info(f"[*] Esperando a que los Sabores aparezcan en Open WebUI (máx {timeout}s)...")
        start = time.time()

        while time.time() - start < timeout:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    # Open WebUI devuelve {"data": [...]} con objetos de modelo
                    models_list = data if isinstance(data, list) else data.get("data", data.get("models", []))
                    model_ids = set()
                    for m in models_list:
                        if isinstance(m, dict):
                            model_ids.add(m.get("id", ""))
                            model_ids.add(m.get("name", "").lower())

                    found = [f for f in expected_flavors if f in model_ids]
                    if len(found) >= len(expected_flavors):
                        logger.info(f"[+] ¡Todos los Sabores detectados! ({', '.join(found)})")
                        return True
                    else:
                        remaining = [f for f in expected_flavors if f not in model_ids]
                        elapsed = int(time.time() - start)
                        logger.info(f"    [{elapsed}s] Esperando sabores faltantes: {remaining}")
            except Exception:
                pass
            time.sleep(5)

        logger.error(f"[!] Timeout ({timeout}s): No todos los sabores aparecieron. setup_memex.py puede estar aún ejecutándose.")
        return False

