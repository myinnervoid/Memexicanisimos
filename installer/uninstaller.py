import os
import shutil
import time
from .logger import MemexLogger
from .docker_utils import DockerUtils

logger = MemexLogger.get_logger()

class MemexUninstaller:
    @staticmethod
    def uninstall(keep_data: bool = True, cwd: str = "."):
        """
        Detiene los contenedores y elimina volúmenes opcionalmente.
        Retorna True solo si todas las operaciones críticas fueron exitosas.
        """
        logger.info("=== Iniciando proceso de Desinstalación ===")
        all_ok = True
        
        # 1. Detener contenedores
        logger.info("[*] Deteniendo servicios y eliminando red interna...")
        if keep_data:
            success = DockerUtils.down(cwd)
        else:
            # Elimina volúmenes anónimos y nombrados declarados en docker-compose
            success, _ = DockerUtils.run_docker_compose(["down", "-v"], cwd)
        
        if not success:
            logger.error("[!] Hubo problemas deteniendo Docker Compose. Puede que ya estuviera abajo.")
            all_ok = False
        else:
            logger.info("[+] Servicios detenidos correctamente.")

        # 2. Archivos de entorno
        files_to_remove = [".env"]
        for f in files_to_remove:
            path = os.path.join(cwd, f)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"[-] Archivo {f} eliminado.")
                except Exception as e:
                    logger.error(f"[!] No se pudo eliminar {f}: {e}")
                    all_ok = False

        # 3. Datos del workspace local si decide no conservarlos
        if not keep_data:
            workspace_dir = os.path.join(cwd, "memex_workspace")
            if os.path.exists(workspace_dir):
                logger.info("[*] Eliminando datos locales de memex_workspace (CUIDADO: Memorias perdidas si no hay backup)...")
                try:
                    shutil.rmtree(workspace_dir)
                    logger.info("[-] Directorio memex_workspace eliminado.")
                except Exception as e:
                    logger.error(f"[!] No se pudo eliminar completamente {workspace_dir}: {e}")
                    all_ok = False
            else:
                logger.info("[-] No se encontró memex_workspace local para eliminar.")

        logger.info("=== Desinstalación completada ===")
        return all_ok
