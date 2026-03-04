"""
Módulo de Detección de Hardware y Recursos.
"""

import os
import subprocess
import socket
import shutil

class HardwareDetector:
    @staticmethod
    def get_ram_gb():
        """Obtiene la RAM total en GB."""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        kb = int(line.split()[1])
                        return round(kb / (1024 * 1024), 1)
        except Exception:
            pass
        return 8.0  # Fallback

    @staticmethod
    def get_cpu_threads():
        """Obtiene el número de hilos lógicos del CPU."""
        return os.cpu_count() or 4

    @staticmethod
    def get_gpu_info() -> dict:
        """
        Intenta detectar la GPU y retorna un diccionario:
        {'name': str, 'vendor': str, 'vram_mb': int}
        """
        info = {'name': 'Gráficos Integrados / Desconocido', 'vendor': 'Unknown', 'vram_mb': 0}
        
        # Intentar NVIDIA (nvidia-smi)
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                info['name'] = parts[0].strip()
                info['vendor'] = 'NVIDIA'
                if len(parts) > 1:
                    info['vram_mb'] = int(parts[1].replace('MiB', '').strip())
                return info
        except Exception:
            pass

        # Fallback a lspci (Intel/AMD)
        try:
            result = subprocess.run(['lspci'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if 'VGA' in result.stdout:
                lines = [l for l in result.stdout.split('\n') if 'VGA' in l]
                if lines:
                    info['name'] = lines[0].split(': ')[-1]
                    if 'intel' in info['name'].lower():
                        info['vendor'] = 'Intel'
                    elif 'amd' in info['name'].lower() or 'radeon' in info['name'].lower():
                        info['vendor'] = 'AMD'
        except Exception:
            pass
        return info

    @staticmethod
    def get_free_disk_space_gb(path="/"):
        """Obtiene el espacio libre en disco en GB para la ruta dada."""
        try:
            total, used, free = shutil.disk_usage(path)
            return round(free / (1024**3), 1)
        except Exception:
            return 0.0

    @staticmethod
    def is_docker_installed() -> bool:
        """Comprueba si Docker está instalado apuntando a su binario."""
        try:
            result = subprocess.run(['docker', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    def is_port_free(port: int) -> bool:
        """Verifica si un puerto TCP está libre en el localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) != 0
