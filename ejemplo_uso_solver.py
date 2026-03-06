# Este script muestra cómo utilizar la clase LogisticsSolver 
# con los nuevos parámetros para elegir diferentes algoritmos (metaheurísticas)

import json
from pathlib import Path
from src.engine.solver import LogisticsSolver
from src.utils.data_manager import DataManager
from src.config import DATA_DIR

def uso_ejemplo_solver():
    print("--- Ejemplo de uso de LogisticsSolver con distintos algoritmos ---")
    
    # 1. Rutas de Archivos para la demo
    plants_file = DATA_DIR / "locations_smurfit.json"
    clients_file = DATA_DIR / "cliente_ubi.json"

    if not plants_file.exists() or not clients_file.exists():
        print(f"Error: Faltan archivos de datos en {DATA_DIR}")
        return

    # 2. Cargar datos
    with open(plants_file, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    # 3. Preparar datos
    dm = DataManager(
        paper_plant=plants_data['paper_plant'],
        carton_plants=plants_data['carton_plants'],
        clients_file=clients_file
    )
    enriched_data = dm.get_optimized_locations(max_customers_per_plant=2)

    # 4. Iniciar clase solver
    solver = LogisticsSolver(enriched_data)
    
    # ----------------------------------------------------------------------
    # Ejemplo A: Usar el algoritmo por defecto (GUIDED_LOCAL_SEARCH)
    # ----------------------------------------------------------------------
    print("\n[A] Ejecutando solver con el algoritmo por DEFECTO:")
    rutas_default = solver.solve(
        n_clientes=3, 
        varias_plantas=False
    )
    if rutas_default:
        print(f"-> Se encontraron {len(rutas_default)} rutas.")

    # ----------------------------------------------------------------------
    # Ejemplo B: Cambiar a Simulated Annealing
    # ----------------------------------------------------------------------
    print("\n[B] Ejecutando solver con SIMULATED_ANNEALING:")
    rutas_sa = solver.solve(
        n_clientes=3, 
        varias_plantas=False,
        metaheuristic='SIMULATED_ANNEALING'
    )
    if rutas_sa:
        print(f"-> Se encontraron {len(rutas_sa)} rutas.")

    # ----------------------------------------------------------------------
    # Ejemplo C: Cambiar a Tabu Search
    # ----------------------------------------------------------------------
    print("\n[C] Ejecutando solver con TABU_SEARCH:")
    rutas_tabu = solver.solve(
        n_clientes=3, 
        varias_plantas=False,
        metaheuristic='TABU_SEARCH'
    )
    if rutas_tabu:
        print(f"-> Se encontraron {len(rutas_tabu)} rutas.")
        
if __name__ == "__main__":
    uso_ejemplo_solver()
