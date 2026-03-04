#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
title: Memexicanisimos OS - Central Hub
author: Memexicanisimos Team
version: 5.0.0
description: |
  Instalador y Gestor unificado con interfaz de pestañas (Notebook).
  Detecta instalaciones previas y ofrece opciones de reinstalación,
  desinstalación, inyección de herramientas, descarga de modelos y monitorización.
  V5.0 incluye el Protocolo Génesis y advertencias de Aider/Docker.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import customtkinter as ctk
import threading
import subprocess
import os
import sys
import time
import urllib.request
import json

# Módulos internos de Memex
from installer.hardware import HardwareDetector
from installer.installer_core import InstallerCore
from installer.uninstaller import MemexUninstaller
from installer.docker_utils import DockerUtils
from installer.logger import MemexLogger
from installer.project_manager import ProjectManager
from installer.models_catalog import ModelsCatalog

logger = MemexLogger.get_logger()

# Directorio del proyecto (donde está este script)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso. Funciona en desarrollo y empaquetado con PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Dark")  # Themes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class MemexInstallerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🤠 Memexicanisimos OS 🌮 - Hub V6.0")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.resizable(True, True)

        # Configurar grid principal (1 fila x 2 columnas para el sidebar y main view)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Frame del Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)  # Empuja botones de abajo hacia el fondo

        # Logo / Texto del Sidebar
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Memex OS 🌮", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Botones de navegación (serán vinculados después de crear los frames)
        self.nav_buttons = {}
        
        # --- Contenedor Principal (Main View) ---
        self.main_container = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        # Redimensiona el ancho del frame interno si el canvas crece
        # Hardware detection
        self.detector = HardwareDetector()
        self.ram_gb = self.detector.get_ram_gb()
        self.cpu_threads = self.detector.get_cpu_threads()
        gpu = self.detector.get_gpu_info()
        self.gpu_name = gpu.get("name", "Desconocido")
        self.gpu_vendor = gpu.get("vendor", "Unknown")

        # Modelo recomendado según RAM
        if self.ram_gb >= 16:
            self.recommended_model = "deepseek-r1:7b"
        elif self.ram_gb >= 8:
            self.recommended_model = "qwen2.5:7b"
        else:
            self.recommended_model = "qwen2.5:1.5b"

        self.selected_model = tk.StringVar(value=self.recommended_model)
        self.install_docker = tk.BooleanVar(value=False)
        self.use_gpu = tk.BooleanVar(value=(self.gpu_vendor == "NVIDIA"))

        # Core installer
        self.installer_core = InstallerCore(workspace_path=os.path.join(PROJECT_DIR, "memex_workspace"))

        self.frames = {}
        self.current_frame = None

        # Widgets de progreso compartidos (se vinculan al frame activo)
        self.progress = None
        self.log_area = None
        self.btn_finish = None
        self.dash_log = None  # Mini consola del Dashboard
        self.btn_back_to_menu = None

        self._build_sidebar_buttons()
        self._build_frames()

        # Detectar si ya hay instalación y mostrar el frame adecuado
        if self._is_installed():
            self.show_frame("ManagementFrame")
        else:
            self.show_frame("WelcomeFrame")

    def _build_sidebar_buttons(self):
        # Botones creados dinámicamente según estado
        self.nav_buttons["WelcomeFrame"] = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, 
                                                         text="🏠 Bienvenida", fg_color="transparent", text_color=("gray10", "gray90"), 
                                                         hover_color=("gray70", "gray30"), anchor="w", 
                                                         command=lambda: self.show_frame("WelcomeFrame"))
        self.nav_buttons["WelcomeFrame"].grid(row=1, column=0, sticky="ew")

        self.nav_buttons["HardwareFrame"] = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, 
                                                         text="💻 Hardware", fg_color="transparent", text_color=("gray10", "gray90"), 
                                                         hover_color=("gray70", "gray30"), anchor="w", 
                                                         command=lambda: self.show_frame("HardwareFrame"))
        self.nav_buttons["HardwareFrame"].grid(row=2, column=0, sticky="ew")

        self.nav_buttons["ConfigFrame"] = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, 
                                                         text="⚙️ Configuración", fg_color="transparent", text_color=("gray10", "gray90"), 
                                                         hover_color=("gray70", "gray30"), anchor="w", 
                                                         command=lambda: self.show_frame("ConfigFrame"))
        self.nav_buttons["ConfigFrame"].grid(row=3, column=0, sticky="ew")

        self.nav_buttons["InstallFrame"] = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, 
                                                         text="⬇️ Instalación", fg_color="transparent", text_color=("gray10", "gray90"), 
                                                         hover_color=("gray70", "gray30"), anchor="w", 
                                                         command=lambda: self.show_frame("InstallFrame"), state="disabled")
        self.nav_buttons["InstallFrame"].grid(row=4, column=0, sticky="ew")

        self.nav_buttons["ManagementFrame"] = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, 
                                                         text="🛠️ Panel de Control", fg_color="transparent", text_color=("gray10", "gray90"), 
                                                         hover_color=("gray70", "gray30"), anchor="w", 
                                                         command=lambda: self.show_frame("ManagementFrame"))
        self.nav_buttons["ManagementFrame"].grid(row=5, column=0, sticky="ew")

    def _build_frames(self):
        self.frames["WelcomeFrame"] = self._create_welcome_frame()
        self.frames["HardwareFrame"] = self._create_hardware_frame()
        self.frames["ConfigFrame"] = self._create_config_frame()
        self.frames["InstallFrame"] = self._create_install_frame()
        self.frames["ManagementFrame"] = self._create_management_frame()

    def show_frame(self, frame_name):
        if self.current_frame:
            self.current_frame.grid_forget()
        self.current_frame = self.frames[frame_name]
        self.current_frame.grid(row=0, column=0, sticky="nsew")
        
        # Actualizar estado visual de los botones del sidebar
        for name, btn in self.nav_buttons.items():
            if name == frame_name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

    # ==================== DETECCIÓN DE INSTALACIÓN ====================

    def _is_installed(self):
        """Devuelve True si los contenedores de Memex existen (aunque estén detenidos)."""
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', 'name=memex-ollama', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=5
            )
            if 'memex-ollama' in result.stdout:
                return True
        except Exception:
            pass
        return os.path.exists(os.path.join(PROJECT_DIR, '.env'))

    # ==================== PANTALLA: BIENVENIDA ====================

    def _create_welcome_frame(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        f.grid_rowconfigure(0, weight=1)
        f.grid_rowconfigure(4, weight=1)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="🌮 Bienvenido a Memexicanisimos OS", font=ctk.CTkFont(size=24, weight="bold")).grid(row=1, column=0, pady=(40, 20))
        ctk.CTkLabel(f, text="El agente cognitivo local con memoria persistente.", font=ctk.CTkFont(size=14)).grid(row=2, column=0, pady=10)
        ctk.CTkLabel(f, text=(
            "Este instalador te guiará paso a paso para configurar Ollama,\n"
            "Open WebUI y las herramientas de memoria FTS5.\n\n"
            "El proceso detectará tus capacidades de hardware y ajustará\n"
            "automáticamente el entorno para garantizar cero colapsos de inferencia."
        ), font=ctk.CTkFont(size=14)).grid(row=3, column=0, pady=10)

        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=40, sticky="s")
        
        ctk.CTkButton(btn_frame, text="Salir", fg_color="gray", hover_color="#444444", command=self.quit).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="Siguiente ➔", command=lambda: self.show_frame("HardwareFrame")).grid(row=0, column=1, padx=10)
        return f

    # ==================== PANTALLA: HARDWARE ====================

    def _create_hardware_frame(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="🔍 Detección de Hardware", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=(20, 20))
        
        info_frame = ctk.CTkFrame(f, corner_radius=10)
        info_frame.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info_frame, text=f"💻 Procesador: {self.cpu_threads} Hilos detectados", font=ctk.CTkFont(size=14)).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(info_frame, text=f"🧠 Memoria RAM: {self.ram_gb} GB", font=ctk.CTkFont(size=14)).grid(row=1, column=0, sticky="w", padx=20, pady=5)
        ctk.CTkLabel(info_frame, text=f"🎮 Tarjeta Gráfica: {self.gpu_name}", font=ctk.CTkFont(size=14)).grid(row=2, column=0, sticky="w", padx=20, pady=5)

        disk_gb = self.detector.get_free_disk_space_gb()
        ctk.CTkLabel(info_frame, text=f"💾 Espacio Libre: {disk_gb} GB", font=ctk.CTkFont(size=14)).grid(row=3, column=0, sticky="w", padx=20, pady=(5, 20))

        ctk.CTkLabel(f, text=f"💡 Recomendamos el modelo: {self.recommended_model}", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2FA572").grid(row=2, column=0, pady=20)

        if disk_gb < 15:
            ctk.CTkLabel(f, text="⚠️ Poco espacio en disco. Necesitas al menos 15GB.", text_color="#FF8C00", font=ctk.CTkFont(size=14)).grid(row=3, column=0)

        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=40)
        
        ctk.CTkButton(btn_frame, text="🡄 Atrás", fg_color="gray", hover_color="#444444", command=lambda: self.show_frame("WelcomeFrame")).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="Siguiente ➔", command=lambda: self.show_frame("ConfigFrame")).grid(row=0, column=1, padx=10)
        return f

    # ==================== PANTALLA: CONFIGURACIÓN ====================

    def _create_config_frame(self):
        f = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        
        ctk.CTkLabel(f, text="⚙️ Configuración del Ecosistema", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))

        # --- Modelo Base Dinámico ---
        model_frame = ctk.CTkFrame(f, corner_radius=10)
        model_frame.pack(fill="x", padx=40, pady=5)
        
        ctk.CTkLabel(model_frame, text="Modelo Base Recomendado para tu Hardware", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))
        ctk.CTkLabel(model_frame, text="Selecciona el modelo principal que controlará el ecosistema.\n"
                                     "Estos modelos han sido filtrados para asegurar estabilidad en tu equipo.").pack(anchor="w", padx=15, pady=(0, 10))
        
        self.selected_model = tk.StringVar(value=self.recommended_model)
        
        # Opción de omitir descarga de modelo
        self.skip_model_download = tk.BooleanVar(value=False)
        skip_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        skip_frame.pack(anchor="w", padx=15, pady=(0, 5))
        ctk.CTkCheckBox(skip_frame, text="⏭️ No descargar modelo (tengo uno local para migrar)",
                        variable=self.skip_model_download, text_color="#F0AD4E").pack(anchor="w")
        ctk.CTkLabel(skip_frame, text="Usa esto si ya tienes modelos en tu Ollama local o planeas copiarlos manualmente.",
                  text_color="gray", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=25)
        
        # Grid scrolleable para los modelos
        models_grid = ctk.CTkScrollableFrame(model_frame, height=200)
        models_grid.pack(fill="x", padx=20, pady=(0, 15))
        
        # Obtener Top 10 según RAM
        top_models = ModelsCatalog.get_top_10_for_hardware(self.ram_gb)
        
        if top_models:
            for i, model in enumerate(top_models):
                row = i // 2
                col = i % 2
                
                # Card para cada modelo
                card = ctk.CTkFrame(models_grid, fg_color="#2b2b2b", corner_radius=8)
                card.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
                models_grid.grid_columnconfigure(col, weight=1)
                
                rb = ctk.CTkRadioButton(card, text=model.name, variable=self.selected_model, value=model.id, font=ctk.CTkFont(weight="bold"))
                rb.pack(anchor="w", padx=10, pady=(10, 2))
                ctk.CTkLabel(card, text=f"Categoría: {model.category} | Req: {model.ram_required_gb}GB RAM", text_color="gray", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=35)
                ctk.CTkLabel(card, text=model.description, text_color="#d0d0d0", font=ctk.CTkFont(size=11), wraplength=180, justify="left").pack(anchor="w", padx=35, pady=(0, 10))
                
                # Preseleccionar si coincide con la recomendación del HardwareDetector
                if self.recommended_model in model.id:
                    self.selected_model.set(model.id)
        else:
             ctk.CTkLabel(models_grid, text="⚠️ No se encontraron modelos seguros para esta cantidad de RAM.", text_color="#FF8C00").pack(pady=20)
             self.selected_model.set("qwen2.5:0.5b") # Fallback extremo

        # --- Perfiles de Instalación ---
        profile_frame = ctk.CTkFrame(f, corner_radius=10)
        profile_frame.pack(fill="x", padx=40, pady=5)
        ctk.CTkLabel(profile_frame, text="Perfiles de Instalación", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))

        self.install_profile = tk.StringVar(value="custom")
        self.cb_whoogle = None
        self.cb_qdrant = None
        self.cb_aider = None

        def set_profile(profile):
            self.install_profile.set(profile)
            state = "disabled" if profile != "custom" else "normal"
            if profile == "level1":
                self.opt_whoogle.set(False)
                self.opt_qdrant.set(False)
                self.opt_aider.set(False)
            elif profile == "level2":
                self.opt_whoogle.set(False)
                self.opt_qdrant.set(True)
                self.opt_aider.set(False)
            elif profile == "level3":
                self.opt_whoogle.set(True)
                self.opt_qdrant.set(True)
                self.opt_aider.set(True)
            for cb in (self.cb_whoogle, self.cb_qdrant, self.cb_aider):
                if cb:
                    cb.configure(state=state)

        profiles = [
            ("Nivel 1: Chat básico (Ollama + Open WebUI)", "level1"),
            ("Nivel 2: RAG (añade Qdrant)", "level2"),
            ("Nivel 3: Completo (SearxNG + Aider)", "level3"),
            ("Personalizado", "custom"),
        ]
        
        for text, value in profiles:
            ctk.CTkRadioButton(profile_frame, text=text, variable=self.install_profile,
                            value=value, command=lambda v=value: set_profile(v)).pack(anchor="w", padx=25, pady=5)
        
        # padding inferior manual
        ctk.CTkLabel(profile_frame, text="").pack(pady=2)

        # --- Módulos Opcionales (Checkboxes) ---
        modules_frame = ctk.CTkFrame(f, corner_radius=10)
        modules_frame.pack(fill="x", padx=40, pady=5)
        ctk.CTkLabel(modules_frame, text="Microservicios (Todos dockerizados)", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))

        self.opt_whoogle = tk.BooleanVar(value=True)
        self.cb_whoogle = ctk.CTkCheckBox(modules_frame, text="🌐 SearxNG (Buscador Privado ~200MB RAM)",
                                          variable=self.opt_whoogle)
        self.cb_whoogle.pack(anchor="w", padx=25, pady=5)

        self.opt_qdrant = tk.BooleanVar(value=self.ram_gb >= 8)
        self.cb_qdrant = ctk.CTkCheckBox(modules_frame, text="🗄️ Qdrant (Base Vectorial RAG ~1GB RAM)",
                                         variable=self.opt_qdrant)
        self.cb_qdrant.pack(anchor="w", padx=25, pady=5)

        self.opt_aider = tk.BooleanVar(value=True)
        self.cb_aider = ctk.CTkCheckBox(modules_frame, text="💻 Aider (Programador IA CLI, solo bajo demanda)",
                                        variable=self.opt_aider)
        self.cb_aider.pack(anchor="w", padx=25, pady=5)
        
        ctk.CTkLabel(modules_frame,
                  text="⚠️ Límite Docker: Aider correrá en contenedor aislado. Comandos como\n"
                       "'/run' se ejecutarán dentro del contenedor, no en tu PC anfitrión.\n"
                       "El audio (/voice) estará deshabilitado.",
                  text_color="#FF8C00", justify="left").pack(anchor="w", padx=35, pady=(0, 10))

        # --- Agente Génesis (opt-in) ---
        self.opt_genesis = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(modules_frame, text="🤖 Activar Agente Génesis (control físico ratón/teclado)",
                        variable=self.opt_genesis).pack(anchor="w", padx=25, pady=(8, 0))
        ctk.CTkLabel(modules_frame,
                  text="⚠️ El agente se ejecuta en TU MÁQUINA (no en Docker).\n"
                       "Puede mover el ratón y teclado. Cada acción pide permiso.\n"
                       "Abortar: ratón a esquina o Ctrl+C.",
                  text_color="#FF8C00", justify="left").pack(anchor="w", padx=35, pady=(0, 2))
                  
        gen_model_frame = ctk.CTkFrame(modules_frame, fg_color="transparent")
        gen_model_frame.pack(anchor="w", padx=35, pady=(0, 15))
        ctk.CTkLabel(gen_model_frame, text="Modelo para el agente:").pack(side="left")
        self.genesis_model = tk.StringVar(value="qwen2.5-coder:7b")
        ctk.CTkComboBox(gen_model_frame, variable=self.genesis_model, width=200,
                     values=["qwen2.5-coder:1.5b", "qwen2.5-coder:7b", "deepseek-r1:7b",
                             "llama3.1:8b", "qwen2.5:7b"]).pack(side="left", padx=10)

        # --- Identidad del Usuario ---
        user_frame = ctk.CTkFrame(f, corner_radius=10)
        user_frame.pack(fill="x", padx=40, pady=5)
        ctk.CTkLabel(user_frame, text="Identidad del Ecosistema", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))

        self.use_default_user = tk.BooleanVar(value=True)
        self.user_name = tk.StringVar(value="Memexicanisimos Memex")
        self.user_email = tk.StringVar(value="Memexicanisimos@memexicanisimos.com")
        self.user_password = tk.StringVar(value="MeMex")

        def toggle_user_fields():
            state = "disabled" if self.use_default_user.get() else "normal"
            for e in user_entries:
                e.configure(state=state)
            if self.use_default_user.get():
                self.user_name.set("Memexicanisimos Memex")
                self.user_email.set("Memexicanisimos@memexicanisimos.com")
                self.user_password.set("MeMex")

        ctk.CTkCheckBox(user_frame, text="Usar usuario predeterminado (recomendado)",
                        variable=self.use_default_user, command=toggle_user_fields).pack(anchor="w", padx=25, pady=5)

        fields = ctk.CTkFrame(user_frame, fg_color="transparent")
        fields.pack(fill="x", padx=35, pady=(5, 10))
        user_entries = []
        for i, (label, var, show) in enumerate([
            ("Nombre:", self.user_name, None),
            ("Email:", self.user_email, None),
            ("Contraseña:", self.user_password, "*"),
        ]):
            ctk.CTkLabel(fields, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=2)
            kw = {"show": show} if show else {}
            e = ctk.CTkEntry(fields, textvariable=var, width=200, state="disabled", **kw)
            e.grid(row=i, column=1, padx=5, pady=2)
            user_entries.append(e)

        # --- Docker y GPU ---
        check_frame = ctk.CTkFrame(f, corner_radius=10)
        check_frame.pack(fill="x", padx=40, pady=5)

        docker_installed = subprocess.run(['which', 'docker'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
        if not docker_installed:
            ctk.CTkCheckBox(check_frame, text="Instalar Docker y Docker Compose (Requerido)",
                            variable=self.install_docker).pack(anchor="w", padx=15, pady=(15, 5))
            self.install_docker.set(True)
        else:
            ctk.CTkLabel(check_frame, text="✅ Docker ya está instalado.", text_color="#2FA572").pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkCheckBox(check_frame, text="Habilitar aceleración de GPU (NVIDIA)",
                        variable=self.use_gpu).pack(anchor="w", padx=15, pady=(5, 15))

        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=20)
        
        ctk.CTkButton(btn_frame, text="🡄 Atrás", fg_color="gray", hover_color="#444444", command=lambda: self.show_frame("HardwareFrame")).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="🚀 Preparar e Instalar", command=self._start_fresh_install).grid(row=0, column=1, padx=10)
        
        return f

    # ==================== PANTALLA: PROGRESO ====================

    def _create_install_frame(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(f, text="⏳ Proceso en ejecución...", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=(20, 10))
        
        self.progress = ctk.CTkProgressBar(f, width=500, mode='indeterminate')
        self.progress.grid(row=1, column=0, pady=10)
        self.progress.start()
        
        # Log terminal falso
        self.log_area = ctk.CTkTextbox(f, height=250, width=700, fg_color="black", text_color="#00FF00", font=("Consolas", 12))
        self.log_area.grid(row=2, column=0, pady=20)
        
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=10)

        self.btn_finish = ctk.CTkButton(btn_frame, text="Finalizar", command=self.quit, state="disabled")
        self.btn_finish.grid(row=0, column=0, padx=10)
        
        # Botón para volver al menú de gestión
        self.btn_back_to_menu = ctk.CTkButton(btn_frame, text="🡄 Volver al Menú",
                                           command=lambda: self.show_frame("ManagementFrame"),
                                           state="disabled", fg_color="gray", hover_color="#444444")
        self.btn_back_to_menu.grid(row=0, column=1, padx=10)
        
        return f

    # ==================== PANTALLA: GESTIÓN ====================

    def _create_management_frame(self):
        f = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        ctk.CTkLabel(f, text="🤠 Panel de Control Memex", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(5, 3))
        ctk.CTkLabel(f, text="V6.0 Sentience Edition — El sistema está instalado.", font=ctk.CTkFont(size=14)).pack(pady=2)

        # ── Notebook con Pestañas -> CTkTabview ────────────────────────────
        notebook = ctk.CTkTabview(f)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        tab_power = notebook.add("🔌 Energía")
        tab_quick = notebook.add("🚀 Acceso")
        tab_conn = notebook.add("🔗 Conexiones")
        tab_solver = notebook.add("🆘 Solucionador")
        tab_tools = notebook.add("🛠️ Herramientas")
        tab_data = notebook.add("💾 Datos")
        tab_hw = notebook.add("⚙️ Hardware")
        tab_projects = notebook.add("📁 Proyectos")
        tab_danger = notebook.add("⚠️ Peligro")

        # ── Pestaña 1: Control de Energía ─────────────────────────
        ctk.CTkLabel(tab_power, text="Control Global:",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=(0, 5))
        ctk.CTkButton(tab_power, text="🟢 Encender Todo el Ecosistema",
                   command=lambda: self._exec_power_cmd("docker compose up -d"),
                   fg_color="#2FA572", hover_color="#1F754E", width=350).pack(pady=4)
        ctk.CTkButton(tab_power, text="🔄 Reiniciar Todo el Ecosistema",
                   command=lambda: self._exec_power_cmd("docker compose down && docker compose up -d"),
                   fg_color="#F0AD4E", hover_color="#D99A3E", width=350).pack(pady=4)
        ctk.CTkButton(tab_power, text="🔴 Apagar Todo y Liberar RAM",
                   command=lambda: self._exec_power_cmd("docker compose down"),
                   fg_color="#D9534F", hover_color="#A94442", width=350).pack(pady=4)

        ctk.CTkLabel(tab_power, text="Encendidos Parciales (Ahorro de RAM):",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=(15, 5))
        ctk.CTkButton(tab_power, text="🧠 Iniciar Solo Cerebro (Ollama + Open WebUI)",
                   command=lambda: self._exec_power_cmd("docker compose up -d ollama open-webui"),
                   width=350).pack(pady=4)
        ctk.CTkButton(tab_power, text="💻 Iniciar Solo Motor para Aider (Ollama)",
                   command=lambda: self._exec_power_cmd("docker compose up -d ollama"),
                   width=350).pack(pady=4)
        ctk.CTkButton(tab_power, text="🌐 Iniciar Solo Búsqueda (SearxNG)",
                   command=lambda: self._exec_power_cmd("docker compose up -d searxng"),
                   width=350).pack(pady=4)

        ctk.CTkLabel(tab_power, text="Servicios Avanzados:",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=(15, 5))
        ctk.CTkButton(tab_power, text="🤖 Encender Daemon (Meta-Agente de Fondo)",
                   command=lambda: self._exec_power_cmd("docker compose --profile daemon up -d daemon"),
                   width=350).pack(pady=4)
        ctk.CTkButton(tab_power, text="🟥 Apagar Daemon",
                   command=lambda: self._exec_power_cmd("docker compose --profile daemon stop daemon"),
                   fg_color="#D9534F", hover_color="#A94442", width=350).pack(pady=4)

        # ── Pestaña 2: Acceso Rápido ──────────────────────────────────────
        core_buttons = [
            ("🌐 Abrir Open WebUI (Cerebro)", self._open_webui),
            ("💻 Iniciar Aider (Creador de Apps)", self._open_aider),
            ("📊 Ver estado del sistema", self._show_status),
            ("📈 Abrir Grafana (Observabilidad)", self._open_grafana),
        ]
        for text, cmd in core_buttons:
            ctk.CTkButton(tab_quick, text=text, command=cmd, width=350).pack(pady=5)

        # ── Pestaña 3: Gestor de Conexiones ─────────────────────────────────
        self._build_connections_tab(tab_conn)

        # ── Pestaña 4: Solucionador (FAQ y Prompts IA) ──────────────────────
        self._build_solver_tab(tab_solver)

        # ── Pestaña 5: Herramientas ───────────────────────────────────────
        tool_buttons = [
            ("⚙️ Inyectar herramientas (setup_memex)", self._inject_tools),
            ("📥 Descargar modelos adicionales", self._download_models),
            ("🚀 Buscar Actualizaciones (Sistema)", self._update_system),
            ("🔄 Sincronizar / Upgrade Servicios", self._sync_services),
            ("🔧 Reparar/Reinstalar un Servicio", self._open_granular_reinstaller),
            ("💾 Migrar Docker a disco externo", self._show_docker_migration),
            ("🤖 Ejecutar Agente Génesis (Host)", self._run_genesis_agent),
            ("🔍 Diagnosticar conexión Open WebUI ↔ Ollama", self._run_diagnostic),
        ]
        
        # Tools in two columns for better space usage, inside a scrollable frame since there are many
        tools_scroll = ctk.CTkScrollableFrame(tab_tools, fg_color="transparent")
        tools_scroll.pack(fill="both", expand=True)
        
        for i, (text, cmd) in enumerate(tool_buttons):
            ctk.CTkButton(tools_scroll, text=text, command=cmd, width=350).pack(pady=5)

        # Interruptor de control físico
        self.allow_physical = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(tools_scroll, text="🖱️ Permitir control físico del ratón/teclado",
                        variable=self.allow_physical).pack(anchor="center", pady=(15, 5))
        ctk.CTkLabel(tools_scroll, text="  (El agente Génesis solo moverá el ratón si está activado)",
                  text_color="#FF8C00").pack(anchor="center")

        # ── Pestaña 4: Datos y Memorias ───────────────────────────────────
        ctk.CTkLabel(tab_data, text="Gestiona tus memorias SQLite FTS5 y respaldos cifrados",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=(15, 10))
        ctk.CTkButton(tab_data, text="📦 Exportar Respaldo Local",
                   command=self._export_memory, width=350).pack(pady=10)
        ctk.CTkButton(tab_data, text="🔄 Restaurar Respaldo",
                   command=self._import_memory, width=350).pack(pady=10)
                   
        # ── Pestaña 5: Rendimiento y Hardware ────────────
        ctk.CTkLabel(tab_hw, text="Ajuste Dinámico de RAM (Docker Limits)",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=(0, 10))
        ctk.CTkLabel(tab_hw, text="Prioriza recursos para Ollama limitando otros contenedores.",
                  text_color="gray").pack(pady=(0, 10))
                  
        # Qdrant Limit
        q_frame = ctk.CTkFrame(tab_hw, fg_color="transparent")
        q_frame.pack(fill="x", pady=5, padx=20)
        ctk.CTkLabel(q_frame, text="Límite Qdrant (RAM GB):", width=180, anchor="w").pack(side="left")
        self.qdrant_ram = tk.StringVar(value="2")
        ctk.CTkComboBox(q_frame, variable=self.qdrant_ram, values=["1", "2", "4", "Sin Límite"], width=120).pack(side="left")

        # WebUI Limit
        w_frame = ctk.CTkFrame(tab_hw, fg_color="transparent")
        w_frame.pack(fill="x", pady=5, padx=20)
        ctk.CTkLabel(w_frame, text="Límite Open WebUI (RAM GB):", width=180, anchor="w").pack(side="left")
        self.webui_ram = tk.StringVar(value="1")
        ctk.CTkComboBox(w_frame, variable=self.webui_ram, values=["0.5", "1", "2", "Sin Límite"], width=120).pack(side="left")
        
        def apply_limits():
            from installer.docker_manager import DockerManager
            import os
            compose_path = os.path.join(PROJECT_DIR, "docker-compose.yml")
            if not os.path.exists(compose_path):
                messagebox.showerror("Error", "No se encontró docker-compose.yml.")
                return
                
            q_limit = self.qdrant_ram.get()
            w_limit = self.webui_ram.get()
            success = DockerManager.apply_resource_limits(compose_path, "qdrant", q_limit)
            success = success and DockerManager.apply_resource_limits(compose_path, "open-webui", w_limit)
            
            if success:
                messagebox.showinfo("Éxito", "Límites aplicados al Compose.\nLos cambios surtirán efecto al reiniciar los contenedores.")
            else:
                messagebox.showwarning("Aviso", "Hubo un problema actualizando el YAML.")

        ctk.CTkButton(tab_hw, text="💾 Aplicar Límites al Compose", command=apply_limits, width=250).pack(pady=20)
        
        # ── Pestaña 6: Proyectos ─────────────────────────────────────────
        list_frame = ctk.CTkFrame(tab_projects, corner_radius=10)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        ctk.CTkLabel(list_frame, text="Proyectos existentes", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=5)

        # Usar un textbox en modo readonly como listbox en ctk 
        # (o usar frame scrolleable con botones, haremos frame con labels cliqueables o de radio)
        # Para mantener similitud simple, usamos un CTkScrollableFrame
        self.projects_list_frame = ctk.CTkScrollableFrame(list_frame)
        self.projects_list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        self.project_radio_var = tk.StringVar(value="")

        # Botones de proyectos
        btn_frame_proj = ctk.CTkFrame(tab_projects, fg_color="transparent")
        btn_frame_proj.pack(fill="x", pady=5)

        ctk.CTkButton(btn_frame_proj, text="🆕 Nuevo", command=self._create_project_dialog, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame_proj, text="✅ Establecer", command=self._set_active_project, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame_proj, text="🗑️ Eliminar", command=self._delete_project, fg_color="#D9534F", hover_color="#A94442", width=100).pack(side="left", padx=5)

        # Indicador de proyecto activo
        self.active_project_label = ctk.CTkLabel(tab_projects, text="Proyecto activo: Ninguno", font=ctk.CTkFont(size=13, weight='bold'))
        self.active_project_label.pack(pady=5)

        self._refresh_projects_list()

        # ── Pestaña 7: Zona de Peligro ────────────────────────────────────
        ctk.CTkLabel(tab_danger, text="Operaciones destructivas. Los datos pueden perderse.",
                  text_color="#FF8C00").pack(pady=(5, 15))

        danger_buttons = [
            ("🔄 Reinstalar (conservar memorias)", self._reinstall_keep),
            ("⚠️ Reinstalar (borrar todo)", self._reinstall_wipe),
            ("🔧 Desinstalación Granular", self._granular_uninstall),
            ("🧹 Desinstalar completamente", self._uninstall),
        ]
        for text, cmd in danger_buttons:
            ctk.CTkButton(tab_danger, text=text, command=cmd, width=350, fg_color="#D9534F", hover_color="#A94442").pack(pady=5)

        # ── Mini Consola de Registro (fuera del notebook) ─────────────────
        log_frame = ctk.CTkFrame(f, corner_radius=10)
        log_frame.pack(fill="x", padx=10, pady=(0, 3))
        ctk.CTkLabel(log_frame, text=" Registro de Actividad ", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=2)
        self.dash_log = ctk.CTkTextbox(log_frame, height=80, fg_color="black", text_color="#00FF00", font=("Consolas", 11))
        self.dash_log.pack(fill="x", padx=10, pady=5)
        self.dash_log.insert(tk.END, "🤠 Memex Dashboard V6.0 Iniciado.\n")
        self.dash_log.configure(state="disabled")

        # ── Monitor de espacio en disco ───────────────────────────────
        disk_frame = ctk.CTkFrame(f, fg_color="transparent")
        disk_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(disk_frame, text="💾 Espacio libre:").pack(side="left")
        self.disk_label = ctk.CTkLabel(disk_frame, text="", font=ctk.CTkFont(size=13, weight='bold'))
        self.disk_label.pack(side="left", padx=5)
        self._update_disk_space()

        return f

    # ==================== MÉTODOS DEL DASHBOARD ====================

    def _update_disk_space(self):
        """Actualiza el indicador de espacio en disco con color dinámico."""
        try:
            free_gb = self.detector.get_free_disk_space_gb()
            color = "#2FA572" if free_gb >= 15 else "#FF8C00"
            self.disk_label.configure(text=f"{free_gb} GB", text_color=color)
        except Exception:
            self.disk_label.configure(text="N/A", text_color="gray")
        self.after(60000, self._update_disk_space)  # Actualizar cada 60s

    def _show_docker_migration(self):
        """Muestra instrucciones para migrar Docker a un disco externo."""
        messagebox.showinfo("Migrar Docker a Disco Externo",
            "Para mover los datos de Docker a un disco externo:\n\n"
            "1. Detén Docker:\n"
            "   sudo systemctl stop docker\n\n"
            "2. Mueve el directorio de datos:\n"
            "   sudo mv /var/lib/docker /mnt/disco/docker\n\n"
            "3. Crea /etc/docker/daemon.json:\n"
            '   { "data-root": "/mnt/disco/docker" }\n\n'
            "4. Inicia Docker:\n"
            "   sudo systemctl start docker\n\n"
            "5. Verifica:\n"
            "   docker info | grep 'Docker Root Dir'\n\n"
            "⚠️ Asegúrate de que la ruta tenga permisos adecuados."
        )

    def _run_genesis_agent(self):
        """Lanza el agente Génesis en una terminal del host, con control físico condicional."""
        agent_path = os.path.join(PROJECT_DIR, "memex_workspace", "genesis_project", "genesis_agent.py")
        if not os.path.exists(agent_path):
            messagebox.showerror(
                "Agente No Encontrado",
                "El agente Génesis no existe en memex_workspace/genesis_project/.\n\n"
                "Opciones para generarlo:\n"
                "  1. Reinstala desde la GUI (el proceso lo crea automáticamente)\n"
                "  2. Enciende el Daemon (lo crea al arrancar)"
            )
            return

        confirm = messagebox.askyesno(
            "⚠️ Advertencia de Seguridad",
            "El Agente Génesis tendrá control del ratón y teclado (si está habilitado).\n\n"
            "Controles de seguridad:\n"
            "  • Cada fase pide permiso antes de ejecutarse\n"
            "  • Ctrl+C detiene el agente inmediatamente\n"
            "  • Mover el ratón a una esquina aborta el control físico\n\n"
            "¿Deseas continuar?"
        )
        if not confirm:
            return

        # Crear script wrapper que establece la variable de entorno
        wrapper_path = os.path.join(PROJECT_DIR, "memex_workspace", "run_agent.sh")
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(f"""#!/bin/bash
export MEMEX_ALLOW_PHYSICAL={"1" if self.allow_physical.get() else "0"}
cd "{os.path.dirname(agent_path)}"
pip install -r requirements.txt 2>/dev/null
python3 genesis_agent.py
read -p "Presiona Enter para cerrar..."
""")
        os.chmod(wrapper_path, 0o755)

        # Buscar terminal disponible y ejecutar el wrapper
        for term_cmd in [
            ["gnome-terminal", "--", "bash", "-c", f"bash {wrapper_path}"],
            ["xfce4-terminal", "-e", f"bash {wrapper_path}"],
            ["xterm", "-e", f"bash {wrapper_path}"],
        ]:
            try:
                subprocess.Popen(term_cmd)
                self.log("🤖 Agente Génesis lanzado con control físico " +
                         ("habilitado" if self.allow_physical.get() else "deshabilitado"))
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue

        messagebox.showinfo(
            "Terminal No Encontrada",
            f"No se encontró una terminal compatible.\n\n"
            f"Ejecuta manualmente:\n"
            f"  cd {os.path.dirname(agent_path)}\n"
            f"  export MEMEX_ALLOW_PHYSICAL={'1' if self.allow_physical.get() else '0'}\n"
            f"  pip install -r requirements.txt\n"
            f"  python3 genesis_agent.py"
        )

    # ==================== MÉTODOS DE PROYECTOS ====================

    def _refresh_projects_list(self):
        """Actualiza la lista de proyectos creando radiobuttons en el frame."""
        for widget in self.projects_list_frame.winfo_children():
            widget.destroy()
            
        projects = ProjectManager.list_projects()
        
        if not projects:
            ctk.CTkLabel(self.projects_list_frame, text="No hay proyectos todavía.", text_color="gray").pack(pady=10)
        else:
            for p in projects:
                rb = ctk.CTkRadioButton(self.projects_list_frame, text=p, variable=self.project_radio_var, value=p)
                rb.pack(anchor="w", pady=2, padx=5)
                
        active = ProjectManager.get_active_project()
        if active:
            self.active_project_label.configure(text=f"Proyecto activo: {active}")
        else:
            self.active_project_label.configure(text="Proyecto activo: Ninguno")

    def _on_project_select(self, event):
        """Selección en la lista (podría habilitar botones)."""
        pass

    def _create_project_dialog(self):
        """Diálogo para crear nuevo proyecto."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nuevo proyecto")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        # Asegurarse de que el diálogo se mantenga enfrente
        dialog.transient(self)
        dialog.after(200, lambda: dialog.grab_set())

        ctk.CTkLabel(dialog, text="Nombre del proyecto:").pack(pady=10)
        name_var = tk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=name_var, width=200)
        entry.pack(pady=5)
        entry.focus()

        def do_create():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre no puede estar vacío")
                return
            model = self.selected_model.get().strip()
            if not model:
                 messagebox.showerror("Error", "Debes seleccionar un modelo base.")
                 return
            success, msg = ProjectManager.create_project(name)
            if success:
                dialog.destroy()
                self._refresh_projects_list()
                messagebox.showinfo("Éxito", f"Proyecto '{name}' creado")
            else:
                messagebox.showerror("Error", msg)

        ctk.CTkButton(dialog, text="Crear", command=do_create).pack(pady=10)

    def _set_active_project(self):
        """Establece el proyecto seleccionado como activo."""
        project = self.project_radio_var.get()
        if not project:
            messagebox.showwarning("Selecciona", "Selecciona un proyecto de la lista")
            return
        success, msg = ProjectManager.set_active_project(project)
        if success:
            self._refresh_projects_list()
            messagebox.showinfo("Éxito", f"Proyecto activo: {project}")
        else:
            messagebox.showerror("Error", msg)

    def _delete_project(self):
        """Elimina el proyecto seleccionado (solo si no es el activo)."""
        project = self.project_radio_var.get()
        if not project:
            messagebox.showwarning("Selecciona", "Selecciona un proyecto de la lista")
            return
        active = ProjectManager.get_active_project()
        if project == active:
            messagebox.showerror("Error", "No puedes eliminar el proyecto activo")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar proyecto '{project}'? (se borrarán todos sus archivos)"):
            import shutil
            project_path = ProjectManager.get_project_path(project)
            shutil.rmtree(project_path)
            self._refresh_projects_list()

    # ==================== DIAGNÓSTICO ====================

    def _run_diagnostic(self):
        """Ejecuta el diagnóstico de red interno de Docker."""
        self._reset_progress_frame()
        threading.Thread(target=self._run_diagnostic_worker, daemon=True).start()

    def _run_diagnostic_worker(self):
        self.log("=== Ejecutando Diagnóstico de Red Docker Bridge ===")
        try:
            from installer.ai_controller import AIController
            
            # Verificación 1: Local / Host
            self.log("[*] Diagnosticando API de Ollama desde el Host...")
            host_alive = AIController.is_alive()
            if host_alive:
                self.log("  ✅ Ollama responde en localhost:11434")
            else:
                self.log("  ⚠️ Ollama no responde en localhost. ¿Está apagado?")

            # Verificación 2: Contenedor a Contenedor
            self.log("\n[*] Diagnosticando red interna (WebUI -> Ollama)...")
            net_ok, message = AIController.verify_docker_network("ollama")
            self.log(f"  {message}")
            if not net_ok:
                self.log("  [Sugerencia] Intenta ejecutar: docker network inspect memex_workspace_default")

        except Exception as e:
            self.log(f"Error imprevisto en diagnóstico: {e}")
        self._finish_progress("Cerrar")

    # ==================== MÉTODOS COMUNES ====================

    def log(self, message):
        """Agrega texto al área de log y al dash_log (100% thread-safe vía after)."""
        def _update_ui():
            if hasattr(self, 'log_area') and self.log_area:
                self.log_area.configure(state="normal")
                self.log_area.insert(tk.END, message + "\n")
                self.log_area.see(tk.END)
            if hasattr(self, 'dash_log') and self.dash_log:
                self.dash_log.configure(state="normal")
                self.dash_log.insert(tk.END, message + "\n")
                self.dash_log.see(tk.END)
                self.dash_log.configure(state="disabled")
        self.after(0, _update_ui)

    def _exec_power_cmd(self, cmd):
        """Ejecuta un comando de control de energía con feedback en el dashboard log."""
        def _worker():
            self.log(f"\n⚡ Ejecutando: {cmd}")
            
            # Auto-cleanup before starting containers to avoid name conflicts
            if " up " in cmd:
                parts = cmd.split(" up ")
                if len(parts) > 1:
                    args = parts[1].strip().split()
                    # Ignorar flags como -d o --force-recreate
                    services = [s for s in args if not s.startswith("-")]
                    
                    self.log("  🧹 Limpiando contenedores previos para evitar conflictos...")
                    if not services:
                        # Si no hay servicios específicos, es un "up" global
                        for svc in ["qdrant", "searxng", "ollama", "open-webui", "daemon", "aider"]:
                            self._force_stop_container(svc)
                    else:
                        # Limpiar solo los servicios solicitados
                        for svc in services:
                            self._force_stop_container(svc)
            
            try:
                process = subprocess.Popen(
                    cmd, shell=True, cwd=PROJECT_DIR,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in process.stdout:
                    self.log("  " + line.strip())
                process.wait()
                if process.returncode == 0:
                    self.log("✅ Comando ejecutado exitosamente.")
                else:
                    self.log(f"❌ Comando falló (código {process.returncode}).")
            except Exception as e:
                self.log(f"❌ Excepción: {e}")
                
            # If we just started services, refresh the connections tab
            if " up " in cmd or " start " in cmd or " down " in cmd or " stop " in cmd:
                self.after(2000, self._refresh_connections)
                
        threading.Thread(target=_worker, daemon=True).start()

    def _reset_progress_frame(self):
        """Limpia el frame de progreso para una nueva tarea."""
        self.show_frame("InstallFrame")
        self.log_area.delete(1.0, tk.END)
        self.btn_finish.configure(state="disabled", text="Finalizar", command=self.quit)
        self.btn_back_to_menu.configure(state="disabled")
        self.progress.configure(mode='indeterminate')
        self.progress.start()

    def _finish_progress(self, button_text="Cerrar", button_command=None):
        """Marca la tarea como finalizada en el frame de progreso."""
        def _update():
            self.progress.stop()
            self.progress.configure(mode='determinate')
            self.progress.set(1.0)
            
            cmd = button_command if button_command else self.quit
            self.btn_finish.configure(state="normal", text=button_text, command=cmd)
            self.btn_back_to_menu.configure(state="normal")
            
        self.after(0, _update)

    def _run_cmd(self, cmd, description):
        """Ejecuta un comando shell con log en tiempo real."""
        self.log(f"[*] {description}...")
        try:
            process = subprocess.Popen(
                cmd, shell=True, cwd=PROJECT_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                self.log("  " + line.strip())
            process.wait()
            if process.returncode != 0:
                self.log(f"[ERROR] Falló: {description}")
                return False
            return True
        except Exception as e:
            self.log(f"[ERROR] Excepción: {str(e)}")
            return False

    # Mapeo servicio-compose → nombre real del contenedor Docker
    CONTAINER_NAMES = {
        "ollama": "memex-ollama",
        "open-webui": "memex-webui",
        "qdrant": "memex-qdrant",
        "searxng": "memex-searxng",
        "daemon": "memex-daemon",
        "aider": "memex-aider-cli",
    }

    def _force_stop_container(self, service_name):
        """
        Detiene y elimina un contenedor de forma robusta.
        Usa docker directo con el nombre del contenedor (más fiable que compose).
        """
        container = self.CONTAINER_NAMES.get(service_name, f"memex-{service_name}")
        self.log(f"  🔧 Deteniendo y eliminando contenedor '{container}'...")
        # docker stop es graceful (SIGTERM + timeout), docker rm -f es forzado
        self._run_cmd(f"docker stop {container} 2>/dev/null || true", f"Deteniendo {container}")
        self._run_cmd(f"docker rm -f {container} 2>/dev/null || true", f"Eliminando {container}")

    def _get_current_port(self):
        """Lee el puerto configurado del .env, con fallback a docker inspect."""
        env_path = os.path.join(PROJECT_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("WEBUI_PORT="):
                        try:
                            return int(line.split("=", 1)[1].strip())
                        except ValueError:
                            pass
        # Fallback: pregunta a Docker directamente
        try:
            r = subprocess.run(
                ["docker", "port", "memex-webui", "8080"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip():
                return int(r.stdout.strip().split(":")[-1])
        except Exception:
            pass
        return 3000  # Default

    def _build_solver_tab(self, parent):
        """Construye la pestaña del Solucionador (FAQ y Generador de Prompts)."""
        ctk.CTkLabel(parent, text="🆘 Solucionador IA & FAQ",
                  font=ctk.CTkFont(size=16, weight='bold')).pack(pady=(10, 2))
        ctk.CTkLabel(parent, text="Diagnóstico y generación de prompts de ayuda",
                  text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 10))

        # --- SECCIÓN 1: FAQ Rápido ---
        faq_frame = ctk.CTkFrame(parent, corner_radius=8)
        faq_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(faq_frame, text="💡 Soluciones Rápidas", font=ctk.CTkFont(weight='bold')).pack(anchor="w", padx=10, pady=(5, 0))
        
        faqs = [
            ("Error 502 Bad Gateway en WebUI", "Open WebUI está arrancando (puede tardar 1-2 min). Revisa 'Conexiones' o espera."),
            ("The container name is already in use", "Usa los botones de '🔌 Energía' (como Reiniciar Todo) para limpiar conflictos automáticamente."),
            ("Ollama no responde / Modelos no cargan", "Apaga todo, haz clic en 'Limpiar Redes Huérfanas' (Peligro) y Reinicia el Ecosistema."),
            ("Quedarse sin RAM / Congelamientos", "Usa 'Apagar Todo y Liberar RAM'. Luego en 'Hardware', aplica 'Límites Conservadores'.")
        ]
        for issue, solution in faqs:
            lbl = ctk.CTkLabel(faq_frame, text=f"• {issue}: ", font=ctk.CTkFont(size=11, weight="bold"))
            lbl.pack(anchor="w", padx=15, pady=(2, 0))
            ctk.CTkLabel(faq_frame, text=solution, text_color="#A9A9A9", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=25, pady=(0, 2))

        # --- SECCIÓN 2: Generador de Prompts IA ---
        prompt_frame = ctk.CTkFrame(parent, corner_radius=8)
        prompt_frame.pack(fill="both", expand=True, padx=15, pady=(10, 5))
        
        ctk.CTkLabel(prompt_frame, text="🤖 Constructor de Prompt de Diagnóstico", font=ctk.CTkFont(weight='bold')).pack(anchor="w", padx=10, pady=5)
        ctk.CTkLabel(prompt_frame, text="Selecciona la app que falla para extraer sus logs y crear un prompt para la IA.", 
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)

        # Controles
        ctrl_frame = ctk.CTkFrame(prompt_frame, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=10)
        
        self.solver_svc_var = tk.StringVar(value="memex-ollama")
        services = ["memex-ollama", "open-webui", "memex-qdrant", "memex-searxng", "memex-daemon"]
        
        ctk.CTkComboBox(ctrl_frame, values=services, variable=self.solver_svc_var, width=200).pack(side="left", padx=(0, 10))
        ctk.CTkButton(ctrl_frame, text="🛠️ Generar Prompt Clínico", 
                      command=self._generate_ai_prompt, 
                      fg_color="#337AB7", hover_color="#286090").pack(side="left")

        # TextBox para el prompt generado
        self.solver_textbox = ctk.CTkTextbox(prompt_frame, height=120, font=ctk.CTkFont(family="monospace", size=10))
        self.solver_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.solver_textbox.insert("0.0", "Haz clic en 'Generar Prompt Clínico' para extraer los logs...")

        # Botón Copiar
        self.btn_copy_prompt = ctk.CTkButton(prompt_frame, text="📋 Copiar Prompt al Portapapeles", 
                                           command=self._copy_solver_prompt, 
                                           fg_color="#5CB85C", hover_color="#4CAE4C", state="disabled")
        self.btn_copy_prompt.pack(pady=(5, 10))

    def _generate_ai_prompt(self):
        """Extrae los logs del contenedor seleccionado y arma el prompt pre-formateado."""
        service = self.solver_svc_var.get()
        self.solver_textbox.delete("0.0", tk.END)
        self.solver_textbox.insert("0.0", f"Extrayendo últimos 100 logs de {service}...\n")
        self.btn_copy_prompt.configure(state="disabled", text="📋 Copiar Prompt al Portapapeles")
        self.update()

        def _worker():
            try:
                # Extraer logs
                result = subprocess.run(
                    ["docker", "logs", "--tail", "100", service],
                    capture_output=True, text=True, timeout=10
                )
                
                # Combine stdout and stderr for docker logs
                logs = result.stdout + "\n" + result.stderr
                logs = logs.strip()
                
                if not logs:
                    prompt = f"No pude extraer logs de {service}. ¿Está el contenedor creado?\nRevisa la pestaña 'Conexiones'."
                    self.after(0, lambda: self._update_solver_text(prompt, False))
                    return

                # Template del prompt
                prompt = (
                    "Soy administrador del sistema Memexicanisimos OS (un stack Docker de IA local). "
                    f"Estoy teniendo problemas con el contenedor '{service}'.\n\n"
                    "Por favor, revisa mis últimos 100 logs y dime:\n"
                    "1. ¿Cuál es la causa raíz del problema?\n"
                    "2. ¿Cuál es el comando exacto o la acción que debo realizar para solucionarlo?\n\n"
                    "=== INICIO DE LOGS MARKBOT ===\n"
                    "```log\n"
                    f"{logs[-3000:]}\n" # Limitar a los últimos 3000 caracteres por seguridad de portapapeles
                    "```\n"
                    "=== FIN DE LOGS ===\n"
                )
                self.after(0, lambda: self._update_solver_text(prompt, True))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self._update_solver_text("Error: Timeout al extraer logs de Docker.", False))
            except Exception as e:
                self.after(0, lambda: self._update_solver_text(f"Error extrayendo logs: {str(e)}", False))

        threading.Thread(target=_worker, daemon=True).start()

    def _update_solver_text(self, text, enable_copy):
        """Actualiza el textbox del solucionador."""
        self.solver_textbox.delete("0.0", tk.END)
        self.solver_textbox.insert("0.0", text)
        if enable_copy:
            self.btn_copy_prompt.configure(state="normal")
            
    def _copy_solver_prompt(self):
        """Copia el texto del solucionador al portapapeles."""
        text = self.solver_textbox.get("0.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.btn_copy_prompt.configure(text="✅ ¡Copiado!")
            self.after(2000, lambda: self.btn_copy_prompt.configure(text="📋 Copiar Prompt al Portapapeles"))

    def _check_service_status(self, container_name):
        """Verifica si un contenedor está corriendo. Retorna (running: bool, status: str)."""
        try:
            r = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                status = r.stdout.strip()
                return status == "running", status
        except Exception:
            pass
        return False, "no encontrado"

    def _build_connections_tab(self, parent):
        """Construye la pestaña de Gestor de Conexiones."""
        ctk.CTkLabel(parent, text="🔗 Gestor de Conexiones",
                  font=ctk.CTkFont(size=16, weight='bold')).pack(pady=(10, 5))
        ctk.CTkLabel(parent, text="Estado de los servicios y configuración de puertos",
                  text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 10))

        # Frame con scroll para las cards de servicios
        self.conn_scroll = ctk.CTkScrollableFrame(parent, height=250)
        self.conn_scroll.pack(fill="both", expand=True, padx=15, pady=5)

        self._refresh_connections()

        # Botones de acción
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="🔄 Refrescar Estado",
                   command=self._refresh_connections,
                   fg_color="#5CB85C", hover_color="#4CAE4C", width=180).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔀 Cambiar Puerto WebUI",
                   command=self._change_webui_port_dialog,
                   fg_color="#337AB7", hover_color="#286090", width=180).pack(side="left", padx=5)

    def _refresh_connections(self):
        """Refresca el estado de las conexiones de todos los servicios."""
        for widget in self.conn_scroll.winfo_children():
            widget.destroy()

        current_port = self._get_current_port()

        services = [
            ("🌐 Open WebUI", "memex-webui", f"Puerto: {current_port}", f"http://localhost:{current_port}"),
            ("🧠 Ollama", "memex-ollama", "Puerto: 11434 (interno)", None),
            ("🗄️ Qdrant", "memex-qdrant", "Puerto: 6333", "http://localhost:6333"),
            ("🔍 SearxNG", "memex-searxng", "Puerto: 8080 (interno)", None),
            ("🤖 Daemon", "memex-daemon", "Perfil: daemon", None),
        ]

        for label, container, port_info, url in services:
            running, status = self._check_service_status(container)

            card = ctk.CTkFrame(self.conn_scroll, corner_radius=8,
                              fg_color="#1a3a1a" if running else "#3a1a1a")
            card.pack(fill="x", pady=3, padx=5)
            card.grid_columnconfigure(1, weight=1)

            indicator = "🟢" if running else "🔴"
            status_text = "En línea" if running else status.capitalize()

            ctk.CTkLabel(card, text=f"{indicator} {label}",
                      font=ctk.CTkFont(size=13, weight='bold')).grid(
                          row=0, column=0, sticky="w", padx=10, pady=(8, 2))

            ctk.CTkLabel(card, text=f"{port_info}  —  {status_text}",
                      text_color="#90EE90" if running else "#FF6B6B",
                      font=ctk.CTkFont(size=11)).grid(
                          row=1, column=0, sticky="w", padx=10, pady=(0, 8))

            if url and running:
                ctk.CTkButton(card, text="Abrir ↗",
                           command=lambda u=url: __import__('webbrowser').open(u),
                           width=60, height=28,
                           fg_color="#337AB7", hover_color="#286090").grid(
                               row=0, column=1, rowspan=2, sticky="e", padx=10, pady=5)

        # Info del puerto actual
        info_frame = ctk.CTkFrame(self.conn_scroll, corner_radius=8, fg_color="#2b2b2b")
        info_frame.pack(fill="x", pady=(10, 3), padx=5)
        ctk.CTkLabel(info_frame, text=f"📍 Puerto WebUI en .env: {current_port}",
                  font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=5)
        ctk.CTkLabel(info_frame, text=f"🌐 URL: http://localhost:{current_port}",
                  text_color="#87CEEB", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(0, 5))

    def _change_webui_port_dialog(self):
        """Abre un diálogo para cambiar el puerto de Open WebUI."""
        current = self._get_current_port()

        win = ctk.CTkToplevel(self)
        win.title("🔀 Cambiar Puerto de Open WebUI")
        win.geometry("400x280")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        ctk.CTkLabel(win, text="🔀 Cambiar Puerto de Open WebUI",
                  font=ctk.CTkFont(size=15, weight='bold')).pack(pady=(15, 5))
        ctk.CTkLabel(win, text=f"Puerto actual: {current}",
                  text_color="gray").pack(pady=2)

        ctk.CTkLabel(win, text="Nuevo puerto:",
                  font=ctk.CTkFont(size=12)).pack(pady=(15, 3))
        port_var = tk.StringVar(value=str(current))
        port_entry = ctk.CTkEntry(win, textvariable=port_var, width=150,
                                justify="center", font=ctk.CTkFont(size=14))
        port_entry.pack(pady=5)

        # Mostrar puertos ocupados conocidos
        occupied = []
        for p in [3000, 3001, 3002, 3003, 3004, 3005]:
            if self._is_port_in_use(p) and p != current:
                occupied.append(str(p))
        if occupied:
            ctk.CTkLabel(win, text=f"⚠️ Puertos ocupados: {', '.join(occupied)}",
                      text_color="#FF8C00", font=ctk.CTkFont(size=10)).pack(pady=2)

        def do_change():
            try:
                new_port = int(port_var.get().strip())
            except ValueError:
                messagebox.showerror("Error", "El puerto debe ser un número válido.")
                return
            if new_port < 1024 or new_port > 65535:
                messagebox.showerror("Error", "El puerto debe estar entre 1024 y 65535.")
                return
            if new_port == current:
                win.destroy()
                return
            if self._is_port_in_use(new_port):
                if not messagebox.askyesno("⚠️ Puerto Ocupado",
                    f"El puerto {new_port} está en uso por otro servicio.\n\n"
                    f"¿Deseas usarlo de todas formas?\n"
                    f"(Esto podría causar conflictos)"):
                    return
            win.destroy()
            self._change_webui_port(new_port)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="✅ Aplicar Cambio", command=do_change,
                   fg_color="#5CB85C", hover_color="#4CAE4C").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", command=win.destroy,
                   fg_color="gray").pack(side="right", padx=5)

    def _change_webui_port(self, new_port):
        """Cambia el puerto de Open WebUI: actualiza .env, recrea contenedor."""
        self._reset_progress_frame()
        threading.Thread(target=self._change_port_worker, args=(new_port,), daemon=True).start()

    def _change_port_worker(self, new_port):
        """Worker para cambiar el puerto de Open WebUI."""
        self.log(f"=== Cambiando puerto de Open WebUI a {new_port} ===")

        # 1. Actualizar .env
        self.log("[1/4] Actualizando .env...")
        env_path = os.path.join(PROJECT_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            with open(env_path, 'w', encoding='utf-8') as f:
                found = False
                for line in lines:
                    if line.strip().startswith("WEBUI_PORT="):
                        f.write(f"WEBUI_PORT={new_port}\n")
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f"WEBUI_PORT={new_port}\n")
            self.log(f"  ✅ .env actualizado: WEBUI_PORT={new_port}")
        else:
            self.log("  ⚠️ No se encontró .env. Creando uno nuevo...")
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f"WEBUI_PORT={new_port}\n")

        # 2. Detener y eliminar contenedor
        self.log("[2/4] Deteniendo Open WebUI...")
        self._force_stop_container("open-webui")

        # 3. Recrear con nuevo puerto
        self.log(f"[3/4] Levantando Open WebUI en puerto {new_port}...")
        self._run_cmd("docker compose up -d open-webui", "Recreando Open WebUI")

        # 4. Esperar healthcheck
        self.log("[4/4] Esperando a que Open WebUI inicie...")
        self._wait_for_health(port=new_port)

        self.log(f"\n✅ Puerto cambiado exitosamente a {new_port}")
        self.log(f"🌐 Accede en: http://localhost:{new_port}")
        self._finish_progress("Cerrar")

        # Refrescar la pestaña de conexiones
        self.after(0, self._refresh_connections)

    def _wait_for_health(self, port=None, timeout=120):
        """Espera a que Open WebUI responda al healthcheck."""
        if port is None:
            port = self._get_current_port()
        self.log("[*] Esperando a que Open WebUI arranque (healthcheck)...")
        for i in range(timeout // 3):
            try:
                resp = urllib.request.urlopen(f"http://localhost:{port}/health", timeout=5)
                if resp.status == 200:
                    self.log("  ✅ Open WebUI está saludable.")
                    return True
            except Exception:
                pass
            self.log(f"  [{(i+1)*3}s] Esperando...")
            time.sleep(3)
        self.log("[!] Open WebUI no respondió al healthcheck en tiempo.")
        return False

    def _wait_for_flavors(self, port=None, timeout=120):
        """Espera a que los Sabores aparezcan en la API de Open WebUI."""
        expected = ["memex-coder", "memex-marketer", "memex-researcher", "memex-editor"]
        self.log("[*] Verificando que los Sabores estén disponibles...")
        for i in range(timeout // 5):
            try:
                resp = urllib.request.urlopen(f"http://localhost:{port}/api/models", timeout=5)
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    models_list = data if isinstance(data, list) else data.get("data", data.get("models", []))
                    model_ids = set()
                    for m in models_list:
                        if isinstance(m, dict):
                            model_ids.add(m.get("id", ""))
                            model_ids.add(m.get("name", "").lower())
                    found = [f for f in expected if f in model_ids]
                    if len(found) >= len(expected):
                        self.log(f"  ✅ ¡Todos los Sabores confirmados! ({', '.join(found)})")
                        return True
                    remaining = [f for f in expected if f not in model_ids]
                    self.log(f"  [{(i+1)*5}s] Faltantes: {remaining}")
            except Exception:
                pass
            time.sleep(5)
        self.log("[!] Algunos sabores no aparecieron. Recarga la página en unos segundos.")
        return False

    # ==================== INSTALACIÓN NUEVA ====================

    def _find_free_port(self, start=3000, end=3020):
        """Busca un puerto libre en el rango dado."""
        import socket
        for port in range(start, end):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    result = s.connect_ex(('127.0.0.1', port))
                    if result != 0:  # Puerto libre
                        return port
            except Exception:
                continue
        return None

    def _is_port_in_use(self, port):
        """Verifica si un puerto está en uso."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except Exception:
            return False

    def _start_fresh_install(self):
        # Verificar prerequisitos antes de todo
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror(
                "Docker No Encontrado",
                "Docker o Docker Compose no están instalados.\n\n"
                "Instala Docker primero:\n"
                "  curl -fsSL https://get.docker.com | sh\n"
                "  sudo usermod -aG docker $USER\n\n"
                "Después cierra sesión y vuelve a abrir."
            )
            return

        # --- Verificar puertos disponibles ---
        preferred_port = 3000
        if self._is_port_in_use(preferred_port):
            # Intentar identificar qué proceso usa el puerto
            try:
                result = subprocess.run(
                    ['ss', '-tlnp', f'sport = :{preferred_port}'],
                    capture_output=True, text=True, timeout=5
                )
                process_info = result.stdout.strip()
            except Exception:
                process_info = "No se pudo identificar el proceso."

            free_port = self._find_free_port(3001, 3020)
            if free_port:
                use_alt = messagebox.askyesno(
                    "⚠️ Puerto Ocupado",
                    f"El puerto {preferred_port} ya está en uso por otro servicio:\n\n"
                    f"{process_info}\n\n"
                    f"¿Deseas usar el puerto {free_port} en su lugar?\n"
                    f"(Open WebUI se abrirá en http://localhost:{free_port})"
                )
                if use_alt:
                    preferred_port = free_port
                else:
                    messagebox.showinfo(
                        "Instalación Cancelada",
                        f"Libera el puerto {preferred_port} y vuelve a intentar.\n\n"
                        "Puedes detener el servicio que lo usa o cambiar su configuración."
                    )
                    return
            else:
                messagebox.showerror(
                    "Sin Puertos Disponibles",
                    "No se encontró ningún puerto libre entre 3000-3020.\n"
                    "Libera algún puerto y vuelve a intentar."
                )
                return

        self._install_port = preferred_port

        # Obtener modelo seleccionado del catálogo dinámico
        clean_model = self.selected_model.get().strip()
        if not clean_model:
            clean_model = self.recommended_model

        # Generar docker-compose dinámico (antes de mostrar progress frame)
        self.installer_core.cfg_mgr.generate_env(
            ram_gb=self.ram_gb,
            use_gpu=self.use_gpu.get(),
            custom_port=preferred_port
        )
        self.installer_core.cfg_mgr.generate_docker_compose(
            include_whoogle=self.opt_whoogle.get(),
            include_qdrant=self.opt_qdrant.get(),
            include_aider=self.opt_aider.get(),
            base_model=clean_model,
            use_gpu=self.use_gpu.get()
        )

        self._reset_progress_frame()
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        self.log("=== Iniciando Instalación de Memex ===")
        port = getattr(self, '_install_port', None) or self._get_current_port()
        self.log(f"[*] Puerto configurado: {port}")

        # 1. Verificar entorno
        self.log("[*] Entorno .env y docker-compose.yml ya generados.")

        # 2. Workspace
        os.makedirs(os.path.join(PROJECT_DIR, "memex_workspace"), exist_ok=True)
        self.log("[*] Directorio memex_workspace verificado.")

        # 3. Docker Compose Up
        success = self._run_cmd("docker compose up -d", "Levantando infraestructura con Docker Compose")
        if not success:
            self.log("[!] Si docker compose falló, asegúrate de tener permisos o usar 'sudo'.")

        # 4. Descargar Modelo (condicional)
        if self.skip_model_download.get():
            self.log("\n[*] ⏭️ Descarga de modelo omitida por el usuario.")
            self.log("    💡 Para migrar tus modelos locales de Ollama:")
            self.log("       1. Copia tu carpeta ~/.ollama/models al volumen Docker:")
            self.log("          docker cp ~/.ollama/models memex-ollama:/root/.ollama/")
            self.log("       2. O descarga modelos después desde Panel de Control → Herramientas → Descargar modelos")
        else:
            modelo = self.selected_model.get()
            self.log(f"\n[*] Descargando modelo base ({modelo})...")
            self._run_cmd(
                f"docker compose exec -T ollama ollama pull {modelo}",
                f"Descargando modelo base ({modelo})"
            )

        # 5. Esperar healthcheck
        self._wait_for_health(port=port)

        # 6. Esperar sabores
        self._wait_for_flavors(port=port)

        # 7. Guardar configuración de usuario
        self.log("\n[*] Guardando configuración de usuario...")
        user_config = {
            "name": self.user_name.get(),
            "email": self.user_email.get(),
            "password": self.user_password.get(),
            "use_default": self.use_default_user.get()
        }
        config_path = os.path.join(PROJECT_DIR, "memex_workspace", "memex_user.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4)
            self.log("  ✅ memex_user.json creado.")
        except Exception as e:
            self.log(f"  ⚠️ Error guardando usuario (no crítico): {e}")

        # 8. Protocolo Génesis (condicional)
        if self.opt_genesis.get():
            self.log("\n⚡ [Génesis] Generando agente autónomo...")
            genesis_dir = os.path.join(PROJECT_DIR, "memex_workspace", "genesis_project")
            if not os.path.exists(genesis_dir):
                try:
                    genesis_src = os.path.join(PROJECT_DIR, "daemon", "genesis_protocol.py")
                    if os.path.exists(genesis_src):
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("genesis_protocol", genesis_src)
                        gp = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(gp)
                        gp.WORKSPACE_DIR = genesis_dir
                        gp.AGENT_FILE = os.path.join(genesis_dir, "genesis_agent.py")
                        gp.REQ_FILE = os.path.join(genesis_dir, "requirements.txt")
                        # Inyectar el modelo elegido en el código del agente
                        chosen_model = self.genesis_model.get()
                        gp.GENESIS_CODE = gp.GENESIS_CODE.replace(
                            'MODEL = "qwen2.5-coder:7b"',
                            f'MODEL = "{chosen_model}"'
                        )
                        gp.trigger_genesis_creation()
                        self.log(f"  ✅ Proyecto Génesis creado (modelo: {chosen_model})")
                        self.log("  📋 Para activar: Herramientas → Ejecutar Agente Génesis")
                    else:
                        self.log("  ⚠️ daemon/genesis_protocol.py no encontrado.")
                except Exception as e:
                    self.log(f"  ⚠️ Error en Génesis (no crítico): {e}")
            else:
                self.log("  Proyecto Génesis ya existe.")
        else:
            self.log("\n[*] Agente Génesis no activado (omitido por el usuario).")

        self.log("\n=== Instalación V5.0 Finalizada ===")
        self._finish_progress("Abrir Open WebUI", self._open_webui)

    # ==================== FUNCIONES DEL GESTOR ====================

    def _open_webui(self):
        """Abre Open WebUI en el navegador."""
        import webbrowser
        port = self._get_current_port()
        webbrowser.open(f'http://localhost:{port}')

    def _open_grafana(self):
        """Abre Grafana (Observabilidad) en el navegador."""
        import webbrowser
        webbrowser.open('http://localhost:3001')

    def _open_aider(self):
        """Lanza Aider Dockerizado mediante DockerManager."""
        from installer.docker_manager import DockerManager
        
        model = self.selected_model.get() or "qwen2.5-coder:1.5b"
        success, msg = DockerManager.launch_aider(cwd=PROJECT_DIR)
        
        if success:
            messagebox.showinfo(
                "💻 Memex Builder",
                f"Aider lanzado con modelo: {model}\n\n"
                "💡 Flujo de trabajo:\n"
                "1. Describe lo que quieres crear\n"
                "2. Aider genera código y hace commit\n"
                "3. Escribe /exit para salir\n\n"
                f"Los archivos se crean en: memex_workspace/"
            )
        else:
            if "fallback" in msg:
                messagebox.showinfo("Comando Aider", f"Ejecuta este comando en tu terminal:\n\n{msg}")
            else:
                messagebox.showerror("Error de Aider", msg)

    def _granular_uninstall(self):
        """Desinstalación quirúrgica: elige qué servicios eliminar."""
        win = ctk.CTkToplevel(self)
        win.title("🔧 Desinstalación Granular")
        win.geometry("400x350")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        ctk.CTkLabel(win, text="Selecciona los servicios a eliminar:",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=10)
        ctk.CTkLabel(win, text="⚠️ Los datos asociados se perderán.",
                  text_color='#cc3333').pack(pady=2)

        services = [
            ("searxng", "🌐 SearxNG (Buscador Privado)", True),
            ("qdrant", "🗄️ Qdrant (Base vectorial RAG)", True),
            ("aider", "💻 Aider (Programador CLI)", True),
            ("ollama", "🧠 Ollama (Motor de IA)", False),
            ("open-webui", "🌐 Open WebUI (Interfaz)", False),
        ]

        service_vars = []
        for svc_name, label, default in services:
            var = tk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(win, text=label, variable=var)
            cb.pack(anchor='w', padx=30, pady=5)
            service_vars.append((svc_name, var))

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=15)

        def do_uninstall():
            selected = [name for name, var in service_vars if var.get()]
            if not selected:
                messagebox.showwarning("Nada seleccionado", "Selecciona al menos un servicio.")
                return
            if messagebox.askyesno("Confirmar",
                                   f"¿Eliminar estos servicios?\n\n" + "\n".join(f"• {s}" for s in selected)):
                win.destroy()
                self._reset_progress_frame()
                threading.Thread(target=self._granular_uninstall_worker,
                                 args=(selected,), daemon=True).start()

        ctk.CTkButton(btn_frame, text="🗑️ Eliminar Seleccionados", command=do_uninstall, fg_color="#D9534F", hover_color="#A94442").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", command=win.destroy, fg_color="gray").pack(side="right", padx=5)

    def _granular_uninstall_worker(self, services):
        self.log(f"=== Desinstalación Granular: {len(services)} servicios ===")
        for svc in services:
            self.log(f"\n[*] Eliminando {svc}...")
            self._force_stop_container(svc)
        self.log("\n✅ Desinstalación granular completada.")
        self.log("Nota: Los volúmenes nombrados se conservan. Usa 'docker volume prune' para limpiar.")
        self._finish_progress("Cerrar")

    def _open_granular_reinstaller(self):
        """Abre un popup para seleccionar qué contenedor reiniciar/recrear sin perder datos."""
        win = ctk.CTkToplevel(self)
        win.title("🔄 Reinstalador Granular")
        win.geometry("420x350")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        ctk.CTkLabel(win, text="¿Qué servicio presenta fallas y deseas recrear?",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=10)
        ctk.CTkLabel(win, text="(Esto no borra tus datos ni memorias)",
                  text_color="gray").pack(pady=2)

        selected_service = tk.StringVar(value="")

        services = [
            ("🌐 Open WebUI (Interfaz Web / Cerebro)", "open-webui"),
            ("🧠 Ollama (Motor de Modelos)", "ollama"),
            ("🗄️ Qdrant (Base de datos RAG)", "qdrant"),
            ("🌐 SearxNG (Buscador Privado)", "searxng"),
        ]
        for label, value in services:
            ctk.CTkRadioButton(win, text=label, variable=selected_service,
                            value=value).pack(anchor="w", padx=40, pady=5)

        def execute_reinstall():
            service = selected_service.get()
            if not service:
                messagebox.showwarning("Aviso", "Debes seleccionar un servicio.")
                return

            win.destroy()
            
            from installer.docker_manager import DockerManager
            DockerManager.execute_granular_reinstall(service=service)
            
            # Avisar al usuario pero el proceso corre de fondo
            messagebox.showinfo("Éxito", f"El proceso de regeneración para '{service}' ha iniciado en segundo plano. Revisa los logs.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Ejecutar Reparación",
                   command=execute_reinstall).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar",
                   command=win.destroy, fg_color="gray").pack(side="right", padx=5)

    def _sync_services(self):
        """
        Compara servicios definidos en docker-compose.yml vs los que están corriendo.
        Ofrece regenerar docker-compose y levantar servicios faltantes (ej: Aider).
        """
        win = ctk.CTkToplevel(self)
        win.title("🔄 Sincronizar Servicios")
        win.geometry("550x550")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        ctk.CTkLabel(win, text="🔄 Sincronización de Servicios",
                  font=ctk.CTkFont(size=16, weight='bold')).pack(pady=10)
        ctk.CTkLabel(win, text="Compara lo que debería estar corriendo vs lo que está activo.",
                  text_color="gray").pack(pady=2)

        status_text = ctk.CTkTextbox(win, height=200, width=500, fg_color="#1e1e1e", text_color="#d4d4d4",
                              font=("Consolas", 12), state="disabled")
        status_text.pack(padx=10, pady=10)

        def log_s(msg):
            status_text.configure(state="normal")
            status_text.insert(tk.END, msg + "\n")
            status_text.see(tk.END)
            status_text.configure(state="disabled")

        scan_data = {"defined": set(), "running": set(), "missing": set()}

        def do_scan():
            status_text.configure(state="normal")
            status_text.delete('1.0', tk.END)
            status_text.configure(state="disabled")
            
            log_s("Escaneando servicios...\n")
            try:
                result_def = subprocess.run(
                    ['docker', 'compose', 'config', '--services'],
                    capture_output=True, text=True, timeout=10, cwd=PROJECT_DIR
                )
                defined = set(result_def.stdout.strip().split('\n')) if result_def.returncode == 0 else set()
                defined.discard('')

                result_run = subprocess.run(
                    ['docker', 'compose', 'ps', '--services', '--filter', 'status=running'],
                    capture_output=True, text=True, timeout=10, cwd=PROJECT_DIR
                )
                running = set(result_run.stdout.strip().split('\n')) if result_run.returncode == 0 else set()
                running.discard('')

                log_s(f"Definidos en compose: {len(defined)}")
                for svc in sorted(defined):
                    icon = "✅" if svc in running else "❌"
                    log_s(f"  {icon} {svc}")

                # Aider usa profiles:cli, no aparece en ps
                missing = defined - running
                missing.discard('aider')  # No cuenta como faltante

                if missing:
                    log_s(f"\n⚠️ Servicios NO corriendo: {', '.join(sorted(missing))}")
                    log_s("\nPresiona '▶️ Levantar Faltantes' para iniciarlos.")
                else:
                    log_s("\n✅ Todos los servicios base están corriendo.")

                if 'aider' in defined:
                    log_s("\n💻 Aider: Disponible (profiles: cli, bajo demanda)")
                    log_s("   → Ejecuta ./memex_builder.sh para usarlo")
                elif self.ram_gb >= 12:
                    log_s(f"\n💡 Tu sistema tiene {self.ram_gb}GB RAM.")
                    log_s("   Puedes activar Aider con '⬆️ Regenerar Compose'.")

                scan_data["defined"] = defined
                scan_data["running"] = running
                scan_data["missing"] = missing

            except Exception as e:
                log_s(f"\n❌ Error: {e}")

        def regenerate_and_sync():
            """Regenera docker-compose.yml con Nivel 3 completo y levanta todo."""
            model = self.selected_model.get() or "qwen2.5-coder:1.5b"
            log_s("\n🔄 Regenerando docker-compose.yml (Nivel 3 + Aider)...")
            try:
                self.installer_core.cfg_mgr.generate_env(
                    ram_gb=self.ram_gb,
                    use_gpu=self.use_gpu.get(),
                    custom_port=3000
                )
                self.installer_core.cfg_mgr.generate_docker_compose(
                    include_whoogle=True,
                    include_qdrant=True,
                    include_aider=True,
                    base_model=model,
                    use_gpu=self.use_gpu.get()
                )
                log_s("✅ docker-compose.yml regenerado.")
                log_s("✅ memex_builder.sh + .aider.conf.yml generados.")
            except Exception as e:
                log_s(f"❌ Error: {e}")
                return
            win.destroy()
            self._reset_progress_frame()
            threading.Thread(target=self._sync_services_worker, args=(True,), daemon=True).start()

        def bring_up_missing():
            if not scan_data["missing"]:
                messagebox.showinfo("Todo OK", "Todos los servicios están corriendo.")
                return
            win.destroy()
            self._reset_progress_frame()
            threading.Thread(target=self._sync_services_worker, args=(False,), daemon=True).start()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text="🔍 Escanear", command=do_scan).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="⬆️ Regenerar Compose",
                   command=regenerate_and_sync, fg_color="#F0AD4E", hover_color="#EC971F", text_color="black").pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="▶️ Levantar Faltantes",
                   command=bring_up_missing, fg_color="#5CB85C", hover_color="#4CAE4C").pack(side="left", padx=4)

        ctk.CTkButton(win, text="Cerrar", command=win.destroy, fg_color="gray").pack(pady=8)

        # Auto-scan al abrir
        win.after(200, do_scan)

    def _sync_services_worker(self, regenerated=True):
        """Worker que levanta todos los servicios definidos en compose."""
        if regenerated:
            self.log("=== Sincronización: Levantando stack completo (Nivel 3) ===")
        else:
            self.log("=== Sincronización: Levantando servicios faltantes ===")

        success = self._run_cmd(
            "docker compose up -d",
            "Levantando todos los servicios definidos"
        )

        if success:
            self.log("\n✅ Todos los servicios sincronizados y corriendo.")
            self.log("[*] Re-inyectando herramientas de Memex...")
            self._run_cmd(
                "docker compose exec -T open-webui python /app/backend/setup_memex.py",
                "Ejecutando setup_memex.py"
            )
            self.log("\n💡 Si activaste Aider, ejecuta:")
            self.log("   ./memex_builder.sh")
        else:
            self.log("\n❌ Error durante la sincronización. Revisa los logs de Docker.")

        self._finish_progress("Cerrar")

    def _reinstall_keep(self):
        if messagebox.askyesno("Confirmar", "¿Reinstalar Memex conservando tus memorias?\n(Los volúmenes de datos se mantendrán)"):
            self._reset_progress_frame()
            threading.Thread(target=self._reinstall_worker, args=(True,), daemon=True).start()

    def _reinstall_wipe(self):
        if messagebox.askyesno("⚠️ Confirmar", "¿Reinstalar borrando TODAS LAS MEMORIAS?\n\nEsta acción es IRREVERSIBLE."):
            self._reset_progress_frame()
            threading.Thread(target=self._reinstall_worker, args=(False,), daemon=True).start()

    def _reinstall_worker(self, keep_volumes):
        self.log("=== Reinstalando Memex ===")
        if keep_volumes:
            self._run_cmd("docker compose down", "Deteniendo contenedores (conservando volúmenes)")
        else:
            self._run_cmd("docker compose down -v", "Eliminando contenedores y volúmenes")
        time.sleep(2)
        self._install_worker()

    def _update_system(self):
        """Abre un diálogo para seleccionar qué servicios actualizar."""
        win = ctk.CTkToplevel(self)
        win.title("🚀 Actualizar Servicios")
        win.geometry("400x350")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        ctk.CTkLabel(win, text="Selecciona qué componentes actualizar:",
                  font=ctk.CTkFont(size=14, weight='bold')).pack(pady=10)
        ctk.CTkLabel(win, text="Tus datos y memorias se conservarán.",
                  text_color="gray").pack(pady=2)

        services = [
            ("ollama", "🧠 Ollama (Motor de IA)"),
            ("open-webui", "🌐 Open WebUI (Interfaz)"),
            ("qdrant", "🗄️ Qdrant (Base Vectorial)"),
            ("searxng", "🔍 SearxNG (Buscador)"),
        ]

        svc_vars = []
        for svc_name, label in services:
            var = tk.BooleanVar(value=(svc_name in ("ollama", "open-webui")))
            cb = ctk.CTkCheckBox(win, text=label, variable=var)
            cb.pack(anchor='w', padx=30, pady=5)
            svc_vars.append((svc_name, var))

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=15)

        def do_update():
            selected = [name for name, var in svc_vars if var.get()]
            if not selected:
                messagebox.showwarning("Nada seleccionado", "Selecciona al menos un servicio.")
                return
            win.destroy()
            self._reset_progress_frame()
            threading.Thread(target=self._update_system_worker, args=(selected,), daemon=True).start()

        ctk.CTkButton(btn_frame, text="⬆️ Actualizar Seleccionados", command=do_update,
                   fg_color="#5CB85C", hover_color="#4CAE4C").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", command=win.destroy, fg_color="gray").pack(side="right", padx=5)

    def _update_system_worker(self, services):
        self.log(f"=== Actualizando {len(services)} servicio(s) ===")
        port = self._get_current_port()

        for i, svc in enumerate(services, 1):
            self.log(f"\n[{i}/{len(services)}] ⬆️ Actualizando {svc}...")
            # Pull new image
            success = self._run_cmd(
                f"docker compose pull {svc}",
                f"Descargando última imagen de {svc}"
            )
            if success:
                # Stop and remove old container robustly
                self._force_stop_container(svc)
                # Recreate container with new image
                self._run_cmd(
                    f"docker compose up -d {svc}",
                    f"Levantando {svc} con la nueva imagen"
                )
                # Para Ollama, verificar la versión actualizada
                if svc == "ollama":
                    self.log("  ⏳ Esperando a que Ollama inicie...")
                    import time
                    time.sleep(8)  # Dar tiempo a que el servicio arranque
                    self.log("  🔄 Verificando versión actualizada de Ollama...")
                    self._run_cmd(
                        "docker exec memex-ollama ollama --version",
                        "Verificando versión de Ollama"
                    )
                self.log(f"  ✅ {svc} actualizado.")
            else:
                self.log(f"  ❌ Error actualizando {svc}. Revisa tu conexión a Internet.")

        # Re-inject tools if Open WebUI was updated
        if "open-webui" in services:
            self.log("\n[+] Re-inyectando herramientas de Memex en Open WebUI...")
            DockerUtils.exec_in_container("open-webui", ["python", "setup_memex.py"], cwd=PROJECT_DIR)
            self._wait_for_health(port=port)

        self.log("\n✅ Actualización completada.")
        self._finish_progress("Cerrar")

    def _uninstall(self):
        if messagebox.askyesno("🧹 Confirmar Desinstalación",
                               "¿Estás seguro de que quieres desinstalar Memex?\n\n"
                               "Se eliminarán:\n"
                               "• Contenedores Docker\n"
                               "• Volúmenes (modelos y base de datos)\n"
                               "• Archivos de configuración (.env)\n"
                               "• Workspace local (memorias)"):
            self._reset_progress_frame()
            threading.Thread(target=self._uninstall_worker, daemon=True).start()

    def _uninstall_worker(self):
        self.log("=== Iniciando Desinstalación ===")
        try:
            success = MemexUninstaller.uninstall(keep_data=False, cwd=PROJECT_DIR)
            if success:
                self.log("✅ Desinstalación completada correctamente.")
            else:
                self.log("❌ Hubo problemas durante la desinstalación (revisa los logs).")
        except Exception as e:
            self.log(f"❌ Excepción: {e}")
        self._finish_progress("Cerrar")

    def _inject_tools(self):
        if messagebox.askyesno("Confirmar", "¿Ejecutar setup_memex.py para inyectar/actualizar herramientas?"):
            self._reset_progress_frame()
            threading.Thread(target=self._inject_tools_worker, daemon=True).start()

    def _inject_tools_worker(self):
        self.log("[*] Ejecutando setup_memex.py en el contenedor open-webui...")
        success = DockerUtils.exec_in_container("open-webui", ["python", "setup_memex.py"], cwd=PROJECT_DIR)
        if success:
            self.log("✅ Herramientas inyectadas correctamente.")
        else:
            self.log("❌ Falló la inyección. Revisa los logs del contenedor.")
        self._finish_progress("Cerrar")

    def _download_models(self):
        """Abre una ventana con modelos del catálogo agrupados por categoría + entrada personalizada."""
        from installer.ai_controller import AIController
        installed = AIController.get_installed_models()
        grouped = ModelsCatalog.get_all_for_download(self.ram_gb, installed)

        win = ctk.CTkToplevel(self)
        win.title("📥 Descargar Modelos")
        win.geometry("550x550")
        win.resizable(False, False)
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        ctk.CTkLabel(win, text="📥 Centro de Descarga de Modelos",
                  font=ctk.CTkFont(size=16, weight='bold')).pack(pady=(10, 2))
        ctk.CTkLabel(win, text=f"RAM detectada: {self.ram_gb}GB — Los modelos compatibles están habilitados.",
                  text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=(0, 5))

        if installed:
            ctk.CTkLabel(win, text=f"✅ Instalados: {', '.join(installed[:5])}{'...' if len(installed) > 5 else ''}",
                      text_color="#2FA572", font=ctk.CTkFont(size=10)).pack(pady=(0, 5))

        # Scrollable area for model cards
        scroll = ctk.CTkScrollableFrame(win, height=300)
        scroll.pack(fill="both", expand=True, padx=15, pady=5)

        model_vars = []
        category_order = ["General", "Coder", "Reasoning", "Embedding"]
        category_icons = {"General": "🧠", "Coder": "💻", "Reasoning": "🔬", "Embedding": "📐"}

        for cat in category_order:
            if cat not in grouped:
                continue
            items = grouped[cat]
            icon = category_icons.get(cat, "📦")

            ctk.CTkLabel(scroll, text=f"{icon} {cat}",
                      font=ctk.CTkFont(size=13, weight='bold')).pack(anchor="w", padx=5, pady=(10, 3))

            for entry in items:
                m = entry["model"]
                fits = entry["fits"]
                is_installed = entry["installed"]

                card = ctk.CTkFrame(scroll, fg_color="#2b2b2b" if fits else "#1a1a1a", corner_radius=6)
                card.pack(fill="x", pady=2, padx=5)

                var = tk.BooleanVar(value=False)

                if is_installed:
                    ctk.CTkLabel(card, text=f"✅ {m.name} ({m.size_b}B) — Instalado",
                              text_color="#2FA572", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=5)
                elif fits:
                    cb = ctk.CTkCheckBox(card, text=f"{m.name} ({m.size_b}B) — Req: {m.ram_required_gb}GB",
                                       variable=var, font=ctk.CTkFont(size=11))
                    cb.pack(anchor="w", padx=10, pady=(5, 1))
                    ctk.CTkLabel(card, text=m.description, text_color="gray",
                              font=ctk.CTkFont(size=9)).pack(anchor="w", padx=35, pady=(0, 5))
                    model_vars.append((m.id, var))
                else:
                    ctk.CTkLabel(card, text=f"⚠️ {m.name} ({m.size_b}B) — Necesita {m.ram_required_gb}GB",
                              text_color="#666666", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=5)

        # Custom model entry
        ctk.CTkLabel(scroll, text="✏️ Modelo Personalizado",
                  font=ctk.CTkFont(size=13, weight='bold')).pack(anchor="w", padx=5, pady=(15, 3))
        ctk.CTkLabel(scroll, text="Escribe el nombre exacto de Ollama (ej: qwen3.5:9b, mistral:7b)",
                  text_color="gray", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10)
        self._custom_model_var = tk.StringVar(value="")
        ctk.CTkEntry(scroll, textvariable=self._custom_model_var, width=350,
                   placeholder_text="nombre-del-modelo:tag").pack(anchor="w", padx=10, pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="⬇️ Descargar Seleccionados",
                   command=lambda: self._download_selected(win, model_vars),
                   fg_color="#5CB85C", hover_color="#4CAE4C").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", command=win.destroy, fg_color="gray").pack(side="right", padx=5)

    def _download_selected(self, win, model_vars):
        selected = [m for m, var in model_vars if var.get()]
        
        # Add custom model if entered
        custom = self._custom_model_var.get().strip()
        if custom:
            selected.append(custom)
        
        win.destroy()
        if not selected:
            return
        self._reset_progress_frame()
        threading.Thread(target=self._download_worker, args=(selected,), daemon=True).start()

    def _download_worker(self, models):
        self.log(f"=== Descargando {len(models)} modelo(s) ===")
        # Asegurar que Ollama esté levantado
        self.log("[*] Verificando que Ollama esté en ejecución...")
        self._run_cmd("docker compose up -d ollama", "Iniciando Ollama si es necesario")
        for i, m in enumerate(models, 1):
            self.log(f"\n[{i}/{len(models)}] ⬇️ Descargando {m}...")
            DockerUtils.pull_model(m, cwd=PROJECT_DIR)
        self.log("\n✅ Todas las descargas completadas.")
        self._finish_progress("Cerrar")

    def _show_status(self):
        """Muestra el estado del sistema en una ventana emergente."""
        status_parts = []

        # Contenedores
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', 'name=memex',
                 '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
                capture_output=True, text=True, timeout=5
            )
            status_parts.append("=== 🐳 Contenedores ===\n" + (result.stdout or "No se pudo obtener info."))
        except Exception:
            status_parts.append("=== Contenedores ===\nError consultando Docker.\n")

        # Modelos instalados
        try:
            result = subprocess.run(
                ['docker', 'exec', 'memex-ollama', 'ollama', 'list'],
                capture_output=True, text=True, timeout=10
            )
            status_parts.append("=== 🤖 Modelos en Ollama ===\n" + (result.stdout or "No se pudo obtener lista."))
        except Exception:
            status_parts.append("=== Modelos ===\nContenedor Ollama no disponible.\n")

        # Hardware
        status_parts.append(
            f"=== 💻 Hardware ===\n"
            f"CPU: {self.cpu_threads} hilos\n"
            f"RAM: {self.ram_gb} GB\n"
            f"GPU: {self.gpu_name}\n"
            f"Disco libre: {self.detector.get_free_disk_space_gb()} GB\n"
        )

        # Ventana
        win = ctk.CTkToplevel(self)
        win.title("📊 Estado de Memexicanisimos")
        win.geometry("600x450")
        win.transient(self)
        win.after(200, lambda: win.grab_set())

        text = ctk.CTkTextbox(win, height=350, width=560, font=("Consolas", 12), fg_color="#1e1e1e", text_color="lightgreen")
        text.insert('1.0', "\n".join(status_parts))
        text.configure(state="disabled")
        text.pack(padx=10, pady=10)
        ctk.CTkButton(win, text="Cerrar", command=win.destroy, fg_color="gray").pack(pady=5)

    # ==================== RESPALDO Y RESTAURACIÓN DE MEMORIAS ====================

    def _export_memory(self):
        """Exporta memorias a un ZIP (con cifrado AES opcional)."""
        from installer.memory_tools import MemoryTools

        output_dir = filedialog.askdirectory(title="Selecciona dónde guardar el respaldo de Memex")
        if not output_dir:
            return

        password = simpledialog.askstring(
            "Contraseña de cifrado (Opcional)",
            "Ingresa una contraseña para cifrar el respaldo (AES).\nDéjalo en blanco para no cifrar:",
            show='*'
        )
        # simpledialog returns None on cancel, "" on empty OK
        if password is None:
            return
        password = password if password.strip() else None

        self._reset_progress_frame()
        threading.Thread(target=self._export_memory_worker, args=(output_dir, password), daemon=True).start()

    def _export_memory_worker(self, output_dir, password):
        from installer.memory_tools import MemoryTools

        self.log(f"[*] Iniciando respaldo en {output_dir}...")
        if password:
            self.log("  🔐 Cifrado AES habilitado.")

        success = MemoryTools.export_memory(output_dir=output_dir, password=password)

        if success:
            self.log("✅ Respaldo creado exitosamente.")
            self.after(0, lambda: messagebox.showinfo(
                "Éxito", f"El respaldo de tus memorias se guardó en:\n{output_dir}"
            ))
        else:
            self.log("❌ Error al crear el respaldo. Revisa los logs.")
            self.after(0, lambda: messagebox.showerror(
                "Error", "No se pudo crear el respaldo. Verifica que memex_memory.db exista."
            ))

        self._finish_progress("Cerrar")

    def _import_memory(self):
        """Restaura memorias desde un ZIP (con descifrado AES si aplica)."""
        if not messagebox.askyesno(
            "⚠️ Advertencia",
            "Restaurar un respaldo SOBRESCRIBIRÁ tus memorias actuales.\n\n"
            "¿Deseas continuar?"
        ):
            return

        zip_filepath = filedialog.askopenfilename(
            title="Selecciona el archivo ZIP de respaldo",
            filetypes=[("Archivos ZIP", "*.zip")]
        )
        if not zip_filepath:
            return

        password = simpledialog.askstring(
            "Contraseña de descifrado",
            "Ingresa la contraseña si el respaldo está cifrado.\nDéjalo en blanco si no lo está:",
            show='*'
        )
        if password is None:
            return
        password = password if password.strip() else None

        self._reset_progress_frame()
        threading.Thread(target=self._import_memory_worker, args=(zip_filepath, password), daemon=True).start()

    def _import_memory_worker(self, zip_filepath, password):
        from installer.memory_tools import MemoryTools

        self.log(f"[*] Importando respaldo desde {os.path.basename(zip_filepath)}...")
        if password:
            self.log("  🔐 Descifrado AES habilitado.")

        success = MemoryTools.import_memory(zip_filepath=zip_filepath, password=password, cwd=PROJECT_DIR)

        if success:
            self.log("✅ Memorias restauradas exitosamente.")
            self.log("[*] Open WebUI se reinició para aplicar los cambios.")
            self.after(0, lambda: messagebox.showinfo(
                "Éxito", "Memorias restauradas. Open WebUI se reinició automáticamente."
            ))
        else:
            self.log("❌ Error al restaurar. Contraseña incorrecta o archivo dañado.")
            self.after(0, lambda: messagebox.showerror(
                "Error", "No se pudo restaurar el respaldo.\nVerifica la contraseña e intenta de nuevo."
            ))

        self._finish_progress("Cerrar")


if __name__ == "__main__":
    app = MemexInstallerGUI()
    app.mainloop()
