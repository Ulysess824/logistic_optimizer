import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import json
import logging
from pathlib import Path
import folium
import polyline

from logistic_core.engine.solver import LogisticsSolver
from logistic_core.utils.data_manager import DataManager
from logistic_core.utils.geo import GeoUtils
from logistic_core.utils.visualizer import Visualizer
from logistic_core.utils.report_generator import generate_dashboard
from logistic_core.utils.fcr_estimator import FCREmissionEstimator
from logistic_core.utils.capacity_estimator import TruckCapacityEstimator, Pallet
from logistic_core.utils.cost_estimator import CostEstimator, FleetSizer
from logistic_core.utils.fleet_estimator import FleetCapexEstimator
from logistic_core.config import (
    RESULTS_DIR, DATA_DIR, MAPS_DIR,
    GLEC_CO2_PER_LITER, GLEC_INTENSITY_GTKM, GLEC_EMPTY_FLOOR_KGKM,
    PAPER_LOAD_KG, PALLET_WEIGHT_KG, VEHICLE_MAX_LOAD_KG,
    TARIFA_INTERNA_DIESEL,
    CAPEX_TRUCK_UNIT_COST, DEFAULT_CYCLE_TIME_DAYS, DAILY_TRUCK_OUTBOUND, DEFAULT_FLEET_BUFFER,
    BACKHAUL_ENABLED, BACKHAUL_SEARCH_RADIUS_KM, BACKHAUL_MAX_RETURN_PALLETS,
)
from logistic_core.utils.backhaul_detector import BackhaulDetector

logger = logging.getLogger(__name__)


# =====================================================================
#     FUNCION AUXILIAR: DASHBOARD HTML (Mapa + Tabla de Eficiencia)
# =====================================================================
def generate_logistics_dashboard(routes, solver, output_path="logistics_dashboard_pallets.html",
                                 map_iframe_src="mapa_flota_dedicada_folium.html",
                                 max_pallets=35, flota_por_planta=None):
    """Genera un dashboard HTML con pestanas (Mapa y Estadisticas) premium."""
    matrix = solver.distance_matrix
    depot_idx = 0
    route_stats = []

    for i, route in enumerate(routes):
        planta_node = next((n for n in route if n['type'] == 'carton_plant'), None)
        clientes_ruta = [n for n in route if n['type'] == 'customer']

        if not planta_node or not clientes_ruta:
            continue

        p_idx = planta_node['matrix_idx']
        last_c_idx = clientes_ruta[-1]['matrix_idx']

        # Ahorros
        dist_real_regreso = matrix[last_c_idx][depot_idx]
        dist_teorica_regreso = matrix[last_c_idx][p_idx] + matrix[p_idx][depot_idx]
        ahorro_km = max(0, (dist_teorica_regreso - dist_real_regreso) / 1000.0)

        # Distancia ruta
        d_ruta_m = sum(matrix[route[j]['matrix_idx']][route[j+1]['matrix_idx']] for j in range(len(route)-1))
        d_ruta_km = d_ruta_m / 1000.0

        carga = sum(n.get('demanda_pallets', 0) for n in clientes_ruta)
        pallets_reales = sum(n.get('n_pallets_original', n.get('demanda_pallets', 0)) for n in clientes_ruta)
        pct_uso = (carga / max_pallets) * 100

        # Construir secuencia "PP -> Planta -> C1 -> C2 -> PP"
        seq = ["PP", planta_node['name']]
        seq.extend(n['name'] for n in clientes_ruta)
        seq.append("PP")

        # Extraer el plant_id original (sin _clone_X)
        raw_id = planta_node.get('id', '')
        plant_id_clean = raw_id.split('_clone_')[0] if '_clone_' in raw_id else raw_id

        route_stats.append({
            "id": i + 1,
            "planta": planta_node['name'].upper().replace(' (MUELLE 2)', '').replace(' (MUELLE 3)', ''),
            "plant_id": plant_id_clean,
            "clientes": len(clientes_ruta),
            "carga": carga,
            "pallets_reales": pallets_reales,
            "pct_uso": min(pct_uso, 100.0),
            "secuencia": " &rarr; ".join(seq),
            "dist_km": round(d_ruta_km, 2),
            "ahorro_km": round(ahorro_km, 2)
        })

    # Agrupar por planta
    plantas_dict = {}
    for s in route_stats:
        pl = s["planta"]
        if pl not in plantas_dict:
            plantas_dict[pl] = []
        plantas_dict[pl].append(s)

    # Construir filas de la tabla
    filas_html = ""
    for planta, rutas_planta in plantas_dict.items():
        rowspan = len(rutas_planta)
        plant_id = rutas_planta[0].get('plant_id', '')
        flota_asignada = flota_por_planta.get(plant_id, 1) if flota_por_planta else 1
        flota_usada = len(rutas_planta)

        for idx, r in enumerate(rutas_planta):
            if r["pct_uso"] >= 80:
                bg_color = "success"
                estado = "Optima"
            elif r["pct_uso"] >= 50:
                bg_color = "warning"
                estado = "Mejorable"
            else:
                bg_color = "danger"
                estado = "Baja Carga"

            # Si hay pallets remontados, la carga real supera los huecos ocupados
            tiene_remontar = r['pallets_reales'] > r['carga']
            label_carga = f"{r['carga']}/{max_pallets} huecos ({r['pallets_reales']}P)" if tiene_remontar else f"{r['carga']}/{max_pallets} P"

            progreso_html = f'''
                <div class="progress" style="height: 24px;" title="{r['pct_uso']:.1f}% | {r['pallets_reales']} pallets fisicos">
                    <div class="progress-bar bg-{bg_color} text-dark fw-bold" style="width: {r['pct_uso']}%">
                        {label_carga}
                    </div>
                </div>
            '''

            filas_html += "<tr>"
            if idx == 0:
                flota_badge = f'<br><span class="badge bg-secondary mt-1">{flota_usada}/{flota_asignada} camiones</span>'
                filas_html += f'<td rowspan="{rowspan}" class="align-middle border-end bg-light"><b>{planta}</b>{flota_badge}</td>'

            filas_html += f'''
                <td class="align-middle text-nowrap">Camion #{r['id']}</td>
                <td class="align-middle text-start" style="font-size: 0.9em;">{r['secuencia']}</td>
                <td class="align-middle" style="min-width: 150px;">{progreso_html}</td>
                <td class="align-middle">{r['dist_km']} km</td>
                <td class="align-middle text-success fw-bold">+{r['ahorro_km']} km</td>
                <td class="align-middle">{estado}</td>
            </tr>
            '''

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard Inteligente de Flota</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .table tbody tr:hover {{ background-color: #f1f5f9; }}
            .border-end {{ border-right: 3px solid #dee2e6 !important; }}
            .nav-tabs .nav-link {{ color: #495057; font-weight: 500; }}
            .nav-tabs .nav-link.active {{ color: #0d6efd; border-bottom: 3px solid #0d6efd; }}
            table {{ box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        </style>
    </head>
    <body class="container-fluid py-4 bg-light">
        <h2 class="mb-4 text-primary fw-bold">Resumen de Flota y Backhauling</h2>

        <ul class="nav nav-tabs mb-3 border-0" id="dashboardTabs" role="tablist">
            <li class="nav-item">
                <button class="nav-link active bg-white border border-bottom-0 shadow-sm" id="map-tab" data-bs-toggle="tab" data-bs-target="#map" type="button">Visor Geografico de Rutas</button>
            </li>
            <li class="nav-item ms-2">
                <button class="nav-link bg-white border border-bottom-0 shadow-sm" id="stats-tab" data-bs-toggle="tab" data-bs-target="#stats" type="button">Eficiencia por Planta</button>
            </li>
        </ul>

        <div class="tab-content bg-white border p-3 rounded shadow-sm" id="dashboardTabsContent">
            <div class="tab-pane fade show active" id="map" role="tabpanel">
                <iframe src="{map_iframe_src}" style="width: 100%; height: 75vh; border: none; border-radius: 8px; background: #eaebed;"></iframe>
            </div>
            <div class="tab-pane fade" id="stats" role="tabpanel">
                <div class="table-responsive">
                    <table class="table table-bordered text-center align-middle">
                        <thead class="table-dark">
                            <tr>
                                <th>Planta de Origen</th>
                                <th>ID Ruta</th>
                                <th class="text-start">Hoja de Ruta de Reparto</th>
                                <th>Carga (Utilizacion Real)</th>
                                <th>Distancia (km)</th>
                                <th>Ahorro Km Vacios</th>
                                <th>Estado de Ruta</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path


# =====================================================================
#              PARAMETROS DE EJECUCION — Modifica estos valores
# =====================================================================

# 1. Archivos de datos y Periodo de Análisis (TFM Echandi)
ANALYSIS_YEAR = 2025
ANALYSIS_MONTH = 4
PLANTS_FILE = DATA_DIR / "locations_smurfit.json"
CLIENTS_FILE = DATA_DIR / "cliente_ubi.json"

# 2. Restricciones físicas y de negocio (Dinámicas)
estimator = TruckCapacityEstimator(
    container_length_m=float(os.getenv("TRAILER_LENGTH", 13.6)),
    container_width_m=float(os.getenv("TRAILER_WIDTH", 2.4)),
    container_height_m=float(os.getenv("TRAILER_HEIGHT", 2.7))
)
pallet_spec = Pallet(
    length_m=1.2, 
    width_m=0.8, 
    height_m=1.5
)

# Cálculo dinámico de capacidad real
cap_info = estimator.capacity(pallet_spec, stackable=False)
MAX_PALLETS = cap_info["total_pallets"]

THRESHOLD_KM_DETOUR = 50       # Desvío máximo permitido para backhauling
MAX_RADIUS_KM = 200      
# Radio máximo de búsqueda alrededor de la planta
N_CANDIDATOS_PLANTA = 30       # Candidatos por planta (fuerza uso de múltiples camiones)
MAX_SEARCH_TIME = 30            # Tiempo máximo de búsqueda del solver (s)
SORTING_STRATEGY = "far_plant_close_depot"

# Motor Geografico: "haversine", "osrm", "google_maps" o "routes_api"
API_TYPE = "osrm"

# Especificaciones de Camion
TRUCK_SPECS = {
    "emissionType": "DIESEL",
    "heightCm": 400,
    "weightKg": 40_000,
}

# 3. Configuracion de Flota por Planta (ID de planta: Numero de camiones)
FLOTA_POR_PLANTA = {
        "CP_CELPACK": 3,
        "CP_ALCALA": 4,
        "CP_ALICANTE": 5,
        "CP_ALMERIA": 5,
        "CP_BURGOS": 4,
        "CP_CANOVELLES": 2,
        "CP_CORDOBA": 3,
        "CP_NAVARRA": 2,
        "CP_HUELVA": 5,
        "CP_VALENCIA": 3,
        "CP_VIGO": 2
}

# 4. Clientes OBLIGATORIOS
MANDATORY_CUSTOMERS = {
    "Alcala": ["Ciudad Real"],
    "Cordoba": ["Andujar"]
}

# 5. Configuracion personalizada de clientes por planta
PLANT_CUSTOMER_LIMITS = None  # O dict con {"CP_ALCALA": 6, ...}
# =====================================================================


def run_optimization(
    max_pallets=35,
    threshold_km=50,
    n_candidatos=30,
    max_search_time=30,
    api_type="osrm",
    flota_por_planta=None,
    sorting_strategy="far_plant_close_depot",
    mandatory_customers=None,
    target_year=None,
    target_month=None,
    silent=False
):
    """
    Ejecución modular del optimizador para experimentación paralela o serial.
    """
    if not silent:
        print(f"\n>>> Ejecutando Optimización: Pallets={max_pallets}, Desvío={threshold_km}km, Candidatos={n_candidatos}")

    with open(PLANTS_FILE, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    geo_engine = GeoUtils(api_type=api_type)
    geo_engine.set_truck_specs(**TRUCK_SPECS)

    dm = DataManager(
        paper_plant=plants_data['paper_plant'],
        carton_plants=plants_data['carton_plants'],
        clients_file=CLIENTS_FILE,
        geo_utils=geo_engine
    )

    enriched_data = dm.get_optimized_locations(
        max_customers_per_plant=None,
        default_limit=n_candidatos,
        threshold_km=threshold_km,
        max_radius_km=MAX_RADIUS_KM,
        mandatory_customers=mandatory_customers or MANDATORY_CUSTOMERS,
        sorting_strategy=sorting_strategy,
        max_pallets=max_pallets,
        target_year=target_year,
        target_month=target_month
    )

    # Preparar flota
    flota_final = {}
    for p in enriched_data['carton_plants']:
        p_id = p['id']
        flota_final[p_id] = (flota_por_planta or FLOTA_POR_PLANTA).get(p_id, 1)

    solver = LogisticsSolver(enriched_data, geo_engine=geo_engine)
    routes = solver.solve(
        n_clientes=n_candidatos,
        varias_plantas=False,
        max_pallets_ruta=max_pallets,
        max_search_time=max_search_time,
        flota_por_planta=flota_final
    )

    if not routes:
        return None, None, None

    # --- FASE BACKHAULING (opcional, post-solve) ---
    # Detecta plantas de retorno candidatas para cada ruta y re-optimiza
    # con los nodos de recogida inyectados si BACKHAUL_ENABLED=True.
    if BACKHAUL_ENABLED:
        detector = BackhaulDetector(
            all_carton_plants=enriched_data["carton_plants"],
            geo_engine=geo_engine,
        )
        backhaul_map = detector.analyze_all_routes(
            routes=routes,
            distance_matrix=solver.distance_matrix,
            search_radius_km=BACKHAUL_SEARCH_RADIUS_KM,
            max_return_pallets=BACKHAUL_MAX_RETURN_PALLETS,
        )
        if backhaul_map:
            # Aplanar los candidatos: un nodo por ruta (el mas cercano al ultimo cliente)
            bh_flat = []
            for route_idx, candidates in backhaul_map.items():
                best = candidates[0]
                best["parent_route_idx"] = route_idx
                for node in solver.nodes:
                    if node.get("id") == best["id"]:
                        best["matrix_idx"] = node.get("matrix_idx", 0)
                        break
                bh_flat.append(best)

            if not silent:
                print(f">>> Backhauling: {len(bh_flat)} candidatos de retorno detectados. Re-optimizando...")

            # Segunda pasada con los nodos de backhauling
            solver_bh = LogisticsSolver(
                enriched_data, geo_engine=geo_engine,
                precomputed_matrix=solver.distance_matrix
            )
            routes_bh = solver_bh.solve(
                n_clientes=n_candidatos,
                varias_plantas=False,
                max_pallets_ruta=max_pallets,
                max_search_time=max_search_time,
                flota_por_planta=flota_final,
                backhaul_nodes=bh_flat,
            )
            if routes_bh:
                routes = routes_bh
                solver = solver_bh
                if not silent:
                    print(">>> Backhauling: Re-optimizacion completada con exito.")

    summary = _build_summary(routes, solver, max_pallets=max_pallets, threshold_km=threshold_km,
                             n_candidatos=n_candidatos)

    return routes, summary, solver

def _build_summary(routes, solver, max_pallets=35, threshold_km=50, n_candidatos=30):
    """Genera un JSON de resumen con KPIs por ruta."""
    route_summaries = []
    total_co2_kg = 0
    total_cost_eur = 0
    total_km = 0
    total_empty_km = 0
    
    cost_estimator = CostEstimator(
        price_per_km=TARIFA_INTERNA_DIESEL
    )

    co2_estimator = FCREmissionEstimator(
        co2_per_liter=GLEC_CO2_PER_LITER,
        intensity_gtkm=GLEC_INTENSITY_GTKM,
        empty_floor_kgkm=GLEC_EMPTY_FLOOR_KGKM
    )

    for i, route in enumerate(routes):
        customer_nodes = [n for n in route if n['type'] == 'customer']
        if not customer_nodes:
            continue

        total_pallets = sum(c.get('demanda_pallets', 0) for c in customer_nodes)
        dist_km = 0
        empty_km = 0
        route_co2_kg = 0
        current_load_kg = 0
        
        for j in range(len(route) - 1):
            n1, n2 = route[j], route[j+1]
            d = solver.distance_matrix[n1['matrix_idx']][n2['matrix_idx']] / 1000
            dist_km += d
            
            if n1['type'] == 'depot':
                current_load_kg = PAPER_LOAD_KG
            elif n1['type'] == 'carton_plant':
                current_load_kg = total_pallets * PALLET_WEIGHT_KG
            elif n1['type'] == 'customer':
                pallets_left = n1.get('demanda_pallets', 0)
                current_load_kg = max(0, current_load_kg - (pallets_left * PALLET_WEIGHT_KG))
                
            if j == len(route) - 2 and n2['type'] == 'depot':
                empty_km += d
                current_load_kg = 0

            leg_co2 = co2_estimator.co2_partial_load(
                distance_km=d,
                current_load=current_load_kg,
                max_load=VEHICLE_MAX_LOAD_KG
            )
            route_co2_kg += leg_co2

        plant_nodes = [n for n in route if n['type'] == 'carton_plant']

        route_summaries.append({
            "route_id": len(route_summaries) + 1,
            "plants": [p['name'] for p in plant_nodes],
            "num_customers": len(customer_nodes),
            "total_pallets": total_pallets,
            "distance_km": round(dist_km, 2),
            "empty_km": round(empty_km, 2),
            "co2_emissions_kg": round(route_co2_kg, 2),
            "estimated_cost_eur": cost_estimator.estimate_cost(dist_km)
        })
        total_km += dist_km
        total_empty_km += empty_km
        total_co2_kg += route_co2_kg
        total_cost_eur += cost_estimator.estimate_cost(dist_km)

    return {
        "num_routes": len(route_summaries),
        "total_km": round(total_km, 2),
        "total_empty_km": round(total_empty_km, 2),
        "total_co2_kg": round(total_co2_kg, 2),
        "total_cost_eur": round(total_cost_eur, 2),
        "parameters": {
            "max_pallets": max_pallets,
            "threshold_km": threshold_km,
            "n_candidatos": n_candidatos
        },
        "total_customers": sum(r["num_customers"] for r in route_summaries),
        "total_pallets_moved": sum(r["total_pallets"] for r in route_summaries),
        "routes": route_summaries
    }

def main():
    print("=====================================================================")
    print(f" LOGISTICS OPTIMIZER - Periodo: {ANALYSIS_MONTH}/{ANALYSIS_YEAR}")
    print("=====================================================================\n")

    print(f"Capacidad Detectada: {MAX_PALLETS} pallets ({cap_info['summary']})")
    print(f"Configuracion: {'Apilable' if cap_info['stackable'] else 'No Apilable'}\n")

    routes, summary, solver = run_optimization(
        max_pallets=MAX_PALLETS,
        threshold_km=THRESHOLD_KM_DETOUR,
        n_candidatos=N_CANDIDATOS_PLANTA,
        api_type=API_TYPE,
        target_year=ANALYSIS_YEAR,
        target_month=ANALYSIS_MONTH
    )

    if not routes:
        print("Error en la optimización.")
        return

    # 6. Guardar resultados (Compatibilidad con dashboard anterior)
    output_json = RESULTS_DIR / "optimized_routes.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(routes, f, indent=2, ensure_ascii=False)
    
    summary_json = RESULTS_DIR / "optimization_summary.json"
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 9. Mapa Folium con rutas OSRM reales (Usando Visualizer centralizado)
    viz = Visualizer(routes, solver.distance_matrix, geo_utils=solver.geo)
    map_output = viz.create_map("Logistics_Dashboard.html")
    print(f"=> Mapa interactivo actualizado: {map_output}")
    
    # 10. Actualizar Dashboard Modular (tab_resumen.html)
    presentation_path = "outputs/Presentacion_Logistica.html"
    try:
        generate_dashboard(summary_json, output_json, presentation_path, is_baseline=False)
        print(f"=> Presentacion (Modular) actualizada: {presentation_path}")
    except Exception as e:
        logger.warning("No se pudo actualizar la Presentacion Modular: %s", e)

    print(f"\nTOTAL: {summary['total_km']:.2f} km | CO2: {summary['total_co2_kg']:.2f} kg | Rutas: {summary['num_routes']} | Coste Est.: {summary['total_cost_eur']:.2f} €")
    
    # 11. Imprimir Estimación de CAPEX y Flota (Ley de Little)
    print("\n=====================================================================")
    print(" INVERSION NECESARIA: FLOTA HEAVY (LEY DE LITTLE)")
    print("=====================================================================")
    capex_estimator = FleetCapexEstimator(
        daily_dispatch_rate=DAILY_TRUCK_OUTBOUND,
        unit_truck_cost=CAPEX_TRUCK_UNIT_COST,
        utilization_buffer=DEFAULT_FLEET_BUFFER
    )
    resumen_capex = capex_estimator.generate_investment_summary(average_cycle_time_days=DEFAULT_CYCLE_TIME_DAYS)
    
    print(f"Salidas diarias constantes (lambda): {resumen_capex['daily_dispatch_rate']} viajes/dia")
    print(f"Tiempo de ciclo logistico (W):       {resumen_capex['average_cycle_time_days']} dias")
    print(f"Flota minima teorica requerida:      {resumen_capex['theoretical_fleet_base']} vehiculos")
    print(f"Flota instalada final (real):        {resumen_capex['final_required_fleet']} vehiculos fisicos (buffer {DEFAULT_FLEET_BUFFER*100-100:.0f}%)")
    print(f"INVERSION TOTAL CAPEX:               {resumen_capex['total_capex_investment']:,.2f} EUR\n")

if __name__ == "__main__":
    main()
