import json
import sys
from pathlib import Path

# Fix path for imports
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.engine.solver import LogisticsSolver
from src.utils.visualizer import Visualizer
from src.utils.data_manager import DataManager
from src.config import RESULTS_DIR, DATA_DIR

def run_optimization():
    print("\n" + "🚀 " * 20)
    print("Logistics Optimizer - Strategic Overhaul Active")
    print("🚀 " * 20 + "\n")

    # 1. Rutas de Archivos
    plants_file = DATA_DIR / "locations_smurfit.json"
    clients_file = DATA_DIR / "cliente_ubi.json"

    if not plants_file.exists() or not clients_file.exists():
        print(f"❌ Error: Faltan archivos de datos en {DATA_DIR}")
        return

    # 2. Cargar Plantas y Sede
    with open(plants_file, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    # 3. Data Engineering: Selección Inteligente de Clientes (Filtro de Retorno)
    dm = DataManager(
        paper_plant=plants_data['paper_plant'],
        carton_plants=plants_data['carton_plants'],
        clients_file=clients_file
    )
    
    # 1. Cargar y seleccionar clientes
    # Seleccionamos hasta 4 clientes por planta que estén en la ruta de vuelta a Mengíbar
    enriched_data = dm.get_optimized_locations(max_customers_per_plant=4, threshold_km=100)
    
    # 2. Solver
    solver = LogisticsSolver(enriched_data)
    
    print(f"\nEngine Status: {'GPS Real' if solver.is_real_road else 'Haversine Matrix'}")
    print(f"Nodos totales a optimizar: {len(solver.nodes)}")

    # 5. Ejecutar Optimización
    routes = solver.solve()

    if routes:
        print(f"\n✅ ÉXITO: Se han generado {len(routes)} rutas logísticas integradas.")
        
        # Guardar resultados
        output_json = RESULTS_DIR / "optimized_routes.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)

        # 6. Visualización con Dashboard
        visualizer = Visualizer(routes, solver.distance_matrix)
        map_path = visualizer.create_map("Logistics_Dashboard.html")
        graph_path = visualizer.create_plotly_graph("Logistics_Graph.html")
        
        print(f"\n🔎 Visualización del Mapa generada en: {map_path}")
        print(f"📊 Visualización del Grafo (Plotly) en: {graph_path}")
        print("\n" + "="*50)
        print("RESUMEN DE OPERACIÓN")
        print("="*50)
        for i, route in enumerate(routes):
            # Calcular km reales para el log
            dist_km = sum(solver.distance_matrix[n1['matrix_idx']][n2['matrix_idx']] 
                         for n1, n2 in zip(route, route[1:])) / 1000
            print(f"Ruta {i+1} (D->{route[1]['name']}->Clientes->D): {dist_km:.2f} km")
    else:
        print("\n❌ FALLO: El optimizador no pudo encontrar una solución válida con las restricciones actuales.")

if __name__ == "__main__":
    run_optimization()
