import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import time

class ProgressFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="⏳ Instalando Memexicanisimos OS...", style='Title.TLabel').pack(pady=(20, 10))
        
        self.progress = ttk.Progressbar(self, mode='determinate', length=500, maximum=100)
        self.progress.pack(pady=10)

        self.lbl_status = ttk.Label(self, text="Preparando...", font=('Helvetica', 10, 'italic'))
        self.lbl_status.pack(pady=2)

        self.log_area = tk.Text(self, height=13, width=70, bg="black", fg="lightgreen", font=("Consolas", 9))
        self.log_area.pack(pady=10)

        self.btn_finish = ttk.Button(self, text="Finalizar", command=self.on_finish, state="disabled")
        self.btn_finish.pack(pady=10)
        
        self.install_thread = None

    def log(self, message):
        """Añade texto thread-safe."""
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.update_idletasks()

    def set_progress(self, val, text):
        """Actualiza progreso thread-safe."""
        self.progress['value'] = val
        self.lbl_status.config(text=text)
        self.update_idletasks()

    def start_installation(self):
        """Llamado desde ConfigFrame."""
        self.log_area.delete(1.0, tk.END)
        self.btn_finish.config(state="disabled")
        self.progress['value'] = 0
        
        if self.install_thread is None or not self.install_thread.is_alive():
            self.install_thread = threading.Thread(target=self._install_worker, daemon=True)
            self.install_thread.start()

    def _install_worker(self):
        self.log("=== Iniciando Secuencia de Instalación ===")
        core = self.controller.installer_core
        
        try:
            # 1. Preparar Entorno
            self.set_progress(10, "Generando configuraciones locales...")
            core.prepare_environment(
                ram_gb=self.controller.detector.get_ram_gb(),
                use_gpu=self.controller.use_gpu.get(),
                port=int(self.controller.webui_port.get()),
                flavors_dict=self.controller.flavors_dict
            )
            time.sleep(1)

            # 2. Verificar Docker
            self.set_progress(30, "Asegurando dependencias (Docker)...")
            if not core.ensure_docker():
                self.log("[X] Advertencia: No se pudo verificar o instalar Docker automáticamente.")
            time.sleep(1)

            # 3. Docker Compose Up
            self.set_progress(50, "Levantando la infraestructura Memex...")
            success = core.docker_compose_up()
            if not success:
               self.log("[!] Hubo advertencias al levantar compose. Revisa logs detallados.")
            
            # 4. Pull de Modelos
            self.set_progress(70, "Descargando Modelos IAs a Memoria local (puede tardar bastante)...")
            models_to_pull = [self.controller.selected_base_model.get()] + list(self.controller.flavors_dict.values())
            success_pull = core.pull_models(models_to_pull)
            if not success_pull:
                self.log("[!] Advertencia: Algunos modelos fallaron al descargar. Continuaremos la instalación, puedes descargarlos manualmente luego en Open WebUI.")

            # 5. Esperar a que Open WebUI esté saludable
            self.set_progress(80, "Esperando a que Open WebUI arranque...")
            port = int(self.controller.webui_port.get())
            health_ok = core.wait_for_health(port=port, timeout=120)
            if not health_ok:
                self.log("[!] Open WebUI no respondió a tiempo al healthcheck.")

            # 6. Esperar a que setup_memex.py inyecte los Sabores
            self.set_progress(90, "Verificando que los Sabores están disponibles...")
            flavors_ready = core.wait_for_flavors(port=port, timeout=120)
            if flavors_ready:
                self.log("[+] ¡Todos los Sabores confirmados en la API de Open WebUI!")
            else:
                self.log("[!] Algunos sabores aún no aparecen. Puedes recargar la página en unos segundos.")

            self.set_progress(100, "¡Instalación Finalizada Exitosamente!")
            self.log("=== TODO LISTO ===")
            self.after(0, lambda: self.btn_finish.config(state="normal", text="Abrir WebUI y Finalizar"))
            
        except Exception as e:
            self.log(f"[X] FALLO CRÌTICO: {str(e)}")
            self.set_progress(0, "Error en la instalación.")
            self.after(0, lambda: self.btn_finish.config(state="normal", text="Reintentar / Salir"))

    def on_finish(self):
        self.controller.show_frame("ResultFrame")
