import os
import sys
import shutil
import json
import yaml
from pathlib import Path
from .logger import MemexLogger

logger = MemexLogger.get_logger()


class ConfigManager:
    def __init__(self, workspace_path="memex_workspace"):
        self.workspace_path = workspace_path
        self.state_file = os.path.join(self.workspace_path, "install_state.json")
        self.flavors_config_file = os.path.join(self.workspace_path, "flavors_config.json")
        os.makedirs(self.workspace_path, exist_ok=True)
        
        # Extraer el core inmutable desde el build efímero de PyInstaller
        self.core_path = self._ensure_persistent_core()

    def _ensure_persistent_core(self) -> str:
        """
        Garantiza que el código de la aplicación (src, daemon, setup_memex) 
        resida en un lugar permanente (~/.memex_os/core).
        Esto es crítico porque Docker Compose no puede montar volúmenes 
        desde la carpeta temporal _MEIPASS de PyInstaller.
        """
        home_dir = os.path.expanduser("~")
        persistent_core_dir = os.path.join(home_dir, ".memex_os", "core")
        
        # Determinar de dónde venimos
        if hasattr(sys, '_MEIPASS'):
            source_dir = sys._MEIPASS
            logger.info(f"[*] Modo Binario detectado. Extrayendo core de {source_dir} a {persistent_core_dir}")
        else:
            source_dir = os.getcwd()
            # En modo desarrollo no es estrictamente necesario, pero lo copiamos 
            # para homogenizar el docker-compose.yml siempre.
            logger.info(f"[*] Modo Script detectado. Reflejando core en {persistent_core_dir}")

        os.makedirs(persistent_core_dir, exist_ok=True)
        
        # Copiar src/
        src_source = os.path.join(source_dir, "src")
        src_dest = os.path.join(persistent_core_dir, "src")
        if os.path.exists(src_source):
            if os.path.exists(src_dest):
                shutil.rmtree(src_dest)
            shutil.copytree(src_source, src_dest)
            
        # Copiar daemon/
        daemon_source = os.path.join(source_dir, "daemon")
        daemon_dest = os.path.join(persistent_core_dir, "daemon")
        if os.path.exists(daemon_source):
            if os.path.exists(daemon_dest):
                shutil.rmtree(daemon_dest)
            shutil.copytree(daemon_source, daemon_dest)
            
        # Copiar setup_memex.py
        setup_source = os.path.join(source_dir, "setup_memex.py")
        setup_dest = os.path.join(persistent_core_dir, "setup_memex.py")
        if os.path.exists(setup_source):
            shutil.copy2(setup_source, setup_dest)
            
        return persistent_core_dir

    def generate_env(self, ram_gb, use_gpu, custom_port):
        """Genera el .env adaptado a la RAM y Seguridad V5.3."""
        import secrets
        context_len = "16384" if ram_gb >= 16 else "8192"
        flash_attn = "1" if use_gpu else "0"
        secret_key = secrets.token_hex(32)

        env_content = f"""# Generado por Memexicanisimos Installer V5.3
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
OLLAMA_CONTEXT_LENGTH={context_len}
OLLAMA_FLASH_ATTENTION={flash_attn}
OLLAMA_KEEP_ALIVE=1m
OLLAMA_KV_CACHE_TYPE=q4_0
OLLAMA_MAX_QUEUE=32
WEBUI_PORT={custom_port}
WEBUI_SECRET_KEY={secret_key}
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        logger.info(f"[*] Archivo .env generado (Contexto: {context_len}).")

    def generate_docker_compose(self, include_whoogle=True, include_qdrant=True,
                                include_aider=True, base_model="qwen2.5-coder:7b",
                                use_gpu=False):
        """
        Genera docker-compose.yml con SearxNG, límites de memoria y GPU opcional.
        - Aider usa paulgauthier/aider con profiles: ["cli"] (no arranca con 'up -d')
        - SearxNG se integra con Open WebUI como motor de búsqueda
        - Qdrant para RAG vectorial
        """
        home_dir = os.path.expanduser("~")  # Ruta absoluta del home

        compose = {
            "services": {
                "ollama": {
                    "image": "ollama/ollama:latest",
                    "container_name": "memex-ollama",
                    "restart": "always",
                    "env_file": [".env"],
                    "volumes": [
                        "ollama_data:/root/.ollama",
                        f"{home_dir}/.ollama:/root/.ollama-host:ro"
                    ],
                    "healthcheck": {
                        "test": ["CMD", "ollama", "list"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "20s"
                    }
                },
                "open-webui": {
                    "image": "ghcr.io/open-webui/open-webui:main",
                    "container_name": "memex-webui",
                    "restart": "always",
                    "ports": ["${WEBUI_PORT:-3000}:8080"],
                    "volumes": [
                        "open-webui-data:/app/backend/data",
                        "./memex_workspace:/app/backend/data/workspace",
                        f"{self.core_path}/setup_memex.py:/app/backend/setup_memex.py",
                        f"{self.core_path}/src/memex_tools.py:/app/backend/memex_tools.py",
                        f"{self.core_path}/src/prompt_injector_tool.py:/app/backend/prompt_injector_tool.py",
                        f"{self.core_path}/src/memex_router.py:/app/backend/memex_router.py",
                        f"{self.core_path}/src/memex_sandbox.py:/app/backend/memex_sandbox.py",
                        f"{self.core_path}/src/skill_context_optimizer.py:/app/backend/skill_context_optimizer.py",
                        f"{self.core_path}/src/skill_evaluator.py:/app/backend/skill_evaluator.py",
                        f"{self.core_path}/src/memory_governor.py:/app/backend/memory_governor.py",
                        f"{self.core_path}/src/memory_governance_skill.py:/app/backend/memory_governance_skill.py"
                    ],
                    "environment": {
                        "OLLAMA_BASE_URL": "http://ollama:11434",
                        "WEBUI_AUTH": "True",
                        "WEBUI_NAME": "Memexicanisimos",
                        "WEBUI_SECRET_KEY": "${WEBUI_SECRET_KEY}",
                        "DATABASE_ENABLE_SQLITE_WAL": "True"
                    },
                    "depends_on": {
                        "ollama": {"condition": "service_healthy"}
                    },
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "30s"
                    },
                    "command": (
                        "bash -c \""
                        "pip install passlib bcrypt pylint flake8 mypy bandit pyflakes black isort && "
                        "bash start.sh & "
                        "until curl -s http://localhost:8080/health > /dev/null; do sleep 2; done; "
                        "python setup_memex.py; wait\""
                    )
                }
            },
            "volumes": {
                "ollama_data": None,
                "open-webui-data": None
            }
        }

        # --- SearxNG (buscador privado, reemplaza a Whoogle) ---
        if include_whoogle:  # Mantenemos el nombre de la variable para compatibilidad
            compose["services"]["searxng"] = {
                "image": "searxng/searxng:latest",
                "container_name": "memex-searxng",
                "restart": "always",
                "ports": ["8080:8080"],
                "environment": {
                    "SEARXNG_BASE_URL": "http://searxng:8080",
                    "SEARXNG_SECRET": "memex-secret-key-change-me"
                },
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                    "start_period": "30s"
                }
            }
            # Configurar Open WebUI para usar SearxNG
            compose["services"]["open-webui"]["environment"]["ENABLE_RAG_WEB_SEARCH"] = "True"
            compose["services"]["open-webui"]["environment"]["RAG_WEB_SEARCH_ENGINE"] = "searxng"
            compose["services"]["open-webui"]["environment"]["SEARXNG_QUERY_URL"] = "http://searxng:8080/search?q=<query>"
            # Añadir dependencia
            compose["services"]["open-webui"]["depends_on"]["searxng"] = {"condition": "service_healthy"}

        # --- Qdrant (RAG vectorial) ---
        if include_qdrant:
            compose["services"]["qdrant"] = {
                "image": "qdrant/qdrant:latest",
                "container_name": "memex-qdrant",
                "restart": "always",
                "ports": ["6333:6333"],
                "volumes": ["qdrant-data:/qdrant/storage"],
                "mem_limit": "2g"  # Límite efectivo en Docker Compose clásico
            }
            compose["volumes"]["qdrant-data"] = None

        # --- Aider (Dockerizado, on-demand) ---
        if include_aider:
            compose["services"]["aider"] = {
                "image": "paulgauthier/aider",
                "container_name": "memex-aider-cli",
                "profiles": ["cli"],  # No arranca con 'up -d', solo con 'run'
                "environment": {
                    "OLLAMA_API_BASE": "http://ollama:11434",
                    "GIT_AUTHOR_NAME": "Memex Builder",
                    "GIT_AUTHOR_EMAIL": "builder@memex.local",
                    "GIT_COMMITTER_NAME": "Memex Builder",
                    "GIT_COMMITTER_EMAIL": "builder@memex.local"
                },
                "volumes": ["./memex_workspace:/app"],
                "working_dir": "/app"
            }
            self.generate_aider_muscle(base_model)

        # --- Daemon (Meta-agente, on-demand) ---
        compose["services"]["daemon"] = {
            "build": "./daemon",
            "container_name": "memex-daemon",
            "restart": "unless-stopped",
            "profiles": ["daemon"],  # No arranca con 'up -d', solo con --profile daemon
            "volumes": ["./memex_workspace:/app/workspace"],
            "depends_on": {
                "ollama": {"condition": "service_healthy"},
                "open-webui": {"condition": "service_healthy"}
            },
            "environment": {
                "OPENWEBUI_API_URL": "http://open-webui:8080/api",
                "WORKSPACE_PATH": "/app/workspace",
                "CHECK_INTERVAL_MINUTES": "10"
            }
        }

        # --- GPU (si está habilitada) ---
        if use_gpu:
            compose["services"]["ollama"]["environment"] = {
                "NVIDIA_VISIBLE_DEVICES": "all",
                "NVIDIA_DRIVER_CAPABILITIES": "compute,utility"
            }
            compose["services"]["ollama"]["device_requests"] = [
                {
                    "driver": "nvidia",
                    "count": -1,
                    "capabilities": ["gpu"]
                }
            ]

        with open("docker-compose.yml", "w", encoding="utf-8") as f:
            yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

        logger.info("[*] docker-compose.yml generado con SearxNG y correcciones.")

    def generate_aider_muscle(self, base_model):
        """
        Genera el script ejecutable y la configuración inteligente (músculo) para Aider.
        - .aider.conf.yml: personalidad y reglas del programador IA
        - memex_builder.sh: lanzador con Docker (sin pip en host)
        """
        # 1. Configuración de Aider (Músculo/Reglas)
        conf_path = os.path.join(self.workspace_path, ".aider.conf.yml")
        aider_model = (
            f"ollama/{base_model}" if "deepseek" in base_model
            else f"ollama_chat/{base_model}"
        )

        muscle_config = f"""# Memex Builder - Aider Muscle Config
model: {aider_model}
dark-mode: true
auto-commits: true
lint: true
# Inyectando capacidades cognitivas base a las extremidades:
message: "Eres Memex Builder, la extremidad ejecutora de Memexicanisimos. Tu tarea es escribir código robusto en base a las instrucciones. Siempre asegúrate de no romper la estructura existente. Piensa paso a paso."
"""
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(muscle_config)

        # 2. Script lanzador (puro Docker, cero pip en host)
        script_path = os.path.join(os.getcwd(), "memex_builder.sh")
        script_content = f"""#!/bin/bash
echo "=========================================================="
echo " 🤖 MEMEX BUILDER (Dockerized Aider)"
echo "=========================================================="
echo " Motor conectado: {base_model}"
echo " Directorio de trabajo: ./memex_workspace"
echo ""
echo " Iniciando contenedor aislado de desarrollo..."
echo " Escribe /exit para salir."
echo "=========================================================="
# Levanta Aider con Docker Compose (profile: cli) y se autodestruye al salir
docker compose run --rm aider
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        os.chmod(script_path, 0o755)
        logger.info("[*] Músculo de Aider (.aider.conf.yml) y script lanzador generados.")

    def save_state(self, config_dict):
        """Guarda el estado de instalación para reinstalaciones."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)
        logger.info("Estado de instalación guardado.")

    def load_state(self):
        """Carga el estado previo si existe."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando estado previo: {e}")
        return {}

    def save_flavors_config(self, flavors_dict):
        """Guarda el diccionario de qué modelo usa cada sabor."""
        try:
            with open(self.flavors_config_file, "w", encoding="utf-8") as f:
                json.dump({"models": flavors_dict}, f, indent=4)
            logger.info("Configuración de Sabores guardada (flavors_config.json).")
        except Exception as e:
            logger.error(f"Error guardando flavors config: {e}")
