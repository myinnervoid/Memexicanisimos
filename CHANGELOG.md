# 📜 CHANGELOG — Historia de Memexicanísimos OS

> **Documento de referencia para retomar desarrollo.**  
> Incluye: mejoras por fase, código clave, comandos de despliegue, y arquitectura acumulada.

---

## v6.0 — Sentience Edition (2026-03-04)

**Objetivo:** Modernizar completamente la interfaz del instalador, implementar un catálogo dinámico de modelos IA basado en hardware, y añadir herramientas inteligentes de gestión de servicios.

### GUI Moderna (CustomTkinter)

- Migración completa de Tkinter/ttk a **CustomTkinter** con tema oscuro profesional
- Navegación por barra lateral (Bienvenida, Hardware, Configuración, Instalación, Panel de Control)
- Widgets modernos: `CTkButton`, `CTkCheckBox`, `CTkRadioButton`, `CTkScrollableFrame`
- Fix global de `grab_set()` en ventanas `CTkToplevel` (error "window not viewable")

### Catálogo Dinámico de Modelos (`installer/models_catalog.py`)

- **23 modelos** catalogados con categorías: General, Coder, Reasoning, Embedding
- Nuevos modelos: `qwen3:8b`, `qwen3.5:9b`, `qwen3-coder:7b`, `gemma3:4b`, `phi3.5:3.8b`, `codestral:22b`
- Modelos de embedding: `nomic-embed-text`, `bge-m3`, `mxbai-embed-large`
- Filtrado automático **Top 10** según RAM detectada del usuario
- Método `get_all_for_download()` para el centro de descarga con indicadores de compatibilidad

### Actualizador Selectivo de Servicios

- Reemplaza la actualización monolítica por un diálogo con checkboxes por servicio
- Servicios: Ollama, Open WebUI, Qdrant, SearxNG
- Cada servicio se actualiza independientemente: `docker compose pull` → `up -d`
- Re-inyección automática de herramientas tras actualizar Open WebUI

### Escáner Inteligente de Puertos

- Verifica si el puerto 3000 está ocupado antes de instalar
- Identifica qué proceso usa cada puerto (vía `ss`)
- Busca puertos libres en el rango 3001-3020
- Genera `.env` y `docker-compose.yml` con el puerto correcto

### Centro de Descarga de Modelos

- Interfaz agrupada por categoría (🧠 General, 💻 Coder, 🔬 Reasoning, 📐 Embedding)
- Indicadores visuales: ✅ Instalado, ☐ Compatible, ⚠️ Necesita más RAM
- Campo de texto para modelos personalizados (ej: `qwen3.5:9b`, `mistral:7b`)

### Opción "No Descargar Modelo"

- Checkbox en Configuración para omitir `ollama pull` durante la instalación
- Instrucciones de migración: `docker cp ~/.ollama/models memex-ollama:/root/.ollama/`

### Preparador de Release (`prepare_release.sh` v6.0)

- Actualizado para incluir: `installer/ui/`, `docs/`, `scripts/`, `tests/`, `model_capabilities.yaml`
- Log verboso por archivo e instrucciones de instalación limpia

---

## Arquitectura Acumulada (v4.0)

```
                ┌──────────────────────┐
                │     GUI (tkinter)    │
                │   memex_gui.py       │
                └──────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
   Docker Compose     setup_memex.py    build.sh
   (dinámico)         (inyección)       (PyInstaller)
         │                 │
    ┌────┴────┐      ┌─────┴──────┐
    │ Ollama  │      │  Open WebUI │──── Skills (src/)
    │ (Motor) │      │  (Cerebro)  │       │
    └─────────┘      └────────────┘       │
                           │         ┌────┴────────────────────┐
                     ┌─────┴────┐    │  memex_tools.py v8.0    │
                     │  Qdrant  │    │  memex_router.py v2.0   │
                     │  (RAG)   │    │  memory_governor.py     │
                     └──────────┘    │  context_optimizer.py   │
                                     │  skill_evaluator.py     │
                     ┌──────────┐    │  prompt_injector.py     │
                     │ Whoogle  │    │  memex_sandbox.py       │
                     │ (Search) │    └─────────────────────────┘
                     └──────────┘
                     ┌──────────┐    ┌─────────────────────────┐
                     │  Aider   │    │   Observability Stack   │
                     │ (CLI)    │    │   Prometheus + Grafana   │
                     └──────────┘    │   + Custom Exporter      │
                                     └─────────────────────────┘
```

```

---

## v5.4 — Chat API & Native Tool Proxy (GSD Phase 5)

**Objetivo:** Evolucionar la arquitectura del Cortex Brain migrándola de una canalización "Zero-Shot Text" (`/api/generate`) a una estructura 100% "Agentic Function Calling" (`/api/chat`), permitiendo cognición ininterrumpida.

### Novedades Principales
- **Agent Chat Loop (Proxy):** `memex_tools.py` ahora implementa `agent_chat_loop()`, un intermediario que cede el control iterativo al LLM. El modelo puede decidir llamar una o varias herramientas recursivamente sin intervención humana o código duro hasta resolver la tarea.
- **Auto-inyección JSON Schema:** Se desarrolló `get_available_tools()` exponiendo la suite local (Lectura de memoria vectorizada, Escritura, Comandos, Shell) como un Schema compatible con OpenAI/Ollama Tools.
- **Backward Compatibility:** Los pipelines legados (`run_subagent`) siguen funcionando transparentemente sin romper el evaluador de Métrica (Juez Cognitivo) o el Agente Motor (PyAutoGUI).
- **GUI Refactor:** La interfaz gráfica (`memex_gui.py` y `updater/memex_gui.py`) migró a un Layout fluido basado en `tk.Canvas` con Scrolling nativo, permitiendo agregar ilimitados microservicios sin romper el botón de instalación en resoluciones bajas.

---

## v5.3 / v5.2 — Refactorización Core, Hilos y Daemon Automata (GSD Milestone 1)

**Objetivo:** Estabilizar y refactorizar el núcleo del software mediante los principios metodológicos GSD (Get Shit Done), enfocándose en resiliencia, UX no bloqueante y la fortificación del Agente Autónomo.

### Novedades Principales
- **Arquitectura Desacoplada (Fase 1):** 
  - Extracción de dependencias y lógica de fondo de `memex_gui.py` hacia `installer/docker_manager.py` y `installer/ai_controller.py`.
  - Integración de una suite de pruebas controladas (Pytest + Mocks) y de la Pestaña *"Rendimiento y Hardware"* para el control granular de recursos en Docker.
- **Async Threading y UI Segura (Fase 2):**
  - Todas las operaciones de fondo (descarga de modelos de 10GB+, logs de instalación) ya no bloquean el Hilo Principal; se utiliza un framework de callbacks `self.after(0)` sobre workers daemon.
  - El puente de terminal Aider CLI fue refactorizado para abstraerse en `DockerManager`, detectando los emuladores gráficos nativos del host antes de actuar.
  - Nuevo panel visual de *"Diagnóstico"* con validación asíncrona por ping (curl) inter-contenedor, probando redes `bridge` sin requerir scripts bash externos.
- **Daemon Automata "Génesis" Resiliente (Fase 3):**
  - **Shield Físico (Pre-flight Checks):** Evita la congelación/rotura de hosts Headless validando la presencia de pantalla/ratón antes de iniciar secuencias usando `pyautogui`.
  - **Network Retry-Loop:** Evita que el agente crashee abruptamente ante un timeout de Ollama o del Córtex; reintenta espaciadamente (backoff).
  - **Sandbox Testing:** Incorporación exitosa de `pytest-mock` para falsear controles del ratón y testear la lógica de Génesis sin mover periféricos físicos, apto para CI/CD.

---

## v1.0 — El Origen (Instalador Bash)

**Fecha:** Febrero 2026  
**Objetivo:** Instalar Ollama + Open WebUI con un solo comando.

### Archivos clave
- `install.sh` — Instalador bash interactivo

### Funcionalidades
- Detección automática de RAM y CPU
- Recomendación de modelo según hardware
- Generación de `.env` con optimizaciones de Ollama
- Instalación de Docker y Ollama
- Despliegue con `docker compose up -d`

### Código clave — Detección de hardware
```bash
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
TOTAL_RAM_GB=$((TOTAL_RAM_MB / 1024))
CPU_THREADS=$(nproc)
FREE_DISK_GB=$(df -BG /home | awk 'NR==2 {print $4}' | sed 's/G//')
```

### Código clave — Optimización Ollama

```bash
cat <<EOF > .env
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
OLLAMA_FLASH_ATTENTION=0
OLLAMA_KV_CACHE_TYPE=q4_0
OLLAMA_KEEP_ALIVE=1m
OLLAMA_CONTEXT_LENGTH=$CONTEXT_LEN
EOF
```

### Comandos

```bash
chmod +x install.sh && ./install.sh
docker compose ps
curl http://localhost:3000/health
```

---

## v2.0 — GUI + Memoria Persistente

**Objetivo:** Interfaz gráfica tkinter + memoria SQLite FTS5 + sistema de Sabores.

### Archivos nuevos

| Archivo | Función |
|---------|---------|
| `memex_gui.py` | GUI principal (tkinter) |
| `installer/` | Módulo de instalación Python |
| `src/memex_tools.py` | Herramientas de memoria (SQLite FTS5) |
| `src/prompt_injector_tool.py` | Inyección de prompts por contexto |
| `setup_memex.py` | Inyector de skills en Open WebUI DB |

### Funcionalidades

- GUI con detección de hardware, configuración, progreso
- Memoria persistente multi-usuario con FTS5
- Sistema de Sabores (Coder, Marketer, Researcher, Editor)
- Inyección automática de tools/filters en Open WebUI

### Código clave — Memoria FTS5

```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT DEFAULT 'default',
        title TEXT NOT NULL,
        type TEXT DEFAULT 'general',
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        content, content_id UNINDEXED,
        tokenize = "porter unicode61"
    )
''')
```

### Código clave — Inyección de skills

```python
cursor.execute("""
    INSERT INTO tool (id, user_id, name, content, specs, meta, updated_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (tool_id, admin_id, name, content, "[]", json.dumps(meta),
      int(time.time()), int(time.time())))
```

---

## v3.0 — Cerebro y Extremidades

**Objetivo:** Aider dockerizado, Router inteligente, Granular reinstaller, Tier system.

### Archivos nuevos/modificados

| Archivo | Cambio |
|---------|--------|
| `src/memex_router.py` | Router inteligente con 3 tiers |
| `src/skill_context_optimizer.py` | Compresión de contexto |
| `src/skill_evaluator.py` | LLM-as-Judge |
| `src/memex_sandbox.py` | Sandboxing |
| `memex_builder.sh` | Lanzador Aider dockerizado |
| `build.sh` | PyInstaller builder |
| `README.md` / `README.es.md` | Docs bilingüe |

### Funcionalidades

- **Router inteligente**: señales múltiples → modelo ligero/medio/pesado
- **Aider dockerizado**: `paulgauthier/aider` con profiles:cli
- **Tier system**: Chat (4GB) / RAG (8GB) / Apps (16GB)
- **Reinstalador granular**: `--force-recreate --no-deps`
- **Sincronizador de servicios**: upgrade a Nivel 3

### Código clave — Router scoring

```python
def _compute_complexity_score(self, message, messages):
    signals = {}
    signals["length"] = min(len(message) / 2000, 1.0)
    signals["history"] = min(len(messages) / 10, 1.0)
    signals["code"] = 1.0 if any(kw in message.lower()
        for kw in self._parse_keywords(self.valves.code_keywords)) else 0.0
    signals["tools"] = 1.0 if any(kw in message.lower()
        for kw in self._parse_keywords(self.valves.tool_keywords)) else 0.0
    score = (signals["length"]*0.3 + signals["history"]*0.2 +
             signals["code"]*0.3 + signals["tools"]*0.2)
    return {"score": score, "signals": signals}
```

### Código clave — Aider Docker

```yaml
aider:
  image: paulgauthier/aider
  container_name: memex-aider-cli
  profiles: ["cli"]
  environment:
    OLLAMA_API_BASE: http://ollama:11434
  volumes:
    - ./memex_workspace:/app
```

### Comandos

```bash
chmod +x build.sh && ./build.sh        # Binario Linux
./memex_builder.sh                      # Lanzar Aider
docker compose up -d --force-recreate --no-deps open-webui  # Reinstalar servicio
```

---

## v4.0 — Sistema Operativo Cognitivo Autónomo

**Objetivo:** Gobernanza de memoria + Observabilidad industrial.

### Principios

1. Memory is a liability unless governed
2. Tokens are currency
3. RAM is oxygen
4. Autonomy must be observable
5. Modularidad > Monolito

---

### 🟢 Fase 1 — Memory Governance Engine

#### Archivos nuevos

| Archivo | Función |
|---------|---------|
| `src/memory_governor.py` | WAL, scoring, entropy, archive, log rotation |
| `src/memory_governance_skill.py` | Skill: gc_memories, health_report |

#### `memex_tools.py` → v8.0.0

- +3 columnas: `importance_score`, `access_count`, `last_accessed`
- +3 índices: `idx_importance`, `idx_last_accessed`, `idx_type`
- `save_memory()` → calcula score inicial con `MEMORY_TYPE_WEIGHT`
- `search_memory()` → incrementa access_count
- `run_governance_cycle()` → wrapper del Governor

#### Fórmula de Scoring (Normalizada)

```python
MAX_EXPECTED_ACCESS = 100
LAMBDA_DECAY = 0.1
MEMORY_TYPE_WEIGHT = {
    "decision": 1.5, "rule": 1.3, "plan": 1.2, "lesson": 1.1,
    "general": 1.0, "note": 0.8, "log": 0.5,
}

def calculate_score(self, memory):
    base = self.MEMORY_TYPE_WEIGHT.get(memory["type"], 1.0)
    normalized_access = log(memory["access_count"] + 1) / log(101)
    recency_factor = exp(-0.1 * days_since_access)
    return base * recency_factor * normalized_access
# Score ∈ [0, WEIGHT], decay suave, no explosión logarítmica
```

#### Entropy Accionable (log2)

```python
def memory_entropy(self, conn):
    # -Σ(p_i × log2(p_i)) — log2 para threshold 2.0 alcanzable (max teórico ~2.8)
    if total < 50: return None  # Skip ruido estadístico
    entropy = -sum((p) * log2(p) for p in proportions if p > 0)
    return entropy  # > 2.0 → trigger compact()
```

#### Ciclo Atómico WAL

```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("BEGIN")
try:
    self._recalculate_scores(conn)
    self._archive_low_scored(conn)  # score < 0.1 → memory_archive
    entropy = self.memory_entropy(conn)
    if entropy and entropy > 2.0: self._compact(conn)
    conn.commit()
except:
    conn.rollback(); raise
```

#### Schema Migration

```sql
ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN last_accessed TEXT;
CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance_score);
CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed);
CREATE INDEX IF NOT EXISTS idx_type ON memories(type);
```

#### Log Rotation (100MB, max 5 backups)

```python
LOG_MAX_BYTES = 100 * 1024 * 1024
MAX_ROTATED_FILES = 5
# gzip + cleanup de archivos más antiguos
```

---

### 🟡 Fase 2 — Observability Industrial

#### Archivos nuevos

| Archivo | Función |
|---------|---------|
| `observability/docker-compose.observability.yml` | Prometheus + Grafana + Exporter |
| `observability/prometheus.yml` | Scrape cada 10s |
| `observability/datasources.yml` | Auto-provision Prometheus |
| `observability/memex_exporter.py` | Custom HTTP :9091 |
| `observability/Dockerfile` | python:3.11-slim |
| `observability/dashboards/memex.json` | 9 paneles |
| `observability/dashboards/dashboards.yml` | Auto-load |

#### Decisión Crítica

```
❌ memex_tokens_total{request_id="abc"}  → ROMPE Prometheus (alta cardinalidad)
✅ memex_tokens_total{model="deepseek"}  → Agregado, correcto
   request_id → SOLO en memex_traces.jsonl
```

#### Métricas (:9091/metrics)

```
memex_memory_total                        memex_router_requests_total
memex_memory_count{type="decision"}       memex_router_misprediction_rate
memex_memory_archived_total               memex_router_avg_confidence
memex_memory_avg_importance_score         memex_router_tier_requests{tier="heavy"}
memex_memory_entropy_score                memex_tokens_total{model="deepseek"}
memex_governance_cycle_duration_seconds   memex_governance_purge_total
```

#### Dashboard Grafana (9 Paneles)

| Panel | Thresholds |
|-------|-----------|
| Memorias Activas | 🟢<1k 🟡<10k 🔴>10k |
| Entropy | 🟢<1.5 🟡<2.0 🔴>2.0 |
| Governance Duration | 🟢<1s 🟡<2s 🔴>2s |
| Misprediction Rate | 🟢<10% 🟡<15% 🔴>15% |

#### Comandos

```bash
# Stack + Observabilidad
docker compose -f docker-compose.yml \
  -f observability/docker-compose.observability.yml up -d

# Verificar
curl http://localhost:9091/metrics        # Exporter
curl http://localhost:9090/api/v1/targets  # Prometheus
xdg-open http://localhost:3001            # Grafana (admin/memex2024)
```

---

### 🔒 Mutation Governance (Contrato v4.0)

| Parámetro | Quién modifica | Inmutable para |
|-----------|---------------|----------------|
| Router thresholds | Meta-Agent (±10%) | Todo lo demás |
| Decay factor (λ) | Manual only | Todos |
| Context reserve tokens | Static | Todos |
| MEMORY_TYPE_WEIGHT | Manual only | Todos |
| MAX_GRAPH_DEPTH | Static | Todos |

---

### 📊 KPIs v4.0

| KPI | Target |
|-----|--------|
| Governance cycle | < 2s / 10k mems |
| Entropy | < 2.0 |
| Misprediction rate | < 15% |
| Router P95 latency | < 5ms |
| Context overflows | 0 |
| Meta-Agent stability | > 0.8 |
| Purge rate | 5-20% / ciclo |

---

## Roadmap — Fases Pendientes para v5.0

| Fase | Componente | Descripción |
|------|-----------|-------------|
| 3 | Router v3 | Jerarquía 3 niveles, confidence fallback, context_budget_manager.py |
| 4 | Meta-Agent | Cooldown 30min, moving avg 50, variance threshold, MAX_ADJ/DAY=0.3 |
| 5 | Workspaces | SQLite aislado, Qdrant namespace, path traversal security |
| 6 | Knowledge Graph | SQLite adjacency list, MAX_DEPTH=4, auto-git registro |

---

## Inventario Completo

```
Memexicanisimos/
├── memex_gui.py                    # GUI principal
├── setup_memex.py                  # Inyector de skills
├── install.sh                      # Instalador bash
├── build.sh                        # PyInstaller (v3.0)
├── memex_builder.sh                # Lanzador Aider
├── docker-compose.yml              # Stack principal
├── .env / .gitignore / LICENSE
├── README.md / README.es.md / CHANGELOG.md
├── installer/
│   ├── config.py                   # Generador dinámico compose
│   ├── hardware.py / docker_utils.py / installer_core.py
│   ├── uninstaller.py / logger.py / memory_tools.py
│   └── ui/ (welcome, hardware, config, progress, result)
├── src/
│   ├── memex_tools.py              # v8.0 — Memoria + Gobernanza
│   ├── memex_router.py             # v2.0 — Router inteligente
│   ├── memory_governor.py          # v1.0 — Gobernanza WAL
│   ├── memory_governance_skill.py
│   ├── prompt_injector_tool.py / skill_context_optimizer.py
│   ├── skill_evaluator.py / memex_sandbox.py
├── observability/
│   ├── docker-compose.observability.yml
│   ├── prometheus.yml / datasources.yml
│   ├── memex_exporter.py / Dockerfile
│   └── dashboards/ (dashboards.yml, memex.json)
├── daemon/
└── memex_workspace/
```

## Comandos de Referencia Rápida

```bash
# Instalación
python3 memex_gui.py                # GUI
./install.sh                        # Bash

# Despliegue
docker compose up -d                # Básico
docker compose -f docker-compose.yml -f observability/docker-compose.observability.yml up -d

# Aider
./memex_builder.sh

# Gestión
docker compose ps
docker compose logs -f open-webui
docker compose down --remove-orphans

# Gobernanza (manual)
docker compose exec open-webui python -c "
from memex_tools import Tools; t = Tools()
print(t.run_governance_cycle())
"

# Métricas
curl http://localhost:9091/metrics

# Build
./build.sh && ./dist/MemexicanisimosOS

# Git
git add -A && git commit -m "mensaje" && git push origin main
```
