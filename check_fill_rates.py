import json
from pathlib import Path

routes_path = Path("outputs/results/optimized_routes.json")
if not routes_path.exists():
    print("No existe el archivo de rutas.")
    exit()

with open(routes_path, "r", encoding="utf-8") as f:
    routes = json.load(f)

print(f"Total de rutas: {len(routes)}")
for i, route in enumerate(routes):
    carga = sum(n.get('demanda_pallets', 0) for n in route if n['type'] == 'customer')
    fill_rate = (carga / 34) * 100
    customers = [n['name'] for n in route if n['type'] == 'customer']
    print(f"Ruta {i+1}: {carga}/34 pallets ({fill_rate:.1f}%) | Clientes: {', '.join(customers)}")
