import sys
import json
import time
import os
from pathlib import Path

# Configuraciones y Rutas
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import main  # Importamos main para usar run_optimization
import logistic_core.config as config

# Configuraciones y Rutas
BASE_DIR = Path(__file__).resolve().parent.parent
YEARLY_DEMAND_FILE = BASE_DIR / "data" / "yearly_demand.json"
TEMP_DAILY_FILE = BASE_DIR / "data" / "temp_daily_demand.json"
YEARLY_STATS_FILE = BASE_DIR / "outputs" / "results" / "yearly_stats.json"

def run_yearly_simulation(limit_days=None):
    """
    Ejecuta la optimización para los días solicitados.
    """
    if not YEARLY_DEMAND_FILE.exists():
        print(f"Error: No se encuentra {YEARLY_DEMAND_FILE}. Ejecuta generate_yearly_data.py primero.")
        return

    with open(YEARLY_DEMAND_FILE, 'r', encoding='utf-8') as f:
        yearly_demand = json.load(f)

    dates = sorted(yearly_demand.keys())
    if limit_days:
        dates = dates[:limit_days]
        print(f"MODO DEMO: Limitando simulación a los primeros {limit_days} días.")

    print(f"Iniciando simulación para {len(dates)} días...")
    
    yearly_results = {}
    
    start_time = time.time()

    for idx, date_str in enumerate(dates):
        print(f"\n[{idx+1}/{len(dates)}] Optimizando día: {date_str}...")
        
        # 1. Escribir demanda diaria en archivo temporal para que main.py lo consuma
        daily_data = yearly_demand[date_str]
        with open(TEMP_DAILY_FILE, 'w', encoding='utf-8') as f:
            json.dump(daily_data, f)
            
        # 2. Modificar dinámicamente el path de clientes en runtime
        original_clients_file = main.CLIENTS_FILE
        main.CLIENTS_FILE = TEMP_DAILY_FILE
        
        # 3. Ejecutar Optimización de forma silenciosa y RÁPIDA (max_search_time=2s)
        try:
            routes, summary, solver = main.run_optimization(
                max_pallets=main.MAX_PALLETS,
                threshold_km=main.THRESHOLD_KM_DETOUR,
                n_candidatos=main.N_CANDIDATOS_PLANTA,
                api_type=main.API_TYPE,
                max_search_time=2, # Reducido para simulación batch
                silent=True
            )
            
            if summary:
                yearly_results[date_str] = {
                    "routes_generated": summary["num_routes"],
                    "total_km": summary["total_km"],
                    "empty_km": summary["total_empty_km"],
                    "total_co2_kg": summary["total_co2_kg"],
                    "total_cost_eur": summary["total_cost_eur"],
                    "total_customers": summary["total_customers"]
                }
                
                # Generar mapa interactivo del día
                map_dir = BASE_DIR / "outputs" / "rutas_diarias"
                map_dir.mkdir(exist_ok=True)
                map_path = map_dir / f"Rutas_{date_str}.html"
                viz = main.Visualizer(routes, solver.distance_matrix, geo_utils=solver.geo)
                viz.create_map(str(map_path))
            else:
                yearly_results[date_str] = {"error": "Sin rutas"}
                print(f"   -> Sin resultados para {date_str}")
                
        except Exception as e:
            print(f"   -> Error iterando en {date_str}: {e}")
            yearly_results[date_str] = {"error": str(e)}

        # Restaurar path original por si acaso
        main.CLIENTS_FILE = original_clients_file

    end_time = time.time()
    
    print("\n==============================================")
    print(f"Simulacion completada en {end_time - start_time:.2f} segundos.")
    print(f"Guardando resultados anuales en {YEARLY_STATS_FILE}")
    
    with open(YEARLY_STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(yearly_results, f, indent=2, ensure_ascii=False)
        
    # Limpiar temporal
    if TEMP_DAILY_FILE.exists():
        os.remove(TEMP_DAILY_FILE)

if __name__ == "__main__":
    run_yearly_simulation()
