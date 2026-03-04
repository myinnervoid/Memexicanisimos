#!/bin/bash
# =============================================================================
#  Memexicanisimos OS v5.2 - Empaquetador Binario
#  Genera un ejecutable standalone usando PyInstaller dentro de un venv.
# =============================================================================

set -e

NAME="MemexicanisimosOS"

echo ""
echo "========================================="
echo "  🤠 Empaquetador de Memexicanisimos OS v5.2"
echo "========================================="
echo ""

# 1. Configurar y activar el entorno virtual
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "🌱 Creando entorno virtual en la carpeta '$VENV_DIR'..."
    # Asegúrate de tener python3-venv instalado en tu sistema (sudo apt install python3-venv)
    python3 -m venv "$VENV_DIR"
fi

echo "🔄 Activando entorno virtual..."
source "$VENV_DIR/bin/activate"

# 2. Verificar e instalar PyInstaller dentro del venv
if ! command -v pyinstaller &> /dev/null; then
    echo "[!] PyInstaller no encontrado en el venv. Instalando..."
    pip install pyinstaller
fi

echo "🧹 Limpiando builds anteriores..."
rm -rf build dist *.spec

echo "🔨 Empaquetando $NAME con PyInstaller..."
pyinstaller \
    --name "$NAME" \
    --onefile \
    --windowed \
    --add-data "assets:assets" \
    --add-data "installer:installer" \
    --add-data "src:src" \
    --add-data "daemon:daemon" \
    --hidden-import installer.hardware \
    --hidden-import installer.installer_core \
    --hidden-import installer.uninstaller \
    --hidden-import installer.docker_utils \
    --hidden-import installer.logger \
    --hidden-import installer.memory_tools \
    --hidden-import installer.config \
    --hidden-import installer.project_manager \
    --paths . \
    memex_gui.py

echo ""
echo "✅ Ejecutable creado en: dist/$NAME"
echo "   Tamaño: $(du -h dist/$NAME | cut -f1)"
echo ""
echo "Para ejecutar:"
echo "  chmod +x dist/$NAME"
echo "  ./dist/$NAME"
echo ""

chmod +x "dist/$NAME"

# Desactivar el entorno virtual al terminar
deactivate
