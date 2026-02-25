import json
import os
import sys
from pathlib import Path

# Add project root to sys.path to ensure src imports work correctly
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.engine.solver import LogisticsSolver
from src.utils.visualizer import Visualizer
from src.config import LOCATIONS_FILE, RESULTS_DIR

def run_optimization():
    print("\n" + "="*50)
    print("SOTA Logistics Optimizer - System Start")
    print("="*50)

    # 1. Load Data
    if not LOCATIONS_FILE.exists():
        print(f"Error: Data file not found at {LOCATIONS_FILE}")
        return

    with open(LOCATIONS_FILE, 'r', encoding='utf-8') as f:
        locations_data = json.load(f)

    # 2. Initialize Solver
    solver = LogisticsSolver(locations_data)
    
    print(f"Engine mode: {'Real Road (GPS)' if solver.is_real_road else 'Estimated (Haversine)'}")
    
    # 3. Solve
    routes = solver.solve()

    if routes:
        print(f"\nSe han hallado {len(routes)} rutas óptimas.")
        
        # Save results (JSON)
        output_json = RESULTS_DIR / "routes.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)
        print(f"Rutas exportadas a: {output_json}")

        # 4. Visualize
        visualizer = Visualizer(routes, solver.distance_matrix)
        map_path = visualizer.create_map("Optimized_final_route.html")
        
        if map_path:
            print(f"Mapa visual disponible en: {map_path}")

        # Console Summary
        print("\n--- Route Summary ---")
        for i, route in enumerate(routes):
            dist_km = 0
            for k in range(len(route)-1):
                idx_a = [n['id'] for n in solver.nodes].index(route[k]['id'])
                idx_b = [n['id'] for n in solver.nodes].index(route[k+1]['id'])
                dist_km += solver.distance_matrix[idx_a][idx_b] / 1000
            
            print(f"Ruta {i+1} ({route[1]['name']}): {len(route)-2} clientes | {dist_km:.2f} km")
    else:
        print("\nFALLO: No se pudo hallar una solución válida con las restricciones actuales.")

if __name__ == "__main__":
    run_optimization()
