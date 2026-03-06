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


def generate_dashboard(summary_path, routes_path, output_path):
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
    unique_plants: set[str] = set()
    unique_customers: set[str] = set()

    for i, route in enumerate(routes, 1):
        depot        = route[0]
        plant        = route[1]
        last_customer = route[-2]

        unique_plants.add(plant["id"])
        
        for n in route:
            if n["type"] == "customer":
                # Usamos una clave única (id o nombre) para contar clientes únicos
                unique_customers.add(n.get("id") or n.get("name"))

        empty_before = geo.haversine_km(plant["lat"], plant["lng"],
                                        depot["lat"], depot["lng"])
        empty_after  = geo.haversine_km(last_customer["lat"], last_customer["lng"],
                                        depot["lat"], depot["lng"])

        savings     = empty_before - empty_after
        improvement = (savings / empty_before * 100) if empty_before > 0 else 0
        total_empty_before += empty_before
        total_empty_after  += empty_after

        plant_name = plant["name"].replace("Smurfit Westrock ", "")
        km_rows_html.append(
            f'<tr class="border-b hover:bg-gray-50">'
            f'<td class="py-2 px-4 font-semibold border-r">Ruta {i} - {plant_name}</td>'
            f'<td class="py-2 px-4 text-center text-red-500 font-mono">{fmt_std(empty_before)} km</td>'
            f'<td class="py-2 px-4 text-center text-green-600 font-mono bg-green-50/30">{fmt_std(empty_after)} km</td>'
            f'<td class="py-2 px-4 text-center font-bold text-blue-600 bg-blue-50/30">{fmt_std(savings)} km</td>'
            f'<td class="py-2 px-4 text-center font-bold text-blue-600 bg-blue-50/30">{fmt_std(improvement, 1)}%</td>'
            f'</tr>'
        )

    total_savings = total_empty_before - total_empty_after
    total_pct     = (total_savings / total_empty_before * 100) if total_empty_before > 0 else 0

    # ──────────────────────────────────────────────────────────────────
    # 2. Construir tabla de rutas (Tab 3)
    # ──────────────────────────────────────────────────────────────────
    route_rows_html: list[str] = []

    for idx, r in enumerate(summary["routes"]):
        plant_str    = ", ".join(r["plants"])
        customers_str = ", ".join(r["customers"])
        bg_class     = ' bg-gray-50' if idx % 2 == 1 else ''
        route_rows_html.append(
            f'<tr class="border-b hover:bg-gray-50{bg_class}">'
            f'<td class="py-3 px-4 font-bold text-center">{r["route_id"]}</td>'
            f'<td class="py-3 px-4">{plant_str}</td>'
            f'<td class="py-3 px-4 text-center">{r["num_customers"]}</td>'
            f'<td class="py-3 px-4 font-mono">{fmt_std(r["distance_km"])} km</td>'
            f'<td class="py-3 px-4 text-xs italic">{customers_str}</td>'
            f'</tr>'
        )

        short_name = r["plants"][0].replace("Smurfit Westrock ", "")

    # ──────────────────────────────────────────────────────────────────
    # 3. Leer y parchear el HTML
    # ──────────────────────────────────────────────────────────────────
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    # --- 3a. KPIs ---
    def _replace_kpi(html_text, label_re, new_value):
        pat = re.compile(
            rf'(<p\s+class="kpi-label">{label_re}</p>\s*'
            rf'<p\s+class="kpi-value"[^>]*>)[^<]+(</p>)',
            re.IGNORECASE | re.DOTALL)
        return pat.sub(rf'\g<1>{new_value}\g<2>', html_text)

    html = _replace_kpi(html, r"Rutas Totales Generadas",  summary["num_routes"])
    html = _replace_kpi(html, r"Distancia Total \(km\)",    f'{fmt_std(summary["total_km"])} <br><span class="text-[10px] uppercase opacity-60">({summary.get("distance_source", "GPS Real")})</span>')
    html = _replace_kpi(html, r"Plantas Visitadas",         len(unique_plants))
    html = _replace_kpi(html, r"Clientes Satisfechos",      len(unique_customers))
    html = _replace_kpi(html, r"Ahorro Km Vac[ií]os",      f"~{fmt_std(total_pct, 1)}%")

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
        f'<p class="text-lg font-mono bg-blue-800 px-4 py-2 rounded">v1.2</p>'
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

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Presentación Dashboard HTML actualizada en: %s", output_path)
