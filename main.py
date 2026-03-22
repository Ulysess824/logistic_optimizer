import json
import logging
from pathlib import Path
import folium
import polyline

from src.engine.solver import LogisticsSolver
from src.utils.data_manager import DataManager
from src.utils.geo import GeoUtils
from src.utils.visualizer import Visualizer
from src.utils.report_generator import generate_dashboard
from src.config import RESULTS_DIR, DATA_DIR

logging.basicConfig(level=logging.WARNING)
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

            progreso_html = f'''
                <div class="progress" style="height: 24px;" title="{r['pct_uso']:.1f}%">
                    <div class="progress-bar bg-{bg_color} text-dark fw-bold" style="width: {r['pct_uso']}%">
                        {r['carga']}/{max_pallets} P
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

# 1. Archivos de datos
PLANTS_FILE = DATA_DIR / "locations_smurfit.json"
CLIENTS_FILE = DATA_DIR / "demanda_simulada.json"

# 2. Restricciones fisicas y de negocio
MAX_PALLETS = 15                # Capacidad maxima por camion (Bin-packing)
THRESHOLD_KM_DETOUR = 80       # Desvio maximo permitido para backhauling
MAX_RADIUS_KM = 200            # Radio maximo de busqueda alrededor de la planta
N_CANDIDATOS_PLANTA = 15       # Candidatos por planta (fuerza uso de multiples camiones)
MAX_SEARCH_TIME = 30            # Tiempo maximo de busqueda del solver (s)
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
            "total_pallets": sum(c.get('demanda_pallets', 0) for c in customer_nodes),
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
        "distance_source": "GPS Real" if solver.is_real_road else "Haversine (estimacion)",
        "parameters": {
            "n_candidatos": N_CANDIDATOS_PLANTA,
            "max_pallets": MAX_PALLETS,
            "threshold_km": THRESHOLD_KM_DETOUR,
            "max_radius_km": MAX_RADIUS_KM,
        },
        "routes": route_summaries
    }


def main():
    print("=====================================================================")
    print(" LOGISTICS OPTIMIZER - EVALUACION Y DASHBOARD INTEGRADO")
    print("=====================================================================\n")

    if not PLANTS_FILE.exists() or not CLIENTS_FILE.exists():
        print(f"Error: Archivos de datos insuficientes ({PLANTS_FILE} o {CLIENTS_FILE}).")
        return

    with open(PLANTS_FILE, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    # 1. Configurar Motor Geografico
    print(f"[1] Conectando con la API de enrutamiento ({API_TYPE}) para calculos reales de carretera...")
    geo_engine = GeoUtils(api_type=API_TYPE)
    geo_engine.set_truck_specs(**TRUCK_SPECS)

    # 2. Auto-Ajuste de Capacidad por clientes obligatorios
    min_needed_capacity = 0
    if MANDATORY_CUSTOMERS:
        for p, custs in MANDATORY_CUSTOMERS.items():
            num_mand = 1 if isinstance(custs, str) else len(custs)
            min_needed_capacity = max(min_needed_capacity, num_mand)

    current_n_clientes = N_CANDIDATOS_PLANTA
    if min_needed_capacity > current_n_clientes:
        logger.warning("Capacidad insuficiente detectada -- Ajustando N_CANDIDATOS de %d a %d",
                       current_n_clientes, min_needed_capacity)
        current_n_clientes = min_needed_capacity

    # 3. Preparacion de Nodos usando DataManager (filtro base + particion de envios)
    print(f"[2] Filtrando los {current_n_clientes} candidatos mas logicos POR PLANTA mediante DataManager...")
    dm = DataManager(
        paper_plant=plants_data['paper_plant'],
        carton_plants=plants_data['carton_plants'],
        clients_file=CLIENTS_FILE,
        geo_utils=geo_engine
    )

    enriched_data = dm.get_optimized_locations(
        max_customers_per_plant=PLANT_CUSTOMER_LIMITS,
        default_limit=current_n_clientes,
        threshold_km=THRESHOLD_KM_DETOUR,
        max_radius_km=MAX_RADIUS_KM,
        mandatory_customers=MANDATORY_CUSTOMERS,
        sorting_strategy=SORTING_STRATEGY,
        max_pallets=MAX_PALLETS
    )

    total_candidatos = sum(len(p.get('customers', [])) for p in enriched_data['carton_plants'])
    print(f"[3] Nodos encontrados: 1 Deposito, {len(enriched_data['carton_plants'])} Plantas y {total_candidatos} Clientes evaluables.")

    # 4. Preparar la flota final (inyectando defaults)
    flota_final = {}
    for p in enriched_data['carton_plants']:
        p_id = p['id']
        flota_final[p_id] = FLOTA_POR_PLANTA.get(p_id, 1)

    print(f"[4] Distribucion de la flota activa: {flota_final}")

    # 5. Resolucion VRP con Limite de Pallets
    print(f"[5] El algoritmo VRP arranca. Objetivo: Minimizar distancia limitando a {MAX_PALLETS} Pallets y respetando la Flota.\n")

    solver = LogisticsSolver(enriched_data, geo_engine=geo_engine)
    routes = solver.solve(
        n_clientes=current_n_clientes,
        varias_plantas=False,
        max_pallets_ruta=MAX_PALLETS,
        max_search_time=MAX_SEARCH_TIME,
        flota_por_planta=flota_final
    )

    if not routes:
        print("El optimizador no devolvio soluciones.")
        return

    print("=" * 70)
    print(" EXTRACCION DE LOG Y REPORTES")
    print("=" * 70)

    # Log de clientes descartados
    if hasattr(solver, 'drop_log_path'):
        print(f"=> Se ha exportado el reporte de descartes a: {solver.drop_log_path}")

    # 6. Guardar rutas detalladas
    output_json = RESULTS_DIR / "optimized_routes.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(routes, f, indent=2, ensure_ascii=False)
    print(f"=> Rutas detalladas guardadas en: {output_json}")

    # 7. Generar y guardar resumen de KPIs
    summary = _build_summary(routes, solver)
    summary_json = RESULTS_DIR / "optimization_summary.json"
    with open(summary_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"=> Resumen KPIs guardado en: {summary_json}")

    # 8. Visualizacion avanzada
    try:
        visualizer = Visualizer(routes, solver.distance_matrix, geo_utils=solver.geo)
        map_path = visualizer.create_map("Logistics_Dashboard.html")
        graph_path = visualizer.create_plotly_graph("Logistics_Graph.html")

        with open(CLIENTS_FILE, 'r', encoding='utf-8') as f:
            raw_clients = json.load(f)
        all_clients_list = []
        for z, dests in raw_clients.items():
            for d in dests:
                if "latitude" in d and "longitude" in d:
                    all_clients_list.append({"name": d.get("municipio_destino", z), "lat": d["latitude"], "lng": d["longitude"]})

        complexity_graph_path = visualizer.create_global_complexity_graph(
            plants_data['paper_plant'], plants_data['carton_plants'], all_clients_list, "Logistics_Global_Complexity.html"
        )
        print(f"=> Mapa interactivo: {map_path}")
        print(f"=> Grafo optimizado: {graph_path}")
        print(f"=> Grafo complejidad: {complexity_graph_path}")
    except Exception as e:
        logger.warning("No se pudieron generar las visualizaciones avanzadas: %s", e)

    # 9. Mapa Folium con rutas OSRM reales
    m_lat = plants_data['paper_plant']['lat']
    m_lng = plants_data['paper_plant']['lng']
    mapa = folium.Map(location=[m_lat, m_lng], zoom_start=6, tiles="CartoDB positron")

    colores_ruta = ['blue', 'green', 'red', 'purple', 'orange', 'darkred', 'cadetblue']

    for i, route in enumerate(routes):
        color_actual = colores_ruta[i % len(colores_ruta)]

        for n in route:
            if n['type'] == 'depot':
                folium.Marker([n['lat'], n['lng']], popup="MENGIBAR (Depot Papel)", icon=folium.Icon(color='black', icon='home')).add_to(mapa)
            elif n['type'] == 'carton_plant':
                folium.Marker([n['lat'], n['lng']], popup=f"PLANTA: {n['name']}", icon=folium.Icon(color='gray', icon='industry', prefix='fa')).add_to(mapa)
            else:
                popup_text = f"{n['name']} | Pedido: {n.get('demanda_pallets', 0)} pallets"
                folium.Marker([n['lat'], n['lng']], popup=popup_text, icon=folium.Icon(color=color_actual)).add_to(mapa)

        for j in range(len(route) - 1):
            start_n = route[j]
            end_n = route[j+1]
            try:
                encoded_poly = geo_engine.get_route_polyline((start_n['lat'], start_n['lng']), (end_n['lat'], end_n['lng']))
                if encoded_poly and encoded_poly != "BILLING_ERROR":
                    decoded_points = polyline.decode(encoded_poly)
                    folium.PolyLine(decoded_points, color=color_actual, weight=5, opacity=0.8).add_to(mapa)
                else:
                    folium.PolyLine([[start_n['lat'], start_n['lng']], [end_n['lat'], end_n['lng']]], color=color_actual, weight=5, opacity=0.8, dash_array='5, 10').add_to(mapa)
            except Exception:
                folium.PolyLine([[start_n['lat'], start_n['lng']], [end_n['lat'], end_n['lng']]], color=color_actual, weight=5, opacity=0.8, dash_array='5, 10').add_to(mapa)

    output_map_html = "mapa_flota_dedicada_folium.html"
    mapa.save(output_map_html)
    print(f"=> Mapa de Rutas geolocalizadas: {output_map_html}")

    # 10. Dashboard de Eficiencia por Planta
    output_dashboard = "logistics_dashboard_pallets.html"
    generate_logistics_dashboard(routes, solver, output_path=output_dashboard, map_iframe_src=output_map_html, max_pallets=MAX_PALLETS, flota_por_planta=flota_final)
    print(f"=> Tablero Interactivo (Eficiencia + Mapa): {output_dashboard}")

    # 11. Actualizar Presentacion HTML (Dashboard Global)
    presentation_path = "outputs/Presentacion_Logistica.html"
    try:
        generate_dashboard(summary_json, output_json, presentation_path)
        print(f"=> Presentacion actualizada: {presentation_path}")
    except Exception as e:
        logger.warning("No se pudo actualizar la Presentacion: %s", e)

    # 12. Resumen en consola
    print("\n" + "=" * 70)
    print(" RESUMEN DE OPERACION")
    print("=" * 70)
    for r in summary['routes']:
        plants_str = ", ".join(r['plants']) if len(r['plants']) > 1 else r['plants'][0]
        print(f"  Ruta {r['route_id']}: {plants_str} -> {r['num_customers']} clientes ({r.get('total_pallets', 0)} pallets) -> {r['distance_km']:.2f} km ({r['empty_km']:.2f} km en vacio)")
    print(f"  TOTAL: {summary['total_km']:.2f} km ({summary['total_empty_km']:.2f} km en vacio) en {summary['num_routes']} rutas")

    print(solver.summary())

    print("\n" + "=" * 70)
    print(" Proceso finalizado. Puedes abrir el html en cualquier navegador.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
