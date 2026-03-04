import tkinter as tk
from tkinter import ttk, messagebox


class ConfigFrame(ttk.Frame):
    """
    Frame de configuración con mega catálogo de modelos,
    módulos opcionales (checkboxes) y Aider dockerizado.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="⚙️ Configuración del Ecosistema", style='Title.TLabel').pack(pady=(20, 10))

        # Cuaderno de pestañas
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)

        # Tab 1: Modelos
        tab_models = ttk.Frame(notebook)
        notebook.add(tab_models, text="🧠 Modelos")
        self._build_models_tab(tab_models)

        # Tab 2: Módulos
        tab_modules = ttk.Frame(notebook)
        notebook.add(tab_modules, text="📦 Módulos")
        self._build_modules_tab(tab_modules)

        # Tab 3: Avanzado
        tab_adv = ttk.Frame(notebook)
        notebook.add(tab_adv, text="⚙️ Avanzado")
        self._build_advanced_tab(tab_adv)

        # Botones de navegación
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", pady=20)

        self.lbl_error = ttk.Label(btn_frame, text="", foreground="red")
        self.lbl_error.pack(side="top", pady=5)

        ttk.Button(btn_frame, text="🡄 Atrás",
                   command=lambda: self.controller.show_frame("HardwareFrame")).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🚀 Preparar e Instalar",
                   command=self._on_next).pack(side="right", padx=10)

    def _build_models_tab(self, parent):
        # --- Mega Catálogo ---
        model_frame = ttk.LabelFrame(parent, text="Modelo Base (Puedes escribir uno nuevo)", padding=10)
        model_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(model_frame, text="Elige el modelo que será el cerebro de tu sistema:").pack(anchor="w")

        self.models_list = [
            "--- 🚀 ULTRALIGEROS (4GB - 8GB RAM) ---",
            "qwen2.5-coder:1.5b | 💻 Código - Súper rápido, Vibe Coding",
            "llama3.2:1b        | 💬 Chat - El más ligero de Meta",
            "phi3.5:3.8b        | 🔬 Razonamiento - Pequeño pero potente",
            "gemma3:4b          | 🧠 General - Eficiente de Google",
            "",
            "--- ⚖️ BALANCEADOS (8GB - 16GB RAM) ---",
            "deepseek-r1:7b     | 🧠 Thinking - Razonamiento profundo",
            "qwen2.5:7b         | ⚡ General - Estándar de oro",
            "llama3.1:8b        | 💬 Chat - Robusto de Meta",
            "phi4:14b           | 🔬 Lógica - Matemáticas avanzadas",
            "",
            "--- 💻 ESPECIALISTAS EN CÓDIGO ---",
            "qwen3-coder:7b     | 💻 Optimizado para agentes",
            "qwen3.5:9b         | 💻 Código SOTA 9B",
            "qwen2.5:14b        | 💻 Heavy Coder Model",
            "deepseek-coder-v2  | 💻 Nivel GPT-4 Turbo en código",
            "codestral          | 💻 Mistral AI para devs",
            "",
            "--- 👁️ MULTIMODAL Y VISIÓN ---",
            "llama3.2-vision:11b| 👁️ OCR y extracción",
            "qwen3-vl:8b        | 👁️ Visual más potente de Qwen",
            "",
            "--- 🗄️ EMBEDDINGS (Para RAG) ---",
            "nomic-embed-text   | 🗄️ Embeddings (274MB)",
            "bge-m3             | 🗄️ Multilingüe",
        ]

        self.selected_model_combo = ttk.Combobox(model_frame, values=self.models_list, width=60)
        default_idx = 7 if hasattr(self.controller, 'ram_gb') and self.controller.ram_gb >= 12 else 1
        self.selected_model_combo.current(default_idx)
        self.selected_model_combo.pack(anchor="w", pady=5)

        # --- Sabores Específicos ---
        common_models = [
            "qwen2.5:1.5b", "llama3.2:3b", "qwen2.5:7b",
            "deepseek-r1:7b", "qwen2.5-coder:1.5b",
            "qwen3-coder:7b", "codestral",
        ]

        def create_flavor_selector(container, label_text, str_var):
            f = ttk.Frame(container)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=label_text, width=20).pack(side="left")
            ttk.Combobox(f, textvariable=str_var, values=common_models, width=30).pack(side="left")

        f_flavors = ttk.LabelFrame(parent, text="Sabores Específicos (Opcional)", padding=5)
        f_flavors.pack(fill="x", padx=10, pady=10)
        ttk.Label(f_flavors, text="Especializa cada sabor (vacío = Modelo Base):").pack(anchor="w", padx=5)

        create_flavor_selector(f_flavors, "Coder (Lógica):", self.controller.flavor_coder)
        create_flavor_selector(f_flavors, "Marketer (Redacción):", self.controller.flavor_marketer)
        create_flavor_selector(f_flavors, "Researcher (Análisis):", self.controller.flavor_researcher)
        create_flavor_selector(f_flavors, "Editor (Corrección):", self.controller.flavor_editor)

    def _build_modules_tab(self, parent):
        """Módulos opcionales con checkboxes individuales."""
        ttk.Label(parent, text="Desactiva módulos para ahorrar RAM en hardware limitado.",
                  wraplength=500).pack(anchor="w", padx=10, pady=(10, 5))

        ram_gb = getattr(self.controller, 'ram_gb', 8)

        modules_frame = ttk.LabelFrame(parent, text="Microservicios (Todos dockerizados)", padding=10)
        modules_frame.pack(fill="x", padx=10, pady=5)

        self.opt_whoogle = tk.BooleanVar(value=True)
        ttk.Checkbutton(modules_frame, text="🌐 Whoogle (Buscador Privado ~200MB RAM)",
                        variable=self.opt_whoogle).pack(anchor="w", pady=3)

        self.opt_qdrant = tk.BooleanVar(value=ram_gb >= 8)
        ttk.Checkbutton(modules_frame, text="🗄️ Qdrant (Base Vectorial RAG ~1GB RAM)",
                        variable=self.opt_qdrant).pack(anchor="w", pady=3)

        self.opt_aider = tk.BooleanVar(value=True)
        ttk.Checkbutton(modules_frame, text="💻 Aider (Programador IA CLI, solo bajo demanda)",
                        variable=self.opt_aider).pack(anchor="w", pady=3)

        # Info
        info_frame = ttk.LabelFrame(parent, text="📊 Estimación de uso de RAM", padding=10)
        info_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(info_frame, text=f"RAM detectada: {ram_gb}GB").pack(anchor="w")
        ttk.Label(info_frame, text="Base (Ollama + Open WebUI + modelo): ~3.5GB").pack(anchor="w")
        ttk.Label(info_frame, text="Whoogle: +200MB | Qdrant: +1GB").pack(anchor="w")
        ttk.Label(info_frame, text="💡 Aider se lanza bajo demanda (profiles: cli)").pack(anchor="w")
        ttk.Label(info_frame, text="   → Solo consume RAM cuando lo usas activamente").pack(anchor="w")

    def _build_advanced_tab(self, parent):
        f_net = ttk.LabelFrame(parent, text="Red y Puertos", padding=10)
        f_net.pack(fill="x", padx=10, pady=10)
        ttk.Label(f_net, text="Puerto de Open WebUI:").pack(side="left", padx=5, pady=5)
        ttk.Entry(f_net, textvariable=self.controller.webui_port, width=10).pack(side="left", padx=5, pady=5)

        f_res = ttk.LabelFrame(parent, text="Recursos", padding=10)
        f_res.pack(fill="x", padx=10, pady=10)
        ttk.Checkbutton(f_res, text="Permitir Aceleración de GPU (NVIDIA)",
                        variable=self.controller.use_gpu).pack(anchor="w", padx=5, pady=5)

    def _extract_model_name(self, raw_selection: str) -> str:
        """Extrae el nombre técnico del modelo de la selección del catálogo."""
        if "|" in raw_selection:
            return raw_selection.split("|")[0].strip()
        return raw_selection.strip()

    def _on_next(self):
        """Valida la configuración y avanza a la instalación."""
        raw_model = self.selected_model_combo.get()
        if raw_model.startswith("---") or raw_model.strip() == "":
            messagebox.showwarning("Selección Inválida",
                                   "Por favor selecciona un modelo válido de la lista.")
            return

        clean_model = self._extract_model_name(raw_model)
        self.controller.selected_base_model.set(clean_model)

        port_str = self.controller.webui_port.get()
        if not port_str.isdigit() or not (1024 <= int(port_str) <= 65535):
            self.lbl_error.config(text="⚠️ El puerto debe ser un número entre 1024 y 65535.")
            return

        port_num = int(port_str)
        
        # --- NEW PORT DETECTION (Auto Increment) ---
        if hasattr(self.controller, 'detector'):
            # Encontrar un puerto libre desde el deseado
            free_port = port_num
            while not self.controller.detector.is_port_free(free_port):
                free_port += 1
                if free_port > 65535:
                    self.lbl_error.config(text=f"⚠️ No se encontraron puertos libres alrededor del {port_num}.")
                    return

            if free_port != port_num:
                self.lbl_error.config(text=f"💡 Puerto {port_num} ocupado. Se utilizará {free_port} automáticamente.")
                # Auto update UI field to reflect the chosen port
                self.controller.webui_port.set(str(free_port))
                port_num = free_port
        else:
           self.lbl_error.config(text="")

        # Consolidar sabores
        base = self.controller.selected_base_model.get()
        self.controller.flavors_dict = {
            "memex-coder": self.controller.flavor_coder.get() or base,
            "memex-marketer": self.controller.flavor_marketer.get() or base,
            "memex-researcher": self.controller.flavor_researcher.get() or base,
            "memex-editor": self.controller.flavor_editor.get() or base,
        }

        # Guardar opciones de módulos
        self.controller.include_whoogle = self.opt_whoogle.get()
        self.controller.include_qdrant = self.opt_qdrant.get()
        self.controller.include_aider = self.opt_aider.get()

        # Generar configuración dinámica
        self.controller.installer_core.cfg_mgr.generate_env(
            ram_gb=self.controller.ram_gb,
            use_gpu=self.controller.use_gpu.get(),
            custom_port=self.controller.webui_port.get()
        )
        self.controller.installer_core.cfg_mgr.generate_docker_compose(
            include_whoogle=self.opt_whoogle.get(),
            include_qdrant=self.opt_qdrant.get(),
            include_aider=self.opt_aider.get(),
            base_model=clean_model
        )

        # Avanzar a instalación
        self.controller.show_frame("ProgressFrame")
        self.controller.frames["ProgressFrame"].start_installation()
