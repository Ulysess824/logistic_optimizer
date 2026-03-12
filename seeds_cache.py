import json
from pathlib import Path
from src.utils.geo import GeoUtils

def seed_cache_from_json(json_path):
    json_path = Path(json_path)
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        routes = json.load(f)

    geo = GeoUtils(api_type="haversine") # Use haversine just to init, the cache is internal
    
    count_poly = 0
    
    print(f"Propagando caché desde {json_path}...")
    
    for route in routes:
        for i in range(len(route) - 1):
            n1 = route[i]
            n2 = route[i+1]
            
            origin = (n1['lat'], n1['lng'])
            dest = (n2['lat'], n2['lng'])
            
            # Si hay polyline guardada en el JSON (o si queremos inferir distancias reales)
            # En este caso, el JSON antiguo no tiene la polyline directamente por nodo, 
            # sino que el Visualizer la generaba. 
            # Pero podemos guardar al menos la distancia si el JSON la tuviera.
            # Como el JSON no tiene distancias por segmento, saltamos esto por ahora
            # y nos enfocamos en que las polylines se guarden cuando el Visualizer las pida.
            pass

    print("Caché preparada para recibir nuevas consultas.")

if __name__ == "__main__":
    seed_cache_from_json("outputs/results/optimized_routes.json")
