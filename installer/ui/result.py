import tkinter as tk
from tkinter import ttk
import sys
import os
import subprocess

class ResultFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="🌮 ¡Memexicanisimos Listo!", style='Title.TLabel').pack(pady=(40, 20))
        
        ttk.Label(self, text="La instalación ha concluido con éxito.", justify="center", font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        desc = (
            "El ecosistema local está corriendo de fondo mediante Docker.\n"
            f"Puedes acceder en cualquier momento desde tu navegador en:\n\n"
            "http://localhost:3000\n\n"
            "Tus agentes (Sabores) y tu herramienta Memex FTS5 ya están conectados."
        )
        ttk.Label(self, text=desc, justify="center").pack(pady=20)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", pady=40)
        
        ttk.Button(btn_frame, text="Terminar", command=self.controller.quit).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Abrir Navegador", command=self.open_browser).pack(side="right", padx=10)

    def open_browser(self):
        port = self.controller.webui_port.get()
        url = f"http://localhost:{port}"
        
        try:
            if sys.platform == 'linux':
                subprocess.Popen(['xdg-open', url])
            elif sys.platform == 'win32':
                os.startfile(url)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', url])
        except Exception:
            pass
        self.controller.quit()
