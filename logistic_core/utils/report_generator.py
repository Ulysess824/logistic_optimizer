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

from logistic_core.config import (
     GLEC_INTENSITY_GTKM, GLEC_EMPTY_FLOOR_KGKM
)
from logistic_core.utils.geo import GeoUtils
from logistic_core.utils.cost_estimator import CostEstimator
from logistic_core.utils.fcr_estimator import FCREmissionEstimator
from logistic_core.utils.external_cost_analyst import ExternalCostAnalyst

logger = logging.getLogger(__name__)

def fmt_std(val, decimals=2):
    """Formatea un número al estilo estándar (punto para decimales)."""
    if val is None: return "0"
    return f"{val:,.{decimals}f}"

def _replace_kpi(html_text, kpi_id, new_value):
    """Reemplaza el valor de un KPI buscando su ID único."""
    pattern = rf'(id="{kpi_id}"[^>]*>).*?(</p>)'
    new_html, count = re.subn(pattern, rf'\g<1>{new_value}\g<2>', html_text, flags=re.IGNORECASE | re.DOTALL)
    if count == 0:
        logger.warning(f"No se pudo encontrar el KPI con ID: {kpi_id}")
    return new_html

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
    cost_est = CostEstimator(1.14)
    co2_est = FCREmissionEstimator(
        intensity_gtkm=GLEC_INTENSITY_GTKM,
        empty_floor_kgkm=GLEC_EMPTY_FLOOR_KGKM
    )
    ext_analyst = ExternalCostAnalyst(internal_rate=1.14, external_rate=1.35)

    # 1. Cálculos de Kilómetros y Filas
    total_empty_before = 0.0
    total_empty_after  = 0.0
    km_rows_html = []
    route_rows_html = []
    unique_plants = set()
    unique_customers = set()
    
    # Totales Agregados
    t_dist_trad, t_empty_trad, t_co2_trad, t_cost_trad = 0.0, 0.0, 0.0, 0.0
    t_dist_vrpb, t_empty_vrpb, t_co2_vrpb, t_cost_vrpb = 0.0, 0.0, 0.0, 0.0
    
    outsourcing_rows_html = []

    plant_groups = {} # Agrupación para diseño compacto v2

    for idx, r in enumerate(summary["routes"]):
        if idx >= len(routes): break
        
        route_nodes = routes[idx]
        depot = route_nodes[0]
        plants_in_route = [n for n in route_nodes if n["type"] == "carton_plant"]
        if not plants_in_route: continue
        
        last_plant = plants_in_route[-1]
        customers_in_route = [n for n in route_nodes if n["type"] == "customer"]
        last_customer = customers_in_route[-1] if customers_in_route else last_plant

        # Identificadores estéticos (Usado en múltiples tablas)
        plants_short = ", ".join([p.replace("Smurfit Westrock ", "").replace("CP_", "") for p in r["plants"]])
        p_full_name = r["plants"][0] if r["plants"] else "Desconocida"
        
        # Agrupamiento por nombre base (v2): Alcalá (Muelle 2) -> Alcalá
        # Usamos regex o split múltiple para limpiar
        p_base_name = p_full_name.split('(')[0].split('[')[0].split('-')[0].strip()
        p_short = p_base_name.replace("Smurfit Westrock ", "").replace("CP_", "").upper()

        # Ahorro teórico vs Tradicional
        empty_before = geo.haversine_km(last_plant["lat"], last_plant["lng"], depot["lat"], depot["lng"])
        empty_after = r["empty_km"]
        
        total_empty_before += empty_before
        total_empty_after  += empty_after
        unique_plants.update(r.get("plants", []))
        unique_customers.update(r.get("customers", []))
        
        dist_vrpb = r["distance_km"]
        route_cost_vrpb = cost_est.estimate_cost(dist_vrpb)
        
        # Escenario Tradicional (Estimado)
        dist_trad = 2 * empty_before
        empty_trad = empty_before
        co2_trad = co2_est.co2_total_trip(dist_loaded=empty_before, dist_empty=empty_before, weight_tons=25.0)
        cost_trad = dist_trad * 1.14

        # --- 1. COLECCIÓN PARA TABLA COMPACTA ---
        if p_short not in plant_groups:
            plant_groups[p_short] = {
                'name_display': p_short,
                'trad_dist': dist_trad, # Valor Base unitario (1 viaje)
                'trad_empty': empty_trad,
                'trad_co2': co2_trad,
                'trad_cost': cost_trad,
                'opt_routes': []
            }
        
        # Muelle descriptivo para la sub-fila
        muelle_info = ""
        if "(" in p_full_name:
            muelle_info = " (" + p_full_name.split('(')[1]
        
        # Ahorro individual contra la base unitaria de esta planta
        route_imp = (empty_trad - empty_after) / empty_trad * 100 if empty_trad > 0 else 0
        
        # Nuevas KPIs de Eficiencia (Unitaria)
        route_cost_km = route_cost_vrpb / dist_vrpb if dist_vrpb > 0 else 0
        route_co2_km  = r.get("co2_emissions_kg", 0) / dist_vrpb if dist_vrpb > 0 else 0
        
        trad_unit_co2_km = co2_trad / dist_trad if dist_trad > 0 else 0
        route_red_co2 = (1 - (route_co2_km / trad_unit_co2_km)) * 100 if trad_unit_co2_km > 0 else 0
            
        plant_groups[p_short]['opt_routes'].append({
            'desc': f'MC-VRPB Ruta #{r["route_id"]}{muelle_info}',
            'dist': r["distance_km"],
            'empty': empty_after,
            'co2': r.get("co2_emissions_kg", 0),
            'co2_abs': r.get("co2_emissions_kg", 0), # Nueva clave para inyección de tabla
            'cost': route_cost_vrpb,
            'imp': route_imp,
            'cost_km': route_cost_km,
            'co2_km': route_co2_km,
            'red_co2': route_red_co2
        })

        # --- 2. CÁLCULO LINEHAUL PARA COMPARATIVA EXTERNA ---
        if customers_in_route and plants_in_route:
            first_plant_node = plants_in_route[0]
            last_customer_node = last_customer
            lh_dist = 0.0
            tracking = False
            for i in range(len(route_nodes) - 1):
                p1 = route_nodes[i]
                p2 = route_nodes[i+1]
                if p1 == first_plant_node: tracking = True
                if tracking: lh_dist += geo.haversine_km(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
                if p2 == last_customer_node: break
            
            if lh_dist > 0:
                ext_metrics = ext_analyst.analyze_leg(lh_dist)
                if ext_metrics:
                    row = (
                        f'<tr class="hover:bg-gray-50 border-b text-[12px]">'
                        f'<td class="px-3 py-2 font-semibold text-gray-800 border-l-4 border-yellow-500 bg-gray-50/30">{plants_short}</td>'
                        f'<td class="px-3 py-1 text-center font-mono">{fmt_std(lh_dist)} km</td>'
                        f'<td class="px-3 py-1 text-center font-mono text-blue-700">{fmt_std(ext_metrics["internal_cost"])} €</td>'
                        f'<td class="px-3 py-1 text-center font-mono text-red-600">{fmt_std(ext_metrics["external_cost"])} €</td>'
                        f'<td class="px-3 py-1 text-center font-mono font-bold text-green-600">+{fmt_std(ext_metrics["savings"])} €</td>'
                        f'<td class="px-3 py-1 text-center font-mono text-purple-600">{fmt_std(ext_metrics["co2_kg"])} kg</td>'
                        f'</tr>'
                    )
                    outsourcing_rows_html.append(row)
            else:
                logger.warning(f"Ruta {r['route_id']}: Linehaul distance calculated as 0.")
        else:
            logger.debug(f"Ruta {r['route_id']}: No customers or plants for outsourcing comparison.")

        # --- 3. FILA DETALLE (Tab Resultados) ---
        route_rows_html.append(
            f'<tr class="border-b hover:bg-gray-50 text-[12px]">'
            f'<td class="py-2 px-3 font-bold text-center">{r["route_id"]}</td>'
            f'<td class="py-2 px-3">{plants_short}</td>'
            f'<td class="py-2 px-3 text-center">{r["num_customers"]}</td>'
            f'<td class="py-2 px-3 font-mono text-center">{fmt_std(r["distance_km"])} km</td>'
            f'<td class="py-2 px-3 font-mono text-center text-purple-600 font-bold">{fmt_std(r.get("co2_emissions_kg", 0))} kg</td>'
            f'<td class="py-2 px-3 font-mono text-center font-bold text-blue-700">{fmt_std(route_cost_vrpb)} €</td>'
            f'</tr>'
        )

        # --- 4. UPDATE TOTALES ---
        t_dist_trad += dist_trad
        t_empty_trad += empty_trad
        t_co2_trad += co2_trad
        t_cost_trad += cost_trad
        t_dist_vrpb += dist_vrpb
        t_empty_vrpb += empty_after
        t_co2_vrpb += r.get("co2_emissions_kg", 0)
        t_cost_vrpb += route_cost_vrpb

    # --- 5. GENERACIÓN FINAL DEL HTML COMPACTO (V2) ---
    for p_key, pg in plant_groups.items():
        # Cabecera de Planta
        km_rows_html.append(
            f'<tr class="bg-gray-100 font-bold text-gray-700 text-[11px] uppercase tracking-wider">'
            f'<td colspan="7" class="px-3 py-1">PLANTA: {pg["name_display"]}</td>'
            f'</tr>'
        )
        # Fila Única Tradicional (Base)
        trad_cost_km = pg["trad_cost"] / pg["trad_dist"] if pg["trad_dist"] > 0 else 0
        trad_co2_km = pg["trad_co2"] / pg["trad_dist"] if pg["trad_dist"] > 0 else 0
        
        km_rows_html.append(
            f'<tr class="bg-gray-50/50 italic text-gray-500 text-[11px] border-b">'
            f'<td class="px-6 py-1 border-l-4 border-gray-300">Escenario Tradicional (Base)</td>'
            f'<td class="px-2 py-1 text-center">-</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(pg["trad_dist"])}</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(trad_cost_km, 3)} €</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(trad_co2_km, 3)} kg/km</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(pg["trad_co2"], 1)} kg</td>'
            f'<td class="px-3 py-1 text-center font-mono">-</td>'
            f'<td class="px-3 py-1 text-center">-</td>'
            f'</tr>'
        )
        # Filas Optimizadas (Multiples)
        for orout in pg['opt_routes']:
            # Estilo condicional para Reducción CO2
            co2_class = "text-green-600 font-bold" if orout["red_co2"] >= 0 else "text-red-500 font-bold"
            co2_sign = "+" if orout["red_co2"] >= 0 else ""
            
            km_rows_html.append(
                f'<tr class="hover:bg-blue-50/20 border-b text-[12px] text-blue-800">'
                f'<td class="px-6 py-2 font-semibold pl-10 underline decoration-blue-200">{orout["desc"]}</td>'
                f'<td class="px-2 py-1 text-[10px] text-blue-600 uppercase font-bold text-center">Optimizado</td>'
                f'<td class="px-3 py-1 text-center font-mono font-bold">{fmt_std(orout["dist"])}</td>'
                f'<td class="px-3 py-1 text-center font-mono font-bold">{fmt_std(orout["cost_km"], 3)} €</td>'
                f'<td class="px-3 py-1 text-center font-mono font-bold text-purple-700">{fmt_std(orout["co2_km"], 3)} kg/km</td>'
                f'<td class="px-3 py-1 text-center font-mono font-bold text-fuchsia-700">{fmt_std(orout["co2_abs"], 1)} kg</td>'
                f'<td class="px-3 py-1 text-center {co2_class}">{co2_sign}{fmt_std(orout["red_co2"], 1)}%</td>'
                f'<td class="px-3 py-1 text-center font-bold text-green-600 bg-green-50/30 border-l border-green-100">'
                f'+{fmt_std(orout["imp"], 1)}%'
                f'</td>'
                f'</tr>'
            )

    total_savings = total_empty_before - total_empty_after
    total_pct = (total_savings / total_empty_before * 100) if total_empty_before > 0 else 0

    if is_baseline:
        # MODO BASELINE: Solo actualizamos la pestaña de Condiciones Normales (tabla externa)
        table_path = Path("outputs/tables/tabla_comparativa_vacios.html")
        if table_path.exists():
            with open(table_path, "r", encoding="utf-8") as f:
                html_table = f.read()
            
            # 1. Inyectar Filas
            marker = '<tbody>'
            start = html_table.find(marker) + len(marker)
            end = html_table.find('<tr id="total-row"', start)
            html_table = html_table[:start] + "\n" + "\n".join(km_rows_html) + "\n" + html_table[end:]

            # 2. Inyectar Totales
            html_table = html_table.replace('{{T_DIST}}', f'{fmt_std(t_dist_vrpb)} km')
            html_table = html_table.replace('{{T_EMPTY}}', f'{fmt_std(t_empty_vrpb)} km')
            html_table = html_table.replace('{{T_CO2}}', f'{fmt_std(t_co2_vrpb)} kg')
            html_table = html_table.replace('{{T_COST}}', f'{fmt_std(t_cost_vrpb)} €')
            html_table = html_table.replace('{{T_PCT}}', f'+{fmt_std(total_pct, 1)}%')

            with open(table_path, "w", encoding="utf-8") as f:
                f.write(html_table)
            logger.info("Fase Baseline: tabla_comparativa_vacios.html actualizada.")
    else:
        # MODO PRODUCCIÓN: Actualizamos Resumen y Resultados
        # 2. Parchear tab_resumen.html
        resumen_path = bodies_dir / "tab_resumen.html"
        if resumen_path.exists():
            with open(resumen_path, "r", encoding="utf-8") as f:
                html_res = f.read()
            
            # KPIs Agregados para tarjetas superiores
            global_cost_km = t_cost_vrpb / summary["total_km"] if summary["total_km"] > 0 else 0
            global_co2_km = summary["total_co2_kg"] / summary["total_km"] if summary["total_km"] > 0 else 0
            
            # Estimación Tradicional total para relativas (VECTO 5-LH / GLEC v3)
            # Factor IDA (Cargado): Floor + Intensity*Carga(25t) = 0.652 + 17.32*25/1000 = 1.085
            f_loaded = GLEC_EMPTY_FLOOR_KGKM + (25 * GLEC_INTENSITY_GTKM / 1000.0)
            total_co2_trad = total_empty_before * (f_loaded + GLEC_EMPTY_FLOOR_KGKM)
            global_co2_km_trad = total_co2_trad / (total_empty_before * 2) if total_empty_before > 0 else 0
            reduction_co2_rel = (1 - (global_co2_km / global_co2_km_trad)) * 100 if global_co2_km_trad > 0 else 0
            
            # Formatear Reducción CO2 (%) de forma robusta
            red_label = f"{'-' if reduction_co2_rel < 0 else ''}{fmt_std(abs(reduction_co2_rel), 1)}%"

            html_res = _replace_kpi(html_res, "kpi-num-routes", summary["num_routes"])
            html_res = _replace_kpi(html_res, "kpi-total-km", f'{fmt_std(summary["total_km"])}')
            html_res = _replace_kpi(html_res, "kpi-total-cost", f'{fmt_std(t_cost_vrpb)} €')
            html_res = _replace_kpi(html_res, "kpi-euros-km", f'{fmt_std(global_cost_km, 3)}')
            html_res = _replace_kpi(html_res, "kpi-co2-km", f'{fmt_std(global_co2_km, 3)}')
            html_res = _replace_kpi(html_res, "kpi-co2-total", f'{fmt_std(summary["total_co2_kg"], 0)}')
            html_res = _replace_kpi(html_res, "kpi-red-co2", red_label)
            html_res = _replace_kpi(html_res, "kpi-vacio-pct", f"~{fmt_std(total_pct, 1)}%")

            # Inyectar Tabla Comparativa
            marker = 'id="comparison-tbody"'
            if marker in html_res:
                idx = html_res.find(marker)
                start = html_res.find('>', idx) + 1
                end = html_res.find('</tbody>', start)
                html_res = html_res[:start] + "\n" + "\n".join(km_rows_html) + "\n" + html_res[end:]

            # Inyectar Tabla de Outsourcing (NUEVO)
            marker_ext = 'id="outsourcing-tbody"'
            if marker_ext in html_res:
                idx = html_res.find(marker_ext)
                start = html_res.find('>', idx) + 1
                end = html_res.find('</tbody>', start)
                html_res = html_res[:start] + "\n" + "\n".join(outsourcing_rows_html) + "\n" + html_res[end:]

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

        # 3. Generar pestaña de bibliografía
        _generate_bibliografia_tab(bodies_dir)
        
        logger.info(f"Dashboard (Producción) actualizado exitosamente.")

def _generate_bibliografia_tab(bodies_dir):
    """Genera la pestaña de bibliografía a partir de docs/Bibliografia.md"""
    bib_path = Path(__file__).parent.parent.parent / "docs" / "Bibliografia.md"
    output_path = bodies_dir / "tab_bibliografia.html"
    
    lines = []
    if bib_path.exists():
        with open(bib_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f8fafc; color: #334155; }}
        .cite-card {{ background: white; border-radius: 12px; padding: 24px; border-left: 6px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 1rem; }}
        .doi {{ color: #2563eb; font-family: monospace; font-weight: bold; border-bottom: 1px dashed #bfdbfe; display: inline-block; margin-bottom: 0.5rem; }}
    </style>
</head>
<body class="p-8">
    <h1 class="text-3xl font-bold text-[#1e3a8a] mb-8 border-b-2 border-blue-100 pb-4">Marco Científico y Referencias Técnicas</h1>
    <div class="grid grid-cols-1 gap-6">"""

    current_section = None
    current_cite = None
    cite_body = []

    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith("# "): continue # Skip main title
        
        if line.startswith("## "):
            # Close previous section if any
            if current_cite:
                html_content += f'<div class="cite-card"><p class="doi">{current_cite}</p><div class="text-sm leading-relaxed text-slate-600">{" ".join(cite_body)}</div></div>'
                current_cite = None
                cite_body = []
            if current_section:
                html_content += "</div></div>"
            
            current_section = line.replace("## ", "")
            html_content += f'<div><h2 class="text-xl font-bold mt-6 mb-4 text-slate-800 uppercase tracking-wide border-l-4 border-blue-500 pl-3">{current_section}</h2><div class="space-y-4">'
        
        elif line.startswith("### "):
            # Close previous cite card
            if current_cite:
                html_content += f'<div class="cite-card"><p class="doi">{current_cite}</p><div class="text-sm leading-relaxed text-slate-600">{" ".join(cite_body)}</div></div>'
            
            current_cite = line.replace("### ", "")
            cite_body = []
            
        elif line.startswith("* ") or line.startswith("- "):
            clean_line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line[2:])
            cite_body.append(f"<p class='mb-1'>• {clean_line}</p>")
        elif line == "---":
            continue
        else:
            cite_body.append(f"<p class='mb-2'>{line}</p>")

    # Final closures
    if current_cite:
        html_content += f'<div class="cite-card"><p class="doi">{current_cite}</p><div class="text-sm leading-relaxed text-slate-600">{" ".join(cite_body)}</div></div>'
    if current_section:
        html_content += "</div></div>"

    html_content += """
    </div>
    <div class="mt-12 p-6 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-800 italic">
        Nota: Estas referencias fundamentan la precisión del motor GLEC v3.0 y la calibración VECTO utilizada en este Dashboard.
    </div>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info("Pestaña de Bibliografía generada.")

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
