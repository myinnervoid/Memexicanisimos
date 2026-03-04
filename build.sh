#!/bin/bash
# =============================================================================
#  Memexicanisimos OS - Script de Empaquetado (PyInstaller)
#  Genera un ejecutable binario nativo para Linux.
#  v3.0 — Incluye daemon/, READMEs, yaml
# =============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[  OK]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "========================================"
echo "  📦 Empaquetado de Memexicanisimos OS"
echo "  v3.0 — Cerebro + Extremidades"
echo "========================================"
echo ""

# 1. Verificar Python
info "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    err "Python3 no está instalado. Instálalo con: sudo apt install python3"
    exit 1
fi
ok "Python3 encontrado: $(python3 --version)"

# 2. Instalar dependencias de empaquetado
info "Instalando dependencias de empaquetado..."
pip3 install --user pyinstaller pyzipper pyyaml 2>/dev/null || pip install pyinstaller pyzipper pyyaml

# 3. Limpiar builds anteriores
info "Limpiando builds anteriores..."
rm -rf build/ dist/ *.spec

# 4. Ejecutar PyInstaller
info "Empaquetando memex_gui.py como ejecutable Linux..."
python3 -m PyInstaller \
    --name "MemexicanisimosOS" \
    --onefile \
    --windowed \
    --add-data "installer:installer" \
    --add-data "src:src" \
    --add-data "daemon:daemon" \
    --add-data "docker-compose.yml:." \
    --add-data "setup_memex.py:." \
    --add-data "install.sh:." \
    --add-data "README.md:." \
    --add-data "README.es.md:." \
    --add-data "LICENSE:." \
    --hidden-import "installer" \
    --hidden-import "installer.hardware" \
    --hidden-import "installer.config" \
    --hidden-import "installer.installer_core" \
    --hidden-import "installer.uninstaller" \
    --hidden-import "installer.docker_utils" \
    --hidden-import "installer.logger" \
    --hidden-import "installer.memory_tools" \
    --hidden-import "installer.ui" \
    --hidden-import "installer.ui.welcome" \
    --hidden-import "installer.ui.hardware" \
    --hidden-import "installer.ui.config" \
    --hidden-import "installer.ui.progress" \
    --hidden-import "installer.ui.result" \
    --hidden-import "yaml" \
    --hidden-import "pyzipper" \
    --collect-all "pyzipper" \
    --collect-all "yaml" \
    --noconfirm \
    --clean \
    memex_gui.py

# 5. Verificar resultado
if [ -f "dist/MemexicanisimosOS" ]; then
    SIZE=$(du -h "dist/MemexicanisimosOS" | cut -f1)
    echo ""
    echo "========================================"
    ok "¡Empaquetado exitoso!"
    echo ""
    echo "  📁 Binario: dist/MemexicanisimosOS"
    echo "  📊 Tamaño:  $SIZE"
    echo ""
    echo "  Para ejecutar:"
    echo "    chmod +x dist/MemexicanisimosOS"
    echo "    ./dist/MemexicanisimosOS"
    echo ""
    echo "  Para distribuir:"
    echo "    cp dist/MemexicanisimosOS /ruta/de/distribucion/"
    echo "========================================"
else
    err "El empaquetado falló. Revisa la salida de PyInstaller arriba."
    exit 1
fi
