"""
Catalog of carefully selected LLMs for Memexicanisimos.
Models are categorized by hardware requirements (RAM).
"""

from dataclasses import dataclass
from typing import List

@dataclass
class AIModel:
    id: str
    name: str                     # Human readable name
    size_b: float                 # Parameter size in billions
    ram_required_gb: float        # Minimum realistic RAM required
    category: str                 # e.g., "General", "Coder", "Reasoning", "Embedding"
    description: str              # Brief description for the UI

class ModelsCatalog:
    """Provides a dynamic catalog of models filtered by tier."""
    
    # Master list of models supported by the ecosystem
    MODELS = [
        # --- Ultralight (< 4GB RAM) ---
        AIModel("qwen2.5:0.5b", "Qwen 2.5 (0.5B)", 0.5, 2.0, "General", "Modelo ultraligero muy rápido, ideal para pruebas de concepto."),
        AIModel("qwen2.5-coder:1.5b", "Qwen 2.5 Coder (1.5B)", 1.5, 3.0, "Coder", "Excelente generador de código para hardware modesto."),
        AIModel("llama3.2:1b", "Llama 3.2 (1B)", 1.0, 3.0, "General", "Modelo compacto de Meta, ágil y versátil."),
        
        # --- Balanced (4GB - 8GB RAM) ---
        AIModel("qwen2.5:3b", "Qwen 2.5 (3B)", 3.0, 4.0, "General", "Responde bien a prompts generales sin consumir mucha memoria."),
        AIModel("llama3.2:3b", "Llama 3.2 (3B)", 3.0, 4.0, "General", "Buen balance entre inteligencia y ligereza."),
        AIModel("gemma3:4b", "Gemma 3 (4B)", 4.0, 5.0, "General", "Modelo compacto de Google con excelente razonamiento."),
        AIModel("phi3.5:3.8b", "Phi 3.5 (3.8B)", 3.8, 5.0, "General", "Modelo eficiente de Microsoft, gran calidad por su tamaño."),
        AIModel("qwen2.5:7b", "Qwen 2.5 (7B)", 7.0, 6.0, "General", "Uno de los mejores modelos de 7B de uso general."),
        AIModel("qwen2.5-coder:7b", "Qwen 2.5 Coder (7B)", 7.0, 6.0, "Coder", "Asistente de programación competente para el día a día."),
        AIModel("qwen3-coder:7b", "Qwen 3 Coder (7B)", 7.0, 6.0, "Coder", "Nueva generación de asistente de código con mejoras en razonamiento."),
        AIModel("llama3.1:8b", "Llama 3.1 (8B)", 8.0, 7.0, "General", "El estándar de código abierto de Meta. Excelente rendimiento."),
        AIModel("deepseek-r1:7b", "DeepSeek-R1 (7B)", 7.0, 6.0, "Reasoning", "Modelo destilado enfocado en razonamiento matemático y lógico."),
        AIModel("qwen3:8b", "Qwen 3 (8B)", 8.0, 7.0, "General", "Tercera generación de Qwen, mejoras significativas en instrucciones."),
        
        # --- Heavy (12GB - 16GB+ RAM) ---
        AIModel("qwen3.5:9b", "Qwen 3.5 (9B)", 9.0, 8.0, "General", "Modelo avanzado de la nueva serie 3.5 con mejoras en razonamiento."),
        AIModel("qwen2.5:14b", "Qwen 2.5 (14B)", 14.0, 10.0, "General", "Modelo pesado de alta capacidad intelectual."),
        AIModel("deepseek-r1:14b", "DeepSeek-R1 (14B)", 14.0, 10.0, "Reasoning", "Alta capacidad de razonamiento encadenado."),
        AIModel("phi4:14b", "Phi-4 (14B)", 14.0, 10.0, "General", "Modelo robusto de Microsoft, muy preciso."),
        AIModel("codestral:22b", "Codestral (22B)", 22.0, 16.0, "Coder", "Modelo de código de Mistral AI, especializado en programación."),
        
        # --- Ultra Heavy (32GB+ RAM) ---
        AIModel("deepseek-r1:32b", "DeepSeek-R1 (32B)", 32.0, 24.0, "Reasoning", "Capacidad de nivel experto para problemas complejos."),
        AIModel("qwen2.5:32b", "Qwen 2.5 (32B)", 32.0, 24.0, "General", "Extensa capacidad para tareas complejas multilingües."),
        AIModel("llama3.1:70b", "Llama 3.1 (70B)", 70.0, 48.0, "General", "Clase servidor. Inteligencia superior para setups potentes."),
        
        # --- Especializados (Embedding / Audio) ---
        AIModel("nomic-embed-text", "Nomic Embed Text", 0.14, 1.0, "Embedding", "Modelo de embedding para RAG y búsqueda semántica."),
        AIModel("bge-m3", "BGE-M3", 0.57, 2.0, "Embedding", "Embedding multilingüe de alta calidad para bases vectoriales."),
        AIModel("mxbai-embed-large", "MxBAI Embed Large", 0.33, 2.0, "Embedding", "Embedding de alto rendimiento para clasificación y búsqueda."),
    ]
    
    @classmethod
    def get_all_models(cls) -> List[AIModel]:
        """Returns all models in the catalog."""
        return cls.MODELS[:]
    
    @classmethod
    def get_top_10_for_hardware(cls, ram_gb: float) -> List[AIModel]:
        """
        Returns the top 10 models that can comfortably run on the given RAM,
        prioritizing the largest/most capable ones that fit the budget.
        Excludes embedding models (those are shown separately).
        """
        available_budget = ram_gb - 1.0 
        
        valid_models = [
            m for m in cls.MODELS 
            if m.ram_required_gb <= available_budget and m.category != "Embedding"
        ]
        
        # Sort by size (descending) to get the most powerful ones that fit
        valid_models.sort(key=lambda x: x.size_b, reverse=True)
        
        return valid_models[:10]
    
    @classmethod
    def get_all_for_download(cls, ram_gb: float, installed: list = None) -> dict:
        """
        Returns models grouped by category, marking which are installed
        and which fit the hardware.
        """
        if installed is None:
            installed = []
        
        available_budget = ram_gb - 1.0
        grouped = {}
        
        for m in cls.MODELS:
            cat = m.category
            if cat not in grouped:
                grouped[cat] = []
            
            fits_hardware = m.ram_required_gb <= available_budget
            is_installed = m.id in installed
            
            grouped[cat].append({
                "model": m,
                "fits": fits_hardware,
                "installed": is_installed,
            })
        
        return grouped
