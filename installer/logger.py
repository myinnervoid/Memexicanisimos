import logging
import sys
import os

class MemexLogger:
    """Configura y provee un logger centralizado que escribe en archivo y consola."""
    
    _logger = None

    @classmethod
    def setup(cls, log_file="memex_workspace/memex_installer.log"):
        if cls._logger is not None:
            return cls._logger

        # Asegurar que el directorio de logs existe antes de crear el FileHandler
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        logger = logging.getLogger("MemexInstaller")
        logger.setLevel(logging.INFO)

        # Formato común
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Archivo Handler
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Consola Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        cls._logger = logger
        return logger

    @classmethod
    def get_logger(cls):
        if cls._logger is None:
            return cls.setup()
        return cls._logger
