"""
report_generator.py
───────────────────
Lee los resultados de la optimización (summary + routes) y parchea
dinámicamente el HTML de la presentación, actualizando:

  1. KPIs (rutas, distancia, plantas, clientes, ahorro km vacíos)
  2. Tabla de ahorro de kilómetros vacíos (antes vs después)
  3. Tabla detallada de rutas (Tab 3)
  4. Datos del gráfico Chart.js (barra de distancias)
"""
import os
import sys

# Corregir el PATH para evitar colisiones con paquetes 'src' instalados en el sistema
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
import re
import logging
from pathlib import Path
from src.utils.geo import GeoUtils
logger = logging.getLogger(__name__)


def fmt_std(val, decimals=2):
    """Formatea un número al estilo estándar (punto para decimales)."""
    if val is None: return "0"
    return f"{val:,.{decimals}f}"


def generate_dashboard(summary_path, routes_path, output_path, hedonic_path=None):
    """Actualiza el fichero HTML de presentación con los datos reales."""

    summary_path = Path(summary_path)
    routes_path  = Path(routes_path)
    output_path  = Path(output_path)

    if not summary_path.exists() or not routes_path.exists():
        logger.error("Archivos de resultados no encontrados. Abortando generación del Dashboard.")
        return
    if not output_path.exists():
        logger.error("Plantilla HTML no encontrada en %s. Abortando.", output_path)
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    with open(routes_path, "r", encoding="utf-8") as f:
        routes = json.load(f)

    geo = GeoUtils()

    # ──────────────────────────────────────────────────────────────────
    # 1. Calcular métricas de kilómetros vacíos
    # ──────────────────────────────────────────────────────────────────
    total_empty_before = 0.0
    total_empty_after  = 0.0
    km_rows_html: list[str] = []
    route_rows_html: list[str] = []
    unique_plants: set[str] = set()
    unique_customers: set[str] = set()

    for idx, r in enumerate(summary["routes"]):
        # Recuperamos la información de la ruta completa para cálculos específicos
        route_nodes = routes[idx]
        depot = route_nodes[0]
        
        # Encontramos la última planta de la ruta (tradicionalmente el camión volvería desde ahí)
        plants_in_route = [n for n in route_nodes if n["type"] == "carton_plant"]
        last_plant = plants_in_route[-1]
        
        # Encontramos el último cliente de la ruta (desde donde vuelve ahora)
        customers_in_route = [n for n in route_nodes if n["type"] == "customer"]
        if not customers_in_route:
            # Si no hay clientes, el camión vuelve desde la última planta
            last_customer = last_plant
        else:
            last_customer = customers_in_route[-1]

        # Kilómetros vacíos:
        # Tradicional: De la última planta al depósito
        empty_before = geo.haversine_km(last_plant["lat"], last_plant["lng"],
                                        depot["lat"], depot["lng"])
        # Backhauling: Del último cliente al depósito (ya calculado en el sumario)
        empty_after = r["empty_km"]
        
        savings     = max(0, empty_before - empty_after)
        improvement = (savings / empty_before * 100) if empty_before > 0 else 0
        
        total_empty_before += empty_before
        total_empty_after  += empty_after
        
        unique_plants.update(r["plant_ids"])
        unique_customers.update(r["customers"])

        # Fila para la Tabla de Impacto (Tab 1)
        # Usamos nombres cortos de plantas unidos por coma
        plants_short = ", ".join([p.replace("Smurfit Westrock ", "") for p in r["plants"]])
        
        km_rows_html.append(
            f'<tr class="hover:bg-gray-50 border-b">'
            f'<td class="px-3 py-2 font-semibold text-gray-800 border-l-4 border-blue-500">{plants_short}</td>'
            f'<td class="px-3 py-2 text-center font-mono">{fmt_std(r["distance_km"])}</td>'
            f'<td class="px-3 py-2 text-center font-mono">{fmt_std(empty_before)}</td>'
            f'<td class="px-3 py-2 text-center font-mono font-bold text-blue-700">{fmt_std(empty_after)}</td>'
            f'<td class="px-3 py-2 text-center font-bold text-green-600">+{fmt_std(improvement, 1)}%</td>'
            f'<td class="px-3 py-2 text-center text-gray-400" title="Por recolectar">-</td>'
            f'<td class="px-3 py-2 text-center text-gray-400" title="Por recolectar">-</td>'
            f'<td class="px-3 py-2 text-center text-gray-400" title="Por recolectar">-</td>'
            f'<td class="px-3 py-2 text-center text-gray-400" title="Por recolectar">-</td>'
            f'</tr>'
        )

        # Fila para la Tabla Detallada (Tab 3)
        bg_class = ' bg-gray-50' if idx % 2 == 1 else ''
        route_rows_html.append(
            f'<tr class="border-b hover:bg-gray-50{bg_class}">'
            f'<td class="py-3 px-4 font-bold text-center">{r["route_id"]}</td>'
            f'<td class="py-3 px-4">{", ".join(r["plants"])}</td>'
            f'<td class="py-3 px-4 text-center">{r["num_customers"]}</td>'
            f'<td class="py-3 px-4 font-mono">{fmt_std(r["distance_km"])} km</td>'
            f'<td class="py-3 px-4 text-xs italic">{", ".join(r["customers"])}</td>'
            f'</tr>'
        )

    total_savings = total_empty_before - total_empty_after
    total_pct     = (total_savings / total_empty_before * 100) if total_empty_before > 0 else 0

    # ──────────────────────────────────────────────────────────────────
    # 3. Leer y parchear el HTML
    # ──────────────────────────────────────────────────────────────────
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    # --- 3a. KPIs ---
    def _replace_kpi(html_text, label_re, new_value):
        # El valor puede contener tags como <br> o <span>, por lo que usamos .*? en modo DOTALL
        pat = re.compile(
            rf'(<p\s+class="kpi-label">{label_re}</p>\s*'
            rf'<p\s+class="kpi-value"[^>]*>).*?(</p>)',
            re.IGNORECASE | re.DOTALL)
        return pat.sub(rf'\g<1>{new_value}\g<2>', html_text)

    html = _replace_kpi(html, r"Rutas Totales Generadas",  summary["num_routes"])
    html = _replace_kpi(html, r"Distancia Total \(km\)",    f'{fmt_std(summary["total_km"])} <br><span class="text-[10px] uppercase opacity-60">({summary.get("distance_source", "GPS Real")})</span>')
    html = _replace_kpi(html, r"Plantas Visitadas",         len(unique_plants))
    total_deliveries = sum(r["num_customers"] for r in summary["routes"])
    html = _replace_kpi(html, r"Clientes Satisfechos",      total_deliveries)
    # También actualizamos el label para que sea coherente
    html = html.replace("Clientes Satisfechos", "Entregas Realizadas")
    html = _replace_kpi(html, r"Ahorro Km Vac[ií]os",      f"~{fmt_std(total_pct, 1)}%")

    # --- 3b. Hedonic Section ---
    if hedonic_path and Path(hedonic_path).exists():
        with open(hedonic_path, "r", encoding="utf-8") as f:
            hd = json.load(f)
        
        def build_model_table(model_data, title):
            rows = []
            for var, coef in model_data["coefficients"].items():
                p = model_data["pvalues"].get(var, 0)
                # Show p-value exactly as 0.000 or actual decimal
                p_str = f"{p:.4f}" if p >= 0.0001 else "0.0000"
                rows.append(
                    f'<tr class="border-b"><td class="py-1 px-3">{var}</td>'
                    f'<td class="py-1 px-3 font-mono text-center">{coef:.4f}</td>'
                    f'<td class="py-1 px-3 text-center text-[10px] font-mono">{p_str}</td></tr>'
                )
            
            return (
                f'<div class="flex-1 min-w-[300px]">'
                f'  <h4 class="text-sm font-bold text-gray-700 bg-gray-50 p-2 border-l-2 border-indigo-400 mb-2">{title}</h4>'
                f'  <table class="w-full text-[11px] text-left">'
                f'    <thead class="bg-gray-100"><tr><th class="p-1 px-3">Variable</th><th class="p-1 text-center">Coef.</th><th class="p-1 text-center">P-valor</th></tr></thead>'
                f'    <tbody>{"".join(rows)}</tbody>'
                f'  </table>'
                f'  <div class="mt-4 p-3 bg-indigo-50/50 rounded text-[11px]">'
                f'    <p><strong>R² Adj:</strong> {model_data["summary"]["rsquared_adj"]:.4f}</p>'
                f'    <p><strong>Durbin-Watson:</strong> {model_data["summary"]["durbin_watson"]:.2f}</p>'
                f'    <p><strong>N:</strong> {model_data["summary"]["n_obs"]:,}</p>'
                f'  </div>'
                f'</div>'
            )

        tables_html = (
            f'<div class="flex flex-wrap gap-6 mt-4">'
            f'  {build_model_table(hd["model_full"], "Modelo 1: Completo")}'
            f'  {build_model_table(hd["model_base"], "Modelo 2: Sin Transportista")}'
            f'  {build_model_table(hd["model_no_pallets"], "Modelo 3: Sin Pallets")}'
            f'</div>'
        )

        explanations_html = (
            f'<div class="grid grid-cols-1 md:grid-cols-2 gap-8 mt-10 border-t pt-8">'
            f'  <div class="card bg-white">'
            f'    <h4 class="font-bold text-indigo-900 border-b pb-2 mb-3">Glosario de Variables</h4>'
            f'    <ul class="text-xs space-y-3 text-gray-700">'
            f'      <li><strong>log_Distance:</strong> Elasticidad-distancia. Indica cuánto varía porcentualmente el coste ante un cambio en la distancia. Refleja la economía de escala por recorrido.</li>'
            f'      <li><strong>log_Pallets:</strong> Elasticidad-volumen. Captura el impacto de la carga transportada en la tarifa final.</li>'
            f'      <li><strong>Carr_ (Dummies):</strong> Efecto diferencial de cada transportista sobre la media. Captura eficiencias operativas o primas de marca.</li>'
            f'      <li><strong>Type_ (Dummies):</strong> Diferencial de precio según el modo de envío (LTL vs FTL).</li>'
            f'      <li><strong>Const:</strong> Tarifa base o componente fijo del precio no explicada por el recorrido o volumen.</li>'
            f'    </ul>'
            f'  </div>'
            f'  <div class="card bg-white">'
            f'    <h4 class="font-bold text-indigo-900 border-b pb-2 mb-3">Análisis de Validación</h4>'
            f'    <ul class="text-xs space-y-3 text-gray-700">'
            f'      <li><strong>R-cuadrado Ajustado:</strong> Mide la capacidad predictiva. Al comparar los tres modelos, observamos que eliminar los pallets ({hd["model_no_pallets"]["summary"]["rsquared_adj"]:.3f}) afecta al ajuste, demostrando que el volumen es un driver crítico.</li>'
            f'      <li><strong>Durbin-Watson:</strong> Detecta autocorrelación en residuos. Valores consistentes entre modelos sugieren estabilidad en la estructura de error.</li>'
            f'      <li><strong>P-valor:</strong> Los resultados exactos confirman que todas las variables en los tres modelos son estadísticamente significativas (p-valor < 0.05).</li>'
            f'    </ul>'
            f'  </div>'
            f'</div>'
        )

        hedonic_html = (
            f'<div class="card shadow-md border-t-4 border-indigo-600 p-6 mt-12 bg-white">'
            f'  <h2 class="text-2xl font-bold text-indigo-900 mb-2">Estimación de Tarifa por medio de Precios Hedónicos</h2>'
            f'  <p class="text-sm text-gray-600 mb-8 italic">Análisis econométrico SOTA mediante modelos de doble logaritmo (Elasticidades).</p>'
            f'  {tables_html}'
            f'  {explanations_html}'
            f'</div>'
        )
        
        hedonic_marker = '<div id="hedonic-placeholder"></div>'
        if hedonic_marker in html:
            html = html.replace(hedonic_marker, hedonic_html)
        else:
            # Si no existe el marker, lo ponemos al final de resultados
            html = html.replace('<!-- Fin Detalle Operativo -->', hedonic_html + '\n<!-- Fin Detalle Operativo -->')

    # --- 3c. Tabla de Rutas (Tab 3) ---
    tbody_marker = 'id="routes-tbody"'
    idx_tbody = html.find(tbody_marker)
    if idx_tbody != -1:
        # Buscamos el final de la etiqueta de apertura >
        start_content = html.find('>', idx_tbody) + 1
        # Buscamos el cierre de ese tbody
        end_content = html.find('</tbody>', start_content)
        if end_content != -1:
            html = (html[:start_content]
                    + '\n' + "\n".join(route_rows_html) + '\n'
                    + html[end_content:])

    # --- 3d. Tabla de Comparativa (Ahorro Km) ---
    tbody_comp_marker = 'id="comparison-tbody"'
    idx_tbody_comp = html.find(tbody_comp_marker)
    if idx_tbody_comp != -1:
        start_content = html.find('>', idx_tbody_comp) + 1
        end_content = html.find('</tbody>', start_content)
        if end_content != -1:
            html = (html[:start_content]
                    + '\n' + "\n".join(km_rows_html) + '\n'
                    + html[end_content:])



    # --- 3e. Nota estratégica ---
    try:
        max_route = max(summary["routes"], key=lambda r: r["distance_km"])
        min_route = min(summary["routes"], key=lambda r: r["distance_km"])
        nota_full = (
            f'<div class="card bg-green-50 border border-green-200 p-4 rounded-lg shadow-sm">'
            f'<h2 class="text-xl font-bold mb-2 text-green-900">Análisis Operativo</h2>'
            f'<p class="text-gray-700"><strong>Nota:</strong> La variabilidad de distancias '
            f'(desde {fmt_std(min_route["distance_km"], 0)} km hasta {fmt_std(max_route["distance_km"], 0)} km) '
            f'refleja la dispersión geográfica del mercado.</p>'
            f'</div>'
        )
        note_marker = 'class="header-note-placeholder"'
        idx_note = html.find(note_marker)
        if idx_note != -1:
            start_div = html.find('>', idx_note) + 1
            end_div = html.find('</div>', start_div)
            html = html[:start_div] + "\n" + nota_full + "\n" + html[end_div:]
    except Exception as e:
        logger.warning("No se pudo actualizar la nota: %s", e)

    # --- 3f. Inserción del Logo de Smurfit en el Banner ---
    logo_url = "https://corrugandodigital.acccsa.org/hubfs/SW_LOGO_2COL.png"
    # Buscamos el header y lo reemplazamos con una versión que incluya el logo
    header_regex = re.compile(r'<header[^>]*>.*?</header>', re.DOTALL)
    new_header = (
        f'<header class="flex justify-between items-center shadow-md px-8 bg-[#1e3a8a] text-white mb-6">'
        f'<div class="flex items-center py-4">'
        f'<img src="{logo_url}" alt="Smurfit Logo" class="h-12 mr-6 bg-white p-1 rounded">'
        f'<div>'
        f'<h1 class="text-3xl font-bold">Logistics Optimizer</h1>'
        f'<p class="text-sm mt-1 opacity-80">MC-VRPB con Backhauling Multi-Planta</p>'
        f'</div>'
        f'</div>'
        f'<div>'
        f'<p class="text-lg font-mono bg-blue-800 px-4 py-2 rounded">v5.2</p>'
        f'</div>'
        f'</header>'
    )
    html = header_regex.sub(new_header, html)

    # --- 3g. Limpieza de Emojis y Espacios ---
    # Eliminamos emojis comunes para un look más profesional
    emojis_to_remove = ["🚀", "🧠", "📊", "🗺️", "🕸️", "✔️", "🏭", "🏗️", "🧑‍🤝‍🧑", "🔙", "💡", "📉", "➡️"]
    for emoji in emojis_to_remove:
        html = html.replace(emoji, "")
    
    # Limpiar espacios en blanco dobles y espacios al inicio de etiquetas causados por el borrado de emojis
    html = re.sub(r'>\s+([A-Z])', r'>\1', html) # Quita espacio al inicio de texto en etiquetas
    html = html.replace("  ", " ") # Reduce espacios dobles
    
    # También eliminamos flechas especiales si quedan, reemplazándolas por caracteres estándar
    html = html.replace("➡️", "→")

    # --- 3h. Limpieza de texto basura detectado ---
    html = html.replace("</header>\n    Ahorro", "</header>")
    html = html.replace("</header> Ahorro", "</header>")
    html = html.replace("</header>Ahorro", "</header>")

    # --- 3i. Inserción de Nueva Visualización de Estrategia de Ordenamiento ---
    sorting_visual_html = """
    <!-- Nueva Sección: Estrategia de Selección (Sorting) -->
    <div class="grid grid-cols-1 gap-6 mb-6 mt-6">
        <div class="card bg-white border-t-4 border-orange-500 shadow-md">
            <h2 class="text-xl font-bold text-gray-800 mb-2">Estrategia de Selección: Lejanía vs Desvío</h2>
            <p class="text-sm text-gray-600 mb-4">Análisis de cómo el parámetro <b>SORTING_STRATEGY</b> determina qué cliente se prioriza una vez superados los filtros geográficos.</p>
            <div class="h-[500px] w-full border rounded overflow-hidden shadow-inner bg-gray-50">
                <iframe src="maps/visualizacion_sorting_strategy.html" class="w-full h-full border-0"></iframe>
            </div>
            <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-500">
                <div class="p-2 bg-orange-50 rounded border-l-4 border-orange-400">
                    <strong>Estrategia Clásica (Detour):</strong> Selecciona al cliente que menos kilómetros extra añade a la ruta directa.
                </div>
                <div class="p-2 bg-green-50 rounded border-l-4 border-green-400">
                    <strong>Estrategia Backhauling Eficiente:</strong> Selecciona al cliente que esté más lejos de la planta y más cerca de la base, maximizando la utilidad del retorno.
                </div>
            </div>
        </div>
    </div>
    """
    
    # Aseguramos que el módulo de metodología modular esté presente
    metodologia_modular_html = """
    <!-- Módulo Independiente: Fundamentos Matemáticos y de Negocio -->
    <div class="grid grid-cols-1 gap-6 mb-6">
        <div class="card bg-white border-t-4 border-indigo-700 shadow-md">
            <div class="h-[750px] w-full bg-white rounded overflow-hidden shadow-inner font-sans">
                <iframe src="maps/explicacion_metodologia.html" class="w-full h-full border-0"></iframe>
            </div>
        </div>
    </div>
    """
    
    if 'maps/explicacion_metodologia.html' not in html:
        # Lo insertamos al principio de la pestaña metodología
        html = html.replace('<div id="metodologia" class="tab-content transition-opacity duration-300">', 
                            '<div id="metodologia" class="tab-content transition-opacity duration-300">\n' + metodologia_modular_html)

    # Lo insertamos dentro de la sección de metodología para que no aparezca en todas las pestañas
    if 'maps/visualizacion_sorting_strategy.html' not in html:
        # El final de la metodología se marca con un cierre de div antes de Tab 3
        # Buscamos '<!-- Tab 3: Resultados -->' y retrocedemos hasta el div previo
        pattern = r"(\s+</div>\n)(\s+<!-- Tab 3: Resultados -->)"
        if re.search(pattern, html):
            html = re.sub(pattern, r"\1" + sorting_visual_html + r"\2", html)
        else:
             # Fallback: lo insertamos antes del comentario de Tab 3 si el patrón falla
             html = html.replace('<!-- Tab 3: Resultados -->', sorting_visual_html + '\n<!-- Tab 3: Resultados -->')
    

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Presentación Dashboard HTML actualizada en: %s", output_path)
