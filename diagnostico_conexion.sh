#!/bin/bash
# Diagnóstico de Conexión para Open WebUI y Ollama

echo "====================================================="
echo "   Diagnóstico de Conexión Open WebUI ↔ Ollama"
echo "====================================================="
echo ""

# 1. Verificar si Ollama está instalado y funcionando
echo "[1/5] Verificando el estado de Ollama en el sistema anfitrión..."
if ! command -v ollama &> /dev/null; then
    echo "  ❌ ERROR: Ollama no está instalado o no está en el PATH."
    echo "     Asegúrate de haberlo instalado con: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
else
    echo "  ✅ Ollama está instalado."
fi

# 2. Probar si la API de Ollama responde localmente
echo "[2/5] Probando conexión local a Ollama (localhost:11434)..."
if curl -s --max-time 5 http://localhost:11434/api/tags > /dev/null; then
    echo "  ✅ Ollama API responde correctamente en el puerto 11434."
    echo "     Modelos disponibles:"
    curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | sed 's/^/       - /'
else
    echo "  ❌ ERROR: No se puede conectar a Ollama en http://localhost:11434."
    echo "     Verifica que el servicio esté corriendo con: systemctl status ollama (o 'ollama serve' en otra terminal)."
    exit 1
fi
echo ""

# 3. Verificar el contenedor de Open WebUI
echo "[3/5] Verificando el estado del contenedor Open WebUI..."
if docker ps --format '{{.Names}}' | grep -q "memex-webui"; then
    echo "  ✅ El contenedor 'memex-webui' está corriendo."
    CONTAINER_RUNNING=true
else
    if docker ps -a --format '{{.Names}}' | grep -q "memex-webui"; then
        echo "  ❌ El contenedor 'memex-webui' existe pero no está corriendo."
        echo "     Intenta iniciarlo con: docker start memex-webui"
    else
        echo "  ❌ ERROR: No se encontró un contenedor llamado 'memex-webui'."
        echo "     Asegúrate de haberlo creado con el instalador o manualmente."
    fi
    CONTAINER_RUNNING=false
fi

if [ "$CONTAINER_RUNNING" = true ]; then
    echo ""
    # 4. Inspeccionar la configuración de red del contenedor
    echo "[4/5] Inspeccionando la configuración de red del contenedor..."
    OLLAMA_URL_IN_CONTAINER=$(docker exec memex-webui printenv | grep OLLAMA_BASE_URL | cut -d '=' -f2)
    if [ -n "$OLLAMA_URL_IN_CONTAINER" ]; then
        echo "  ℹ️  Variable OLLAMA_BASE_URL dentro del contenedor: $OLLAMA_URL_IN_CONTAINER"
    else
        echo "  ⚠️  Variable OLLAMA_BASE_URL no definida en el contenedor."
    fi

    # 5. Probar la conexión desde DENTRO del contenedor
    echo "[5/5] Probando la conexión a Ollama desde DENTRO del contenedor..."
    # Intentamos con la URL por defecto del host, que es la más común para solucionar esto.
    TEST_URL="http://host.docker.internal:11434/api/tags"
    echo "  Probando con $TEST_URL..."
    if docker exec memex-webui curl -s --max-time 5 "$TEST_URL" > /dev/null; then
        echo "  ✅ ÉXITO: El contenedor puede conectarse a Ollama a través de 'host.docker.internal:11434'."
        echo "     Este es el camino correcto. Tu problema debería solucionarse configurando esta URL."
    else
        echo "  ❌ El contenedor NO puede conectarse a Ollama a través de 'host.docker.internal:11434'."
        # Intentamos con la IP del gateway por defecto en Linux
        GATEWAY_IP=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null)
        if [ -n "$GATEWAY_IP" ]; then
            TEST_URL_IP="http://$GATEWAY_IP:11434/api/tags"
            echo "  Probando con la IP del gateway de Docker ($TEST_URL_IP)..."
            if docker exec memex-webui curl -s --max-time 5 "$TEST_URL_IP" > /dev/null; then
                echo "  ✅ ÉXITO: El contenedor puede conectarse a Ollama a través de la IP del gateway ($GATEWAY_IP)."
                echo "     Podrías usar esta IP en tu configuración."
            else
                echo "  ❌ Todas las pruebas fallaron. Es probable que haya un problema de red o firewall."
            fi
        fi
    fi
fi

echo ""
echo "====================================================="
echo "   📝 Recomendaciones Finales"
echo "====================================================="

if [ "$CONTAINER_RUNNING" = true ]; then
    cat << EOF

    Opción 1 (Recomendada): Recrea el contenedor con la configuración de red correcta.
        docker stop open-webui
        docker rm open-webui
        docker run -d -p 3000:8080 \\
          --add-host=host.docker.internal:host-gateway \\
          -v open-webui:/app/backend/data \\
          -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \\
          --name open-webui \\
          --restart always \\
          ghcr.io/open-webui/open-webui:main

        Luego accede a http://localhost:3000. La variable de entorno hará la conexión automática.

    Opción 2: Si no quieres recrear el contenedor, configura la URL manualmente:
        1. Abre Open WebUI en http://localhost:3000.
        2. Ve a "Panel de Administración" (el ícono de engranaje).
        3. En la pestaña "Conexiones", busca "OpenAI" o "Ollama".
        4. Añade una nueva conexión con la URL: http://host.docker.internal:11434
        5. Guarda y verifica que aparezca como "Conectado".
EOF
fi
