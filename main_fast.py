import json
import logging
from pathlib import Path
import subprocess

from src.engine.solver import LogisticsSolver
from src.utils.visualizer import Visualizer
from src.utils.data_manager import DataManager
from src.utils.report_generator import generate_dashboard
from src.config import RESULTS_DIR, DATA_DIR

logger = logging.getLogger(__name__)

# ======================================================================
#  PARÁMETROS DE EJECUCIÓN — Modifica estos valores para configurar
# ======================================================================
N_CLIENTES = 4              
VARIAS_PLANTAS = False        
MAX_PLANTAS_RUTA = 3        
MAX_CUSTOMERS_PER_PLANT = 1
THRESHOLD_KM = 150          
MAX_RADIUS_KM = 200          
MAX_SEARCH_TIME = 90

TRUCK_SPECS = {
    "emissionType": "DIESEL",
    "heightCm": 400,
    "weightKg": 40_000,
}

MANDATORY_CUSTOMERS = {
    "Alcalá": ["Ciudad Real"], 
    "Alicante": ["Alcoy/Alcoi"]
}
# ======================================================================

def run_fast_optimization():
    logger.info("=" * 60)
    logger.info("Logistics Optimizer FAST — Sin Simulación GIF")
    logger.info("=" * 60)

    # 0. Auto-Ajuste de Capacidad (N_CLIENTES)
    min_needed_capacity = 0
    if MANDATORY_CUSTOMERS:
        for p, custs in MANDATORY_CUSTOMERS.items():
            num_mand = 1 if isinstance(custs, str) else len(custs)
            min_needed_capacity = max(min_needed_capacity, num_mand)
    
    current_n_clientes = max(N_CLIENTES, min_needed_capacity)
    if min_needed_capacity > N_CLIENTES:
        logger.warning("Auto-ajustando N_CLIENTES a %d para carga obligatoria.", current_n_clientes)

    # 1. Rutas de Archivos
    plants_file = DATA_DIR / "locations_smurfit.json"
    clients_file = DATA_DIR / "cliente_ubi.json"

    # 2. Cargar Plantas
    with open(plants_file, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    # Inicializar Motor Geográfico
    from src.utils.geo import GeoUtils
    geo_engine = GeoUtils(api_type="haversine")
    geo_engine.set_truck_specs(**TRUCK_SPECS)

    # 3. Selección de Clientes
    dm = DataManager(
        paper_plant=plants_data['paper_plant'],
        carton_plants=plants_data['carton_plants'],
        clients_file=clients_file,
        geo_utils=geo_engine
    )

    enriched_data = dm.get_optimized_locations(
        max_customers_per_plant=MAX_CUSTOMERS_PER_PLANT,
        threshold_km=THRESHOLD_KM,
        max_radius_km=MAX_RADIUS_KM,
        mandatory_customers=MANDATORY_CUSTOMERS,
    )

    # 4. Resolver
    solver = LogisticsSolver(enriched_data, geo_engine=geo_engine)
    routes = solver.solve(
        n_clientes=current_n_clientes,
        varias_plantas=VARIAS_PLANTAS,
        max_plantas_ruta=MAX_PLANTAS_RUTA,
        max_search_time=MAX_SEARCH_TIME,
    )

    if routes:
        logger.info("Generando reportes...")

        # 6. Guardar JSONs
        output_json = RESULTS_DIR / "optimized_routes.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)

        summary = _build_summary(routes, solver, current_n_clientes)
        summary_json = RESULTS_DIR / "optimization_summary.json"
        with open(summary_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # 7. Visualización (Mapas y Grafos)
        visualizer = Visualizer(routes, solver.distance_matrix, geo_utils=solver.geo)
        visualizer.create_map("Logistics_Dashboard.html")
        visualizer.create_plotly_graph("Logistics_Graph.html")
        
        # 8. Actualizar Presentación HTML
        presentation_path = "outputs/Presentacion_Logistica.html"
        generate_dashboard(summary_json, output_json, presentation_path)
        
        # 9. Refresco Final (Sin Simulación)
        logger.info("Actualizando dashboard...")
        try:
            subprocess.run(["python", "refresh_dashboard.py"], check=True)
            logger.info("Dashboard actualizado correctamente.")
        except Exception as e:
            logger.warning("Error al refrescar dashboard: %s", e)
        
        logger.info("=" * 60)
        logger.info("PROCESO FAST COMPLETADO (Sin GIF)")
        logger.info("=" * 60)
    else:
        logger.error("El optimizador no encontró una solución.")

def _build_summary(routes, solver, n_clientes):
    """Genera un JSON de resumen con KPIs por ruta."""
    route_summaries = []
    total_km = 0
    total_empty_km = 0

    for i, route in enumerate(routes):
        dist_km = 0
        empty_km = 0
        for j in range(len(route) - 1):
            n1, n2 = route[j], route[j+1]
            d = solver.distance_matrix[n1['matrix_idx']][n2['matrix_idx']] / 1000
            dist_km += d
            if j == len(route) - 2 and n2['type'] == 'depot':
                empty_km += d

        plant_nodes = [n for n in route if n['type'] == 'carton_plant']
        customer_nodes = [n for n in route if n['type'] == 'customer']

        route_summaries.append({
            "route_id": i + 1,
            "plants": [p['name'] for p in plant_nodes],
            "plant_ids": [p['id'] for p in plant_nodes],
            "num_plants": len(plant_nodes),
            "num_customers": len(customer_nodes),
            "customers": [c['name'] for c in customer_nodes],
            "distance_km": round(dist_km, 2),
            "empty_km": round(empty_km, 2),
            "num_stops": len(route)
        })
        total_km += dist_km
        total_empty_km += empty_km

    return {
        "num_routes": len(routes),
        "total_km": round(total_km, 2),
        "total_empty_km": round(total_empty_km, 2),
        "distance_source": "Haversine (Rápido)",
        "parameters": {
            "n_clientes": n_clientes,
            "varias_plantas": VARIAS_PLANTAS,
            "max_plantas_ruta": MAX_PLANTAS_RUTA,
        },
        "routes": route_summaries
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run_fast_optimization()
