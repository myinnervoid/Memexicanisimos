#!/bin/bash
# =============================================================================
#  Memexicanisimos OS - Desinstalador CLI
#  Elimina contenedores, volúmenes, imágenes y archivos de configuración.
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
ok()    { echo -e "${GREEN}[  OK]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "========================================"
echo "  🗑️  Desinstalador de Memexicanisimos"
echo "========================================"
echo ""

# --- 1. Contenedores y volúmenes ---
read -p "¿Detener y eliminar contenedores Docker + volúmenes? [Y/n]: " CLEAN_DOCKER
if [[ ! "$CLEAN_DOCKER" =~ ^[Nn]$ ]]; then
    info "Deteniendo contenedores y eliminando volúmenes..."
    docker compose down -v 2>/dev/null && ok "Contenedores y volúmenes eliminados." || warn "docker compose down falló (puede que ya estén eliminados)."
fi

# --- 2. Volúmenes huérfanos ---
read -p "¿Limpiar volúmenes Docker huérfanos? [y/N]: " PRUNE_VOLS
if [[ "$PRUNE_VOLS" =~ ^[Yy]$ ]]; then
    info "Limpiando volúmenes huérfanos..."
    docker volume prune -f 2>/dev/null && ok "Volúmenes huérfanos eliminados." || warn "Falló la limpieza."
fi

# --- 3. Imágenes Docker ---
read -p "¿Eliminar imágenes de Ollama y Open WebUI? [y/N]: " CLEAN_IMAGES
if [[ "$CLEAN_IMAGES" =~ ^[Yy]$ ]]; then
    info "Eliminando imágenes..."
    docker rmi ollama/ollama:latest ghcr.io/open-webui/open-webui:main 2>/dev/null \
        && ok "Imágenes eliminadas." || warn "Algunas imágenes no se pudieron eliminar (puede que no existan)."
fi

# --- 4. Archivos de configuración ---
read -p "¿Eliminar archivos de configuración (.env, logs, state)? [Y/n]: " CLEAN_CONFIG
if [[ ! "$CLEAN_CONFIG" =~ ^[Nn]$ ]]; then
    info "Eliminando archivos de configuración..."
    rm -f "$PROJECT_DIR/.env" && info "  .env eliminado"
    rm -f "$PROJECT_DIR/memex_installer.log" && info "  memex_installer.log eliminado"
    rm -f "$PROJECT_DIR/memex_workspace/flavors_config.json" 2>/dev/null && info "  flavors_config.json eliminado"
    rm -f "$PROJECT_DIR/memex_workspace/install_state.json" 2>/dev/null && info "  install_state.json eliminado"
    rm -f "$PROJECT_DIR/memex_workspace/memex_errors.txt" 2>/dev/null && info "  memex_errors.txt eliminado"
    rm -f "$PROJECT_DIR/memex_workspace/memex_installer.log" 2>/dev/null && info "  memex_installer.log (workspace) eliminado"
    ok "Configuración limpiada."
fi

# --- 5. Workspace (MEMORIAS) ---
echo ""
warn "⚠️  La siguiente opción ELIMINARÁ TODAS TUS MEMORIAS de forma PERMANENTE."
read -p "¿Eliminar memex_workspace completo (memorias, TODO.md, exportaciones)? [y/N]: " CLEAN_WORKSPACE
if [[ "$CLEAN_WORKSPACE" =~ ^[Yy]$ ]]; then
    read -p "¿Estás COMPLETAMENTE seguro? Escribe 'BORRAR' para confirmar: " CONFIRM
    if [[ "$CONFIRM" == "BORRAR" ]]; then
        info "Eliminando memex_workspace..."
        rm -rf "$PROJECT_DIR/memex_workspace"
        ok "memex_workspace eliminado."
    else
        warn "Cancelado. El workspace se conserva."
    fi
fi

# --- 6. Ollama del host ---
echo ""
read -p "¿Desinstalar Ollama del sistema host? (solo si lo instalaste fuera de Docker) [y/N]: " CLEAN_OLLAMA
if [[ "$CLEAN_OLLAMA" =~ ^[Yy]$ ]]; then
    info "Deteniendo servicio Ollama..."
    sudo systemctl stop ollama 2>/dev/null || true
    sudo systemctl disable ollama 2>/dev/null || true
    info "Removiendo binarios de Ollama..."
    sudo apt remove -y ollama 2>/dev/null || sudo rm -f /usr/local/bin/ollama
    sudo rm -rf /usr/share/ollama 2>/dev/null || true
    ok "Ollama del host eliminado."
fi

# --- 7. Verificar puertos ---
echo ""
info "Verificando que el puerto 3000 está libre..."
if ! lsof -i :3000 >/dev/null 2>&1; then
    ok "Puerto 3000 libre y disponible."
else
    warn "Puerto 3000 aún ocupado. Puedes matarlo con: sudo kill -9 \$(sudo lsof -t -i :3000)"
fi

echo ""
echo "========================================"
echo "  ✅ Desinstalación completada"
echo "========================================"
echo ""
info "Para reinstalar desde cero, ejecuta:"
echo "  python3 memex_gui.py"
echo ""
