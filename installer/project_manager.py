# installer/project_manager.py
"""
Gestión de múltiples proyectos dentro del workspace de Memexicanisimos.
Cada proyecto tiene su propia estructura src/docs/data y puede ser
establecido como "activo" para que el agente trabaje en él.
"""
import os
import json
from .logger import MemexLogger

logger = MemexLogger.get_logger()


class ProjectManager:
    WORKSPACE = "memex_workspace"
    PROJECTS_DIR = os.path.join(WORKSPACE, "projects")
    ACTIVE_PROJECT_FILE = os.path.join(WORKSPACE, "active_project.json")

    @classmethod
    def ensure_structure(cls):
        """Crea los directorios necesarios si no existen."""
        os.makedirs(cls.PROJECTS_DIR, exist_ok=True)

    @classmethod
    def list_projects(cls):
        """Devuelve lista de nombres de proyectos."""
        cls.ensure_structure()
        if not os.path.exists(cls.PROJECTS_DIR):
            return []
        return [d for d in os.listdir(cls.PROJECTS_DIR)
                if os.path.isdir(os.path.join(cls.PROJECTS_DIR, d))]

    @classmethod
    def create_project(cls, name):
        """Crea un nuevo proyecto con estructura básica."""
        cls.ensure_structure()
        project_path = os.path.join(cls.PROJECTS_DIR, name)
        if os.path.exists(project_path):
            return False, "El proyecto ya existe"
        os.makedirs(project_path)
        # Subdirectorios útiles
        os.makedirs(os.path.join(project_path, "src"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "docs"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "data"), exist_ok=True)
        logger.info(f"Proyecto '{name}' creado en {project_path}")
        return True, project_path

    @classmethod
    def get_project_path(cls, name):
        """Devuelve la ruta completa de un proyecto."""
        return os.path.join(cls.PROJECTS_DIR, name)

    @classmethod
    def get_active_project(cls):
        """Devuelve el nombre del proyecto activo o None."""
        if os.path.exists(cls.ACTIVE_PROJECT_FILE):
            try:
                with open(cls.ACTIVE_PROJECT_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("active")
            except Exception as e:
                logger.error(f"Error leyendo proyecto activo: {e}")
        return None

    @classmethod
    def set_active_project(cls, name):
        """Establece el proyecto activo."""
        if name not in cls.list_projects():
            return False, "El proyecto no existe"
        with open(cls.ACTIVE_PROJECT_FILE, 'w') as f:
            json.dump({"active": name}, f)
        logger.info(f"Proyecto activo cambiado a '{name}'")
        return True, name

    @classmethod
    def get_active_project_path(cls):
        """Devuelve la ruta completa del proyecto activo."""
        active = cls.get_active_project()
        if active:
            return cls.get_project_path(active)
        return None
