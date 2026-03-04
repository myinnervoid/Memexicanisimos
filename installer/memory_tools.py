import os
import shutil
import zipfile
import pyzipper
from datetime import datetime
from .logger import MemexLogger
from .docker_utils import DockerUtils

logger = MemexLogger.get_logger()

class MemoryTools:
    """Herramientas de respaldo y restauración para memex_memory.db local."""

    WORKSPACE_DIR = "memex_workspace"
    DB_NAME = "memex_memory.db"
    
    @staticmethod
    def export_memory(output_dir: str = ".", password: str = None) -> bool:
        """Comprime el archivo sqlite local SQLite en un ZIP, con clave opcional."""
        source_db = os.path.join(MemoryTools.WORKSPACE_DIR, MemoryTools.DB_NAME)
        
        if not os.path.exists(source_db):
            logger.error(f"[!] No se encontró base de datos en {source_db} para respaldar.")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = os.path.join(output_dir, f"memex_backup_{timestamp}.zip")

        logger.info(f"[*] Iniciando respaldo de memoria a {zip_filename} ...")
        
        try:
            if password:
                with pyzipper.AESZipFile(zip_filename, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                    zf.setpassword(password.encode('utf-8'))
                    zf.write(source_db, arcname=MemoryTools.DB_NAME)
                logger.info(f"[+] Respaldo Cifrado completado con éxito: {zip_filename}")
            else:
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(source_db, arcname=MemoryTools.DB_NAME)
                logger.info(f"[+] Respaldo completado con éxito: {zip_filename}")
            return True
        except Exception as e:
            logger.error(f"[!] Error exportando memoria: {e}")
            return False

    @staticmethod
    def import_memory(zip_filepath: str, password: str = None, cwd: str = ".") -> bool:
        """Restaura la memoria de un ZIP sobreescribiendo el DB del Workspace y reiniciando el servicio."""
        if not os.path.exists(zip_filepath):
            logger.error(f"[!] Archivo {zip_filepath} no encontrado para importar.")
            return False

        target_dir = os.path.join(cwd, MemoryTools.WORKSPACE_DIR)
        os.makedirs(target_dir, exist_ok=True)

        logger.info(f"[*] Restaurando memoria desde {zip_filepath} ...")
        
        try:
            # Extraer
            if password:
                with pyzipper.AESZipFile(zip_filepath) as zf:
                    zf.setpassword(password.encode('utf-8'))
                    zf.extract(MemoryTools.DB_NAME, path=target_dir)
            else:
                with zipfile.ZipFile(zip_filepath) as zf:
                    zf.extract(MemoryTools.DB_NAME, path=target_dir)

            logger.info("[+] Base de datos extraída en Workspace local.")

            # Reiniciar WebUI para forzar liberación SQLite
            logger.info("[*] Reiniciando contenedor memex-webui...")
            DockerUtils.run_docker_compose(["restart", "open-webui"], cwd)
            
            logger.info("[+] Importación de memoria finalizada y activa.")
            return True
        except RuntimeError as e: # Bad password for pyzipper
            logger.error(f"[!] Falló la extracción. Clave incorrecta o archivo dañado. {e}")
            return False
        except Exception as e:
            logger.error(f"[!] Error importando memoria: {e}")
            return False

    @staticmethod
    def encrypt_file(filepath, password, output=None):
        """Cifra un archivo con AES-256 usando pyzipper."""
        if not os.path.exists(filepath):
            logger.error(f"Archivo no encontrado: {filepath}")
            return False
        if output is None:
            output = filepath + ".aes"
        try:
            with pyzipper.AESZipFile(output, 'w',
                                     compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode('utf-8'))
                zf.write(filepath, arcname=os.path.basename(filepath))
            logger.info(f"Archivo cifrado: {output}")
            return True
        except Exception as e:
            logger.error(f"Error cifrando archivo: {e}")
            return False

    @staticmethod
    def decrypt_file(filepath, password, output=None):
        """Descifra un archivo AES cifrado con pyzipper."""
        if not os.path.exists(filepath):
            logger.error(f"Archivo no encontrado: {filepath}")
            return False
        if output is None:
            if filepath.endswith(".aes"):
                output = filepath[:-4]
            else:
                output = filepath + ".decrypted"
        try:
            with pyzipper.AESZipFile(filepath, 'r') as zf:
                zf.setpassword(password.encode('utf-8'))
                # Extraer el primer archivo
                for name in zf.namelist():
                    zf.extract(name, path=os.path.dirname(output) or ".")
                    extracted = os.path.join(os.path.dirname(output) or ".", name)
                    if extracted != output:
                        os.rename(extracted, output)
                    break
            logger.info(f"Archivo descifrado: {output}")
            return True
        except RuntimeError as e:
            logger.error(f"Contraseña incorrecta o archivo dañado: {e}")
            return False
        except Exception as e:
            logger.error(f"Error descifrando archivo: {e}")
            return False
