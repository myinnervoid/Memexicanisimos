# 🌮 Memexicanisimos OS (Memex)

**Cerebro y Extremidades de IA 100% Locales.** Un entorno de desarrollo autónomo con memoria persistente, orquestación de agentes y programación en terminal.

Memexicanisimos OS no es solo un chatbot; es un **ecosistema completo de Inteligencia Artificial (MLOps)** diseñado para correr fluidamente en hardware de consumo (8GB - 16GB RAM). Unifica la planificación visual y la ejecución de código en un solo cerebro compartido.

[Read this in English.](README.md)

---

### 🎉 Novedades en la v6.0 (Sentience Edition)

- **GUI Moderna:** Migración completa a **CustomTkinter** con tema oscuro profesional y navegación por barra lateral.
- **Catálogo Dinámico de Modelos:** Recomienda automáticamente los mejores modelos de IA para tu hardware (2GB→70B), con categorías: General, Coder, Reasoning, Embedding.
- **Actualizador Selectivo:** Actualiza Ollama, Open WebUI o Qdrant de forma independiente — sin reiniciar todo.
- **Gestor de Conexiones y Puertos Dinámicos:** Detecta puertos ocupados (3000-3020) y sugiere alternativas libres. Incluye un panel de 'Conexiones' en tiempo real para reasignar el puerto de Open WebUI en caliente y ver el estado de cada servicio.
- **Solucionador IA (FAQ Clínico):** Pestaña integrada de 'Solucionador' que detecta fallos, extrae los últimos logs de Docker y los formatea automáticamente en un Prompt Clínico listo para copiar y pegar y obtener soporte técnico casi instantáneo.
- **Limpieza Automática y Robustez:** Los botones de Energía ahora destruyen forzosamente los contenedores huérfanos antes de recrear las redes, extinguiendo para siempre los errores por colisión de nombres (*"container already in use"*).
- **Omitir Descarga de Modelo:** Nuevo checkbox para omitir la descarga del modelo durante la instalación — útil para migrar modelos locales de Ollama.
- **Centro de Descarga de Modelos:** Navega, filtra por categoría y descarga cualquier modelo del catálogo o escribe nombres de modelos personalizados.

---

## 🏗️ La Arquitectura y sus Componentes

Hemos diseñado este sistema para que funcione como un **fuerte inexpugnable**, pre-configurado y libre de fricción.

### 🐳 1. Docker: El Fuerte Inexpugnable

Todo el ecosistema vive dentro de una red aislada de contenedores Docker. ¿Por qué?

- **Cero Conflictos de Puertos:** Detección inteligente de puertos asegura que Memex nunca choque con servicios existentes en tu máquina.
- **Portabilidad:** Funciona exactamente igual en Ubuntu, Arch Linux, Fedora o macOS.
- **Limpieza:** Si algo falla, eliminas el contenedor y tu sistema operativo anfitrión queda intacto.

### 🧠 2. Ollama: El Motor Optimizado

El corazón del sistema. En lugar de cargar múltiples modelos y colapsar tu RAM, configuramos Ollama **quirúrgicamente** para la máxima eficiencia:

| Variable | Valor | Efecto |
|----------|-------|--------|
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Solo un modelo en RAM a la vez |
| `OLLAMA_NUM_PARALLEL` | `1` | Ejecución secuencial estricta (previene bloqueos OOM) |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | Límite seguro que previene la "explosión de caché KV" |
| `OLLAMA_KEEP_ALIVE` | `1m` | Descarga automática del modelo tras 1 minuto inactivo |

### 🌐 3. Open WebUI: El Cerebro y los "Sabores"

Actúa como tu panel de control y planificador. Viene cargado nativamente con **"Sabores"** (Agentes especializados):

- 💻 **Memex Coder:** Tu arquitecto de software.
- 📈 **Memex Marketer:** Copywriter que recuerda la voz de tu marca.
- 📚 **Memex Researcher:** Para indexar bases de datos y analizar documentos.
- 🤖 **Memex Auto:** Un orquestador dinámico (Auto-Router) que envía tareas simples a modelos ligeros (1.5B) y tareas complejas a modelos pesados (7B), ahorrando RAM en tiempo real.

### ✋ 4. Aider CLI: Las Extremidades

Mientras Open WebUI planifica, **Aider ejecuta.** Es un agente de terminal (invocado vía `./memex_builder.sh`) que se conecta a tu mismo modelo de Ollama. Consume menos de 100MB de RAM.

### 🗄️ 5. Memoria Persistente Híbrida y Function Calling (v5.4)

Tu agente **no sufre de amnesia** ni está limitado a solo responder texto:

- **Function Calling Nativo:** El LLM (ej. Qwen 2.5/3.5) usa un proxy especial (`agent_chat_loop`) que le permite ejecutar comandos en tu PC localmente de forma autónoma.
- **SQLite FTS5:** Recuerda reglas de negocio, preferencias y hechos importantes a través de las sesiones de chat.
- **Qdrant (RAG):** Indexa repositorios completos de código o PDFs para que la IA entienda el contexto macro de tus proyectos.

---

## 🚀 Instalación Adaptativa (Tiers)

El instalador gráfico detecta automáticamente tu hardware y recomienda los mejores modelos:

| Nivel | Componentes | RAM aprox |
|-------|-------------|-----------|
| 🟢 **Nivel 1 (Chat)** | Solo Open WebUI y Ollama | ~3.5GB |
| 🟡 **Nivel 2 (RAG)** | + Buscador Privado SearxNG y Vector DB Qdrant | ~5.0GB |
| 🔴 **Nivel 3 (Apps)** | + Script `memex_builder.sh` para programación con Aider | ~5.5GB |

### Selección Dinámica de Modelos (v6.0)

El instalador presenta un **Top 10** de modelos filtrados para tu RAM:

| RAM | Modelos ejemplo |
|-----|----------------|
| 4GB | Qwen 2.5 (0.5B), Llama 3.2 (1B) |
| 8GB | Qwen 2.5 (7B), DeepSeek-R1 (7B), Qwen 3 (8B) |
| 16GB | Qwen 3.5 (9B), Phi-4 (14B), DeepSeek-R1 (14B) |
| 32GB+ | DeepSeek-R1 (32B), Llama 3.1 (70B) |

### Inicio Rápido (Linux — Copiar y Pegar)

> ⚠️ **Importante:** DEBES crear una carpeta dedicada para el proyecto. Docker y el instalador necesitan ejecutarse desde esta carpeta. NO instales directamente en tu carpeta personal.

**1. Instala prerrequisitos, descarga y ejecuta:**

```bash
# Instala dependencias (solo una vez)
sudo apt install -y python3-yaml python3-tk git
pip install customtkinter

# Crea tu carpeta del proyecto y descarga
mkdir -p ~/Memexicanisimos && cd ~/Memexicanisimos
git clone https://github.com/myinnervoid/Memexicanisimos.git .

# Ejecuta el instalador
python3 memex_gui.py
```

**2. Para volver a abrir después:**

```bash
cd ~/Memexicanisimos && python3 memex_gui.py
```

> 💡 **Consejo:** Si ya ejecutaste el comando antes, solo abre una terminal, presiona ⬆️ (flecha arriba) y el último comando aparecerá en tu historial. Asegúrate de estar en la carpeta del proyecto.

---

## 🛠️ Guía Rápida: Cómo Crear y Aportar Nuevos "Skills"

Memexicanisimos es una **plataforma extensible**. Usamos el sistema de Tools y Filters de Open WebUI para inyectar "Skills" (Habilidades).

### Método 1: Usando el Prompt Injector (Sin código)

1. Abre un chat en Open WebUI.
2. Llama a la herramienta **Memex Prompt Injector**.
3. Escribe un prompt como este:

> *"Genera un System Prompt para un nuevo agente 'Scrum Master'. Debe usar la herramienta `search_memory` para recordar los bloqueos del equipo de ayer, y usar `create_task` para organizar el TODO.md de hoy."*

El inyector te devolverá la configuración perfecta para crear un nuevo "Sabor" en el panel de administración.

### Método 2: Desarrollando un Skill en Python (Para Contribuidores)

Si quieres crear una herramienta real (ej. buscar en una API externa), crea un archivo en la carpeta `src/`. Todas las herramientas deben seguir el estándar **pydantic**.

**Plantilla Básica de un Skill:**

```python
"""
title: Mi Nuevo Skill
author: Tu Nombre
version: 1.0.0
"""
from pydantic import BaseModel
from typing import Callable, Any

class Tools:
    class Valves(BaseModel):
        api_key: str = ""

    async def mi_nueva_funcion(
        self,
        parametro: str,
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Instrucciones MUY CLARAS para que la IA sepa cuándo usar esta herramienta.
        :param parametro: Qué significa este dato.
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "Ejecutando...", "done": False}
            })

        resultado = f"Procesado: {parametro}"

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "Completado", "done": True}
            })

        return resultado
```

Luego, añádelo al archivo `setup_memex.py` para que el instalador lo inyecte automáticamente en la base de datos de Open WebUI.

---

## 🎛️ Panel de Gestión y Reparación

Si una aplicación falla, **no tienes que reinstalar todo.** Ejecuta `python3 memex_gui.py`, entra al Panel de Control, y usa el **Reinstalador Granular** para recrear únicamente el servicio que falla sin perder tus memorias ni tus modelos.

---

## 📁 Sistema de Múltiples Proyectos

Organiza tu trabajo en proyectos separados desde la pestaña **Proyectos**:

- **Crea proyectos** con directorios dedicados `src/`, `docs/` y `data/`.
- **Establece un proyecto activo** para que el Agente Génesis trabaje automáticamente en ese directorio.
- Los proyectos viven en `memex_workspace/projects/`.

---

## 📄 Licencia

MIT License. Consulta el archivo [LICENSE](LICENSE) para más detalles.
