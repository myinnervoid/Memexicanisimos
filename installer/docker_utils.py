import subprocess
import time
import socket
from .logger import MemexLogger

logger = MemexLogger.get_logger()

class DockerUtils:
    @staticmethod
    def run_docker_compose(commands: list, cwd: str = ".") -> tuple[bool, str]:
        """Ejecuta docker compose y devuelve (éxito, salida o error)"""
        cmd = ["docker", "compose"] + commands
        str_cmd = ' '.join(cmd)
        
        try:
            logger.info(f"[*] Ejecutando: {str_cmd} ...")
            process = subprocess.Popen(
                cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            
            output_lines = []
            for line in process.stdout:
                msg = line.strip()
                logger.info(msg)
                output_lines.append(msg)
                
            process.wait()
            success = process.returncode == 0
            if not success:
                logger.error(f"[!] Fallo al ejecutar: {str_cmd}")
                
            return success, "\n".join(output_lines)
        except Exception as e:
            msg = f"Excepción en '{str_cmd}': {str(e)}"
            logger.error(msg)
            return False, msg

    @staticmethod
    def down(cwd: str = ".") -> bool:
        """Detiene y remueve contenedores."""
        success, _ = DockerUtils.run_docker_compose(["down"], cwd)
        return success

    @staticmethod
    def up(cwd: str = ".") -> bool:
        """Levanta y detachea los contenedores."""
        success, _ = DockerUtils.run_docker_compose(["up", "-d"], cwd)
        return success

    @staticmethod
    def exec_in_container(container: str, commands: list, cwd: str = ".") -> bool:
        """Ejecuta comandos dentro de un servicio activo."""
        success, _ = DockerUtils.run_docker_compose(["exec", "-T", container] + commands, cwd)
        return success

    @staticmethod
    def pull_model(model_name: str, cwd: str = ".") -> bool:
        """Le pide a Memex Ollama jalar un modelo."""
        logger.info(f"[*] Descargando modelo: {model_name} (Esto puede tomar minutos...)")
        success = DockerUtils.exec_in_container("ollama", ["ollama", "pull", model_name], cwd)
        return success

    @staticmethod
    def update_system_images(cwd: str = ".") -> bool:
        """
        Actualiza las imágenes base de Open WebUI y Ollama (Update Manager).
        Equivale a 'docker compose pull' seguido de un reinicio selectivo.
        Los contenedores cuyas imágenes no hayan cambiado no se reinician.
        Los volúmenes (datos, memorias) se preservan siempre.
        """
        logger.info("[*] Buscando actualizaciones en registros de imágenes...")
        success_pull, output_pull = DockerUtils.run_docker_compose(["pull"], cwd)

        if not success_pull:
            logger.error("[!] Falló la descarga de las nuevas imágenes.")
            return False

        logger.info("[+] Imágenes descargadas. Aplicando actualizaciones (reiniciando contenedores modificados)...")
        # 'up -d' recrea automáticamente solo los contenedores cuyas imágenes hayan cambiado
        success_up, _ = DockerUtils.run_docker_compose(["up", "-d"], cwd)

        if success_up:
            logger.info("[+] Actualización aplicada con éxito.")
        else:
            logger.error("[!] Falló el reinicio de los contenedores tras la actualización.")

        return success_up

