import tkinter as tk
from tkinter import ttk

class WelcomeFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="🌮 Bienvenido a Memexicanisimos OS", style='Title.TLabel').pack(pady=(40, 20))
        ttk.Label(self, text="El agente cognitivo local con memoria persistente.", justify="center").pack(pady=10)
        
        desc = (
            "Este instalador te guiará paso a paso para configurar Ollama,\n"
            "Open WebUI y las herramientas de memoria FTS5.\n\n"
            "El proceso detectará tus capacidades de hardware y ajustará\n"
            "automáticamente el entorno para garantizar cero colapsos de inferencia."
        )
        ttk.Label(self, text=desc, justify="center").pack(pady=10)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", pady=40)
        
        ttk.Button(btn_frame, text="Salir", command=self.controller.quit).pack(side="left", padx=10)
        
        self.next_btn = ttk.Button(btn_frame, text="Siguiente ➔", command=lambda: self.controller.show_frame("HardwareFrame"))
        self.next_btn.pack(side="right", padx=10)
