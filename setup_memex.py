import sqlite3
import json
import time
import os
import sys
import uuid
import requests
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_PATH = "/app/backend/data/webui.db"
MEMEX_TOOL_PATH = "/app/backend/memex_tools.py"
PROMPT_INJECTOR_PATH = "/app/backend/prompt_injector_tool.py"
ROUTER_FILTER_PATH = "/app/backend/memex_router.py"
SANDBOX_FILTER_PATH = "/app/backend/memex_sandbox.py"
CONTEXT_OPTIMIZER_PATH = "/app/backend/skill_context_optimizer.py"
EVALUATOR_TOOL_PATH = "/app/backend/skill_evaluator.py"
GOVERNANCE_TOOL_PATH = "/app/backend/memory_governance_skill.py"
API_BASE_URL = "http://localhost:8080"
ERROR_LOG_PATH = "/app/backend/data/workspace/memex_errors.txt"

def log_error(context: str, error_msg: str):
    """Guarda los errores en un archivo de bitácora para su posterior análisis."""
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] SETUP ERROR en {context}: {error_msg}\n")
    except Exception:
        pass

def wait_for_api():
    """Espera a que la API de Open WebUI esté disponible."""
    retries = 30
    print("Esperando a que la API de Open WebUI esté saludable...")
    while retries > 0:
        try:
            r = requests.get(f"{API_BASE_URL}/health")
            if r.status_code == 200:
                print("API lista.")
                return True
        except requests.exceptions.ConnectionError as e:
            log_error("wait_for_api", f"Intento fallido: {str(e)}")
            pass
        except Exception as e:
            log_error("wait_for_api exceptions", str(e))
        time.sleep(2)
        retries -= 1
    log_error("wait_for_api", "Tiempo de espera agotado para la API de Open WebUI")
    print("Tiempo de espera agotado para la API.")
    return False

def get_or_create_admin_user():
    """
    Obtiene el ID del primer usuario administrador.
    Si no existe ningún usuario, crea uno por defecto (admin@memex.local / admin123).
    Retorna el ID del usuario administrador.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            conn.close()
            error_m = "La tabla 'user' no existe. La base de datos no está inicializada."
            log_error("get_or_create_admin_user", error_m)
            raise Exception(error_m)

        cursor.execute("SELECT id, email FROM user WHERE role = 'admin' ORDER BY created_at LIMIT 1")
        admin = cursor.fetchone()

        if admin:
            admin_id = admin[0]
            print(f"Usuario administrador existente encontrado: ID {admin_id}")
        else:
            print("No se encontró ningún administrador. Creando usuario por defecto: admin@memex.local / admin123")
            hashed = pwd_context.hash("admin123")
            admin_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user (id, name, email, password, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (admin_id, "Administrador", "admin@memex.local", hashed, "admin", int(time.time()), int(time.time())))
            conn.commit()
            print(f"Usuario administrador creado con ID {admin_id}")

        conn.close()
        return admin_id
    except Exception as e:
        log_error("get_or_create_admin_user", str(e))
        raise

def inject_memex_tool(admin_id):
    """Lee el código de memex_tools.py y lo inyecta en la tabla de tools de Open WebUI."""
    if not os.path.exists(MEMEX_TOOL_PATH):
        error_m = f"Error: No se encontró {MEMEX_TOOL_PATH}"
        log_error("inject_memex_tool", error_m)
        print(error_m)
        return

    with open(MEMEX_TOOL_PATH, "r", encoding="utf-8") as f:
        tool_content = f.read()

    meta = {
        "title": "Memex Advanced Tools",
        "author": "Memexicanisimos Team",
        "version": "7.0.0",
        "description": "Memoria persistente, orquestación de agentes, análisis de código, git, tareas y más."
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM tool WHERE id = 'memex'")
        if cursor.fetchone():
            print("La herramienta Memex ya está instalada en la BD. Actualizando...")
            cursor.execute("UPDATE tool SET content = ?, meta = ? WHERE id = 'memex'", 
                           (tool_content, json.dumps(meta)))
        else:
            print("Inyectando herramienta Memex en la BD...")
            cursor.execute("""
                INSERT INTO tool (id, user_id, name, content, specs, meta, updated_at, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "memex", 
                admin_id,
                "Memex Tools", 
                tool_content, 
                "[]", 
                json.dumps(meta),
                int(time.time()),
                int(time.time())
            ))

        conn.commit()
        conn.close()
    except Exception as e:
        log_error("inject_memex_tool", str(e))
        print(f"Error inyectando herramienta: {e}")

def inject_prompt_injector_tool(admin_id):
    """Lee el código de prompt_injector_tool.py y lo inyecta en la tabla de tools de Open WebUI."""
    if not os.path.exists(PROMPT_INJECTOR_PATH):
        error_m = f"Aviso: No se encontró {PROMPT_INJECTOR_PATH}. Omitiendo inyección del Prompt Injector."
        log_error("inject_prompt_injector_tool", error_m)
        print(error_m)
        return

    with open(PROMPT_INJECTOR_PATH, "r", encoding="utf-8") as f:
        tool_content = f.read()

    meta = {
        "title": "Memex Prompt Injector & Architect",
        "author": "Memexicanisimos Team",
        "version": "1.0.0",
        "description": "Genera System Prompts optimizados para nuevos agentes con integración de herramientas Memex."
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM tool WHERE id = 'memex-prompt-injector'")
        if cursor.fetchone():
            print("El Prompt Injector ya está instalado. Actualizando...")
            cursor.execute("UPDATE tool SET content = ?, meta = ? WHERE id = 'memex-prompt-injector'",
                           (tool_content, json.dumps(meta)))
        else:
            print("Inyectando Prompt Injector en la BD...")
            cursor.execute("""
                INSERT INTO tool (id, user_id, name, content, specs, meta, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "memex-prompt-injector",
                admin_id,
                "Memex Prompt Injector",
                tool_content,
                "[]",
                json.dumps(meta),
                int(time.time()),
                int(time.time())
            ))

        conn.commit()
        conn.close()
        print("Prompt Injector inyectado correctamente.")
    except Exception as e:
        log_error("inject_prompt_injector_tool", str(e))
        print(f"Error inyectando Prompt Injector: {e}")

def inject_router_filter(admin_id):
    """Inyecta el Auto-Router (Filter) en la tabla de tools/functions de Open WebUI."""
    if not os.path.exists(ROUTER_FILTER_PATH):
        error_m = f"Aviso: No se encontró {ROUTER_FILTER_PATH}. Omitiendo inyección del Router."
        log_error("inject_router_filter", error_m)
        print(error_m)
        return

    with open(ROUTER_FILTER_PATH, "r", encoding="utf-8") as f:
        filter_content = f.read()

    meta = {
        "title": "Memex Auto-Router v2.0 (Orchestrator)",
        "author": "Memexicanisimos Team",
        "version": "2.0.0",
        "description": "Enrutamiento dinámico multi-señal con 3 tiers, semáforo de concurrencia y telemetría."
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Open WebUI almacena filters en la tabla 'function'
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='function'")
        if cursor.fetchone():
            cursor.execute("SELECT id FROM function WHERE id = 'memex-router'")
            if cursor.fetchone():
                print("El Auto-Router ya existe. Actualizando...")
                cursor.execute("UPDATE function SET content = ?, meta = ? WHERE id = 'memex-router'",
                               (filter_content, json.dumps(meta)))
            else:
                print("Inyectando Auto-Router (Filter)...")
                cursor.execute("""
                    INSERT INTO function (id, user_id, name, type, content, meta, is_active, is_global, updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "memex-router",
                    admin_id,
                    "Memex Auto-Router",
                    "filter",
                    filter_content,
                    json.dumps(meta),
                    1,  # is_active
                    1,  # is_global (aplica a todos los modelos)
                    int(time.time()),
                    int(time.time())
                ))
        else:
            print("Tabla 'function' no existe aún. El Router se inyectará tras la primera carga de Open WebUI.")

        conn.commit()
        conn.close()
        print("Auto-Router inyectado correctamente.")
    except Exception as e:
        log_error("inject_router_filter", str(e))
        print(f"Error inyectando Router: {e}")

def inject_sandbox_filter(admin_id):
    """Inyecta el Sandbox Guard (Filter) en la tabla de functions de Open WebUI."""
    if not os.path.exists(SANDBOX_FILTER_PATH):
        error_m = f"Aviso: No se encontró {SANDBOX_FILTER_PATH}. Omitiendo inyección del Sandbox."
        log_error("inject_sandbox_filter", error_m)
        print(error_m)
        return

    with open(SANDBOX_FILTER_PATH, "r", encoding="utf-8") as f:
        filter_content = f.read()

    meta = {
        "title": "Memex Pyodide Sandbox Guard",
        "author": "Memexicanisimos Team",
        "version": "1.0.0",
        "description": "Guardia de seguridad que detecta código peligroso antes de ejecutarse en Pyodide."
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='function'")
        if cursor.fetchone():
            cursor.execute("SELECT id FROM function WHERE id = 'memex-sandbox'")
            if cursor.fetchone():
                print("El Sandbox Guard ya existe. Actualizando...")
                cursor.execute("UPDATE function SET content = ?, meta = ? WHERE id = 'memex-sandbox'",
                               (filter_content, json.dumps(meta)))
            else:
                print("Inyectando Sandbox Guard (Filter)...")
                cursor.execute("""
                    INSERT INTO function (id, user_id, name, type, content, meta, is_active, is_global, updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "memex-sandbox",
                    admin_id,
                    "Memex Sandbox Guard",
                    "filter",
                    filter_content,
                    json.dumps(meta),
                    1,  # is_active
                    1,  # is_global
                    int(time.time()),
                    int(time.time())
                ))
        else:
            print("Tabla 'function' no existe aún. El Sandbox se inyectará tras la primera carga.")

        conn.commit()
        conn.close()
        print("Sandbox Guard inyectado correctamente.")
    except Exception as e:
        log_error("inject_sandbox_filter", str(e))
        print(f"Error inyectando Sandbox: {e}")

def inject_context_optimizer(admin_id):
    """Inyecta el Context Optimizer (Filter) en la tabla de functions de Open WebUI."""
    if not os.path.exists(CONTEXT_OPTIMIZER_PATH):
        print("⚠️ skill_context_optimizer.py no encontrado. Omitiendo.")
        return
    with open(CONTEXT_OPTIMIZER_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    meta = {
        "title": "Memex Context Optimizer (Skill)",
        "author": "Memexicanisimos Team",
        "version": "1.0.0",
        "description": "Comprime historial para evitar 'lost-in-the-middle' y reducir RAM."
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM function WHERE id = 'memex-context-optimizer'")
        if cursor.fetchone():
            print("El Context Optimizer ya existe. Actualizando...")
            cursor.execute("UPDATE function SET content = ?, meta = ? WHERE id = 'memex-context-optimizer'",
                           (content, json.dumps(meta)))
        else:
            print("Inyectando Context Optimizer (Filter)...")
            cursor.execute("""
                INSERT INTO function (id, user_id, name, type, content, meta, is_active, is_global, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "memex-context-optimizer", admin_id, "Memex Context Optimizer", "filter",
                content, json.dumps(meta), 1, 1, int(time.time()), int(time.time())
            ))
        conn.commit()
        conn.close()
        print("✅ Context Optimizer inyectado.")
    except Exception as e:
        log_error("inject_context_optimizer", str(e))
        print(f"Error inyectando Context Optimizer: {e}")

def inject_evaluator_tool(admin_id):
    """Inyecta la herramienta Evaluator (LLM-as-Judge) en la tabla de tools de Open WebUI."""
    if not os.path.exists(EVALUATOR_TOOL_PATH):
        print("⚠️ skill_evaluator.py no encontrado. Omitiendo.")
        return
    with open(EVALUATOR_TOOL_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    meta = {
        "title": "Memex LLM-as-Judge (Skill)",
        "author": "Memexicanisimos Team",
        "version": "1.0.0",
        "description": "Evalúa código o texto usando un modelo juez y criterios personalizados."
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tool WHERE id = 'memex-evaluator'")
        if cursor.fetchone():
            print("El Evaluator ya existe. Actualizando...")
            cursor.execute("UPDATE tool SET content = ?, meta = ? WHERE id = 'memex-evaluator'",
                           (content, json.dumps(meta)))
        else:
            print("Inyectando Evaluator Tool...")
            cursor.execute("""
                INSERT INTO tool (id, user_id, name, content, specs, meta, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "memex-evaluator", admin_id, "Memex Evaluator",
                content, "[]", json.dumps(meta),
                int(time.time()), int(time.time())
            ))
        conn.commit()
        conn.close()
        print("✅ Evaluator Tool inyectada.")
    except Exception as e:
        log_error("inject_evaluator_tool", str(e))
        print(f"Error inyectando Evaluator: {e}")

def inject_governance_tool(admin_id):
    """Inyecta la herramienta de Gobernanza de Memoria en Open WebUI."""
    if not os.path.exists(GOVERNANCE_TOOL_PATH):
        print("⚠️ memory_governance_skill.py no encontrado. Omitiendo.")
        return
    with open(GOVERNANCE_TOOL_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    meta = {
        "title": "Memex Memory Governance",
        "author": "Memexicanisimos Team",
        "version": "1.0.0",
        "description": "Gobernanza inteligente de memoria: ciclo de limpieza, reporte de salud, entropy."
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tool WHERE id = 'memex-governance'")
        if cursor.fetchone():
            print("El Governance Tool ya existe. Actualizando...")
            cursor.execute("UPDATE tool SET content = ?, meta = ? WHERE id = 'memex-governance'",
                           (content, json.dumps(meta)))
        else:
            print("Inyectando Memory Governance Tool...")
            cursor.execute("""
                INSERT INTO tool (id, user_id, name, content, specs, meta, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "memex-governance", admin_id, "Memex Governance",
                content, "[]", json.dumps(meta),
                int(time.time()), int(time.time())
            ))
        conn.commit()
        conn.close()
        print("✅ Memory Governance Tool inyectada.")
    except Exception as e:
        log_error("inject_governance_tool", str(e))
        print(f"Error inyectando Governance Tool: {e}")

def inject_flavors(admin_id, config_path='/app/backend/data/workspace/flavors_config.json'):
    """Inyecta modelos personalizados (Sabores) en la tabla 'model' con los nuevos system prompts."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            models_config = config.get("models", {})
    except Exception as e:
        log_error("inject_flavors_config", str(e))
        models_config = {}  # fallback

    flavors = [
        {
            "id": "memex-coder",
            "name": "Memex Coder",
            "base_model": models_config.get("memex-coder", "deepseek-r1:7b"),
            "params": {
                "temperature": 0.2,
                "top_p": 0.95,
                "max_tokens": 2048,
                "system": "Eres un ingeniero de software experto con memoria persistente. Dispones de las siguientes herramientas:\n- save_memory(title, content, tags, memory_type): guarda hechos, planes o lecciones.\n- search_memory(query, limit, memory_type): busca en la memoria por palabras clave.\n- get_memory_by_id(id): recupera una memoria completa.\n- list_recent_memories(limit, memory_type): lista memorias recientes.\n- delete_memory(id): elimina una memoria.\n- write_plan(plan_content, title): guarda un plan estructurado.\n- add_lesson(lesson, context): guarda una lección aprendida.\n- search_lessons(query, limit): busca lecciones relevantes.\n- run_subagent(task_description, model): ejecuta una subtarea en un contexto limpio.\n- run_command(command): ejecuta un comando del sistema (lista blanca: pytest, npm test, etc.).\n- write_file(path, content, overwrite): escribe archivos en el workspace.\n- write_markdown_doc(title, content, tags, path): genera documentos markdown con frontmatter.\n- generate_code_file(language, specification, path): genera código según especificación y lo guarda.\n- create_project_structure(project_type, name): crea proyectos base (python-basic, fastapi, react, node-express).\n- read_external_file(path): lee archivos de proyectos externos (solo lectura).\n\nDebes seguir estas reglas de trabajo autónomo:\n1. **Planificación**: Para tareas con más de 3 pasos o decisiones arquitectónicas, escribe un plan detallado con `write_plan`.\n2. **Verificación**: Antes de dar una tarea por terminada, ejecuta pruebas con `run_command` que demuestren su funcionamiento.\n3. **Lecciones aprendidas**: Cuando recibas una corrección del usuario, usa `add_lesson` para registrar la lección y no repetir el error.\n4. **Elegancia**: Para cambios no triviales, pregúntate si hay una forma más elegante. Si la solución es un parche, propón una mejor.\n5. **Subagentes**: Para tareas complejas, divídelas en subtareas y usa `run_subagent` para cada una.\n\nAl iniciar una sesión, busca lecciones relevantes con `search_lessons(query=\"lección\")` y tenlas en cuenta.\n\nIMPORTANTE: No incluyas etiquetas <think> ni ningún tipo de razonamiento interno en tu respuesta final. Responde siempre de forma directa y en español."
            }
        },
        {
            "id": "memex-marketer",
            "name": "Memex Marketer",
            "base_model": models_config.get("memex-marketer", "llama3.2:3b"),
            "params": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 1024,
                "system": "Eres un experto en marketing y redacción publicitaria con memoria persistente. Tus herramientas:\n- save_memory, search_memory, get_memory_by_id, list_recent_memories, delete_memory.\n- write_plan, add_lesson, search_lessons, run_subagent, run_command.\n\nReglas:\n- Cuando el usuario describa su audiencia, tono o valores de marca, guárdalo con `save_memory` (tipo 'marca').\n- Antes de redactar un nuevo copy, busca en la memoria con `search_memory` palabras como 'voz de marca'.\n- Si encuentras una memoria con detalles de la marca, úsala.\n- Al finalizar, sugiere guardar el nuevo copy como ejemplo con `save_memory`.\n- Si el usuario te corrige, usa `add_lesson` para aprender.\n- Para análisis de mercado complejos, usa `run_subagent` para explorar tendencias.\n\nIMPORTANTE: No incluyas etiquetas <think> ni ningún tipo de razonamiento interno en tu respuesta final. Responde siempre de forma directa y en español."
            }
        },
        {
            "id": "memex-researcher",
            "name": "Memex Researcher",
            "base_model": models_config.get("memex-researcher", "deepseek-r1:7b"),
            "params": {
                "temperature": 0.3,
                "max_tokens": 2048,
                "system": "Eres un analista de datos e investigador con memoria persistente. Herramientas disponibles:\n- save_memory, search_memory, get_memory_by_id, list_recent_memories, delete_memory.\n- write_plan, add_lesson, search_lessons, run_subagent, run_command.\n- write_markdown_doc(title, content, tags, path): genera documentos markdown con frontmatter.\n- read_external_file(path): lee archivos de proyectos externos (solo lectura).\n- index_project(project_path): indexa un proyecto para búsqueda semántica en Qdrant.\n- semantic_search(query, limit): busca fragmentos relevantes en proyectos indexados.\n\nProtocolo:\n1. Cuando recibas un documento largo, identifica entidades clave y guárdalas con `save_memory` (tipo 'entidad').\n2. Si el usuario pregunta sobre un tema, busca en la memoria con `search_memory`.\n3. Si encuentras múltiples memorias sobre el mismo tema, resúmelas en una nueva memoria.\n4. Usa `run_subagent` para tareas de extracción paralelas.\n5. Registra lecciones con `add_lesson` cuando descubras patrones.\n6. Para documentar hallazgos, usa `write_markdown_doc` para generar reportes con frontmatter.\n7. Para buscar en proyectos indexados, usa `semantic_search`.\n\nIMPORTANTE: No incluyas etiquetas <think> ni ningún tipo de razonamiento interno en tu respuesta final. Responde siempre de forma directa y en español."
            }
        },
        {
            "id": "memex-editor",
            "name": "Memex Editor",
            "base_model": models_config.get("memex-editor", "qwen2.5:1.5b"),
            "params": {
                "temperature": 0.1,
                "max_tokens": 512,
                "system": "Eres un corrector de estilo y traductor meticuloso con memoria persistente. Herramientas:\n- save_memory, search_memory, get_memory_by_id, list_recent_memories, delete_memory.\n- write_plan, add_lesson, search_lessons.\n\nMecánica:\n- Cuando el usuario indique una preferencia de estilo, guárdala con `save_memory` (tipo 'estilo').\n- Antes de corregir un texto, busca en la memoria si hay reglas aplicables con `search_memory`.\n- Si encuentras una regla, aplícala estrictamente.\n- Si el usuario te corrige, usa `add_lesson` para no repetir el error.\n\nIMPORTANTE: No incluyas etiquetas <think> ni ningún tipo de razonamiento interno en tu respuesta final. Responde siempre de forma directa y en español."
            }
        },
        {
            "id": "memex-auto",
            "name": "Memex Auto",
            "base_model": models_config.get("memex-auto", "qwen2.5:1.5b"),
            "params": {
                "temperature": 0.4,
                "max_tokens": 2048,
                "system": "Eres Memex Auto, un agente inteligente con enrutamiento dinámico. El sistema selecciona automáticamente el mejor modelo para cada tarea:\n- Consultas simples y saludos: modelo ultraligero.\n- Código, análisis y razonamiento: modelo pesado.\n\nTienes acceso a TODAS las herramientas de Memex:\n- Memoria persistente: save_memory, search_memory, list_recent_memories, delete_memory.\n- Planificación: write_plan, add_lesson, search_lessons.\n- Orquestación: run_subagent, run_command.\n- Análisis de código: analyze_code, generate_tests, generate_docstring.\n- Tareas: create_task, list_tasks.\n- Git: git_status, git_commit.\n- Red: fetch_url, summarize_text.\n- Escritura: write_file, write_markdown_doc, generate_code_file, create_project_structure.\n- Lectura externa: read_external_file (proyectos montados en solo lectura).\n- RAG: index_project (indexar proyecto en Qdrant), semantic_search (búsqueda semántica).\n\nReglas:\n1. Siempre busca en la memoria antes de responder con `search_memory`.\n2. Guarda hechos importantes con `save_memory`.\n3. Registra correcciones con `add_lesson`.\n4. Para crear archivos, usa `write_file` o `generate_code_file`. Para proyectos completos, usa `create_project_structure`.\n5. Para buscar en proyectos indexados, usa `semantic_search`.\n\nIMPORTANTE: No incluyas etiquetas <think> ni ningún tipo de razonamiento interno. Responde de forma directa y en español."
            }
        }
    ]

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for flavor in flavors:
            cursor.execute("SELECT id FROM model WHERE id = ?", (flavor["id"],))
            if cursor.fetchone():
                print(f"Sabor {flavor['name']} ya existe, actualizando...")
                meta = {
                    "profile_image_url": "/favicon.png",
                    "description": f"Sabor oficial de Memex. Usa {flavor['base_model']} con configuración óptima y herramientas inyectadas.",
                    "toolIds": ["memex", "memex-prompt-injector", "memex-evaluator"]
                }
                cursor.execute("""
                    UPDATE model SET params = ?, meta = ?, updated_at = ? WHERE id = ?
                """, (json.dumps(flavor["params"]), json.dumps(meta), int(time.time()), flavor["id"]))
                continue

            print(f"Inyectando Sabor: {flavor['name']}...")
            meta = {
                "profile_image_url": "/favicon.png",
                "description": f"Sabor oficial de Memex. Usa {flavor['base_model']} con configuración óptima y herramientas inyectadas.",
                "toolIds": ["memex", "memex-prompt-injector", "memex-evaluator"]
            }
            cursor.execute("""
                INSERT INTO model (id, user_id, base_model_id, name, params, meta, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flavor["id"],
                admin_id,
                flavor["base_model"],
                flavor["name"],
                json.dumps(flavor["params"]),
                json.dumps(meta),
                int(time.time()),
                int(time.time())
            ))

        conn.commit()
        conn.close()
    except Exception as e:
        log_error("inject_flavors", str(e))
        print(f"Error inyectando sabores: {e}")

if __name__ == "__main__":
    print("=== Iniciando Configuración Nativa de Memex ===")
    if not wait_for_api():
        err_msg = "=== Fallo: API no disponible ==="
        log_error("main", err_msg)
        print(err_msg)
        sys.exit(1)

    try:
        admin_id = get_or_create_admin_user()
        inject_memex_tool(admin_id)
        inject_prompt_injector_tool(admin_id)
        inject_router_filter(admin_id)
        inject_sandbox_filter(admin_id)
        inject_context_optimizer(admin_id)
        inject_evaluator_tool(admin_id)
        inject_governance_tool(admin_id)
        inject_flavors(admin_id)
        print("=== Configuración Nativa Completada ===")
    except Exception as e:
        err_msg = f"=== Error durante la configuración: {e} ==="
        log_error("main", err_msg)
        print(err_msg)
        sys.exit(1)
