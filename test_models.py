import sys
import os

from installer.models_catalog import ModelsCatalog

# Test logic for RAM Tiers
def test_models_catalog():
    print("Testing Models Catalog Filtering...")
    
    tiers = [4.0, 8.0, 16.0, 32.0, 64.0]
    
    for ram in tiers:
        print(f"\n--- Testing Hardware: {ram} GB RAM ---")
        models = ModelsCatalog.get_top_10_for_hardware(ram)
        
        if not models:
            print("  No models met the criteria.")
        else:
            for i, m in enumerate(models, 1):
                print(f"  {i}. {m.name} ({m.size_b}B) - Requires: {m.ram_required_gb}GB - {m.category}")

if __name__ == "__main__":
    test_models_catalog()
