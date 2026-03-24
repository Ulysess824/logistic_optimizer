import json
import time
import psutil
import os
from pathlib import Path
import numpy as np

from src.engine.solver import LogisticsSolver
from src.utils.data_manager import DataManager
from stress_test_full.report_generator import generate_stress_html

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # MB

def run_scenario(name, params):
    print(f"\n>>> EJECUTANDO ESCENARIO: {name}")
    start_mem = get_memory_usage()
    start_time = time.time()
    
    # Cargar datos base
    locations_path = Path("data/locations_smurfit.json")
    with open(locations_path, 'r', encoding='utf-8') as f:
        locations_data = json.load(f)
    
    dm = DataManager(
        paper_plant=locations_data['paper_plant'],
        carton_plants=locations_data['carton_plants'],
        clients_file=Path("data/demanda_simulada.json")
    )
    
    # 1. Filtro y Pre-procesamiento
    enriched_data = dm.get_optimized_locations(
        max_customers_per_plant=params.get('max_customers_per_plant', 10),
        max_radius_km=params.get('max_radius_km', 400),
        sorting_strategy=params.get('sorting_strategy', 'detour')
    )
    
    # Inyectar demanda extrema si es necesario
    if params.get('extreme_demand'):
        for plant in enriched_data['carton_plants']:
            for cust in plant.get('customers', []):
                cust['demanda_pallets'] = 35 # Camión completo
                
    solver = LogisticsSolver(enriched_data)
    
    solver_start = time.time()
    routes = solver.solve(
        n_clientes=params.get('n_clientes', 15),
        varias_plantas=params.get('varias_plantas', False),
        max_plantas_ruta=params.get('max_plantas_ruta', 2),
        max_search_time=params.get('max_search_time', 10),
        max_pallets_ruta=35
    )
    solver_end = time.time()
    
    end_time = time.time()
    end_mem = get_memory_usage()
    
    return {
        "scenario_name": name,
        "total_nodes": len(solver.nodes),
        "total_routes": len(routes) if routes else 0,
        "total_time_s": round(end_time - start_time, 2),
        "solver_time_s": round(solver_end - solver_start, 2),
        "memory_diff_mb": round(end_mem - start_mem, 2),
        "solution_found": routes is not None,
        "parameters": params
    }

def main():
    scenarios = [
        {
            "name": "ULTRA-DENSIDAD (100 clientes/planta)",
            "n_clientes": 50,
            "max_customers_per_plant": 100,
            "max_radius_km": 500,
            "varias_plantas": False,
            "max_search_time": 60
        },
        {
            "name": "TRANS-IBERIA (2000km Radio)",
            "n_clientes": 10,
            "max_customers_per_plant": 10,
            "max_radius_km": 2000,
            "varias_plantas": True,
            "max_plantas_ruta": 3,
            "max_search_time": 45
        },
        {
            "name": "FULL PACK (FTL forzado 35 pallets)",
            "n_clientes": 10,
            "max_customers_per_plant": 20,
            "max_radius_km": 300,
            "extreme_demand": True,
            "varias_plantas": False,
            "max_search_time": 30
        },
        {
            "name": "MULTI-PLANTA TOTAL (11 plantas/ruta)",
            "n_clientes": 30,
            "max_customers_per_plant": 5,
            "max_radius_km": 600,
            "varias_plantas": True,
            "max_plantas_ruta": 11,
            "max_search_time": 60
        },
        {
            "name": "LIMIT-TIME (Complejidad en 2s)",
            "n_clientes": 20,
            "max_customers_per_plant": 50,
            "max_radius_km": 400,
            "varias_plantas": False,
            "max_search_time": 2
        }
    ]
    
    all_results = []
    results_dir = Path("stress_test_full/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    for s in scenarios:
        res = run_scenario(s['name'], s)
        all_results.append(res)
        
        # Guardar individual por si falla
        safe_name = s['name'].replace(" ", "_").replace("/", "-")
        with open(results_dir / f"{safe_name}.json", 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2)

    with open(results_dir / "all_stress_results.json", 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
        
    print("\n[OK] Stress Test finalizado. Generando HTML...")
    generate_stress_html("stress_test_full/results/all_stress_results.json", "stress_test_full/stress_report.html")
    print("[OK] Reporte generado.")

if __name__ == "__main__":
    main()
