import json
import os

path = r'c:\Users\kike\.gemini\antigravity\scratch\logistics_optimizer\notebooks\model_validation\operations_research\Estimación Tarifa propia.ipynb'

with open(path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Fix sys.path
nb['cells'][1]['source'][2] = "    \"sys.path.append(os.path.abspath(os.path.join('../../../')))\\n\",\n"

# Fix TARGET_RATE to 1.35
nb['cells'][3]['source'][3] = "    \"TARGET_RATE = 1.35\\n\",\n"

# Adjust bounds for 1.35
# We need to increase max km to 135,000 and lower min fuel a bit
nb['cells'][3]['source'][14] = "    \"    (100_000, 140_000),  # Kilometraje\\n\",\n" # Increase KM range
nb['cells'][3]['source'][15] = "    \"    (0.380, 0.500),   # Combustible\\n\",\n"  # Lower Fuel a bit

# Update description in markdown
nb['cells'][2]['source'][0] = "    \"## 🎯 Escenario Estratégico Objetivo (1.35 €/km)\\n\",\n"

with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook updated successfully.")
