import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from .logger import MemexLogger
from .docker_utils import DockerUtils

logger = MemexLogger.get_logger()

# Directorio del proyecto (se asume que este archivo está en env/installer/ y el compose está un nivel arriba)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DockerManager:
    """
    Controlador exclusivo para orquestación de Docker Compose y reparación.
    Desacopla la lógica de infraestructura de la interfaz gráfica principal.
    """

    @staticmethod
    def _execute_in_background(target_func, *args, **kwargs):
        """Ejecuta una función en un hilo demonio."""
        threading.Thread(target=target_func, args=args, kwargs=kwargs, daemon=True).start()

    @staticmethod
    def execute_granular_reinstall(service: str, open_webui_fix: bool = True):
        """Fuerza la recreación aislada de un servicio y sus dependencias sin perder datos."""
        
        def _worker():
            try:
                logger.info(f"[*] Recreando aisaldamente el servicio '{service}'...")
                cmd = ["docker", "compose", "up", "-d", "--force-recreate", "--no-deps", service]
                # Ejecutar en la raíz del proyecto
                subprocess.run(cmd, cwd=PROJECT_DIR, check=True)
                
                # Si es WebUI, podríamos querer re-inyectar los scripts por si acaso
                if service == "open-webui" and open_webui_fix:
                    logger.info(f"[*] Post-instalando herramientas en {service}...")
                    subprocess.run(
                        ["docker", "compose", "exec", "-T", "open-webui", "python", "/app/backend/setup_memex.py"],
                        cwd=PROJECT_DIR
                    )
                logger.info(f"[+] Servicio '{service}' recreado con éxito.")
                # Aquí se podría emitir un evento para GUI, pero mantenemos simpleza
            except Exception as e:
                logger.error(f"[!] Error recreando {service}: {str(e)}")

        DockerManager._execute_in_background(_worker)

    @staticmethod
    def stop_service(service: str):
        """Detiene un servicio en específico."""
        DockerUtils.run_docker_compose(["stop", service], cwd=PROJECT_DIR)

    @staticmethod
    def apply_resource_limits(compose_path: str, service_name: str, limit_gb_str: str) -> bool:
        """
        Lee el docker-compose.yml y sobreescribe los deploy limits de un servicio en RAM.
        Usa una aproximación pura de lectura/escritura de texto o json/yaml si está disponible.
        Asumimos estructura estandar de compose V3.
        """
        import yaml
        
        try:
            with open(compose_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if 'services' not in data or service_name not in data['services']:
                logger.warning(f"No se encontró el servicio {service_name} en el Compose.")
                return False
                
            svc = data['services'][service_name]
            
            # Limpiar si es "Sin Límite"
            if limit_gb_str == "Sin Límite":
                if 'deploy' in svc and 'resources' in svc['deploy']:
                    if 'limits' in svc['deploy']['resources'] and 'memory' in svc['deploy']['resources']['limits']:
                        del svc['deploy']['resources']['limits']['memory']
            else:
                # Asegurar estructura
                if 'deploy' not in svc: svc['deploy'] = {}
                if 'resources' not in svc['deploy']: svc['deploy']['resources'] = {}
                if 'limits' not in svc['deploy']['resources']: svc['deploy']['resources']['limits'] = {}
                
                mem_str = f"{limit_gb_str}gb"
                if mem_str == "0.5gb": mem_str = "512m"
                svc['deploy']['resources']['limits']['memory'] = mem_str
                logger.info(f"Limites aplicados en {service_name}: {mem_str}")
                
            with open(compose_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                
            return True
            
        except Exception as e:
            logger.error(f"Error modificando yaml {compose_path}: {e}")
            return False

    @staticmethod
    def launch_aider(cwd: str) -> tuple[bool, str]:
        """
        Inicia un terminal del sistema host adjuntándose al contenedor Aider.
        Retorna (True, None) si tiene éxito, o (False, ErrorMsg) si falla.
        """
        builder_script = os.path.join(cwd, "memex_builder.sh")
        
        try:
            # Check si aider vive en compose
            result = subprocess.run(
                ['docker', 'compose', 'config', '--services'],
                capture_output=True, text=True, timeout=5, cwd=cwd
            )
            if 'aider' not in result.stdout:
                return False, "El servicio Aider no está en tu docker-compose.yml. Reinstala con opción Aider."

            cmd = builder_script if os.path.exists(builder_script) else "docker compose run --rm aider"
            
            terminal_opened = False
            for terminal_cmd in [
                ["x-terminal-emulator", "-e", cmd],
                ["gnome-terminal", "--", "bash", "-c", cmd],
                ["xfce4-terminal", "-e", cmd],
                ["xterm", "-e", cmd],
            ]:
                try:
                    subprocess.Popen(terminal_cmd, cwd=cwd)
                    terminal_opened = True
                    break
                except FileNotFoundError:
                    continue
                    
            if terminal_opened:
                return True, "Terminal abierta exitosamente."
            else:
                return False, f"Comando fallback: cd {cwd} && {cmd}"
                
        except Exception as e:
            return False, f"Error imprevisto: {str(e)}"
