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
FORCED_GROUPS = []
N_CLIENTES = 4              
VARIAS_PLANTAS = False        
MAX_PLANTAS_RUTA = 1        
MAX_CUSTOMERS_PER_PLANT = 1
THRESHOLD_KM = 100          
MAX_RADIUS_KM = 100          
MAX_SEARCH_TIME = 90        


# Especificaciones de Camión (Tráiler estándar para bobinas de papel)
TRUCK_SPECS = {
    "emissionType": "DIESEL",
    "heightCm": 400,        # Altura máxima: 4.0 metros
    "weightKg": 40_000,     # Peso Máximo Autorizado: 40 toneladas
    # --- POSIBLES FUTURAS IMPLEMENTACIONES PARA API DE RUTAS ---
    # "trafficModel": "BEST_GUESS", # Considerar el tráfico real según hora de salida.
    # "avoidTolls": True,           # Priorizar rutas sin peaje para reducir costes.
}

# Diccionario de clientes que es OBLIGATORIO visitar para cada planta.
# Acepta tanto clientes que estén o no seleccionados previamente por el filtro kilométrico.
# Formato: {"Nombre_Corto_Planta": ["Nombre_Del_Municipio_Cliente"]}
# Ejemplo: {"Córdoba": ["El Carpio", "Montilla"]}
# Ejemplo de uso:
MANDATORY_CUSTOMERS = {
    "Alcalá": ["Madrid"], 
    "Córdoba": ["Andujar"]
    }
PLANT_GROUPS = []
# ======================================================================


def run_optimization():
    logger.info("=" * 60)
    logger.info("Logistics Optimizer — Inicio de ejecución")
    logger.info("=" * 60)
    # 0. Auto-Ajuste de Capacidad (N_CLIENTES)
    # Calculamos cuántos clientes obligatorios tiene cada planta para no desbordar el solver
    min_needed_capacity = 0
    if MANDATORY_CUSTOMERS:
        for p, custs in MANDATORY_CUSTOMERS.items():
            num_mand = 1 if isinstance(custs, str) else len(custs)
            min_needed_capacity = max(min_needed_capacity, num_mand)
    
    current_n_clientes = N_CLIENTES
    if min_needed_capacity > current_n_clientes:
        logger.warning("¡Capacidad insuficiente detectada! Ajustando N_CLIENTES de %d a %d para soportar carga obligatoria.", 
                       current_n_clientes, min_needed_capacity)
        current_n_clientes = min_needed_capacity

    # 1. Rutas de Archivos
    plants_file = DATA_DIR / "locations_smurfit.json"
    clients_file = DATA_DIR / "cliente_ubi.json"

    if not plants_file.exists() or not clients_file.exists():
        logger.error("Faltan archivos de datos en %s", DATA_DIR)
        return

    # 2. Cargar Plantas y Sede
    with open(plants_file, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    # Inicializar Motor Geográfico (Haversine para máxima velocidad)
    from src.utils.geo import GeoUtils
    geo_engine = GeoUtils(api_type="haversine")
    geo_engine.set_truck_specs(**TRUCK_SPECS)

    # 3. Selección Inteligente de Clientes (Filtros Radio/Retorno via API)
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
        mandatory_customers=MANDATORY_CUSTOMERS,   # ← activo, edita el dict arriba
    )

    # Debug: Mostrar candidatos por planta
    for plant in enriched_data['carton_plants']:
        cust_list = [f"{c['name']} (OBL)" if c.get('obligatorio') else c['name'] for c in plant['customers']]
        logger.info(f"Candidatos para {plant['name']}: {cust_list}")

    # 4. Resolver VRP
    solver = LogisticsSolver(enriched_data, geo_engine=geo_engine)
    logger.info("Motor de distancias: %s", 'GPS Real' if solver.is_real_road else 'Haversine')
    logger.info("Nodos totales a optimizar: %d", len(solver.nodes))

    # 5. Ejecutar Optimización
    routes = solver.solve(
        n_clientes=current_n_clientes,
        varias_plantas=VARIAS_PLANTAS,
        max_plantas_ruta=MAX_PLANTAS_RUTA,
        max_search_time=MAX_SEARCH_TIME,
    )

    if routes:
        logger.info("Se han generado %d rutas logísticas integradas.", len(routes))

        # 6. Guardar rutas detalladas
        output_json = RESULTS_DIR / "optimized_routes.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)
        logger.info("Rutas guardadas en: %s", output_json)

        # 7. Generar y guardar resumen de KPIs
        summary = _build_summary(routes, solver)
        summary_json = RESULTS_DIR / "optimization_summary.json"
        with open(summary_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info("Resumen guardado en: %s", summary_json)

        # 8. Visualización
        visualizer = Visualizer(routes, solver.distance_matrix, geo_utils=solver.geo)
        map_path = visualizer.create_map("Logistics_Dashboard.html")
        graph_path = visualizer.create_plotly_graph("Logistics_Graph.html")
        
        # Grafo Global de Complejidad (Sin filtrar)
        with open(clients_file, 'r', encoding='utf-8') as f:
            raw_clients = json.load(f)
        all_clients_list = []
        for z, dests in raw_clients.items():
            for d in dests:
                if "latitude" in d and "longitude" in d:
                    all_clients_list.append({"name": d.get("municipio_destino", z), "lat": d["latitude"], "lng": d["longitude"]})
        
        complexity_graph_path = visualizer.create_global_complexity_graph(
            plants_data['paper_plant'], plants_data['carton_plants'], all_clients_list, "Logistics_Global_Complexity.html"
        )

        logger.info("Mapa: %s", map_path)
        logger.info("Grafo Optimizado: %s", graph_path)
        logger.info("Grafo Complejidad: %s", complexity_graph_path)

        # 9. Actualizar Presentación HTML (Dashboard Global)
        presentation_path = "outputs/Presentacion_Logistica.html"
        generate_dashboard(summary_json, output_json, presentation_path)
        
        # 10. Procesos Adicionales (Simulación y Refresco Final)
        logger.info("Ejecutando procesos complementarios...")
        try:
            # Generamos la simulación (GIF) primero para que el dashboard lo muestre actualizado
            subprocess.run(["python", "ejemplo_simulacion.py"], check=True)
            # Refrescamos el dashboard una última vez para asegurar sincronización
            subprocess.run(["python", "refresh_dashboard.py"], check=True)
            logger.info("Simulación y Dashboard actualizados correctamente.")
        except Exception as e:
            logger.warning("No se pudo completar el proceso de simulación/refresco: %s", e)
        
        # 11. Log de resumen
        logger.info("=" * 60)
        logger.info("RESUMEN DE OPERACIÓN")
        logger.info("=" * 60)
        for r in summary['routes']:
            plants_str = ", ".join(r['plants']) if len(r['plants']) > 1 else r['plants'][0]
            logger.info("Ruta %d: %s → %d clientes → %.2f km (%.2f km en vacío)",
                        r['route_id'], plants_str, r['num_customers'], r['distance_km'], r['empty_km'])
        logger.info("TOTAL: %.2f km (%.2f km en vacío) en %d rutas", summary['total_km'], summary['total_empty_km'], summary['num_routes'])
        
        # Resumen Analítico
        print("\n")
        print(solver.summary())
        print("\n")
    else:
        logger.error("El optimizador no encontró una solución válida.")


def _build_summary(routes, solver):
    """Genera un JSON de resumen con KPIs por ruta."""
    route_summaries = []
    total_km = 0
    total_empty_km = 0

    for i, route in enumerate(routes):
        customer_nodes = [n for n in route if n['type'] == 'customer']
        if not customer_nodes:
            continue

        dist_km = 0
        empty_km = 0
        for j in range(len(route) - 1):
            n1, n2 = route[j], route[j+1]
            d = solver.distance_matrix[n1['matrix_idx']][n2['matrix_idx']] / 1000
            dist_km += d
            if j == len(route) - 2 and n2['type'] == 'depot':
                empty_km += d

        plant_nodes = [n for n in route if n['type'] == 'carton_plant']

        route_summaries.append({
            "route_id": len(route_summaries) + 1,
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
        "num_routes": len(route_summaries),
        "total_km": round(total_km, 2),
        "total_empty_km": round(total_empty_km, 2),
        "distance_source": "GPS Real" if solver.is_real_road else "Haversine (estimación)",
        "parameters": {
            "n_clientes": N_CLIENTES,
            "varias_plantas": VARIAS_PLANTAS,
            "max_plantas_ruta": MAX_PLANTAS_RUTA,
        },
        "routes": route_summaries
    }


if __name__ == "__main__":
    run_optimization()
