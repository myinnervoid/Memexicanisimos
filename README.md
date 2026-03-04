# 🌮 Memexicanisimos OS (Memex)

**Local AI Brain and Limbs.** An autonomous development environment with persistent memory, agent orchestration, and terminal programming.

Memexicanisimos OS is not just a chatbot; it's a **complete local AI MLOps ecosystem** designed to run smoothly on consumer hardware (8GB - 16GB RAM). It unifies visual planning and code execution into a single shared AI brain.

We look for privacy

[Lee esto en Español.](README.es.md)

---

### 🎉 What's New in v6.0 (Sentience Edition)

- **Modern GUI:** Fully migrated to **CustomTkinter** with professional dark theme and sidebar navigation.
- **Dynamic Model Catalog:** Automatically recommends the best AI models for your hardware tier (2GB→70B), with categories: General, Coder, Reasoning, Embedding.
- **Selective Updater:** Update Ollama, Open WebUI, or Qdrant independently — no need to restart everything.
- **Smart Port Scanner & Connection Manager:** Detects occupied ports (3000-3020) and auto-suggests free alternatives. Includes a real-time 'Connections' dashboard to hot-swap Open WebUI ports and view service status.
- **AI Problem Solver (FAQ):** A built-in troubleshooting 'Solucionador' tab that analyzes Docker logs and formats them into clinical AI prompts ready to copy & paste for instant technical support.
- **Global Power Robustness:** Auto-cleanup logic in the power buttons prevents "container name already in use" conflict errors by forcefully destroying orphans before recreating networks.
- **Skip Model Download:** New checkbox to skip model download during installation — useful for migrating existing local Ollama models.
- **Model Download Center:** Browse, filter by category, and download any model from the catalog or enter custom model names.

---

## 🏗️ Architecture and Components

We designed this system to work as an **impenetrable, zero-friction fortress.**

### 🐳 1. Docker: The Fortress

The entire ecosystem lives inside an isolated Docker network. Why?

- **Zero Port Conflicts:** Smart port detection ensures Memex never clashes with existing services on your machine.
- **Portability:** It runs exactly the same on Ubuntu, Arch, Fedora, or macOS.
- **Cleanliness:** If something breaks, simply remove the container, leaving your host OS pristine.

### 🧠 2. Ollama: The Tuned Engine

The heart of the system. Instead of loading multiple models and crashing your RAM, we surgically tune Ollama for maximum efficiency:

| Variable | Value | Effect |
|----------|-------|--------|
| `OLLAMA_MAX_LOADED_MODELS` | `1` | Only one model in RAM at a time |
| `OLLAMA_NUM_PARALLEL` | `1` | Strict sequential execution (prevents OOM) |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | Safe limit preventing KV cache explosions |
| `OLLAMA_KEEP_ALIVE` | `1m` | Auto-unloads models after 1 minute idle |

### 🌐 3. Open WebUI: The Brain & Flavors

Acts as your control panel and planner. It comes natively loaded with **"Flavors"** (Specialized Agents):

- 💻 **Memex Coder:** Your software architect.
- 📈 **Memex Marketer:** Copywriter that remembers your brand voice.
- 📚 **Memex Researcher:** Indexes databases and analyzes dense documents.
- 🤖 **Memex Auto:** A dynamic orchestrator (Auto-Router) that routes simple tasks to light models (1.5B) and complex tasks to heavy models (7B), saving RAM in real-time.

### ✋ 4. Aider CLI: The Limbs

While Open WebUI plans, **Aider executes.** It's a terminal agent (invoked via `./memex_builder.sh`) that connects to your shared Ollama engine. It reads your code, edits files, and commits to Git automatically, consuming less than 100MB of RAM.

### 🗄️ 5. Hybrid Persistent Memory & Function Calling (v5.4)

Your agent **does not suffer from amnesia**, nor is it limited to just outputting text:

- **Native Function Calling:** The LLM (e.g. Qwen 2.5/3.5) uses a proxy (`agent_chat_loop`) that allows it to execute local OS tools autonomously before returning a final answer.
- **SQLite FTS5:** It remembers business rules, preferences, and important facts across chat sessions via indexed searches.
- **Qdrant (RAG):** Indexes complete code repositories or PDFs so the AI understands the macro context of your projects.

---

## 🚀 Adaptive Installation (Tiers)

The GUI installer automatically detects your hardware and recommends the best models:

| Tier | Components | Approx RAM |
|------|------------|------------|
| 🟢 **Tier 1 (Chat)** | Open WebUI and Ollama only | ~3.5GB |
| 🟡 **Tier 2 (RAG)** | + SearxNG Private Search and Qdrant Vector DB | ~5.0GB |
| 🔴 **Tier 3 (Apps)** | + `memex_builder.sh` script for terminal programming with Aider | ~5.5GB |

### Dynamic Model Selection (v6.0)

The installer presents a **Top 10** of models filtered for your RAM:

| RAM | Example Models |
|-----|---------------|
| 4GB | Qwen 2.5 (0.5B), Llama 3.2 (1B) |
| 8GB | Qwen 2.5 (7B), DeepSeek-R1 (7B), Qwen 3 (8B) |
| 16GB | Qwen 3.5 (9B), Phi-4 (14B), DeepSeek-R1 (14B) |
| 32GB+ | DeepSeek-R1 (32B), Llama 3.1 (70B) |

### Quick Start (Linux — Copy & Paste)

> ⚠️ **Important:** You MUST create a dedicated folder for the project. Docker and the installer need to be run from this folder. Do NOT install in your home directory directly.

**1. Install prerequisites, download and launch:**

```bash
# Install dependencies (one time only)
sudo apt install -y python3-yaml python3-tk git
pip install customtkinter

# Create your project folder and download
mkdir -p ~/Memexicanisimos && cd ~/Memexicanisimos
git clone https://github.com/myinnervoid/Memexicanisimos.git .

# Launch the installer
python3 memex_gui.py
```

**2. To reopen later:**

```bash
cd ~/Memexicanisimos && python3 memex_gui.py
```

> 💡 **Tip:** If you already ran the command before, just open a terminal, press ⬆️ (arrow up) and the last command will appear in your history. Make sure you're in the project folder.

---

## 🛠️ Quick Guide: How to Create and Contribute "Skills"

Memexicanisimos is **extensible by design.** We use Open WebUI's Tools and Filters system to inject "Skills".

### Method 1: Using Prompt Injector (No code)

1. Open a chat in Open WebUI.
2. Call the **Memex Prompt Injector** tool.
3. Write a prompt like:

> *"Generate a System Prompt for a 'Scrum Master' agent. It must use the `search_memory` tool to recall yesterday's blockers, and `create_task` to organize today's TODO.md."*

The injector will return the perfect setup for a new "Flavor".

### Method 2: Developing a Python Skill (For Contributors)

To create a real tool (e.g., querying an external API), create a file in the `src/` folder following the **pydantic** standard.

**Basic Skill Template:**

```python
"""
title: My New Skill
author: Your Name
version: 1.0.0
"""
from pydantic import BaseModel
from typing import Callable, Any

class Tools:
    class Valves(BaseModel):
        # Settings visible in the Web Interface
        api_key: str = ""

    async def my_new_function(
        self,
        parameter: str,
        __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        VERY CLEAR instructions so the AI knows when to use this tool.
        :param parameter: What this data means.
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "Running...", "done": False}
            })

        result = f"Processed: {parameter}"

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"description": "Completed", "done": True}
            })

        return result
```

Then add it to `setup_memex.py` so the installer injects it automatically into the Open WebUI database on the next deployment.

---

## 🎛️ Management and Repair Panel

If an app crashes (e.g., Open WebUI freezes), **you don't need to reinstall everything.** Run `python3 memex_gui.py` again, enter the Control Panel, and use the **Granular Reinstaller** to recreate only the failing service without losing your memories or models.

---

## 📁 Multi-Project System

Organize your work into separate projects via the **Projects** tab:

- **Create projects** with dedicated `src/`, `docs/`, and `data/` directories.
- **Set an active project** so the Genesis Agent automatically works within that directory.
- Projects live in `memex_workspace/projects/`.

---

## 📄 License

MIT License. See the [LICENSE](LICENSE) file for details.
