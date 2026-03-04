"""
title: Memex Advanced Tools
author: Memexicanisimos Team
version: 8.0.0
description: |
  Herramientas de memoria persistente con aislamiento multi-usuario (__user__),
  orquestación de agentes, análisis de código, gestión de tareas,
  integración git, exportación/importación de memorias y más.
requirements: pydantic, requests
"""

import sqlite3
import os
import json
import subprocess
import requests
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        """Configuración opcional para la herramienta."""
        pass

    def __init__(self):
        self.valves = self.Valves()
        self.db_path = "/app/backend/data/memex_memory.db"
        self.workspace_path = "/app/backend/data/workspace"
        self.error_log_path = "/app/backend/data/workspace/memex_errors.txt"
        # Lista blanca ampliada con herramientas de análisis y git
        self.allowed_commands = [
            "pytest", "npm test", "go test", "ls", "cat", "head", "tail", "wc",
            "git status", "git diff", "git log", "git add", "git commit", "git push", "git pull",
            "pylint", "flake8", "mypy", "bandit", "pyflakes", "black", "isort",
        ]
        self.ollama_url = "http://ollama:11434"  # Nombre del servicio en docker-compose
        self._init_db()

    # ==================== Internos ====================

    def _log_error(self, context: str, error_msg: str):
        """Guarda los errores en un archivo de bitácora para su posterior análisis."""
        try:
            os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.error_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] TOOL ERROR en {context}: {error_msg}\n")
        except Exception:
            pass

    def _init_db(self):
        """Inicializa las tablas SQLite y el índice FTS5."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    title TEXT NOT NULL,
                    type TEXT DEFAULT 'general',
                    tags TEXT,
                    importance_score REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Migrar tablas existentes: añadir columnas si no existen
            migrations = [
                "ALTER TABLE memories ADD COLUMN user_id TEXT DEFAULT 'default'",
                "ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.5",
                "ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0",
                "ALTER TABLE memories ADD COLUMN last_accessed TEXT",
            ]
            for sql in migrations:
                try:
                    cursor.execute(sql)
                except Exception:
                    pass  # La columna ya existe
            # Índices para governance (evitar full table scans)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    content_id UNINDEXED,
                    tokenize = "porter unicode61"
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            self._log_error("_init_db", str(e))
            print(f"Error inicializando base de datos: {e}")

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _get_user_id(__user__=None) -> str:
        """Extrae el ID de usuario del parámetro __user__ de Open WebUI."""
        if __user__ and isinstance(__user__, dict):
            return __user__.get("id", __user__.get("email", "default"))
        return "default"

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Retorna el array estandarizado de Function Calling (Tools) compatible con
        el endpoint /api/chat de Ollama.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "Guarda una nueva memoria a largo plazo en la base de datos vectorial del Córtex.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título descriptivo de la memoria."},
                            "content": {"type": "string", "description": "El contenido detallado a recordar."},
                            "tags": {"type": "string", "description": "Etiquetas separadas por comas (ej. 'plan, backend')."},
                            "memory_type": {"type": "string", "description": "Clasificación: general, plan, lesson, decision, rule, entidad."}
                        },
                        "required": ["title", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memory",
                    "description": "Busca en la memoria a largo plazo usando palabras clave.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Las palabras clave a buscar."},
                            "limit": {"type": "integer", "description": "Cantidad máxima de resultados."},
                            "memory_type": {"type": "string", "description": "Filtrar por tipo (ej. lesson, plan)."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Ejecuta un comando en la terminal del workspace (Ej: ls, cat, pytest, git status).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Comando a ejecutar."},
                            "cwd": {"type": "string", "description": "Directorio de trabajo (opcional, usa workspace si está vacío)."}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Crea o sobrescribe un archivo en el workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Ruta relativa al workspace (ej. 'src/app.py')."},
                            "content": {"type": "string", "description": "Contenido exacto del archivo."},
                            "overwrite": {"type": "boolean", "description": "True para sobrescribir archivos existentes."}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_url",
                    "description": "Realiza un GET a una URL (HTTP/HTTPS) y extrae su texto. Útil para navegar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL completa a visitar."}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "Crea una nueva tarea en el archivo TODO.md del proyecto.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título de la tarea."},
                            "description": {"type": "string", "description": "Detalles adicionales (opcional)."},
                            "priority": {"type": "string", "description": "Prioridad: alta, media, baja."}
                        },
                        "required": ["title"]
                    }
                }
            }
        ]

    # ==================== Herramientas de memoria básicas ====================


    def save_memory(self, title: str, content: str, tags: str = "", memory_type: str = "general", __user__: dict = None) -> str:
        """
        Guarda una nueva memoria con tipo específico. Cada usuario tiene su propio espacio.
        Tipos comunes: general, plan, lesson, decision, rule, entidad, marca, estilo.
        Calcula importance_score inicial basado en tipo y longitud.
        """
        if not title.strip() or not content.strip():
            return "Error: El título y el contenido no pueden estar vacíos."
        uid = self._get_user_id(__user__)

        # Scoring inicial basado en tipo (MEMORY_TYPE_WEIGHT) y longitud
        MEMORY_TYPE_WEIGHT = {
            "decision": 1.5, "rule": 1.3, "plan": 1.2, "lesson": 1.1,
            "general": 1.0, "entidad": 1.0, "marca": 0.9, "estilo": 0.9,
            "note": 0.8, "log": 0.5,
        }
        base_weight = MEMORY_TYPE_WEIGHT.get(memory_type, 1.0)
        length_bonus = min(len(content.strip()) / 1000, 0.3)
        initial_score = min(base_weight * 0.5 + length_bonus, base_weight)
        now_iso = datetime.now().isoformat()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (user_id, title, type, tags, importance_score, access_count, last_accessed) "
                "VALUES (?, ?, ?, ?, ?, 0, ?)",
                (uid, title.strip(), memory_type, tags.strip(), initial_score, now_iso)
            )
            memory_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO memories_fts (rowid, content, content_id) VALUES (?, ?, ?)",
                (memory_id, content.strip(), memory_id)
            )
            conn.commit()
            conn.close()
            return f"✅ Memoria guardada: '{title}' (ID: {memory_id}, tipo: {memory_type}, score: {initial_score:.2f})"
        except Exception as e:
            self._log_error("save_memory", str(e))
            return f"❌ Error al guardar memoria: {str(e)}"

    def search_memory(self, query: str, limit: int = 5, memory_type: Optional[str] = None, __user__: dict = None) -> str:
        """
        Busca memorias por palabras clave usando FTS5. Solo devuelve memorias del usuario actual.
        Actualiza access_count y last_accessed para gobernanza.
        """
        if not query.strip():
            return "Error: La consulta no puede estar vacía."
        uid = self._get_user_id(__user__)
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sanitized = query.replace('"', ' ').strip()
            sql = '''
                SELECT m.id, m.title, m.type, m.tags, m.created_at, f.content
                FROM memories_fts f
                JOIN memories m ON f.content_id = m.id
                WHERE memories_fts MATCH ? AND m.user_id = ?
            '''
            params = [sanitized, uid]
            if memory_type:
                sql += " AND m.type = ?"
                params.append(memory_type)
            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            # Governance: incrementar access_count y actualizar last_accessed
            now_iso = datetime.now().isoformat()
            for r in rows:
                cursor.execute(
                    "UPDATE memories SET access_count = access_count + 1, "
                    "last_accessed = ? WHERE id = ?",
                    (now_iso, r[0])
                )
            conn.commit()
            conn.close()
            if not rows:
                return f"No se encontraron memorias para: '{query}'."
            results = []
            for r in rows:
                results.append({
                    "id": r[0], "title": r[1], "type": r[2],
                    "tags": r[3], "date": r[4],
                    "content": r[5][:200] + "..." if len(r[5]) > 200 else r[5]
                })
            return json.dumps(results, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_error("search_memory", str(e))
            return f"Error en búsqueda: {str(e)}"

    def get_memory_by_id(self, memory_id: int) -> str:
        """Recupera una memoria completa por ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.id, m.title, m.type, m.tags, m.created_at, f.content
                FROM memories m
                LEFT JOIN memories_fts f ON m.id = f.content_id
                WHERE m.id = ?
            ''', (memory_id,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return f"No existe memoria con ID {memory_id}."
            result = {
                "id": row[0], "title": row[1], "type": row[2],
                "tags": row[3], "date": row[4],
                "content": row[5] if row[5] else ""
            }
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_error(f"get_memory_by_id({memory_id})", str(e))
            return f"Error al recuperar memoria: {str(e)}"

    def list_recent_memories(self, limit: int = 10, memory_type: Optional[str] = None, __user__: dict = None) -> str:
        """Lista memorias recientes del usuario actual, opcionalmente filtradas por tipo."""
        uid = self._get_user_id(__user__)
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "SELECT id, title, type, tags, created_at FROM memories WHERE user_id = ?"
            params = [uid]
            if memory_type:
                sql += " AND type = ?"
                params.append(memory_type)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return "No hay memorias almacenadas."
            results = [{"id": r[0], "title": r[1], "type": r[2], "tags": r[3], "date": r[4]} for r in rows]
            return json.dumps(results, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_error("list_recent_memories", str(e))
            return f"Error al listar memorias: {str(e)}"

    def delete_memory(self, memory_id: int) -> str:
        """Elimina una memoria por ID (irreversible)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
            if not cursor.fetchone():
                conn.close()
                return f"No se encontró memoria con ID {memory_id}."
            cursor.execute("DELETE FROM memories_fts WHERE content_id = ?", (memory_id,))
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            conn.close()
            return f"✅ Memoria con ID {memory_id} eliminada permanentemente."
        except Exception as e:
            self._log_error(f"delete_memory({memory_id})", str(e))
            return f"Error al eliminar memoria: {str(e)}"

    # ==================== Herramientas de orquestación ====================

    def write_plan(self, plan_content: str, title: Optional[str] = None) -> str:
        """Guarda un plan estructurado en la memoria."""
        if not plan_content.strip():
            return "Error: El plan no puede estar vacío."
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        plan_title = title if title else f"Plan {timestamp}"
        return self.save_memory(plan_title, plan_content, tags="plan", memory_type="plan")

    def add_lesson(self, lesson: str, context: str = "") -> str:
        """Guarda una lección aprendida para no repetir errores."""
        if not lesson.strip():
            return "Error: La lección no puede estar vacía."
        content = f"Lección: {lesson}\nContexto: {context}"
        return self.save_memory("Lección: " + lesson[:50], content, tags="lección, mejora", memory_type="lesson")

    def search_lessons(self, query: str, limit: int = 5) -> str:
        """Busca lecciones aprendidas relevantes."""
        return self.search_memory(query, limit, memory_type="lesson")

    def run_subagent(self, task_description: str, model: str = "deepseek-r1:7b", json_schema: Optional[Dict[str, Any]] = None) -> str:
        """Ejecuta una subtarea en un contexto limpio llamando al modelo a través de Ollama. Puede forzar JSON."""
        if not task_description.strip():
            return "Error: La descripción de la tarea no puede estar vacía."
        try:
            prompt = f"Ejecuta la siguiente tarea y devuelve SOLO el resultado:\n\n{task_description}"
            payload = {"model": model, "prompt": prompt, "stream": False}
            if json_schema:
                payload["format"] = json_schema

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get("response", "Sin respuesta")
            else:
                self._log_error("run_subagent", f"Status: {response.status_code}, Text: {response.text}")
                return f"Error en subagente: {response.status_code} - {response.text}"
        except Exception as e:
            self._log_error("run_subagent", str(e))
            return f"Excepción al ejecutar subagente: {str(e)}"

    def agent_chat_loop(self, messages: List[Dict[str, Any]], model: str = "qwen2.5:7b", 
                        tools: Optional[List[Dict[str, Any]]] = None, max_iterations: int = 5) -> str:
        """
        Proxy agéntico que usa el endpoint /api/chat de Ollama con Function Calling nativo.
        Maneja cadenas de llamadas a herramientas automáticamente hasta que el modelo emite una respuesta final.
        """
        if tools is None:
            tools = self.get_available_tools()
            
        current_iteration = 0
        
        while current_iteration < max_iterations:
            current_iteration += 1
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "tools": tools
            }
            
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=180
                )
                response.raise_for_status()
                response_data = response.json()
                message_out = response_data.get("message", {})
                
                # Agregamos la respuesta del asistente (incluso si solo contiene tool_calls)
                messages.append(message_out)
                
                tool_calls = message_out.get("tool_calls")
                
                if not tool_calls:
                    # El agente decidió responder al usuario o terminó la cadena
                    return message_out.get("content", "")
                    
                # Si hay llamadas a herramientas, las ejecutamos localmente
                for tc in tool_calls:
                    func_call = tc.get("function", {})
                    fn_name = func_call.get("name")
                    fn_args = func_call.get("arguments", {})
                    
                    try:
                        # Obtenemos la función dinámicamente de la instancia actual de Tools
                        func = getattr(self, fn_name)
                        
                        # Manejo especial para __user__ que Open WebUI inyecta globalmente
                        if "__user__" not in fn_args:
                            # En el futuro se puede mapear contexto global, por ahora pasamos None
                            fn_args["__user__"] = None
                            
                        # Ejecutar código local!
                        print(f"🔧 [Agent Proxy] Ejecutando: {fn_name}({fn_args})")
                        result = str(func(**fn_args))
                    except Exception as fn_e:
                        self._log_error(f"agent_chat_loop->{fn_name}", str(fn_e))
                        result = f"Error ejecutando herramienta {fn_name}: {str(fn_e)}"
                        
                    # Agregamos el resultado al array ininterrumpido como rol 'tool'
                    messages.append({
                        "role": "tool",
                        "content": result
                    })
                    
            except Exception as e:
                self._log_error("agent_chat_loop_http", str(e))
                return f"Excepción en bucle agéntico: {str(e)}"
                
        return "Error: Máximo de iteraciones alcanzado. El agente no logró concluir la tarea."

    def run_command(self, command: str, cwd: Optional[str] = None) -> str:
        """
        Ejecuta un comando del sistema de forma segura (solo comandos permitidos).
        Si cwd no se especifica, usa el workspace.
        """
        allowed = False
        for allowed_cmd in self.allowed_commands:
            if command.strip().startswith(allowed_cmd):
                allowed = True
                break
        if not allowed:
            self._log_error("run_command", f"Intentó ejecutar comando no permitido: {command}")
            return f"Error: Comando '{command}' no permitido. Los comandos permitidos son: {', '.join(self.allowed_commands)}"

        work_dir = cwd if cwd else self.workspace_path
        try:
            result = subprocess.run(command, shell=True, cwd=work_dir, capture_output=True, text=True, timeout=60)
            output = result.stdout + result.stderr
            if result.returncode != 0:
                self._log_error("run_command", f"Comando '{command}' falló con código {result.returncode}:\n{output}")
            return output if output else "Comando ejecutado sin salida."
        except subprocess.TimeoutExpired:
            self._log_error("run_command", f"Timeout en '{command}'")
            return "Error: El comando excedió el tiempo límite (60s)."
        except Exception as e:
            self._log_error("run_command", str(e))
            return f"Error al ejecutar comando: {str(e)}"

    # ==================== Análisis de código ====================

    def analyze_code(self, file_path: str, tool: str = "pylint") -> str:
        """
        Ejecuta un linter o analizador estático sobre un archivo en el workspace.
        Herramientas permitidas: pylint, flake8, mypy, bandit, pyflakes, black, isort.
        """
        allowed_tools = ['pylint', 'flake8', 'mypy', 'bandit', 'pyflakes', 'black', 'isort']
        if tool not in allowed_tools:
            return f"Herramienta no permitida. Usa: {allowed_tools}"
        full_path = os.path.join(self.workspace_path, file_path)
        if not os.path.exists(full_path):
            return f"El archivo '{file_path}' no existe en el workspace."
        # black --check solo reporta, no modifica; isort --check-only igual
        extra = ""
        if tool == "black":
            extra = " --check --diff"
        elif tool == "isort":
            extra = " --check-only --diff"
        cmd = f"{tool}{extra} {full_path}"
        return self.run_command(cmd)

    # ==================== Generación de pruebas ====================

    def generate_tests(self, file_path: str, framework: str = "pytest") -> str:
        """
        Genera pruebas unitarias para el archivo dado usando un subagente.
        El archivo debe estar en el workspace.
        """
        full_path = os.path.join(self.workspace_path, file_path)
        if not os.path.exists(full_path):
            return f"El archivo '{file_path}' no existe en el workspace."
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            self._log_error("generate_tests", str(e))
            return f"Error leyendo el archivo: {e}"
        prompt = (
            f"Genera pruebas unitarias con {framework} para el siguiente código Python. "
            f"Devuelve estrictamente un JSON conformando el esquema solicitado.\n\n{code}"
        )
        schema = {
            "type": "object",
            "properties": {"codigo": {"type": "string"}},
            "required": ["codigo"]
        }
        raw_response = self.run_subagent(prompt, model="qwen2.5:7b", json_schema=schema)
        try:
            # Extraer el código evadiendo markdown o errores de parseo string
            return json.loads(raw_response).get("codigo", raw_response)
        except json.JSONDecodeError:
            return raw_response

    # ==================== Documentación automática ====================

    def generate_docstring(self, file_path: str, function_name: Optional[str] = None) -> str:
        """
        Genera o completa docstrings para una función específica o todo el archivo.
        """
        full_path = os.path.join(self.workspace_path, file_path)
        if not os.path.exists(full_path):
            return f"El archivo '{file_path}' no existe en el workspace."
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            self._log_error("generate_docstring", str(e))
            return f"Error leyendo el archivo: {e}"
        if function_name:
            prompt = (
                f"Genera un docstring completo (descripción, parámetros, retorno) "
                f"para la función '{function_name}' en el siguiente código:\n\n{code}\n\n"
                f"Devuelve solo el docstring."
            )
        else:
            prompt = (
                f"Añade docstrings completos a TODAS las funciones y clases en este código. "
                f"Devuelve el código completo con los docstrings añadidos:\n\n{code}"
            )
        return self.run_subagent(prompt, model="qwen2.5:7b")

    # ==================== Gestión de tareas (TODO) ====================

    def create_task(self, title: str, description: str = "", priority: str = "media") -> str:
        """
        Crea una nueva tarea en el archivo TODO.md del workspace.
        Prioridades: alta, media, baja.
        """
        todo_path = os.path.join(self.workspace_path, "TODO.md")
        # Encabezado si el archivo no existe
        if not os.path.exists(todo_path):
            with open(todo_path, 'w', encoding='utf-8') as f:
                f.write("# 📋 Tareas de Memexicanisimos\n\n")
        entry = f"- [ ] **{title}** (prioridad: {priority})"
        if description:
            entry += f"\n  {description}"
        entry += "\n\n"
        try:
            with open(todo_path, 'a', encoding='utf-8') as f:
                f.write(entry)
            return f"✅ Tarea '{title}' creada en TODO.md"
        except Exception as e:
            self._log_error("create_task", str(e))
            return f"Error al crear tarea: {e}"

    def list_tasks(self, status: str = "all") -> str:
        """
        Lista las tareas del TODO.md. status puede ser 'pending', 'done' o 'all'.
        """
        todo_path = os.path.join(self.workspace_path, "TODO.md")
        if not os.path.exists(todo_path):
            return "No hay archivo TODO.md. Crea una tarea primero con create_task."
        try:
            with open(todo_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._log_error("list_tasks", str(e))
            return f"Error leyendo TODO.md: {e}"
        tasks = []
        for line in content.split('\n'):
            line_s = line.strip()
            if line_s.startswith('- [ ]'):
                if status in ('all', 'pending'):
                    tasks.append(f"⏳ {line_s[5:].strip()}")
            elif line_s.startswith('- [x]') or line_s.startswith('- [X]'):
                if status in ('all', 'done'):
                    tasks.append(f"✅ {line_s[5:].strip()}")
        if not tasks:
            return "No se encontraron tareas con ese filtro."
        return "\n".join(tasks)

    # ==================== Exportación / Importación de memorias ====================

    def export_memories(self, filter_type: Optional[str] = None) -> str:
        """
        Exporta todas las memorias (o filtradas por tipo) a un archivo JSON en el workspace.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if filter_type:
                cursor.execute("""
                    SELECT m.id, m.title, m.type, m.tags, m.created_at, f.content
                    FROM memories m LEFT JOIN memories_fts f ON m.id = f.content_id
                    WHERE m.type = ?
                """, (filter_type,))
            else:
                cursor.execute("""
                    SELECT m.id, m.title, m.type, m.tags, m.created_at, f.content
                    FROM memories m LEFT JOIN memories_fts f ON m.id = f.content_id
                """)
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return "No hay memorias para exportar."
            memories = []
            for r in rows:
                memories.append({
                    "id": r[0], "title": r[1], "type": r[2],
                    "tags": r[3].split(',') if r[3] else [],
                    "created_at": r[4],
                    "content": r[5] if r[5] else ""
                })
            filename = f"memories_export_{int(time.time())}.json"
            filepath = os.path.join(self.workspace_path, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(memories, f, indent=2, ensure_ascii=False)
            return f"✅ Exportadas {len(memories)} memorias a {filename}"
        except Exception as e:
            self._log_error("export_memories", str(e))
            return f"Error exportando memorias: {str(e)}"

    def import_memories(self, filename: str) -> str:
        """
        Importa memorias desde un archivo JSON en el workspace.
        Formato esperado: lista de objetos con title, content, type, tags.
        """
        filepath = os.path.join(self.workspace_path, filename)
        if not os.path.exists(filepath):
            return f"El archivo '{filename}' no existe en el workspace."
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                memories = json.load(f)
            if not isinstance(memories, list):
                return "El archivo no tiene el formato correcto (debe ser una lista de memorias)."
            conn = self._get_connection()
            cursor = conn.cursor()
            count = 0
            for mem in memories:
                title = mem.get('title', 'Sin título')
                content = mem.get('content', '')
                mem_type = mem.get('type', 'general')
                tags = ','.join(mem.get('tags', [])) if isinstance(mem.get('tags'), list) else mem.get('tags', '')
                cursor.execute(
                    "INSERT INTO memories (title, type, tags, created_at) VALUES (?, ?, ?, ?)",
                    (title, mem_type, tags, mem.get('created_at', datetime.now().isoformat()))
                )
                memory_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO memories_fts (rowid, content, content_id) VALUES (?, ?, ?)",
                    (memory_id, content, memory_id)
                )
                count += 1
            conn.commit()
            conn.close()
            return f"✅ Importadas {count} memorias desde {filename}."
        except Exception as e:
            self._log_error("import_memories", str(e))
            return f"Error importando memorias: {str(e)}"

    # ==================== Estadísticas de memoria ====================

    def memory_stats(self) -> str:
        """Muestra estadísticas detalladas de las memorias almacenadas."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT type, COUNT(*) FROM memories GROUP BY type")
            stats = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM memories")
            dates = cursor.fetchone()
            conn.close()
            if total == 0:
                return "No hay memorias almacenadas."
            lines = [f"📊 **Total: {total} memorias**"]
            if dates[0] and dates[1]:
                lines.append(f"📅 Desde: {dates[0]} hasta: {dates[1]}")
            lines.append("---")
            for tipo, count in stats:
                pct = round((count / total) * 100, 1)
                lines.append(f"  {tipo}: {count} ({pct}%)")
            return "\n".join(lines)
        except Exception as e:
            self._log_error("memory_stats", str(e))
            return f"Error obteniendo estadísticas: {str(e)}"

    def run_governance_cycle(self) -> str:
        """
        Ejecuta un ciclo completo de gobernanza de memoria:
        recalcula scores, archiva memorias irrelevantes, y compacta si hay exceso de entropy.
        Usa transacciones atómicas WAL para seguridad.
        """
        try:
            from memory_governor import MemoryGovernor
            gov = MemoryGovernor(self.db_path)
            gov.migrate_schema()
            result = gov.run_cycle()
            return (
                f"✅ Gobernanza completada: {result['memories_scored']} evaluadas, "
                f"{result['memories_archived']} archivadas, "
                f"entropy={result['entropy']}, duración={result['duration_seconds']}s"
            )
        except Exception as e:
            self._log_error("run_governance_cycle", str(e))
            return f"❌ Error en gobernanza: {str(e)}"

    # ==================== Integración con Git ====================

    def git_status(self) -> str:
        """Muestra el estado de git en el workspace."""
        return self.run_command("git status")

    def git_commit(self, message: str) -> str:
        """Hace git add . y luego un commit con el mensaje dado."""
        self.run_command("git add .")
        return self.run_command(f'git commit -m "{message}"')

    # ==================== Utilidades de texto y red ====================

    def fetch_url(self, url: str) -> str:
        """
        Obtiene el contenido de una URL (solo HTTP/HTTPS). Útil para investigar.
        El contenido se limita a 5000 caracteres para no saturar el contexto.
        """
        if not url.startswith(('http://', 'https://')):
            return "Solo se permiten URLs HTTP/HTTPS."
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text[:5000]
            return content
        except Exception as e:
            self._log_error("fetch_url", str(e))
            return f"Error al obtener URL: {e}"

    def summarize_text(self, text: str) -> str:
        """Resume un texto largo usando un subagente."""
        if len(text) > 10000:
            text = text[:10000] + "\n[...texto truncado...]"
        prompt = f"Resume el siguiente texto de forma concisa y clara en español:\n\n{text}"
        return self.run_subagent(prompt, model="qwen2.5:7b")

    # ==================== Abrir archivo en editor ====================

    def open_in_editor(self, file_path: str) -> str:
        """
        Abre el archivo en el editor predeterminado del sistema (Linux: xdg-open).
        """
        full_path = os.path.join(self.workspace_path, file_path)
        if not os.path.exists(full_path):
            return f"El archivo '{file_path}' no existe en el workspace."
        try:
            subprocess.Popen(['xdg-open', full_path])
            return f"Abriendo {file_path} en el editor predeterminado..."
        except Exception as e:
            self._log_error("open_in_editor", str(e))
            return f"Error al abrir archivo: {e}"

    # ==================== Herramientas de Escritura y Proyectos (Fase 1) ====================

    def _safe_path(self, requested_path: str, base_dir: Optional[str] = None) -> str:
        """
        Valida que la ruta esté dentro del directorio base permitido (workspace o external).
        Previene path traversal.
        """
        if base_dir is None:
            base_dir = self.workspace_path
        abs_base = os.path.abspath(base_dir)
        abs_req = os.path.abspath(os.path.join(base_dir, requested_path))
        if not abs_req.startswith(abs_base):
            raise ValueError(f"Acceso denegado: la ruta '{requested_path}' está fuera del directorio permitido.")
        return abs_req

    def write_file(self, path: str, content: str, overwrite: bool = False) -> str:
        """
        Crea o sobrescribe un archivo en el workspace.
        :param path: Ruta relativa al workspace (ej. 'docs/README.md').
        :param content: Contenido del archivo.
        :param overwrite: Si False, no sobrescribe si el archivo ya existe.
        """
        try:
            full_path = self._safe_path(path)
            if os.path.exists(full_path) and not overwrite:
                return f"⚠️ El archivo '{path}' ya existe. Usa overwrite=True para sobrescribirlo."
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ Archivo guardado: {path}"
        except Exception as e:
            self._log_error("write_file", str(e))
            return f"❌ Error al guardar archivo: {str(e)}"

    def write_markdown_doc(self, title: str, content: str, tags: str = "", path: Optional[str] = None) -> str:
        """
        Genera un archivo Markdown con frontmatter YAML.
        :param title: Título del documento.
        :param content: Contenido principal (sin frontmatter).
        :param tags: Etiquetas separadas por comas.
        :param path: Ruta donde guardar (por defecto 'docs/{title_slug}.md').
        """
        from datetime import date
        import re

        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        if not path:
            path = f"docs/{slug}.md"
        today = date.today().isoformat()
        tags_list = [t.strip() for t in tags.split(',') if t.strip()]
        frontmatter = f"""---
title: {title}
date: {today}
tags: {tags_list}
generated_by: memex
---

"""
        full_content = frontmatter + content
        return self.write_file(path, full_content, overwrite=True)

    def generate_code_file(self, language: str, specification: str, path: str) -> str:
        """
        Usa un subagente para generar código según especificación y lo guarda en la ruta indicada.
        :param language: Lenguaje de programación (python, javascript, etc.)
        :param specification: Descripción del código a generar.
        :param path: Ruta donde guardar el archivo (relativa al workspace).
        """
        prompt = (
            f"Genera código en {language} que cumpla con la siguiente especificación. "
            f"Obligatorio: La respuesta debe ser 100% JSON estructurado.\n\n"
            f"Especificación: {specification}"
        )
        schema = {
            "type": "object",
            "properties": {"codigo": {"type": "string"}},
            "required": ["codigo"]
        }
        generated = self.run_subagent(prompt, model="qwen2.5:7b", json_schema=schema)
        if generated.startswith("Error") or generated.startswith("Excepción"):
            return f"❌ Error en generación: {generated}"
            
        try:
            # Extraemos la propiedad "codigo" del JSON generado por Ollama
            codigo_final = json.loads(generated).get("codigo", generated)
        except json.JSONDecodeError:
            codigo_final = generated
            
        return self.write_file(path, codigo_final, overwrite=True)

    def create_project_structure(self, project_type: str, name: str) -> str:
        """
        Genera la estructura de carpetas y archivos base para un tipo de proyecto.
        Tipos soportados: python-basic, fastapi, react, node-express.
        """
        base_path = os.path.join("proyectos", name)
        templates = {
            "python-basic": {
                "README.md": f"# {name}\n\nProyecto Python básico.\n",
                "main.py": "def main():\n    print('Hola, mundo!')\n\nif __name__ == '__main__':\n    main()\n",
                "requirements.txt": "# dependencias\n",
            },
            "fastapi": {
                "README.md": f"# {name}\n\nAPI con FastAPI.\n",
                "main.py": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef read_root():\n    return {'message': 'Hola, mundo'}\n",
                "requirements.txt": "fastapi\nuvicorn\n",
            },
            "react": {
                "README.md": f"# {name}\n\nAplicación React.\n",
                "src/App.js": "function App() {\n  return <div>Hola, mundo</div>;\n}\n\nexport default App;\n",
                "src/index.js": "import React from 'react';\nimport ReactDOM from 'react-dom';\nimport App from './App';\n\nReactDOM.render(<App />, document.getElementById('root'));\n",
                "package.json": '{\n  "name": "' + name + '",\n  "version": "1.0.0",\n  "dependencies": {},\n  "scripts": {\n    "start": "react-scripts start"\n  }\n}\n',
            },
            "node-express": {
                "README.md": f"# {name}\n\nAPI con Express.\n",
                "index.js": "const express = require('express');\nconst app = express();\n\napp.get('/', (req, res) => res.send('Hola, mundo'));\napp.listen(3000, () => console.log('Servidor en puerto 3000'));\n",
                "package.json": '{\n  "name": "' + name + '",\n  "version": "1.0.0",\n  "dependencies": {\n    "express": "^4.18.2"\n  }\n}\n',
            }
        }
        if project_type not in templates:
            return f"❌ Tipo de proyecto no soportado. Usa: {', '.join(templates.keys())}"
        results = []
        for rel_path, content in templates[project_type].items():
            full_path = os.path.join(base_path, rel_path)
            res = self.write_file(full_path, content, overwrite=True)
            results.append(res)
        return "\n".join(results)

    def read_external_file(self, path: str) -> str:
        """
        Lee un archivo de un directorio externo montado (solo lectura).
        La ruta debe ser relativa a /app/backend/data/external_projects.
        """
        external_base = "/app/backend/data/external_projects"
        if not os.path.exists(external_base):
            return "⚠️ El directorio de proyectos externos no está montado. Contacta al administrador."
        try:
            full_path = self._safe_path(path, base_dir=external_base)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            self._log_error("read_external_file", str(e))
            return f"❌ Error al leer archivo externo: {str(e)}"

    # ==================== RAG con Qdrant (Fase 2) ====================

    def index_project(self, project_path: str) -> str:
        """
        Indexa todos los archivos de un proyecto (dentro del workspace o externo)
        en Qdrant para búsqueda semántica.
        :param project_path: Ruta relativa al workspace del proyecto a indexar.
        """
        try:
            full_path = self._safe_path(project_path, base_dir=self.workspace_path)
        except ValueError:
            # Intentar en external_projects
            external_base = "/app/backend/data/external_projects"
            try:
                full_path = self._safe_path(project_path, base_dir=external_base)
            except ValueError as e:
                return f"❌ {str(e)}"

        if not os.path.isdir(full_path):
            return f"❌ La ruta '{project_path}' no es un directorio válido."

        extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.md', '.txt', '.json', '.yaml', '.yml', '.toml']
        chunks = []
        for root, _, files in os.walk(full_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except Exception:
                        continue
                    words = content.split()
                    chunk_size = 500
                    for i in range(0, len(words), chunk_size):
                        chunk = ' '.join(words[i:i + chunk_size])
                        chunks.append({
                            "text": chunk,
                            "metadata": {
                                "file": os.path.relpath(file_path, full_path),
                                "project": project_path
                            }
                        })

        if not chunks:
            return "No se encontraron archivos para indexar."

        # Obtener embeddings desde Ollama
        embeddings = []
        for chunk_idx, chunk in enumerate(chunks):
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": chunk["text"]},
                    timeout=30
                )
                if response.status_code == 200:
                    embedding = response.json().get("embedding")
                    if embedding:
                        embeddings.append({
                            "id": chunk_idx,
                            "vector": embedding,
                            "payload": chunk["metadata"]
                        })
                else:
                    self._log_error("index_project", f"Embedding error: {response.text[:200]}")
            except Exception as e:
                self._log_error("index_project", f"Embedding exception: {str(e)}")

        if not embeddings:
            return "❌ No se pudieron generar embeddings. ¿Está el modelo nomic-embed-text disponible?"

        # Enviar a Qdrant
        qdrant_url = "http://qdrant:6333"
        collection = "memex_projects"

        # Crear colección si no existe
        try:
            requests.put(f"{qdrant_url}/collections/{collection}", json={
                "vectors": {"size": len(embeddings[0]["vector"]), "distance": "Cosine"}
            }, timeout=10)
        except Exception as e:
            self._log_error("index_project", f"Qdrant collection error: {str(e)}")

        # Insertar puntos
        points = [{"id": emb["id"], "vector": emb["vector"], "payload": emb["payload"]} for emb in embeddings]
        try:
            response = requests.put(
                f"{qdrant_url}/collections/{collection}/points",
                json={"points": points},
                timeout=60
            )
            if response.status_code == 200:
                return f"✅ Indexados {len(chunks)} fragmentos de '{project_path}' en Qdrant."
            else:
                return f"❌ Error al guardar en Qdrant: {response.text[:200]}"
        except Exception as e:
            self._log_error("index_project", str(e))
            return f"❌ Error conectando con Qdrant: {str(e)}"

    def semantic_search(self, query: str, limit: int = 5) -> str:
        """
        Busca fragmentos de código/documentación semánticamente similares a la consulta.
        Requiere que haya proyectos indexados con index_project.
        :param query: Texto de búsqueda en lenguaje natural.
        :param limit: Número máximo de resultados.
        """
        if not query.strip():
            return "Error: La consulta no puede estar vacía."

        # Obtener embedding de la consulta
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": query},
                timeout=30
            )
            if response.status_code != 200:
                return f"❌ Error obteniendo embedding: {response.text[:200]}"
            query_vector = response.json().get("embedding")
            if not query_vector:
                return "❌ No se pudo generar el embedding de la consulta."
        except Exception as e:
            return f"❌ Error de conexión con Ollama: {str(e)}"

        # Buscar en Qdrant
        qdrant_url = "http://qdrant:6333"
        collection = "memex_projects"
        search_payload = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True
        }
        try:
            response = requests.post(
                f"{qdrant_url}/collections/{collection}/points/search",
                json=search_payload,
                timeout=15
            )
            if response.status_code != 200:
                return f"❌ Error en búsqueda Qdrant: {response.text[:200]}"
            results = response.json().get("result", [])
        except Exception as e:
            return f"❌ Error conectando con Qdrant: {str(e)}"

        if not results:
            return "No se encontraron resultados. ¿Has indexado algún proyecto con `index_project`?"

        output = "### 🔍 Resultados de la búsqueda semántica\n\n"
        for res in results:
            score = res.get("score", 0)
            payload = res.get("payload", {})
            file_name = payload.get("file", "desconocido")
            project = payload.get("project", "")
            output += f"- **Archivo:** `{file_name}` (proyecto: `{project}`, similitud: {score:.2f})\n"

        return output

