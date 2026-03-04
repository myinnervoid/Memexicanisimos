# SPEC.md — Project Specification

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: No code may be written until this spec is marked `FINALIZED`.

## Vision
Memexicanisimos OS (Memex) es un ecosistema completo de Inteligencia Artificial (MLOps) diseñado para correr fluidamente en hardware de consumo (8GB - 16GB RAM). Unifica la planificación visual (a través de Open WebUI) y la ejecución de código autónoma en terminal (mediante Aider) en un solo cerebro compartido y 100% local, respetando la privacidad del usuario sin depender de servicios en la nube.

## Goals
1. **Ejecución Local y Aislada** — Mantener todo el ecosistema (Docker, Ollama, Qdrant) encapsulado para evitar conflictos de puertos y asegurar portabilidad entre distribuciones (Ubuntu, Arch, Fedora, macOS).
2. **Máxima Eficiencia de Recursos** — Operar con fluidez en equipos de bajos recursos mediante cargas y descargas dinámicas de modelos, orquestación concurrente estricta y delegación de tareas (Auto-Router entre modelos 1.5B y 7B).
3. **Memoria Persistente Híbrida** — Proveer al agente contexto cognitivo a largo plazo mediante almacenamiento SQLite FTS5 (hechos y preferencias) y Qdrant Vector DB (RAG de repositorios).
4. **Extensibilidad "Skill-based"** — Habilitar la creación rápida de herramientas y agentes especializados ("Sabores") mediante inyección de prompts o desarrollo de herramientas Pydantic.

## Non-Goals (Out of Scope)
- No existirá dependencia obligatoria de APIs comerciales de terceros (OpenAI, Anthropic) para el core del sistema.
- No se desarrollará un cliente de interfaz gráfica desde cero (se aprovecha la madurez de Open WebUI).
- No es un sistema diseñado para clústeres empresariales grandes; el foco absoluto es el "Personal Computing" / Workstations de consumo.

## Constraints
- **Hardware Constraint:** Debe ser capaz de arrancar y asistir en programación (Tier 3) usando un máximo de 5.5GB a 8GB de RAM.
- **Arquitectura:** Debe ejecutarse estricta y obligatoriamente dentro de contenedores Docker pre-configurados.
- **Comportamiento del LLM:** `OLLAMA_MAX_LOADED_MODELS` y `OLLAMA_NUM_PARALLEL` deben mantenerse en `1` para prevenir bloqueos OOM (Out Of Memory).

## Success Criteria
- [ ] Instalador gráfico adaptativo (`MemexicanisimosOS`) despliega exitosamente los 3 niveles de servicio sin intervención manual compleja.
- [ ] "Memex Coder" (Aider) puede editar archivos y hacer commits leyendo el contexto persistente sin fallos de OOM.
- [ ] La base de datos vectorial Qdrant es capaz de indexar repositorios de código locales correctamente.
- [ ] La creación e inyección de nuevas "Skills" funciona fluidamente usando el Memex Prompt Injector.
- [ ] Sistema de Múltiples Proyectos permite aislar directorios (`src/`, `docs/`, `data/`) de forma individual.

## User Stories (Optional)

### As a Desarrollador Local
- I want to ejecutar un agente de código (Aider) que conozca la arquitectura general de mi proyecto
- So that no tenga que explicarle el contexto desde cero en cada sesión.

### As a Usuario con Hardware Limitado
- I want to instalar el sistema mediante Tiers (Niveles) y usar el Auto-Router
- So that mi PC no colapse por problemas de memoria RAM mientras la IA me asiste.

## Technical Requirements (Optional)

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Orquestación Docker Compose | Must-have | Estandariza todo el despliegue |
| Ollama Optimization (`KEEP_ALIVE=1m`) | Must-have | Libera VRAM/RAM activamente |
| Scripts Python/Bash de Instalación | Must-have | Embalan la complejidad de Docker y entornos |
| Control Físico Opcional (Agente Génesis) | Nice-to-have | Para UI testing automáticos o RPA básico |

---

*Last updated: 2026-02-27*
