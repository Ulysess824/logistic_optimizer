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
     DATA_DIR,
     GLEC_INTENSITY_GTKM, GLEC_EMPTY_FLOOR_KGKM,
     MAX_SEARCH_TIME, DIST_LIMIT, DEFAULT_N_CLIENTES, DEFAULT_MAX_PLANTS_PER_ROUTE,
     ALLOW_ROUTE_SPLITTING,
     GLEC_CO2_PER_LITER, PAPER_LOAD_KG, PALLET_WEIGHT_KG, VEHICLE_MAX_LOAD_KG,
     TRAILER_LENGTH_M, TRAILER_WIDTH_M, TRAILER_HEIGHT_M,
     PALLET_LENGTH_M, PALLET_WIDTH_M, PALLET_HEIGHT_M,
     LOAD_STACKABLE,
     DEFAULT_MAX_CUSTOMERS, DEFAULT_THRESHOLD_KM,
     TARIFA_INTERNA_DIESEL, TARIFA_INTERNA_EV, EXTERNAL_PROVIDER_RATE_PER_KM,
     CAPEX_TRUCK_UNIT_COST, DEFAULT_CYCLE_TIME_DAYS, 
     DAILY_TRUCK_OUTBOUND, DEFAULT_FLEET_BUFFER,
     SOFTWARE_TMS_CAPEX, ELECTRIC_PLANTS_LIST, EV_CONS_EMPTY, EV_CONS_FULL,
     DIESEL_CAPEX, EV_CAPEX, EV_MOVES_AYUDA,
     FLEET_MIX_DIESEL, FLEET_MIX_EV, ANNUAL_DRIVER_COST_PER_TRUCK, KMS_ANUALES_POR_CAMION, TCO_HORIZON_YEARS,
     TCO_WACC, TCO_INFLACION_ANUAL, TCO_TAX_RATE,
     DIESEL_SEGURO_ANUAL, DIESEL_MANT_ANUAL, DIESEL_NEUMATICOS_ANUAL,
     DIESEL_RENTING_MENSUAL, DIESEL_LEASING_MENSUAL,
     EV_CONSUMO_KWH_KM, EV_COSTE_KWH, EV_MANT_ANUAL,
     EV_RENTING_MENSUAL, EV_LEASING_MENSUAL,
     DIESEL_CONSUMO_L_100KM, DIESEL_COSTE_COMBUSTIBLE_L,
     BASE_TCO_DIESEL, BASE_TCO_EV
)
from logistic_core.utils.geo import GeoUtils
from logistic_core.utils.cost_estimator import CostEstimator
from logistic_core.utils.fcr_estimator import FCREmissionEstimator
from logistic_core.utils.external_cost_analyst import ExternalCostAnalyst
from logistic_core.utils.operational_analyzer import OperationalAnalyzer
from logistic_core.utils.strategic_analyzer import StrategicAnalyzer
from logistic_core.utils.visualizer import Visualizer

logger = logging.getLogger(__name__)

import numpy as np

def fmt_std(val, decimals=1):
    """Formatea un número con separador de miles (_) y 1 decimal por defecto."""
    if val is None: return "0"
    try:
        # Si es una lista o array, intentamos sumar (caso de flujos)
        if isinstance(val, (list, np.ndarray)):
            val = float(np.sum(val))
        return f"{float(val):_.{decimals}f}"
    except:
        return str(val)

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

    geo = GeoUtils(api_type="osrm")
    cost_est = CostEstimator(
        price_per_km=TARIFA_INTERNA_DIESEL
    )
    price_km = cost_est.price_per_km
    
    co2_est = FCREmissionEstimator(
        intensity_gtkm=GLEC_INTENSITY_GTKM,
        empty_floor_kgkm=GLEC_EMPTY_FLOOR_KGKM
    )
    # 4. External Analyst unificado con TCO real
    ext_analyst = ExternalCostAnalyst(internal_rate=price_km, external_rate=EXTERNAL_PROVIDER_RATE_PER_KM)

    # 1. Cálculos de Kilómetros y Filas
    total_empty_before = 0.0
    total_empty_after  = 0.0
    t_systemic_savings = 0.0
    t_backhauling_saving = 0.0 # Nuevo acumulador histórico de rentabilidad de retornos
    t_co2_savings_systemic = 0.0
    t_dist_vrpb = 0.0
    t_empty_vrpb = 0.0
    t_co2_vrpb = 0.0
    t_cost_vrpb = 0.0
    t_kwh_total = 0.0
    t_ev_km = 0.0
    t_empty_vrpb = 0
    t_co2_savings_systemic = 0
    t_total_customers = 0
    t_total_pallets = 0
    
    km_rows_html = []
    route_rows_html = []
    unique_plants = set()
    unique_customers = set()
    
    # Totales Agregados
    t_dist_trad, t_empty_trad, t_co2_trad, t_cost_trad = 0.0, 0.0, 0.0, 0.0
    t_dist_vrpb, t_empty_vrpb, t_co2_vrpb, t_cost_vrpb = 0.0, 0.0, 0.0, 0.0
    t_co2_savings_systemic = 0.0
    t_kwh_total = 0.0
    t_ev_km = 0.0
    
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
        plants_short = ", ".join([p.replace("Smurfit Westrock ", "").replace("CP_", "").replace("Muelle", "Ruta") for p in r["plants"]])
        p_full_name = r["plants"][0] if r["plants"] else "Desconocida"
        
        # Agrupamiento por nombre base (v2): Alcalá (Muelle 2) -> Alcalá
        # Usamos regex o split múltiple para limpiar
        p_base_name = p_full_name.split('(')[0].split('[')[0].split('-')[0].strip()
        p_short = p_base_name.replace("Smurfit Westrock ", "").replace("CP_", "").upper()

        # 1. Escenario Tradicional Real (OSRM en lugar de Haversine)
        # Camión 1: Mengíbar -> Planta y Planta -> Mengíbar (Real Inbound/Outbound)
        dist_m_p = geo.get_route_distance((depot["lat"], depot["lng"]), (last_plant["lat"], last_plant["lng"])) / 1000.0
        dist_p_m = geo.get_route_distance((last_plant["lat"], last_plant["lng"]), (depot["lat"], depot["lng"])) / 1000.0
        dist_m_p_m = dist_m_p + dist_p_m
        
        # Camión 2: Planta -> Clientes (Solo IDA, no vuelve a planta)
        dist_p_c_only_out = 0
        for c in customers_in_route:
            # Ahora solo sumamos la ida (el camión se queda en destino o no computamos su retorno)
            dist_p_c_only_out += geo.get_route_distance((last_plant["lat"], last_plant["lng"]), (c["lat"], c["lng"])) / 1000.0
            
        dist_p_c_p = dist_p_c_only_out # Cambiamos la referencia para el resto del script
        
        dist_trad_systemic = dist_m_p_m + dist_p_c_p
        
        is_ev = p_short in ELECTRIC_PLANTS_LIST
        # 🎯 Tarifa dinámica según tecnología de la planta (Diésel vs. Eléctrico)
        price_km = TARIFA_INTERNA_EV if is_ev else TARIFA_INTERNA_DIESEL
        tco_km = BASE_TCO_EV if is_ev else BASE_TCO_DIESEL
        
        ext_analyst.internal_rate = price_km
        cost_est.price_per_km = price_km

        cost_trad_systemic = dist_trad_systemic * price_km
        co2_trad_systemic = co2_est.co2_total_trip(dist_loaded=dist_trad_systemic/2, dist_empty=dist_trad_systemic/2, weight_tons=25.0)
        
        if is_ev:
            co2_trad_systemic = 0.0

        empty_after = r["empty_km"]
        
        total_empty_before += (dist_m_p_m / 2.0)
        total_empty_after  += empty_after
        unique_plants.update(r.get("plants", []))
        unique_customers.update(r.get("customers", []))
        
        # Guardamos la distancia original del solver para asegurar consistencia 100% con el mapa
        dist_vrpb_json = r.get("distance_km", 0)
        dist_vrpb = dist_vrpb_json
        
        route_co2_kg = 0
        route_kwh_sum = 0
        empty_after_osrm = 0 
        
        # Necesitamos la suma total de pallets para el tramo Planta->Primer Cliente
        # Detectar si es ruta encadenada (más de una planta de cartón)
        is_chained = len(plants_in_route) > 1
        
        if is_chained:
            # Calcular pallets por cada tramo de planta
            pallets_per_plant = []
            for plant in plants_in_route:
                p_id = plant.get("id", "").split("_chain_")[0].split("_clone_")[0]
                # Sumar pallets de clientes que pertenecen a esta planta en esta ruta
                p_sum = sum(c.get("demanda_pallets", 0) for c in customers_in_route 
                           if p_id in str(c.get("parent_cp", "")))
                pallets_per_plant.append(p_sum)
            
            # El fill rate de la ruta es el promedio de las ocupaciones por planta
            route_fill_rate = sum(p / 34.0 for p in pallets_per_plant) / len(pallets_per_plant) * 100
            # Los pallets totales de la ruta (para el conteo global) siguen siendo la suma
            total_pallets = sum(pallets_per_plant)
        else:
            total_pallets = sum(c.get('demanda_pallets', 0) for c in customers_in_route)
            route_fill_rate = (total_pallets / 34.0) * 100
        
        # 1. Pre-calcular las patas raw para poder escalarlas
        raw_legs = []
        for i in range(len(route_nodes) - 1):
            n1 = route_nodes[i]
            n2 = route_nodes[i+1]
            ld = geo.get_route_distance((n1["lat"], n1["lng"]), (n2["lat"], n2["lng"])) / 1000.0
            raw_legs.append(ld)
            
        sum_raw = sum(raw_legs)
        scale_fac = dist_vrpb_json / sum_raw if sum_raw > 0 else 1.0

        for i in range(len(route_nodes) - 1):
            n1 = route_nodes[i]
            n2 = route_nodes[i+1]
            leg_dist = raw_legs[i] * scale_fac
            
            # Replicamos la lógica de cálculo de carga de main.py
            if n1["type"] == "depot":
                current_load_kg = PAPER_LOAD_KG
            elif n1["type"] == "carton_plant":
                current_load_kg = total_pallets * PALLET_WEIGHT_KG
            elif n1["type"] == "customer":
                pallets_left = n1.get("demanda_pallets", 0)
                current_load_kg = max(0, current_load_kg - (pallets_left * PALLET_WEIGHT_KG))
                
            if i == len(route_nodes) - 2 and n2["type"] == "depot":
                current_load_kg = 0 # Vuelta final siempre vacía
                empty_after_osrm = leg_dist

            # Cálculo CO2 (Modelo GLEC)
            leg_co2 = co2_est.co2_partial_load(
                distance_km=leg_dist,
                current_load=current_load_kg,
                max_load=VEHICLE_MAX_LOAD_KG
            )
            route_co2_kg += leg_co2

            # Cálculo Energético (Modelo Dinámico EV)
            if is_ev:
                load_ratio = current_load_kg / VEHICLE_MAX_LOAD_KG
                leg_cons_rate = EV_CONS_EMPTY + (EV_CONS_FULL - EV_CONS_EMPTY) * load_ratio
                route_kwh_sum += (leg_dist * leg_cons_rate)
            
        if is_ev:
            route_co2_kg = 0.0
            
        # Sobrescribimos en el diccionario por coherencia
        r["distance_km"] = dist_vrpb_json
        r["co2_emissions_kg"] = route_co2_kg
        r["kwh_consumed"] = route_kwh_sum if is_ev else 0.0
        
        if is_ev:
            t_kwh_total += r["kwh_consumed"]
            t_ev_km += dist_vrpb_json
            
        t_total_customers += len(customers_in_route)
        t_total_pallets += total_pallets
            
        route_cost_vrpb = cost_est.estimate_cost(dist_vrpb)
        
        # --- CÁLCULO DE AHORRO SISTÉMICO (REDEFINIDO) ---
        # El ahorro es la diferencia entre la tarifa externa y nuestra TCO interna 
        # aplicada exclusivamente a la distancia de entrega (desde planta hasta último cliente).
        dist_planta_a_clientes = 0
        if customers_in_route:
            last_cust = customers_in_route[-1]
            found_plant = False
            for i in range(len(route_nodes) - 1):
                n_a = route_nodes[i]
                n_b = route_nodes[i+1]
                if n_a["type"] == "carton_plant": found_plant = True
                if found_plant:
                    ld = geo.get_route_distance((n_a["lat"], n_a["lng"]), (n_b["lat"], n_b["lng"])) / 1000.0
                    seg_dist = ld * scale_fac
                    dist_planta_a_clientes += seg_dist
                if n_b == last_cust: break
            
            ext_comp = ext_analyst.analyze_leg(dist_planta_a_clientes)
            systemic_saving_route = ext_comp.get("savings", 0)
            systemic_co2_saving_route = ext_comp.get("co2_kg", 0)
        else:
            systemic_saving_route = 0.0
            systemic_co2_saving_route = 0.0

        # Acumular para el KPI global
        header_alert = f'<p class="text-[11px] text-orange-600 mb-4 bg-orange-50 inline-block px-2 py-1 rounded">ℹ Análisis del segmento Linehaul (Entrega): Flota Propia ({fmt_std(price_km)} €/km) vs. Tarifa Externa ({fmt_std(ext_analyst.external_rate)} €/km).</p>'
        t_systemic_savings += systemic_saving_route
        t_co2_savings_systemic += systemic_co2_saving_route

        if p_short not in plant_groups:
            # Calculamos métricas puramente para la fila gris base (1 camión inbound sin clientes)
            base_1_camion_km = dist_m_p_m
            base_1_camion_cost = base_1_camion_km * price_km
            base_1_camion_co2 = co2_est.co2_total_trip(dist_loaded=dist_m_p_m/2, dist_empty=dist_m_p_m/2, weight_tons=25.0)
            if is_ev:
                base_1_camion_co2 = 0.0

            plant_groups[p_short] = {
                'name_display': p_short,
                'trad_dist': 0, 
                'trad_empty': 0,
                'trad_co2': 0,
                'trad_cost': 0,
                'base_km': base_1_camion_km,
                'base_cost': base_1_camion_cost,
                'base_co2': base_1_camion_co2,
                'opt_routes': []
            }
        
        # Acumulamos la base para esta planta
        plant_groups[p_short]['trad_dist'] += dist_trad_systemic
        plant_groups[p_short]['trad_empty'] += (dist_m_p_m / 2.0) + (dist_p_c_p / 2.0)
        plant_groups[p_short]['trad_co2'] += co2_trad_systemic
        plant_groups[p_short]['trad_cost'] += cost_trad_systemic
        
        muelle_info = ""
        
        # Ahorro individual contra la base sistémica (ambos camiones iban vacíos al retorno)
        empty_trad_systemic = (dist_m_p_m / 2.0) + (dist_p_c_p / 2.0)
        route_imp = (empty_trad_systemic - empty_after_osrm) / empty_trad_systemic * 100 if empty_trad_systemic > 0 else 0
        
        # AHORRO FINANCIERO PURO SOBRE LOS KILÓMETROS INÚTILES
        empty_trad_cost = (dist_m_p_m / 2.0) * price_km # Solo comparamos el retorno del Inbound Primary contra el retorno final optimizado
        empty_opt_cost = empty_after_osrm * price_km
        empty_ret_saving_money = empty_trad_cost - empty_opt_cost
        
        # route_fill_rate ya calculado arriba contemplando encadenamiento
        route_milla_vacia_pct = (empty_after_osrm / dist_vrpb) * 100 if dist_vrpb > 0 else 0
        
        plant_groups[p_short]['opt_routes'].append({
            'route_id': r.get("route_id", 0),
            'desc': f'Ruta #{r.get("route_id", i+1)}',
            'dist': dist_vrpb,
            'empty': empty_after_osrm,
            'fill_rate': route_fill_rate,
            'milla_vacia': route_milla_vacia_pct,
            'customers': r.get("num_customers", len(customers_in_route)),
            'total_pallets': total_pallets,
            'co2': route_co2_kg,
            'cost': route_cost_vrpb,
            'imp': route_imp,
            'empty_ret_saving': empty_ret_saving_money,
            'systemic_saving': systemic_saving_route,
            'systemic_co2_saving': systemic_co2_saving_route,
            'is_ev': is_ev,
            'kwh': route_kwh_sum
        })

        # --- 2. CÁLCULO LINEHAUL PARA COMPARATIVA EXTERNA (REAL DISTANCE) ---
        if customers_in_route and plants_in_route:
            # Ahora usamos exactamente la misma distancia real calculada arriba para coherencia total
            lh_dist = dist_planta_a_clientes
            
            if lh_dist > 0:
                ext_metrics = ext_analyst.analyze_leg(lh_dist)
                if ext_metrics:
                    border_col = "fuchsia-500" if is_ev else "yellow-500"
                    txt_col = "fuchsia-800 font-black" if is_ev else "gray-800 font-semibold"
                    lbl_ev = "(EV) " if is_ev else ""
                    
                    row = (
                        f'<tr class="hover:bg-gray-50 border-b text-[12px]">'
                        f'<td class="px-3 py-2 {txt_col} border-l-4 border-{border_col} bg-gray-50/30">{lbl_ev}{plants_short}</td>'
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

        route_rows_html.append(
            f'<tr class="border-b hover:bg-gray-50 text-[12px]">'
            f'<td class="py-2 px-3 font-bold text-center">{r["route_id"]}</td>'
            f'<td class="py-2 px-3">{plants_short}</td>'
            f'<td class="py-2 px-3 text-center">{r["num_customers"]}</td>'
            f'<td class="py-2 px-3 font-mono text-center font-bold text-orange-600">{int(total_pallets)}</td>'
            f'<td class="py-2 px-3 font-mono text-center font-bold text-amber-600 bg-amber-50/30">{fmt_std(route_fill_rate, 1)}%</td>'
            f'<td class="py-2 px-3 font-mono text-center">{fmt_std(r["distance_km"])} km</td>'
            f'<td class="py-2 px-3 font-mono text-center font-bold text-blue-700">{fmt_std(r["distance_km"] * price_km)} €</td>'
            f'<td class="py-2 px-3 font-mono text-center font-bold text-green-600">+{fmt_std(systemic_saving_route)} €</td>'
            f'</tr>'
        )

        # --- 4. UPDATE TOTALES ---
        t_dist_trad += dist_trad_systemic
        t_empty_trad += empty_trad_systemic
        t_co2_trad += co2_trad_systemic
        t_cost_trad += cost_trad_systemic
        t_dist_vrpb += dist_vrpb
        t_empty_vrpb += empty_after_osrm
        t_co2_vrpb += r.get("co2_emissions_kg", 0)
        t_cost_vrpb += route_cost_vrpb
        t_backhauling_saving += empty_ret_saving_money
    
    t_systemic_savings = sum([orout['systemic_saving'] for pg in plant_groups.values() for orout in pg['opt_routes']])

    # --- 5. GENERACIÓN FINAL DEL HTML COMPACTO (V2) ---
    for p_key, pg in plant_groups.items():
        # Cabecera de Planta
        is_plant_ev = pg['name_display'] in ELECTRIC_PLANTS_LIST
        motor_label = "CAMIÓN ELÉCTRICO (Zero Emissions)" if is_plant_ev else "DIÉSEL (Euro VI - Alta Eficiencia)"
        motor_class = "text-fuchsia-600" if is_plant_ev else "text-gray-400"
        
        km_rows_html.append(
            f'<tr class="bg-gray-100 font-bold text-gray-700 text-[11px] uppercase tracking-wider">'
            f'<td colspan="11" class="px-3 py-1">'
            f'<span>PLANTA: {pg["name_display"]}</span>'
            f'<div class="{motor_class} text-[9px] font-medium tracking-normal mt-0.5">{motor_label}</div>'
            f'</td>'
            f'</tr>'
        )
        # Fila Única Tradicional (Inbound Puro)
        base_km = pg.get("base_km", 0)
        base_cost = pg.get("base_cost", 0)
        base_co2 = pg.get("base_co2", 0)
        
        is_plant_ev = pg['name_display'] in ELECTRIC_PLANTS_LIST
        base_co2_km = base_co2 / base_km if base_km > 0 else 0
        
        if is_plant_ev:
            b_co2_km_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">0 (EV)</td>'
            # El escenario base asume 50% cargado (bobinas) y 50% vacío de retorno
            base_kwh = (base_km / 2 * EV_CONS_FULL) + (base_km / 2 * EV_CONS_EMPTY)
            b_co2_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">{fmt_std(base_kwh, 1)} kWh</td>'
        else:
            b_co2_km_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(base_co2_km, 3)} kg/km</td>'
            b_co2_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(base_co2, 1)} kg</td>'
        
        km_rows_html.append(
            f'<tr class="bg-gray-50/50 italic text-gray-500 text-[11px] border-b">'
            f'<td class="px-6 py-1 border-l-4 border-gray-300" title="Ruta de un camión que sale del depot, va a la planta y regresa vacío">Escenario Base Inbound (Sin clientes)</td>'
            f'<td class="px-2 py-1 text-center font-bold text-slate-400">Referencia</td>'
            f'<td class="px-2 py-1 text-center font-bold text-slate-400">Total Op.</td>'
            f'<td class="px-3 py-1 text-center font-mono text-orange-400">-</td>'
            f'<td class="px-3 py-1 text-center font-mono text-amber-400">-</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(base_km)}</td>'
            f'<td class="px-3 py-1 text-center font-mono font-bold text-red-400 bg-red-50/20">50.0%</td>'
            f'<td class="px-3 py-1 text-center font-mono text-blue-700">{fmt_std(base_cost, 2)} €</td>'
            f'{b_co2_td}'
            f'<td class="px-3 py-1 text-center font-mono">-</td>'
            f'<td class="px-3 py-1 text-center">Referencia</td>'
            f'</tr>'
        )
        # NUEVO: Fila de Agregación Línea Base (Impacto Total Planta sin Optimizar)
        num_routes = len(pg['opt_routes'])
        agg_base_km = base_km * num_routes
        agg_base_cost = base_cost * num_routes
        agg_base_co2 = base_co2 * num_routes
        agg_base_empty = (base_km / 2) * num_routes
        
        if is_plant_ev:
            agg_base_kwh = (agg_base_km / 2 * EV_CONS_FULL) + (agg_base_km / 2 * EV_CONS_EMPTY)
            agg_b_co2_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">{fmt_std(agg_base_kwh, 1)} kWh</td>'
        else:
            agg_b_co2_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(agg_base_co2, 1)} kg</td>'

        km_rows_html.append(
            f'<tr class="bg-slate-100 text-slate-700 font-bold text-[11px] border-b border-slate-200">'
            f'<td class="px-6 py-2 border-l-4 border-slate-300 uppercase tracking-tighter">'
            f'LINEA BASE TOTAL PLANTA (Proyectada x{num_routes} rutas)'
            f'</td>'
            f'<td class="px-2 py-1 text-center">-</td>'
            f'<td class="px-2 py-1 text-center font-bold text-slate-400">Escala</td>'
            f'<td class="px-3 py-1 text-center font-mono text-orange-400">-</td>'
            f'<td class="px-3 py-1 text-center font-mono text-amber-400">-</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(agg_base_km)}</td>'
            f'<td class="px-3 py-1 text-center font-mono font-bold text-red-400 bg-red-50/10">50.0%</td>'
            f'<td class="px-3 py-1 text-center font-mono bg-slate-200/40 text-blue-700">{fmt_std(agg_base_cost, 2)} €</td>'
            f'{agg_b_co2_td}'
            f'<td class="px-3 py-1 text-center font-mono">-</td>'
            f'<td class="px-3 py-1 text-center">Referencia</td>'
            f'</tr>'
        )
        
        # Filas Optimizadas (Multiples)
        total_p_dist, total_p_cost, total_p_co2, total_p_cust = 0, 0, 0, 0
        total_p_sys_saving, total_p_sys_co2_saving = 0, 0
        total_p_ret_saving = 0
        
        for orout in pg['opt_routes']:
            r_dist = orout['dist']
            r_cost = orout['cost']
            r_co2 = orout['co2']
            r_cust = orout['customers']
            r_empty = orout['empty']
            r_fill_rate = orout['fill_rate']
            r_milla_vacia = orout['milla_vacia']
            
            total_p_dist += r_dist
            total_p_cost += r_cost
            total_p_co2 += r_co2
            total_p_cust += r_cust
            total_p_sys_saving += orout['systemic_saving']
            total_p_sys_co2_saving += orout['systemic_co2_saving']
            total_p_ret_saving += orout['empty_ret_saving']
            
            # Formateo de CO2 para la ruta
            r_co2_km = r_co2 / r_dist if r_dist > 0 else 0
            if is_plant_ev:
                o_co2_km_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">0 (EV)</td>'
                o_co2_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">{fmt_std(orout["kwh"], 1)} kWh</td>'
            else:
                o_co2_km_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(r_co2_km, 3)} kg/km</td>'
                o_co2_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(r_co2, 1)} kg</td>'
            
            r_price = TARIFA_INTERNA_EV if orout['is_ev'] else TARIFA_INTERNA_DIESEL
            r_tco = BASE_TCO_EV if orout['is_ev'] else BASE_TCO_DIESEL
            r_tco_cost = r_dist * r_tco
            r_revenue = r_dist * r_price
            r_net = r_revenue - r_tco_cost
            
            km_rows_html.append(
                f'<tr class="hover:bg-blue-50/20 border-b text-[12px] text-blue-800">'
                f'<td class="px-6 py-2 font-semibold pl-12">{orout["desc"]}</td>'
                f'<td class="px-2 py-1 text-[10px] text-blue-600 uppercase font-bold text-center">Optimizado</td>'
                f'<td class="px-3 py-1 text-center font-bold text-indigo-600">{r_cust}</td>'
                f'<td class="px-3 py-1 text-center font-bold text-orange-500">{int(orout.get("total_pallets",0))}</td>'
                f'<td class="px-3 py-1 text-center font-bold text-amber-600 bg-amber-50/20">{fmt_std(r_fill_rate, 1)}%</td>'
                f'<td class="px-3 py-1 text-center font-mono font-bold">{fmt_std(r_dist)}</td>'
                f'<td class="px-3 py-1 text-center font-bold text-red-500 bg-red-50/30">{fmt_std(r_milla_vacia, 1)}%</td>'
                f'<td class="px-3 py-1 text-center font-mono font-bold text-blue-700">{fmt_std(r_revenue, 2)} €</td>'
                f"{o_co2_td}"
                f'<td class="px-3 py-1 text-center font-bold text-teal-600">+{fmt_std(orout["systemic_co2_saving"], 1)} kg</td>'
                f'<td class="px-3 py-1 text-center font-bold text-emerald-600 bg-emerald-50/50">+{fmt_std(orout["systemic_saving"], 0)} €</td>'
                f'</tr>'
            )
            
        # NUEVO: Fila de Agregación TOTAL Optimizado (Realidad tras Algoritmo)
        p_avg_co2_km = total_p_co2 / total_p_dist if total_p_dist > 0 else 0
        p_total_empty_after = sum([orout.get("empty_km", orout.get("empty", 0)) for orout in pg['opt_routes']])
        p_total_savings_empty = agg_base_empty - p_total_empty_after
        p_total_pct_empty = (p_total_savings_empty / agg_base_empty * 100) if agg_base_empty > 0 else 0
 
        if is_plant_ev:
            p_co2_km_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">0 (EV)</td>'
            p_co2_td = f'<td class="px-3 py-1 text-center font-mono text-fuchsia-700 font-bold">{fmt_std(sum([r.get("kwh",0) for r in pg["opt_routes"]]), 1)} kWh</td>'
        else:
            p_co2_km_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(p_avg_co2_km, 3)} kg/km</td>'
            p_co2_td = f'<td class="px-3 py-1 text-center font-mono">{fmt_std(total_p_co2, 1)} kg</td>'
 
        # Cálculo de Fill Rate y Milla Vacía agregados por planta
        p_total_pallets = sum([r.get("total_pallets", 0) for r in pg["opt_routes"]])
        # Promediamos el fill rate de las rutas de la planta
        p_avg_fill_rate = sum([r.get("fill_rate", 0) for r in pg["opt_routes"]]) / len(pg["opt_routes"]) if pg["opt_routes"] else 0
        p_avg_milla_vacia = (p_total_empty_after / total_p_dist * 100) if total_p_dist > 0 else 0
 
        p_total_tco = total_p_dist * (BASE_TCO_EV if is_plant_ev else BASE_TCO_DIESEL)
        p_total_rev = total_p_dist * (TARIFA_INTERNA_EV if is_plant_ev else TARIFA_INTERNA_DIESEL)
        p_total_net = p_total_rev - p_total_tco
 
        km_rows_html.append(
            f'<tr class="bg-blue-100 text-blue-900 font-bold text-[11px] border-b border-blue-200">'
            f'<td class="px-6 py-2 border-l-4 border-blue-400 uppercase tracking-tighter pl-10">'
            f'TOTAL PLANTA (Optimizado Real)'
            f'</td>'
            f'<td class="px-2 py-1 text-center font-bold text-blue-600 underline">Realizado</td>'
            f'<td class="px-3 py-1 text-center font-bold text-indigo-700">{total_p_cust}</td>'
            f'<td class="px-3 py-1 text-center font-bold text-orange-600">{int(p_total_pallets)}</td>'
            f'<td class="px-3 py-1 text-center font-bold text-amber-700 bg-amber-100/50">{fmt_std(p_avg_fill_rate, 1)}%</td>'
            f'<td class="px-3 py-1 text-center font-mono">{fmt_std(total_p_dist)}</td>'
            f'<td class="px-3 py-1 text-center font-bold text-red-800 bg-red-200/50">{fmt_std(p_avg_milla_vacia, 1)}%</td>'
            f'<td class="px-3 py-1 text-center font-mono bg-blue-200/40 text-blue-900">{fmt_std(p_total_rev, 2)} €</td>'
            f"{p_co2_td}"
            f'<td class="px-3 py-1 text-center font-bold text-teal-700">+{fmt_std(total_p_sys_co2_saving, 1)} kg</td>'
            f'<td class="px-3 py-1 text-center font-bold text-emerald-700 bg-emerald-100/50">+{fmt_std(total_p_sys_saving, 0)} €</td>'
            f'</tr>'
        )

    total_savings = total_empty_before - total_empty_after
    # Milla Vacía Absoluta (Total Sistema Optimizado)
    total_pct = (total_empty_after / t_dist_vrpb * 100) if t_dist_vrpb > 0 else 0

    if is_baseline:
        # MODO BASELINE: Solo actualizamos la pestaña de Condiciones Normales (tabla externa)
        table_path = Path("outputs/tables/tabla_comparativa_vacios.html")
        if table_path.exists():
            with open(table_path, "r", encoding="utf-8") as f:
                html_table = f.read()
            
            # 1. Inyectar Filas (Búsqueda más robusta del cuerpo de la tabla)
            marker = '<tbody id="comparison-tbody" class="divide-y divide-gray-100">'
            idx_marker = html_table.find(marker)
            if idx_marker == -1:
                # Intento genérico si falló el específico
                idx_marker = html_table.find('<tbody')
            
            if idx_marker != -1:
                # Encontrar el final de la etiqueta <tbody>
                start = html_table.find('>', idx_marker) + 1
                end = html_table.find('<tr id="total-row"', start)
                if end != -1:
                    html_table = html_table[:start] + "\n" + "\n".join(km_rows_html) + "\n" + html_table[end:]
                else:
                    logger.error("No se encontró el marcador <tr id=\"total-row\" para cerrar la inyección.")
            else:
                logger.error("No se encontró el marcador <tbody> en tabla_comparativa_vacios.html")

            # 2. Inyectar Totales (Sincronizado con Resumen Ejecutivo)
            global_co2_km = summary["total_co2_kg"] / summary["total_km"] if summary["total_km"] > 0 else 0
            f_loaded = GLEC_EMPTY_FLOOR_KGKM + (25 * GLEC_INTENSITY_GTKM / 1000.0)
            total_co2_trad = total_empty_before * (f_loaded + GLEC_EMPTY_FLOOR_KGKM)
            global_co2_km_trad = total_co2_trad / (total_empty_before * 2) if total_empty_before > 0 else 0
            reduction_co2_rel = (1 - (global_co2_km / global_co2_km_trad)) * 100 if global_co2_km_trad > 0 else 0

            # KPIs Globales para Footer
            g_fill_rate = (t_total_pallets / (summary["num_routes"] * 34)) * 100 if summary["num_routes"] > 0 else 0
            g_milla_vacia = (t_empty_vrpb / summary["total_km"] * 100) if summary["total_km"] > 0 else 0

            html_table = html_table.replace('{{T_CUST}}', str(t_total_customers))
            html_table = html_table.replace('{{T_FILL}}', f'{fmt_std(g_fill_rate, 1)}%')
            html_table = html_table.replace('{{T_MV_PCT}}', f'{fmt_std(g_milla_vacia, 1)}%')
            html_table = html_table.replace('{{T_DIST}}', f'{fmt_std(t_dist_vrpb)} km')
            html_table = html_table.replace('{{T_EMPTY}}', f'{fmt_std(t_empty_vrpb)} km')
            html_table = html_table.replace('{{T_CO2}}', f'{fmt_std(summary["total_co2_kg"], 0)} kg')
            html_table = html_table.replace('{{T_COST}}', f'{fmt_std(t_cost_vrpb)} €')
            html_table = html_table.replace('{{T_RED_ABS}}', f'+{fmt_std(t_co2_savings_systemic, 1)} kg')
            html_table = html_table.replace('{{T_RED_PCT}}', f"{'-' if reduction_co2_rel < 0 else ''}{fmt_std(abs(reduction_co2_rel), 1)}%")
            html_table = html_table.replace('{{T_VACIO_PCT}}', f'+{fmt_std(total_pct, 1)}%')
            html_table = html_table.replace('{{T_SAVING_EVIT}}', f'+{fmt_std(t_backhauling_saving, 0)} €')
            html_table = html_table.replace('{{T_SAVING_SYST}}', f'+{fmt_std(t_systemic_savings, 0)} €')

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
            html_res = _replace_kpi(html_res, "kpi-total-customers", summary.get("total_customers", 0))
            html_res = _replace_kpi(html_res, "kpi-total-km", f'{fmt_std(summary["total_km"])}')
            html_res = _replace_kpi(html_res, "kpi-total-cost", f'{fmt_std(t_cost_vrpb)} €')
            html_res = _replace_kpi(html_res, "kpi-euros-km", f'{fmt_std(global_cost_km, 3)}')
            html_res = _replace_kpi(html_res, "kpi-co2-km", f'{fmt_std(global_co2_km, 3)}')
            html_res = _replace_kpi(html_res, "kpi-co2-total", f'{fmt_std(summary["total_co2_kg"], 0)}')
            html_res = _replace_kpi(html_res, "kpi-red-co2-abs", f'{fmt_std(t_co2_savings_systemic, 1)} kg')
            html_res = _replace_kpi(html_res, "kpi-red-co2", red_label)
            html_res = _replace_kpi(html_res, "kpi-vacio-pct", f"~{fmt_std(total_pct, 1)}%")
            html_res = _replace_kpi(html_res, "kpi-systemic-saving", f"{fmt_std(t_systemic_savings, 0)} €")

            # --- NUEVOS KPIS ELÉCTRICOS (Inyección dinámica si no existen) ---
            if 'id="kpi-total-kwh"' not in html_res:
                kwh_cards = """
        <div class="card text-center border-t-4 border-fuchsia-600 bg-fuchsia-50/30 p-4">
            <p class="kpi-label text-fuchsia-700">Energía Total (kWh)</p>
            <p id="kpi-total-kwh" class="kpi-value text-2xl text-fuchsia-800">0</p>
        </div>
        <div class="card text-center border-t-4 border-fuchsia-400 p-4">
            <p class="kpi-label text-fuchsia-600 text-[10px]">Eficiencia (kWh/km)</p>
            <p id="kpi-avg-kwh-km" class="kpi-value text-2xl text-fuchsia-700">0</p>
        </div>"""
                # Insertar antes del cierre del primer grid
                grid_end_tag = '<!-- ROI Analysis Section'
                if grid_end_tag in html_res:
                    parts = html_res.split(grid_end_tag)
                    # El grid termina un poco antes
                    grid_close = parts[0].rfind('</div>')
                    html_res = parts[0][:grid_close] + kwh_cards + parts[0][grid_close:] + grid_end_tag + parts[1]

            avg_kwh_km = t_kwh_total / t_ev_km if t_ev_km > 0 else 0
            html_res = _replace_kpi(html_res, "kpi-total-kwh", f"{fmt_std(t_kwh_total, 1)}")
            html_res = _replace_kpi(html_res, "kpi-avg-kwh-km", f"{fmt_std(avg_kwh_km, 2)}")

            # --- CÁLCULO DE ROI Y PAYBACK (Retirado del Dashboard) ---
            pass

            # Inyectar Botón de Descarga Operacional al FINAL (NUEVO)
            if 'id="btn-download-operational"' not in html_res:
                btn_html = """
        <div class="flex justify-end mt-10 mb-10 mr-4">
            <a href="../../results_analysis/reporte_operativo_rutas.xlsx" download 
               class="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-6 py-3 rounded-2xl text-sm font-bold shadow-2xl transition-all hover:-translate-y-1 border border-slate-600"
               id="btn-download-operational">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                Descargar Reporte Operativo Detallado (Excel - 2 Hojas)
            </a>
        </div>
                """
                if '</body>' in html_res:
                    html_res = html_res.replace('</body>', btn_html + '</body>')

            # Inyectar Tabla Comparativa
            marker = 'id="comparison-tbody"'
            if marker in html_res:
                idx = html_res.find(marker)
                start = html_res.find('>', idx) + 1
                end = html_res.find('</tbody>', start)
                html_res = html_res[:start] + "\n" + "\n".join(km_rows_html) + "\n" + html_res[end:]
            
            # Actualizar el aviso naranja dinámicamente
            if "Análisis del segmento Linehaul" in html_res:
                pattern_alert = r'<p class="text-\[11px\] text-orange-600 mb-4 bg-orange-50 inline-block px-2 py-1 rounded">.*?</p>'
                html_res = re.sub(pattern_alert, header_alert, html_res)

            # Inyectar Tabla de Outsourcing (NUEVO)
            marker_ext = 'id="outsourcing-tbody"'
            if marker_ext in html_res:
                idx = html_res.find(marker_ext)
                start = html_res.find('>', idx) + 1
                end = html_res.find('</tbody>', start)
                html_res = html_res[:start] + "\n" + "\n".join(outsourcing_rows_html) + "\n" + html_res[end:]

            # Los KPIs de Eficiencia (Ocupación y Milla Vacía) ya están integrados en las filas de km_rows_html
            # que se inyectan en comparison-tbody. Eliminamos la tabla redundante que se inyectaba aquí.
            pass

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

        # 3. Generar pestaña de bibliografía y parámetros
        _generate_bibliografia_tab(bodies_dir)
        _generate_parametros_tab(bodies_dir)
        
        # 4. Generar pestañas Ejecutivas (Negocio/Riesgos)
        _generate_finanzas_tab(bodies_dir, t_dist_trad, t_dist_vrpb, ext_analyst.external_rate, price_km, summary["num_routes"])
        _generate_implementacion_tab(bodies_dir)

        # 5. GENERACIÓN DE GRAFOS DE RED (Centralizado para no sobrecargar main.py)
        try:
            # 1. Cargar datos maestros para el grafo de complejidad
            plants_file = DATA_DIR / "locations_smurfit.json"
            clients_file = DATA_DIR / "cliente_ubi.json"
            
            if plants_file.exists() and clients_file.exists():
                with open(plants_file, 'r', encoding='utf-8') as f:
                    plants_data = json.load(f)
                with open(clients_file, 'r', encoding='utf-8') as f:
                    raw_clients = json.load(f)
                    
                all_clients_list = []
                for z, dests in raw_clients.items():
                    for d in dests:
                        if "latitude" in d and "longitude" in d:
                            all_clients_list.append({
                                "name": d.get("municipio_destino", z), 
                                "lat": d["latitude"], 
                                "lng": d["longitude"]
                            })

                # 2. Instanciar Visualizer (sin matriz, usará geo fallback)
                viz = Visualizer(routes, distance_matrix=None, geo_utils=geo)
                
                # 3. Generar HTMLs en la carpeta de resultados
                viz.create_plotly_graph("Logistics_Graph.html")
                viz.create_global_complexity_graph(
                    plants_data['paper_plant'], 
                    plants_data['carton_plants'], 
                    all_clients_list, 
                    "Logistics_Global_Complexity.html"
                )
                logger.info("Grafos de red actualizados correctamente.")
            else:
                logger.warning("No se encontraron archivos de datos para generar grafos.")
        except Exception as e:
            logger.warning(f"No se pudieron actualizar los grafos de red: {e}")

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

def _generate_parametros_tab(bodies_dir):
    """Genera la pestaña de parámetros técnicos y económicos."""
    output_path = bodies_dir / "tab_parametros.html"
    

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f8fafc; color: #334155; }}
        .param-card {{ background: white; border-radius: 12px; padding: 20px; border-top: 4px solid #3b82f6; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
        .label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; font-weight: 700; }}
        .value {{ font-size: 1.25rem; font-weight: 700; color: #1e293b; font-family: 'ui-monospace', monospace; }}
        .unit {{ font-size: 0.875rem; color: #94a3b8; margin-left: 4px; font-weight: 400; }}
    </style>
</head>
<body class="p-8">
    <h1 class="text-3xl font-bold text-[#1e3a8a] mb-8 border-b-2 border-blue-100 pb-4">Parámetros de Configuración del Sistema</h1>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        <!-- Grupo 1: Motor de Optimización -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mr-3">1</span>
                Algoritmo y Solver
            </h2>
            <div class="param-card">
                <div class="mb-4">
                    <p class="label">Tiempo Máx. Búsqueda</p>
                    <p class="value">{MAX_SEARCH_TIME}<span class="unit">segundos</span></p>
                </div>
                <div class="mb-4">
                    <p class="label">Límite Distancia Ruta</p>
                    <p class="value">{DIST_LIMIT/1000:,.0f}<span class="unit">km</span></p>
                </div>
                <div class="mb-4">
                    <p class="label">Paradas Máx. por Ruta</p>
                    <p class="value">{DEFAULT_N_CLIENTES}<span class="unit">clientes</span></p>
                </div>
                <div class="mb-0">
                    <p class="label">Route Splitting (Fragmentación)</p>
                    <p class="value">{'Activado' if ALLOW_ROUTE_SPLITTING else 'Desactivado'}</p>
                </div>
            </div>
        </div>

        <!-- Grupo 2: Huella de Carbono y Pesos -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-green-100 text-green-600 rounded-full flex items-center justify-center mr-3">2</span>
                Factores KPI (GLEC v3)
            </h2>
            <div class="param-card" style="border-top-color: #10b981;">
                <div class="mb-4">
                    <p class="label">Emisión Base Vacío</p>
                    <p class="value">{GLEC_EMPTY_FLOOR_KGKM:.3f}<span class="unit">kg/km</span></p>
                </div>
                <div class="mb-4">
                    <p class="label">Intensidad por Carga</p>
                    <p class="value">{GLEC_INTENSITY_GTKM:.2f}<span class="unit">g CO2/tkm</span></p>
                </div>
                <div class="mb-4">
                    <p class="label">Peso Bobina Papel</p>
                    <p class="value">{PAPER_LOAD_KG:,.0f}<span class="unit">kg</span></p>
                </div>
                <div class="mb-0">
                    <p class="label">Peso Pallet Cartón</p>
                    <p class="value">{PALLET_WEIGHT_KG:,.0f}<span class="unit">kg</span></p>
                </div>
            </div>
        </div>

        <!-- Grupo 3: Dimensión y Estiba -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mr-3">3</span>
                Capacidad y Estiba
            </h2>
            <div class="param-card" style="border-top-color: #a855f7;">
                <div class="mb-4">
                    <p class="label">Remontabilidad (1+1)</p>
                    <p class="value">{'Global (ON)' if LOAD_STACKABLE else 'Dinamica (Per-Client)'}</p>
                    <p class="text-[9px] text-purple-600 mt-1 uppercase italic font-bold">Lógica: math.ceil(n/2) para huecos suelo</p>
                </div>
                <div class="mb-4">
                    <p class="label">Dimensiones Trailer (LxAxH)</p>
                    <p class="value">{TRAILER_LENGTH_M}x{TRAILER_WIDTH_M}x{TRAILER_HEIGHT_M}<span class="unit">m</span></p>
                </div>
                <div class="mb-0">
                    <p class="label">Capacidad Máx. Suelo</p>
                    <p class="value">33-34<span class="unit">slots</span></p>
                </div>
            </div>
        </div>

        <!-- Grupo 4: Costes Operativos Finales -->
        <div class="space-y-6 md:col-span-2 lg:col-span-3">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mr-3">4</span>
                Estructura de Costes (Tarifa Técnica)
            </h2>
            <div class="param-card" style="border-top-color: #f59e0b;">
                <div class="flex flex-col md:flex-row justify-between items-center gap-8">
                    <div class="text-center md:text-left">
                        <p class="label">Tarifa Técnica Interna (TCO Diésel Base)</p>
                        <p class="text-4xl font-black text-amber-700 font-mono">{TARIFA_INTERNA_DIESEL:,.1f}<span class="text-lg unit">€/km</span></p>
                        <p class="text-[10px] text-slate-400 mt-1 uppercase">Basado en Modelo MITMA 2026 (Ref. Notebook estimación)</p>
                    </div>
                    <div class="h-16 w-px bg-slate-100 hidden md:block"></div>
                    <div class="bg-amber-50 p-4 rounded-lg flex-1">
                        <p class="text-xs text-amber-800 font-bold mb-2 uppercase">Nota sobre el Desglose:</p>
                        <p class="text-xs text-amber-700 leading-relaxed italic">
                            Los costes fijos (Personal, Amortización, Seguros, Indirectos) y variables (Combustible, Mantenimiento) han sido desacoplados de la configuración global. 
                            El detalle actuarial y la validación de SciPy residen exclusivamente en el activo técnico de control de costes.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Grupo 5: Filtros de Datos -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mr-3">5</span>
                Filtros y Backhauling
            </h2>
            <div class="param-card" style="border-top-color: #6366f1;">
                <div class="mb-4">
                    <p class="label">Umbral de Desvío Máximo</p>
                    <p class="value">{DEFAULT_THRESHOLD_KM}<span class="unit">km</span></p>
                </div>
                <div class="mb-0">
                    <p class="label">Multi-Planta en Ruta</p>
                    <p class="value">{'Activado' if DEFAULT_MAX_PLANTS_PER_ROUTE > 1 else 'Desactivado'}</p>
                </div>
            </div>
        </div>

        <!-- Grupo 6: Configuración de Flota Mixta (NUEVO) -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-sky-100 text-sky-600 rounded-full flex items-center justify-center mr-3">6</span>
                Configuración de Flota
            </h2>
            <div class="param-card" style="border-top-color: #0ea5e9;">
                <div class="mb-4">
                    <p class="label">Composición de Flota</p>
                    <p class="value text-sky-700">{FLEET_MIX_DIESEL}D + {FLEET_MIX_EV}E<span class="unit">({FLEET_MIX_DIESEL + FLEET_MIX_EV} u)</span></p>
                </div>
                <div class="mb-4">
                    <p class="label">Utilización Anual</p>
                    <p class="value">{KMS_ANUALES_POR_CAMION:_}<span class="unit">km/u/año</span></p>
                </div>
                <div class="mb-0">
                    <p class="label">Horizonte Temporal</p>
                    <p class="value">{TCO_HORIZON_YEARS}<span class="unit">años análisis</span></p>
                </div>
            </div>
        </div>

        <!-- Grupo 7: Macroeconomía y Tasas -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mr-3">7</span>
                Variable Financiera
            </h2>
            <div class="param-card" style="border-top-color: #f43f5e;">
                <div class="mb-4">
                    <p class="label">Coste Capital (WACC)</p>
                    <p class="value">{TCO_WACC[0]*100:.1f}<span class="unit">% (Año 1)</span></p>
                </div>
                <div class="mb-4">
                    <p class="label">Inflación Proyectada</p>
                    <p class="value">{TCO_INFLACION_ANUAL[0]*100:.1f}<span class="unit">% (Año 1)</span></p>
                </div>
                <div class="mb-0">
                    <p class="label">Impuesto Sociedades</p>
                    <p class="value">{TCO_TAX_RATE*100:.0f}<span class="unit">% (IS)</span></p>
                </div>
            </div>
        </div>

        <!-- Grupo 8: Desglose TCO Diésel -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-slate-200 text-slate-600 rounded-full flex items-center justify-center mr-3">8</span>
                TCO Diésel (Euro VI)
            </h2>
            <div class="param-card" style="border-top-color: #475569;">
                <div class="mb-4">
                    <p class="label">CAPEX Unitario</p>
                    <p class="value text-slate-700">{DIESEL_CAPEX:_}<span class="unit">€/u</span></p>
                </div>
                <div class="mb-4 flex justify-between gap-2">
                    <div class="flex-1">
                        <p class="label">Mantenim.</p>
                        <p class="text-sm font-bold">{DIESEL_MANT_ANUAL:_}€</p>
                    </div>
                    <div class="flex-1 text-right">
                        <p class="label">Seguro/Imp</p>
                        <p class="text-sm font-bold">{DIESEL_SEGURO_ANUAL:_}€</p>
                    </div>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-100 italic text-[10px] text-slate-400">
                    Renting: {DIESEL_RENTING_MENSUAL:_} €/m | Leasing: {DIESEL_LEASING_MENSUAL:_} €/m
                </div>
            </div>
        </div>

        <!-- Grupo 9: Desglose TCO Eléctrico -->
        <div class="space-y-6">
            <h2 class="text-lg font-bold text-slate-700 flex items-center">
                <span class="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mr-3">9</span>
                TCO Eléctrico (BEV)
            </h2>
            <div class="param-card" style="border-top-color: #2563eb;">
                <div class="mb-4">
                    <p class="label">CAPEX Unitario</p>
                    <p class="value text-blue-700">{EV_CAPEX:_} <span class="text-xs font-normal text-slate-400">(Ayuda: {EV_MOVES_AYUDA:_}€)</span></p>
                </div>
                <div class="mb-4 flex justify-between gap-2">
                    <div class="flex-1">
                        <p class="label">Consumo kWh</p>
                        <p class="text-sm font-bold">{EV_CONSUMO_KWH_KM:.1f}<span class="text-[9px] ml-1">kWh/km</span></p>
                    </div>
                    <div class="flex-1 text-right">
                        <p class="label">Precio Energía</p>
                        <p class="text-sm font-bold">{EV_COSTE_KWH:.1f}<span class="text-[9px] ml-1">€/kWh</span></p>
                    </div>
                </div>
                <div class="mt-4 pt-4 border-t border-slate-100 italic text-[10px] text-slate-400">
                    Renting: {EV_RENTING_MENSUAL:_} €/m | Leasing: {EV_LEASING_MENSUAL:_} €/m
                </div>
            </div>
        </div>

    </div>

    <div class="mt-12 p-6 bg-slate-100 rounded-lg border border-slate-200 text-xs text-slate-500">
        Estos parametros definen el comportamiento del modelo de optimizacion y la precision de los KPIs financieros y ambientales reportados en el dashboard. Actualizacion automatica sincronizada con config.py.
    </div>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info("Pestana de Parametros generada.")

def _generate_finanzas_tab(bodies_dir, km_baseline, km_opt, ext_rate, int_rate, num_routes):
    # --- Seccion 1: Business Case (Asset-Light vs Asset-Heavy) ---
    analyzer = StrategicAnalyzer(
        days_per_year=250, 
        software_capex=25000, 
        truck_unit_cost=CAPEX_TRUCK_UNIT_COST,
        cycle_time_days=DEFAULT_CYCLE_TIME_DAYS,
        daily_dispatch=DAILY_TRUCK_OUTBOUND,
        fleet_buffer=DEFAULT_FLEET_BUFFER
    )
    # Generar tabla financiera resumida (TCO)
    # bc = analyzer.generate_business_case(km_baseline, km_opt, int_rate, ext_rate, num_routes)
    bc = {
        "roi_pct": 0, 
        "payback_years": 0, 
        "annual_net_saving": 0,
        "asset_light": {"capex_eur": 0, "opex_anual": 0},
        "operational": {"daily_dispatch": 0, "fleet_size_required": 0},
        "asset_heavy": {"capex_eur": 0, "fleet_capex": 0, "opex_anual": 0}
    } # Mock para evitar crash posterior

    
    # --- Seccion 1B: TCO Flota Mixta vs Diesel ---
    try:
        tabla = analyzer.generar_tabla_comparativa(n_diesel=FLEET_MIX_DIESEL, n_ev=FLEET_MIX_EV)
        rec = tabla["recomendacion"]
        m_tco = tabla['flota_mixta'][rec['modalidad']] 
        c_tco = rec
        color_tco = "text-emerald-300" if c_tco['ahorro_pct'] >= 0 else "text-red-400"
    except Exception as e:
        logger.error(f"Error generando TCO misto: {e}")
        m_tco = {'capex_neto': 0, 'opex_anual': 0, 'tco_total': 0}
        c_tco = {'payback_years': 0, 'ahorro_pct': 0, 'modalidad': 'compra'}
        color_tco = "text-red-400"
        tabla = analyzer.generar_tabla_comparativa(n_diesel=FLEET_MIX_DIESEL, n_ev=FLEET_MIX_EV)
        rec = tabla["recomendacion"]

    n_d = tabla["flota_mixta"]["compra"]["n_diesel"]
    n_e = tabla["flota_mixta"]["compra"]["n_ev"]
    n_t = tabla["flota_mixta"]["compra"]["n_total"]

    # Helper para generar celdas de la tabla de inversion
    def _inv_cell(tco_van, coste_km, is_best=False):
        border = 'border-2 border-green-400' if is_best else 'border border-slate-200'
        bg = 'bg-green-50/40' if is_best else 'bg-white'
        return (
            f'<td class="px-4 py-4 text-center {bg} {border} rounded-lg">'
            f'<p class="text-lg font-mono font-bold text-slate-800">{fmt_std(abs(tco_van), 0)} EUR</p>'
            f'<p class="text-[11px] text-slate-500 mt-1">{fmt_std(coste_km, 1)} EUR/km</p>'
            f'</td>'
        )

    def _inv_total_cell(data, mod_name, is_best=False):
        border = 'border-2 border-green-500' if is_best else 'border border-slate-700'
        bg = 'bg-green-900/20' if is_best else 'bg-slate-800'
        badge = '<span class="ml-2 bg-green-500 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase">Optimo</span>' if is_best else ''
        return (
            f'<td class="px-4 py-5 text-center {bg} {border}">'
            f'<p class="text-xl font-mono font-bold text-white">{fmt_std(abs(data["tco_total"]), 0)} EUR{badge}</p>'
            f'<p class="text-[11px] text-slate-400 mt-1">{fmt_std(data["coste_km_medio"], 1)} EUR/km medio</p>'
            f'</td>'
        )

    # Construir filas
    rows_diesel = '<tr class="border-b border-slate-100"><td class="px-4 py-4 font-bold text-slate-700 bg-slate-50"><p class="text-sm">' + str(n_d) + 'x Diesel (Euro VI)</p><p class="text-[10px] text-slate-400">' + fmt_std(DIESEL_CAPEX, 0) + ' EUR/u CAPEX</p></td>'
    rows_ev = '<tr class="border-b border-slate-100"><td class="px-4 py-4 font-bold text-fuchsia-700 bg-fuchsia-50/30"><p class="text-sm">' + str(n_e) + 'x Electrico (BEV)</p><p class="text-[10px] text-fuchsia-400">' + fmt_std(EV_CAPEX, 0) + ' EUR/u (MOVES: -' + fmt_std(EV_MOVES_AYUDA, 0) + ')</p></td>'
    rows_total = '<tr><td class="px-4 py-5 font-black text-white bg-slate-900 rounded-bl-xl"><p class="text-sm uppercase tracking-wider">' + str(n_t) + ' Camiones (Mixta)</p><p class="text-[10px] text-slate-400">' + str(TCO_HORIZON_YEARS) + ' anos | ' + fmt_std(KMS_ANUALES_POR_CAMION, 0) + ' km/ano/u</p></td>'

    for mod in ["compra", "leasing", "renting"]:
        is_best = (mod == rec["modalidad"])
        d = tabla["por_camion"]["diesel"][mod]
        e = tabla["por_camion"]["electrico"][mod]
        m = tabla["flota_mixta"][mod]
        rows_diesel += _inv_cell(d["tco_van_acumulado"], d["coste_neto_por_km"], is_best)
        rows_ev += _inv_cell(e["tco_van_acumulado"], e["coste_neto_por_km"], is_best)
        rows_total += _inv_total_cell(m, mod, is_best)

    rows_diesel += '</tr>'
    rows_ev += '</tr>'
    rows_total += '</tr>'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; }}</style>
</head>
<body class="p-8 pb-32">
    <div class="max-w-7xl mx-auto">
        <h1 class="text-3xl font-black text-slate-800 mb-2 border-b-2 border-slate-200 pb-4">Análisis de Inversión y TCO</h1>
        <p class="text-slate-500 text-sm mb-8">Evaluación estratégica de modalidades de adquisición y Coste Total de Propiedad (TCO).</p>

        <!-- Bloque de Parámetros de Simulación -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Macroeconomía</p>
                <p class="text-xs text-slate-700 mt-2">WACC: <b>{float(TCO_WACC[0])*100:.1f}% a {float(TCO_WACC[-1])*100:.1f}%</b></p>
                <p class="text-xs text-slate-700">Inflación: <b>{float(TCO_INFLACION_ANUAL[0])*100:.1f}%</b></p>
                <p class="text-xs text-slate-700">Tax Rate: <b>{float(TCO_TAX_RATE)*100:.1f}%</b></p>
            </div>
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Operación</p>
                <p class="text-xs text-slate-700 mt-2">Uso: <b>{fmt_std(KMS_ANUALES_POR_CAMION, 0)} km/año</b></p>
                <p class="text-xs text-slate-700">Horizonte: <b>{TCO_HORIZON_YEARS} años</b></p>
                <p class="text-xs text-slate-700">Flota Total: <b>{n_t} camiones</b></p>
            </div>
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Diesel (Euro VI)</p>
                <p class="text-xs text-slate-700 mt-2">Capex: <b>{fmt_std(DIESEL_CAPEX, 0)} €</b></p>
                <p class="text-xs text-slate-700">Gasoil: <b>{DIESEL_COSTE_COMBUSTIBLE_L} €/L</b></p>
                <p class="text-xs text-slate-700">Consumo: <b>{DIESEL_CONSUMO_L_100KM} L/100</b></p>
            </div>
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm border-l-4 border-emerald-500">
                <p class="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">Vehículo Eléctrico</p>
                <p class="text-xs text-slate-700 mt-2">Capex: <b>{fmt_std(EV_CAPEX, 0)} €</b></p>
                <p class="text-xs text-slate-700">Moves III: <b>-{fmt_std(EV_MOVES_AYUDA, 0)} €</b></p>
                <p class="text-xs text-slate-700">Energía: <b>{EV_COSTE_KWH} €/kWh</b></p>
            </div>
        </div>

        <!-- ================================================================ -->
        <!-- SECCION 2: TABLA DE INVERSION POR MODALIDAD                      -->
        <!-- ================================================================ -->
        <div class="mb-4">
            <h2 class="text-2xl font-black text-slate-800 mb-1">Cálculo de TCO por Modalidad</h2>
            <p class="text-slate-500 text-xs">Comparativa de flujos de caja descontados (VAN) para flota mixta ({FLEET_MIX_DIESEL} Diésel / {FLEET_MIX_EV} BEV).</p>
        </div>

        <div class="overflow-x-auto rounded-2xl shadow-xl border border-slate-200 mb-8">
            <table class="w-full text-sm border-collapse">
                <thead>
                    <tr class="bg-slate-800 text-white">
                        <th class="px-4 py-4 text-left text-[11px] uppercase tracking-wider rounded-tl-2xl">Tecnologia / Flota</th>
                        <th class="px-4 py-4 text-center text-[11px] uppercase tracking-wider">
                            <div class="flex flex-col items-center">
                                <span class="text-amber-300 font-black">Compra</span>
                                <span class="text-[9px] text-slate-400 font-normal mt-1">Propiedad directa</span>
                            </div>
                        </th>
                        <th class="px-4 py-4 text-center text-[11px] uppercase tracking-wider">
                            <div class="flex flex-col items-center">
                                <span class="text-blue-300 font-black">Leasing</span>
                                <span class="text-[9px] text-slate-400 font-normal mt-1">Arrendamiento financiero</span>
                            </div>
                        </th>
                        <th class="px-4 py-4 text-center text-[11px] uppercase tracking-wider rounded-tr-2xl">
                            <div class="flex flex-col items-center">
                                <span class="text-green-300 font-black">Renting</span>
                                <span class="text-[9px] text-slate-400 font-normal mt-1">Operativo (Full-Service)</span>
                            </div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {rows_diesel}
                    {rows_ev}
                </tbody>
                <tfoot class="bg-slate-900 text-white border-t-4 border-slate-700">
                    {rows_total}
                </tfoot>
            </table>
        </div>

        <!-- Badge de Recomendacion -->
        <div class="bg-gradient-to-r from-green-600 to-emerald-700 text-white p-6 rounded-2xl shadow-xl flex items-center justify-between">
            <div>
                <p class="text-xs uppercase tracking-wider font-bold text-green-200">Escenario Óptimo (TCO)</p>
                <p class="text-2xl font-black mt-1">{rec['modalidad'].upper()}</p>
                <p class="text-sm text-green-100 mt-1">Ahorro de {fmt_std(rec['ahorro_vs_peor_eur'], 0)} EUR vs {rec['vs_modalidad'].upper()} (-{fmt_std(rec['ahorro_pct'], 1)}%)</p>
            </div>
            <div class="text-right">
                <p class="text-4xl font-black font-mono">{fmt_std(abs(tabla['flota_mixta'][rec['modalidad']]['tco_total']), 0)}</p>
                <p class="text-xs text-green-200 mt-1">EUR TCO Total ({TCO_HORIZON_YEARS} anos)</p>
            </div>
        </div>

        <!-- Dashboard Interactivo de Gráficos (Extracción Estratégica) -->
        <h2 class="text-2xl font-black text-slate-800 mt-12 mb-6 border-b pb-2">Análisis de Sensibilidad (VAN)</h2>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <h4 class="text-center font-bold text-slate-700 mb-2">Evolución del VAN Acumulado</h4>
                <iframe src="../../results_analysis/grafico_evolucion_van.html" style="width: 100%; height: 500px; border: none; border-radius: 8px;"></iframe>
            </div>
            <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <h4 class="text-center font-bold text-slate-700 mb-2">Comparativa TCO: Diésel vs Eléctrico</h4>
                <iframe src="../../results_analysis/grafico_tco_comparativo.html" style="width: 100%; height: 500px; border: none; border-radius: 8px;"></iframe>
            </div>
        </div>

        <div class="mt-8 flex justify-center pb-12">
            <a href="../../results_analysis/resumen_comparativo_modalidades.xlsx" target="_blank" class="bg-slate-800 text-white px-8 py-4 rounded-xl font-bold hover:bg-slate-700 transition-all shadow-lg flex items-center transform hover:-translate-y-1">
                <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                Descargar Desglose Financiero (Excel)
            </a>
        </div>

    </div>
</body>
</html>"""
    
    with open(bodies_dir / "tab_finanzas.html", "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Pestana de Finanzas generada.")

def _generate_implementacion_tab(bodies_dir):
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; }
        .grid-line { border-left: 2px dashed #cbd5e1; }
    </style>
</head>
<body class="p-8 pb-32">
    <div class="max-w-7xl mx-auto">
        <h1 class="text-3xl font-black text-slate-800 mb-2 border-b-2 border-slate-200 pb-4">Análisis de Riesgos e Implementación</h1>


        <!-- Riesgos: Matriz 2x2 simulada -->
        <h2 class="text-xl font-bold text-slate-800 mb-6 flex items-center"><span class="w-8 h-8 rounded bg-yellow-100 text-yellow-600 flex items-center justify-center mr-3 font-black text-lg">!</span> Riesgos Operativos</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
            <div class="bg-white border-l-4 border-red-500 p-6 rounded-lg shadow-sm">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-slate-800">1. Resistencia de los Transportistas (Sindicatos)</h3>
                    <span class="bg-red-100 text-red-700 text-xs font-bold px-2 py-1 rounded">Alta Prob.</span>
                </div>
                <p class="text-[11px] text-orange-600 mb-4 bg-orange-50 inline-block px-2 py-1 rounded">ℹ Análisis del segmento Linehaul (Entrega): Flota Propia (1.34 €/km) vs. Tarifa Externa (2.22 €/km).</p>
                <div class="bg-slate-50 p-3 rounded text-xs">
                    <strong class="text-slate-700 block mb-1">Solución Propuesta:</strong>
                    Implementar modelo "Share-the-saving". Devolver un 30% del margen ahorrado directamente al conductor.
                </div>
            </div>

            <div class="bg-white border-l-4 border-orange-500 p-6 rounded-lg shadow-sm">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-slate-800">2. Fallo de la API Geográfica</h3>
                    <span class="bg-orange-100 text-orange-700 text-xs font-bold px-2 py-1 rounded">Prob. Media</span>
                </div>
                <p class="text-sm text-slate-600 mb-4">Incapacidad de resolver la matriz OSRM colapsando todo el proceso de optimización del día.</p>
                <div class="bg-slate-50 p-3 rounded text-xs">
                    <strong class="text-slate-700 block mb-1">Solución Propuesta:</strong>
                    Uso de <code>geo_cache.py</code> y fallback automático a la fórmula Haversine integrada como *failsafe*.
                </div>
            </div>

            <div class="bg-white border-l-4 border-yellow-400 p-6 rounded-lg shadow-sm">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-slate-800">3. Ventanas de Tiempo (Time Windows)</h3>
                    <span class="bg-yellow-100 text-yellow-700 text-xs font-bold px-2 py-1 rounded">Impacto Alto</span>
                </div>
                <p class="text-sm text-slate-600 mb-4">Los clientes no pueden recepcionar la carga fuera del horario pactado 09:00 - 14:00.</p>
                <div class="bg-slate-50 p-3 rounded text-xs">
                    <strong class="text-slate-700 block mb-1">Solución Propuesta:</strong>
                    Evolución planificada a **VRPTW** en Fase 2.
                </div>
            </div>

            <div class="bg-white border-l-4 border-blue-500 p-6 rounded-lg shadow-sm">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-slate-800">4. Volatilidad Demanda Física</h3>
                    <span class="bg-blue-100 text-blue-700 text-xs font-bold px-2 py-1 rounded">Prob. Baja</span>
                </div>
                <p class="text-sm text-slate-600 mb-4">La ocupación del trailer supera físicamente el límite de pallets en la ruta pre-optimizada.</p>
                <div class="bg-slate-50 p-3 rounded text-xs">
                    <strong class="text-slate-700 block mb-1">Solución Propuesta:</strong>
                    Dimensionamiento condicional `AddDimensionWithVehicleCapacity` integrado en las restricciones del solver.
                </div>
            </div>
        </div>



    </div>
</body>
</html>"""
    with open(bodies_dir / "tab_implementacion.html", "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Pestaña de Implementación generada.")


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
# Fin de report_generator.py
