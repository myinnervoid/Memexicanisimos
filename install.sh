#!/bin/bash
# Memexicanisimos (Memex) - Smart Installer
# Compatible con Debian/Ubuntu/Linux Mint
# Versión mejorada con detección de hardware y optimizaciones

set -euo pipefail

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🌮 Bienvenido al instalador de Memexicanisimos (Memex)${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo ""

# --- Funciones auxiliares ---
error_exit() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    mkdir -p memex_workspace
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INSTALLER ERROR: $1" >> memex_workspace/memex_errors.txt
    exit 1
}

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# --- Verificación de sistema ---
info "Verificando especificaciones del sistema..."

# Memoria RAM total en MB
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
TOTAL_RAM_GB=$((TOTAL_RAM_MB / 1024))
info "RAM detectada: ${TOTAL_RAM_GB} GB"

# Número de núcleos/hilos CPU
CPU_THREADS=$(nproc)
info "Hilos CPU detectados: ${CPU_THREADS}"

# Espacio en disco libre (en GB)
FREE_DISK_GB=$(df -BG /home | awk 'NR==2 {print $4}' | sed 's/G//')
info "Espacio libre en /home: ${FREE_DISK_GB} GB"

# --- Recomendación de modelo ---
RECOMMENDED_MODEL=""
WARNING_MSG=""
if [ "$TOTAL_RAM_GB" -le 4 ]; then
    RECOMMENDED_MODEL="qwen2.5:1.5b"
    WARNING_MSG="Sistema con <=4GB RAM. Se recomienda un modelo ultraligero (qwen2.5:1.5b)."
elif [ "$TOTAL_RAM_GB" -le 8 ]; then
    RECOMMENDED_MODEL="qwen2.5:7b"
    WARNING_MSG="Sistema con ~8GB RAM. Modelos como qwen2.5:7b o llama3.1:8b funcionarán bien."
elif [ "$TOTAL_RAM_GB" -le 16 ]; then
    RECOMMENDED_MODEL="deepseek-r1:7b"
    WARNING_MSG="Sistema con 12-16GB RAM. Modelos como deepseek-r1:7b o qwen2.5-coder:7b son ideales."
else
    RECOMMENDED_MODEL="deepseek-r1:14b"
    WARNING_MSG="Sistema con más de 16GB RAM. Puedes usar modelos más grandes como deepseek-r1:14b."
fi

# Detectar RAM y asignar contexto óptimo
detect_context_length() {
    local ram_gb=$1
    if [ "$ram_gb" -le 4 ]; then
        echo "2048"
    elif [ "$ram_gb" -le 8 ]; then
        echo "4096"
    elif [ "$ram_gb" -le 16 ]; then
        echo "8192"
    else
        echo "16384"
    fi
}

CONTEXT_LEN=$(detect_context_length $TOTAL_RAM_GB)
info "Tamaño de contexto recomendado: $CONTEXT_LEN tokens"

# Generar archivo .env para docker-compose
crear_env() {
    cat <<EOF > .env
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
OLLAMA_FLASH_ATTENTION=0
OLLAMA_KV_CACHE_TYPE=q4_0
OLLAMA_KEEP_ALIVE=1m
OLLAMA_CONTEXT_LENGTH=$CONTEXT_LEN
EOF
    info "Variables de entorno guardadas en .env para Docker Compose."
}

if [ -f .env ]; then
    read -p "El archivo .env ya existe. ¿Sobrescribirlo con las nuevas optimizaciones? [y/N]: " OVERWRITE_ENV
    if [[ "$OVERWRITE_ENV" =~ ^[Yy]$ ]]; then
        crear_env
    else
        info "Manteniendo archivo .env existente."
    fi
else
    crear_env
fi

echo ""
warn "$WARNING_MSG"
info "Modelo recomendado: ${RECOMMENDED_MODEL}"
echo ""

# --- Instalación de dependencias ---
read -p "¿Instalar/verificar Docker? (requerido para Open WebUI) [y/N]: " INSTALL_DOCKER
if [[ "$INSTALL_DOCKER" =~ ^[Yy]$ ]]; then
    if ! command -v docker &> /dev/null; then
        info "Instalando Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh || error_exit "Fallo al instalar Docker"
        sudo usermod -aG docker $USER
        warn "Se ha agregado tu usuario al grupo 'docker'. Deberás cerrar sesión y volver a entrar para que los cambios surtan efecto."
    else
        info "Docker ya está instalado."
    fi
fi

read -p "¿Instalar Ollama en el sistema host? (No es necesario si usarás el Stack Unificado con Docker) [y/N]: " INSTALL_OLLAMA
if [[ "$INSTALL_OLLAMA" =~ ^[Yy]$ ]]; then
    if ! command -v ollama &> /dev/null; then
        info "Instalando Ollama en el host..."
        curl -fsSL https://ollama.com/install.sh | sh || error_exit "Fallo al instalar Ollama"
    else
        info "Ollama ya está instalado en el host."
    fi

    # Configurar variables de entorno para limitar recursos (crítico en 16GB)
    info "Configurando límites de recursos para Ollama host (systemd override)..."
    sudo mkdir -p /etc/systemd/system/ollama.service.d
    sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null <<EOF
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q4_0"
Environment="OLLAMA_KEEP_ALIVE=1m"
Environment="OLLAMA_CONTEXT_LENGTH=$CONTEXT_LEN"
EOF
    sudo systemctl daemon-reload
    sudo systemctl restart ollama
    info "Configuración aplicada. Puedes verificarla con: systemctl show ollama | grep OLLAMA_"
fi

# --- Despliegue del Stack (Ollama + Open WebUI) ---
read -p "¿Iniciar Memex (Ollama + Open WebUI) con Docker Compose? [y/N]: " START_STACK
if [[ "$START_STACK" =~ ^[Yy]$ ]]; then
    if ! command -v docker &> /dev/null; then
        error_exit "Docker no está instalado. No se puede continuar con docker-compose."
    fi

    info "Iniciando el Stack Unificado (Memex + Ollama)..."
    docker compose up -d || error_exit "Fallo al iniciar el Stack con Docker Compose."
    info "El Stack está corriendo. Open WebUI estará disponible en http://localhost:3000"
    
    # --- Descarga del modelo ---
    read -p "¿Descargar ahora el modelo recomendado (${RECOMMENDED_MODEL}) dentro del contenedor? [y/N]: " PULL_MODEL
    if [[ "$PULL_MODEL" =~ ^[Yy]$ ]]; then
        info "Descargando ${RECOMMENDED_MODEL} (esto puede tomar varios minutos)..."
        docker compose exec memex-ollama ollama pull "$RECOMMENDED_MODEL" || error_exit "Fallo al descargar el modelo en Docker"
    fi
fi

echo ""
echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 Memexicanisimos instalado con éxito${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo ""
echo -e "📋 Resumen de la instalación:"
echo -e "- RAM detectada: $TOTAL_RAM_GB GB → Contexto: $CONTEXT_LEN tokens"
echo -e "- Modelo base recomendado: $RECOMMENDED_MODEL"
echo -e "- Sabores instalados: Coder, Marketer, Researcher, Editor"
echo -e "- Acceso web: ${YELLOW}http://localhost:3000${NC}"
echo -e ""
echo -e "Pasos siguientes:"
echo -e "1. Abre ${YELLOW}http://localhost:3000${NC} en tu navegador."
echo -e "2. Crea la primera cuenta, que será la de administrador."
echo -e "3. ¡Listo! Todo nuestro entorno 'Memex' estará configurado para ti."
echo -e ""
echo -e "¡Disfruta de tu agente local con memoria persistente!"
