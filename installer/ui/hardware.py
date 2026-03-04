import tkinter as tk
from tkinter import ttk

class HardwareFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.detector = controller.detector
        
        ttk.Label(self, text="🔍 Detección de Hardware", style='Title.TLabel').pack(pady=(20, 20))
        
        self.info_frame = ttk.Frame(self, relief="groove", borderwidth=2, padding=20)
        self.info_frame.pack(fill="x", padx=40, pady=10)
        
        self.lbl_cpu = ttk.Label(self.info_frame, text="💻 Procesador: Detectando...")
        self.lbl_cpu.pack(anchor="w", pady=5)
        
        self.lbl_ram = ttk.Label(self.info_frame, text="🧠 Memoria RAM: Detectando...")
        self.lbl_ram.pack(anchor="w", pady=5)
        
        self.lbl_gpu = ttk.Label(self.info_frame, text="🎮 Tarjeta Gráfica: Detectando...")
        self.lbl_gpu.pack(anchor="w", pady=5)
        
        self.lbl_disk = ttk.Label(self.info_frame, text="💾 Espacio Libre: Detectando...")
        self.lbl_disk.pack(anchor="w", pady=5)

        self.lbl_recom = ttk.Label(self, text="", style='Success.TLabel')
        self.lbl_recom.pack(pady=20)

        # Warnings / Problems
        self.lbl_warn = ttk.Label(self, text="", foreground="red", font=('Helvetica', 10, 'bold'))
        self.lbl_warn.pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", pady=20)
        ttk.Button(btn_frame, text="🡄 Atrás", command=lambda: self.controller.show_frame("WelcomeFrame")).pack(side="left", padx=10)
        self.btn_next = ttk.Button(btn_frame, text="Siguiente ➔", command=lambda: self.controller.show_frame("ConfigFrame"))
        self.btn_next.pack(side="right", padx=10)

    def on_show(self):
        """Called when frame is brought to front to refresh stats."""
        ram = self.detector.get_ram_gb()
        cpu = self.detector.get_cpu_threads()
        gpu = self.detector.get_gpu_info()
        disk = self.detector.get_free_disk_space_gb()

        self.lbl_cpu.config(text=f"💻 Procesador: {cpu} Hilos lógicos")
        self.lbl_ram.config(text=f"🧠 Memoria RAM: {ram} GB")
        
        # GPU could be NVIDIA with VRAM
        gpu_txt = f"{gpu['name']}"
        if gpu['vram_mb'] > 0:
            gpu_txt += f" ({gpu['vram_mb']} MB VRAM)"
        self.lbl_gpu.config(text=f"🎮 GPU: {gpu_txt}")
        
        self.lbl_disk.config(text=f"💾 Espacio Libre (/): {disk} GB")

        # Basic analysis
        recom_model = "qwen2.5:1.5b"
        if ram >= 16:
            recom_model = "deepseek-r1:7b"
        elif ram >= 8:
            recom_model = "qwen2.5:7b"
            
        self.controller.recommended_model = recom_model
        # Only set if not user overridden already
        if not self.controller.selected_base_model.get():
            self.controller.selected_base_model.set(recom_model)

        self.lbl_recom.config(text=f"💡 Recomendamos como base: {recom_model}")

        # Warnings blocker
        self.btn_next.config(state="normal")
        self.lbl_warn.config(text="")
        if disk < 15:
            self.lbl_warn.config(text="⚠️ Poco espacio en disco. Necesitas al menos 15GB libres.")
            self.btn_next.config(state="disabled")
