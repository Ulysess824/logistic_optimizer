import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from pathlib import Path
from logistic_core.engine.solver import LogisticsSolver
from logistic_core.utils.geo import GeoUtils

def main():
    """
    Ejemplo de uso de la nueva dimensión VRP 'Capacidad Física Acumulada (Volumen/Pallets)'.
    Demuestra cómo configurar y ejecutar el solver con 'max_pallets_ruta'.
    """
    print("--- Ejemplo de Uso: Dimensión de Pallets ---")
    
    # 1. Rutas de prueba
    plants_file = Path("data/locations_smurfit.json")
    clients_file = Path("data/demanda_simulada.json")
    
    if not plants_file.exists() or not clients_file.exists():
        print("Archivos de datos no encontrados. Ejecuta 'python generar_demanda.py' primero.")
        return

    # 2. Carga mínima de datos de la estructura
    # NOTA: Para este ejemplo saltaremos la fase de DataManager que filtra por radio
    # y simplemente extraeremos el depósito, 1 planta y 3 clientes manualmente.
    with open(plants_file, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)
        
    with open(clients_file, 'r', encoding='utf-8') as f:
        clients_data = json.load(f)

    # Extraer algunos clientes (Lezo) que tienen la nueva 'demanda_pallets' inyectada
    clientes_lezo = clients_data.get("20100", [])
    clientes_formateados = []
    
    for i, clf in enumerate(clientes_lezo[:3]):
        clientes_formateados.append({
            "id": f"C_20100_LEZ_{i}",
            "name": clf["municipio_destino"],
            "lat": clf["latitude"],
            "lng": clf["longitude"],
            "demanda_pallets": clf.get("demanda_pallets", 0),
            "parent_cp": "CP1" # Vinculado a Planta Cartón 1 para VRPB
        })

    enriched_data = {
        "paper_plant": plants_data["paper_plant"],
        "carton_plants": [
            {
                **plants_data["carton_plants"][0],
                "customers": clientes_formateados
            }
        ]
    }
    
    print("Candidatos inyectados al solver:")
    for c in clientes_formateados:
        print(f" - {c['name']} (Pallets requeridos: {c['demanda_pallets']})")

    # 3. Inicializar Motor Geográfico y Solver
    geo_engine = GeoUtils(api_type="haversine")
    solver = LogisticsSolver(enriched_data, geo_engine=geo_engine)
    
    print(f"\nDistancias base calculadas: Min={solver.distance_matrix[solver.distance_matrix > 0].min()}m")

    # 4. Uso del método solve modificado
    # Aquí es donde le pedimos al camión que tenga, por ejemplo, 15 pallets como máximo.
    # Si la suma de los clientes supera 15, dejará a alguien fuera o usará varios camiones si estuvieran habilitados.
    print("\nEjecutando Solve con 'max_pallets_ruta=15'...")
    routes = solver.solve(
        n_clientes=5,                 # Límite por número estático
        varias_plantas=False,         # Comportamiento VRPB clásico (1 planta por ruta)
        max_pallets_ruta=15,          # NUEVO PARÁMETRO: Límite por volumen físico acumulado
        max_search_time=10
    )
    
    if routes:
        print("\nResultado:")
        for i, route in enumerate(routes):
            # Calcular pallets consolidados 
            # (solo suman los nodos tipo 'customer', excluyendo depósitos y plantas)
            total_route_pallets = sum(node.get("demanda_pallets", 0) for node in route if node['type'] == 'customer')
            print(f" Ruta {i+1}: {len(route)-2} clientes visitados. Total Volumen Cargado: {total_route_pallets}/15 Pallets.")
    else:
        print("\nEl solver no encontró solución dentro de la capacidad de pallets solicitada.")

if __name__ == "__main__":
    main()
