"""
report_generator.py
───────────────────
Generador de dashboard modular. Actualiza los componentes en HTML_Bodies/
en lugar de parchar un único archivo masivo.
"""
import os
import sys
import json
import math
import re
import logging
from pathlib import Path

# Corregir el PATH para evitar colisiones
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.geo import GeoUtils

logger = logging.getLogger(__name__)

def fmt_std(val, decimals=2):
    """Formatea un número al estilo estándar (punto para decimales)."""
    if val is None: return "0"
    return f"{val:,.{decimals}f}"

def _replace_kpi(html_text, label_re, new_value):
    """Reemplaza el valor de un KPI buscando su etiqueta."""
    pat = re.compile(
        rf'(<p\s+class="kpi-label">{label_re}</p>\s*'
        rf'<p\s+class="kpi-value"[^>]*>).*?(</p>)',
        re.IGNORECASE | re.DOTALL)
    return pat.sub(rf'\g<1>{new_value}\g<2>', html_text)

def generate_dashboard(summary_path, routes_path, output_path, hedonic_path=None, is_baseline=False):
    """Actualiza los componentes HTML del dashboard con datos reales."""
    
    summary_path = Path(summary_path)
    routes_path  = Path(routes_path)
    output_path  = Path(output_path)
    bodies_dir   = output_path.parent / "HTML_Bodies"

    if not summary_path.exists() or not routes_path.exists():
        logger.error(f"Archivos de resultados no encontrados: {summary_path}")
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    with open(routes_path, "r", encoding="utf-8") as f:
        routes = json.load(f)

    geo = GeoUtils()

    # 1. Cálculos de Kilómetros y Filas
    total_empty_before = 0.0
    total_empty_after  = 0.0
    km_rows_html = []
    route_rows_html = []
    unique_plants = set()
    unique_customers = set()

    for idx, r in enumerate(summary["routes"]):
        # Por seguridad, verificamos que el índice exista en el array de rutas detalladas
        if idx >= len(routes): break
        
        route_nodes = routes[idx]
        depot = route_nodes[0]
        plants_in_route = [n for n in route_nodes if n["type"] == "carton_plant"]
        if not plants_in_route: continue
        last_plant = plants_in_route[-1]
        
        customers_in_route = [n for n in route_nodes if n["type"] == "customer"]
        last_customer = customers_in_route[-1] if customers_in_route else last_plant

        # Ahorro teórico: Planta -> Base vs Cliente -> Base
        empty_before = geo.haversine_km(last_plant["lat"], last_plant["lng"], depot["lat"], depot["lng"])
        empty_after = r["empty_km"]
        
        savings = max(0, empty_before - empty_after)
        improvement = (savings / empty_before * 100) if empty_before > 0 else 0
        
        total_empty_before += empty_before
        total_empty_after  += empty_after
        unique_plants.update(r["plant_ids"])
        unique_customers.update(r.get("customers", []))

        # Fila Comparativa (Estética Premium)
        plants_short = ", ".join([p.replace("Smurfit Westrock ", "").replace("CP_", "") for p in r["plants"]])
        km_rows_html.append(
            f'<tr class="hover:bg-gray-50 border-b text-[12px]">'
            f'<td class="px-3 py-2 font-semibold text-gray-800 border-l-4 border-blue-500">{plants_short}</td>'
            f'<td class="px-3 py-2 text-center font-mono">{fmt_std(r["distance_km"])}</td>'
            f'<td class="px-3 py-2 text-center font-mono">{fmt_std(empty_before)}</td>'
            f'<td class="px-3 py-2 text-center font-mono font-bold text-blue-700">{fmt_std(empty_after)}</td>'
            f'<td class="px-3 py-2 text-center font-bold text-green-600">+{fmt_std(improvement, 1)}%</td>'
            f'</tr>'
        )

        # Fila Detalle (Tab Resultados) - Incluyendo CO2
        route_rows_html.append(
            f'<tr class="border-b hover:bg-gray-50 text-[12px]">'
            f'<td class="py-2 px-3 font-bold text-center">{r["route_id"]}</td>'
            f'<td class="py-2 px-3">{plants_short}</td>'
            f'<td class="py-2 px-3 text-center">{r["num_customers"]}</td>'
            f'<td class="py-2 px-3 font-mono text-center">{fmt_std(r["distance_km"])} km</td>'
            f'<td class="py-2 px-3 font-mono text-center text-purple-600 font-bold">{fmt_std(r.get("co2_emissions_kg", 0))} kg</td>'
            f'</tr>'
        )

    total_savings = total_empty_before - total_empty_after
    total_pct = (total_savings / total_empty_before * 100) if total_empty_before > 0 else 0

    if is_baseline:
        # MODO BASELINE: Solo actualizamos la pestaña de Condiciones Normales
        baseline_tab_path = bodies_dir / "tab_baseline.html"
        if baseline_tab_path.exists():
            # Aquí podríamos inyectar la tabla específica o actualizar el iframe que ya tiene
            logger.info("Fase Baseline: Componente tab_baseline detectado.")
            # Por ahora, el baseline se visualiza vía iframe a tablas externas o inyección directa si se requiere.
    else:
        # MODO PRODUCCIÓN: Actualizamos Resumen y Resultados
        # 2. Parchear tab_resumen.html
        resumen_path = bodies_dir / "tab_resumen.html"
        if resumen_path.exists():
            with open(resumen_path, "r", encoding="utf-8") as f:
                html_res = f.read()
            
            html_res = _replace_kpi(html_res, r"Rutas Totales Generadas", summary["num_routes"])
            html_res = _replace_kpi(html_res, r"Distancia Total \(km\)", f'{fmt_std(summary["total_km"])}')
            html_res = _replace_kpi(html_res, r"Plantas Visitadas", len(unique_plants))
            html_res = _replace_kpi(html_res, r"Entregas Realizadas", len(unique_customers))
            html_res = _replace_kpi(html_res, r"Ahorro Km Vac[ií]os", f"~{fmt_std(total_pct, 1)}%")

            # Inyectar Tabla Comparativa
            marker = 'id="comparison-tbody"'
            if marker in html_res:
                idx = html_res.find(marker)
                start = html_res.find('>', idx) + 1
                end = html_res.find('</tbody>', start)
                html_res = html_res[:start] + "\n" + "\n".join(km_rows_html) + "\n" + html_res[end:]

            with open(resumen_path, "w", encoding="utf-8") as f:
                f.write(html_res)

        # 3. Parchear tab_resultados.html
        resultados_path = bodies_dir / "tab_resultados.html"
        if resultados_path.exists():
            with open(resultados_path, "r", encoding="utf-8") as f:
                html_resul = f.read()

            marker = 'id="routes-tbody"'
            if marker in html_resul:
                idx = html_resul.find(marker)
                start = html_resul.find('>', idx) + 1
                end = html_resul.find('</tbody>', start)
                html_resul = html_resul[:start] + "\n" + "\n".join(route_rows_html) + "\n" + html_resul[end:]
            
            with open(resultados_path, "w", encoding="utf-8") as f:
                f.write(html_resul)

    logger.info(f"Dashboard ({'Baseline' if is_baseline else 'Producción'}) actualizado exitosamente.")

if __name__ == "__main__":
    # Test local inteligente: busca qué archivos existen y actualiza
    opt_sum = "outputs/results/optimization_summary.json"
    opt_rout = "outputs/results/optimized_routes.json"
    bas_sum = "outputs/results/baseline_summary.json"
    bas_rout = "outputs/results/baseline_routes.json"
    shell = "outputs/Presentacion_Logistica.html"

    if Path(opt_sum).exists():
        generate_dashboard(opt_sum, opt_rout, shell, is_baseline=False)
    
    if Path(bas_sum).exists():
        generate_dashboard(bas_sum, bas_rout, shell, is_baseline=True)
