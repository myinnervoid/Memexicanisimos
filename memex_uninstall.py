#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
title: Memexicanisimos OS - Desinstalador Gráfico
author: Memexicanisimos Team
version: 1.0.0
description: Desinstala Memexicanisimos limpiando contenedores, volúmenes, imágenes y archivos de configuración.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import sys
import shutil
import socket

# Directorio del proyecto (donde está este script)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


class MemexUninstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌮 Memexicanisimos OS - Desinstalador")
        self.geometry("700x520")
        self.configure(padx=20, pady=20)
        self.resizable(False, False)

        # Opciones de limpieza
        self.opt_containers = tk.BooleanVar(value=True)
        self.opt_volumes = tk.BooleanVar(value=True)
        self.opt_images = tk.BooleanVar(value=False)
        self.opt_config = tk.BooleanVar(value=True)
        self.opt_workspace = tk.BooleanVar(value=False)  # PELIGROSO: borra memorias
        self.opt_ollama_host = tk.BooleanVar(value=False)
        self.opt_prune = tk.BooleanVar(value=False)

        self.frames = {}
        self.current_frame = None

        self._create_styles()
        self._build_frames()
        self.show_frame("OptionsFrame")

    def _create_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 11))
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('TButton', font=('Helvetica', 10, 'bold'), padding=6)
        style.configure('Danger.TButton', font=('Helvetica', 10, 'bold'), padding=6)
        style.configure('Warning.TLabel', foreground='#cc6600', font=('Helvetica', 10, 'italic'))
        style.configure('Danger.TLabel', foreground='red', font=('Helvetica', 10, 'bold'))
        self.configure(bg='#f0f0f0')

    def _build_frames(self):
        self.frames["OptionsFrame"] = self._create_options_frame()
        self.frames["ProgressFrame"] = self._create_progress_frame()
        self.frames["DoneFrame"] = self._create_done_frame()

    def show_frame(self, frame_name):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.current_frame = self.frames[frame_name]
        self.current_frame.pack(fill="both", expand=True)

    # ==================== PANTALLAS ====================

    def _create_options_frame(self):
        f = ttk.Frame(self)
        ttk.Label(f, text="🗑️ Desinstalador de Memexicanisimos", style='Title.TLabel').pack(pady=(10, 15))
        ttk.Label(f, text="Selecciona qué componentes deseas eliminar:").pack(anchor="w", padx=20)

        # Opciones
        opts_frame = ttk.LabelFrame(f, text="Componentes Docker", padding=10)
        opts_frame.pack(fill="x", padx=20, pady=10)

        ttk.Checkbutton(opts_frame, text="Detener y eliminar contenedores (memex-ollama, memex-webui)",
                        variable=self.opt_containers).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts_frame, text="Eliminar volúmenes Docker (ollama_data, open-webui-data)",
                        variable=self.opt_volumes).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts_frame, text="Eliminar imágenes Docker (ollama, open-webui)",
                        variable=self.opt_images).pack(anchor="w", pady=2)
        ttk.Checkbutton(opts_frame, text="Limpiar volúmenes huérfanos (docker volume prune)",
                        variable=self.opt_prune).pack(anchor="w", pady=2)

        # Archivos locales
        files_frame = ttk.LabelFrame(f, text="Archivos Locales", padding=10)
        files_frame.pack(fill="x", padx=20, pady=10)

        ttk.Checkbutton(files_frame, text="Eliminar configuración (.env, flavors_config.json, install_state.json, logs)",
                        variable=self.opt_config).pack(anchor="w", pady=2)

        ws_check = ttk.Checkbutton(files_frame, text="⚠️ Eliminar memex_workspace (¡BORRA TODAS LAS MEMORIAS!)",
                                   variable=self.opt_workspace)
        ws_check.pack(anchor="w", pady=2)
        ttk.Label(files_frame, text="    Esto eliminará memex_memory.db, TODO.md, exportaciones y errores.",
                  style='Warning.TLabel').pack(anchor="w")

        # Host Ollama
        host_frame = ttk.LabelFrame(f, text="Sistema Host (Opcional)", padding=10)
        host_frame.pack(fill="x", padx=20, pady=10)

        ttk.Checkbutton(host_frame, text="Detener y desinstalar Ollama del host (systemd + apt)",
                        variable=self.opt_ollama_host).pack(anchor="w", pady=2)
        ttk.Label(host_frame, text="    Solo necesario si instalaste Ollama directamente (no Docker).",
                  style='Warning.TLabel').pack(anchor="w")

        # Botones
        btn_frame = ttk.Frame(f)
        btn_frame.pack(side="bottom", pady=15)
        ttk.Button(btn_frame, text="Cancelar", command=self.quit).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🗑️ Desinstalar", command=self._confirm_uninstall).pack(side="right", padx=10)
        return f

    def _create_progress_frame(self):
        f = ttk.Frame(self)
        ttk.Label(f, text="⏳ Desinstalando Memexicanisimos...", style='Title.TLabel').pack(pady=(20, 10))

        self.progress = ttk.Progressbar(f, mode='determinate', length=500, maximum=100)
        self.progress.pack(pady=10)

        self.lbl_status = ttk.Label(f, text="Preparando...")
        self.lbl_status.pack(pady=2)

        self.log_area = tk.Text(f, height=14, width=70, bg="black", fg="#ff6666", font=("Consolas", 9))
        self.log_area.pack(pady=10)

        self.btn_done = ttk.Button(f, text="Cerrar", command=self.quit, state="disabled")
        self.btn_done.pack(pady=10)
        return f

    def _create_done_frame(self):
        f = ttk.Frame(self)
        ttk.Label(f, text="✅ Desinstalación Completada", style='Title.TLabel').pack(pady=(60, 20))
        ttk.Label(f, text="Memexicanisimos ha sido eliminado de tu sistema.", justify="center").pack(pady=10)
        ttk.Label(f, text="Para reinstalar, ejecuta:\n\npython3 memex_gui.py",
                  justify="center", font=('Consolas', 11)).pack(pady=20)
        ttk.Button(f, text="Cerrar", command=self.quit).pack(pady=20)
        return f

    # ==================== LÓGICA ====================

    def _confirm_uninstall(self):
        # Verificar que al menos una opción está seleccionada
        any_selected = any([
            self.opt_containers.get(), self.opt_volumes.get(), self.opt_images.get(),
            self.opt_config.get(), self.opt_workspace.get(), self.opt_ollama_host.get(),
            self.opt_prune.get()
        ])
        if not any_selected:
            messagebox.showwarning("Sin selección", "Selecciona al menos un componente para desinstalar.")
            return

        # Advertencia especial si borra memorias
        if self.opt_workspace.get():
            confirm = messagebox.askyesno(
                "⚠️ Advertencia Crítica",
                "Vas a ELIMINAR el directorio memex_workspace.\n\n"
                "Esto borrará PERMANENTEMENTE:\n"
                "• Todas tus memorias (memex_memory.db)\n"
                "• Tareas (TODO.md)\n"
                "• Exportaciones y logs de errores\n\n"
                "¿Estás completamente seguro?",
                icon='warning'
            )
            if not confirm:
                return

        self.show_frame("ProgressFrame")
        threading.Thread(target=self._uninstall_worker, daemon=True).start()

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.update_idletasks()

    def set_progress(self, val, text):
        self.progress['value'] = val
        self.lbl_status.config(text=text)
        self.update_idletasks()

    def _run_cmd(self, cmd, description, allow_fail=False):
        self.log(f"[*] {description}...")
        try:
            process = subprocess.Popen(
                cmd, shell=True, cwd=PROJECT_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                self.log("  " + line.strip())
            process.wait()
            if process.returncode != 0 and not allow_fail:
                self.log(f"[!] Advertencia: {description} terminó con código {process.returncode}")
            return process.returncode == 0
        except Exception as e:
            self.log(f"[ERROR] {str(e)}")
            return False

    def _uninstall_worker(self):
        self.log("=" * 50)
        self.log("  DESINSTALACIÓN DE MEMEXICANISIMOS OS")
        self.log("=" * 50)

        total_steps = sum([
            self.opt_containers.get() or self.opt_volumes.get(),
            self.opt_prune.get(),
            self.opt_images.get(),
            self.opt_config.get(),
            self.opt_workspace.get(),
            self.opt_ollama_host.get(),
        ])
        step = 0

        def advance(text):
            nonlocal step
            step += 1
            pct = int((step / max(total_steps, 1)) * 100)
            self.set_progress(pct, text)

        # 1. Contenedores y volúmenes
        if self.opt_containers.get() or self.opt_volumes.get():
            if self.opt_volumes.get():
                advance("Deteniendo contenedores y eliminando volúmenes...")
                self._run_cmd("docker compose down -v -t 15", "docker compose down -v (contenedores + volúmenes)", allow_fail=True)
            else:
                advance("Deteniendo contenedores...")
                self._run_cmd("docker compose down -t 15", "docker compose down (solo contenedores)", allow_fail=True)

        # 2. Prune de volúmenes huérfanos
        if self.opt_prune.get():
            advance("Limpiando volúmenes huérfanos...")
            self._run_cmd("docker volume prune -f", "docker volume prune", allow_fail=True)

        # 3. Imágenes
        if self.opt_images.get():
            advance("Eliminando imágenes Docker...")
            self._run_cmd(
                "docker rmi ollama/ollama:latest ghcr.io/open-webui/open-webui:main 2>/dev/null",
                "Eliminando imágenes de Ollama y Open WebUI",
                allow_fail=True
            )

        # 4. Archivos de configuración
        if self.opt_config.get():
            advance("Eliminando archivos de configuración...")
            config_files = [".env", "memex_installer.log"]
            workspace_configs = [
                "memex_workspace/flavors_config.json",
                "memex_workspace/install_state.json",
                "memex_workspace/memex_errors.txt",
                "memex_workspace/memex_installer.log",
            ]
            for cf in config_files + workspace_configs:
                full = os.path.join(PROJECT_DIR, cf)
                if os.path.exists(full):
                    try:
                        os.remove(full)
                        self.log(f"  [-] Eliminado: {cf}")
                    except Exception as e:
                        self.log(f"  [!] No se pudo eliminar {cf}: {e}")

        # 5. Workspace completo
        if self.opt_workspace.get():
            advance("Eliminando memex_workspace (MEMORIAS)...")
            ws = os.path.join(PROJECT_DIR, "memex_workspace")
            if os.path.exists(ws):
                try:
                    shutil.rmtree(ws)
                    self.log("  [-] Directorio memex_workspace eliminado completamente.")
                except Exception as e:
                    self.log(f"  [!] Error eliminando workspace: {e}")
            else:
                self.log("  [-] memex_workspace no encontrado (ya limpio).")

        # 6. Ollama del host
        if self.opt_ollama_host.get():
            advance("Desinstalando Ollama del sistema host...")
            self._run_cmd("sudo systemctl stop ollama 2>/dev/null", "Deteniendo servicio Ollama", allow_fail=True)
            self._run_cmd("sudo systemctl disable ollama 2>/dev/null", "Deshabilitando servicio Ollama", allow_fail=True)
            # Intentar desinstalar via apt o eliminar binario
            self._run_cmd(
                "sudo apt remove -y ollama 2>/dev/null || sudo rm -f /usr/local/bin/ollama",
                "Removiendo binario de Ollama",
                allow_fail=True
            )
            # Limpiar directorio de Ollama del host
            self._run_cmd("sudo rm -rf /usr/share/ollama 2>/dev/null", "Limpiando archivos de Ollama", allow_fail=True)

        # 7. Finalizando (Eliminada comprobación dura al puerto 3000)
        self.log("")
        self.log("[*] Los procesos de desinstalación han concluido.")
        self.log("  Si experimentabas colisión de puertos previamente, los puertos configurados deberían estar libres ahora.")

        # Fin
        self.log("")
        self.log("=" * 50)
        self.log("  ✅ DESINSTALACIÓN COMPLETADA")
        self.log("=" * 50)
        self.log("")
        self.log("Para reinstalar desde cero, ejecuta:")
        self.log("  python3 memex_gui.py")

        self.set_progress(100, "¡Desinstalación completada!")
        self.after(0, lambda: self.btn_done.config(state="normal"))


if __name__ == "__main__":
    app = MemexUninstallerGUI()
    app.mainloop()
