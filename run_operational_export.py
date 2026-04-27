import os
import json
import pandas as pd
from pathlib import Path
from logistic_core.config import (
    TARIFA_INTERNA_DIESEL, TARIFA_INTERNA_EV,
    BASE_TCO_DIESEL, BASE_TCO_EV,
    ELECTRIC_PLANTS_LIST
)
from logistic_core.utils.external_cost_analyst import ExternalCostAnalyst

def run_export():
    print("Iniciando exportación operativa (JSON Summary -> Excel)...")
    
    # 1. Cargar datos del resumen de optimización
    summary_path = Path("outputs/results/optimization_summary.json")
    
    if not summary_path.exists():
        print(f"Error: No se encuentra {summary_path}")
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
        
    routes_list = summary_data.get("routes", [])
    ext_analyst = ExternalCostAnalyst()
    
    trips_rows = []
    systemic_rows = []
    
    for i, r in enumerate(routes_list):
        # Identificar planta principal y tecnología
        p_list = r.get("plants", [])
        p_full_name = p_list[0] if p_list else "Desconocida"
        # Limpiar nombre para match con lista EV
        p_clean = p_full_name.split('(')[0].strip()
        is_ev = p_clean in ELECTRIC_PLANTS_LIST or p_full_name in ELECTRIC_PLANTS_LIST
        
        # Parámetros financieros
        price_km = TARIFA_INTERNA_EV if is_ev else TARIFA_INTERNA_DIESEL
        tco_km = BASE_TCO_EV if is_ev else BASE_TCO_DIESEL
        
        dist_km = r.get("distance_km", 0)
        empty_km = r.get("empty_km", 0)
        total_pallets = r.get("total_pallets", 0)
        co2_kg = r.get("co2_emissions_kg", 0)
        
        # Cálculos Económicos Directos
        tco_real = dist_km * tco_km
        ingreso_tarifa = dist_km * price_km
        beneficio_neto = ingreso_tarifa - tco_real
        
        # Segmento Linehaul para Ahorro Sistémico
        # Distancia de ida (Planta -> Clientes)
        lh_dist = dist_km - empty_km
        ext_metrics = ext_analyst.analyze_leg(lh_dist)
        
        # Sheet 1: Detalle de Viajes
        trips_rows.append({
            "Ruta ID": r.get("route_id", i+1),
            "Planta": p_full_name,
            "Tecnología": "ELÉCTRICO (EV)" if is_ev else "DIÉSEL (Euro VI)",
            "Clientes": r.get("num_customers", 1),
            "Pallets": total_pallets,
            "Llenado (%)": round((total_pallets / 34) * 100, 1),
            "Distancia (KM)": round(dist_km, 2),
            "Milla Vacía (%)": round((empty_km / dist_km * 100), 1) if dist_km > 0 else 0,
            "TCO Real (€)": round(tco_real, 2),
            "Ingreso Tarifa (€)": round(ingreso_tarifa, 2),
            "Bº Neto (€)": round(beneficio_neto, 2),
            "CO2 Total (kg)": round(co2_kg, 2),
            "CO2 Evitado (kg)": round(ext_metrics["co2_kg"], 2),
            "Ahorro vs. Mercado (€)": round(ext_metrics["savings"], 2)
        })
        
        # Sheet 2: Desglose Linehaul
        systemic_rows.append({
            "Planta / Origen": p_full_name,
            "Ruta ID": r.get("route_id", i+1),
            "Distancia Linehaul (km)": round(lh_dist, 2),
            "Coste In-house (Tarifa Interna)": round(ext_metrics["internal_cost"], 2),
            "Coste Proveedor (Tarifa Mercado)": round(ext_metrics["external_cost"], 2),
            "Beneficio Capturado (€)": round(ext_metrics["savings"], 2),
            "CO2 Externalizado (kg)": round(ext_metrics["co2_kg"], 2)
        })

    # Crear DataFrames
    df_trips = pd.DataFrame(trips_rows)
    df_systemic = pd.DataFrame(systemic_rows)
    
    # Guardar en Excel con dos hojas
    output_path = Path("results_analysis/reporte_operativo_rutas.xlsx")
    os.makedirs(output_path.parent, exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_trips.to_excel(writer, sheet_name='Detalle de Viajes', index=False)
        df_systemic.to_excel(writer, sheet_name='Ahorro Sistémico (Linehaul)', index=False)
        
        workbook = writer.book
        # Formatos
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#111827', 'font_color': 'white', 'border': 1})
        num_fmt = workbook.add_format({'num_format': '#,##0.00'})
        
        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            df = df_trips if sheetname == 'Detalle de Viajes' else df_systemic
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
                worksheet.set_column(col_num, col_num, 18)
            # Aplicar formato numérico a columnas de dinero/km
            worksheet.set_column(2, len(df.columns)-1, 15, num_fmt)

    print(f"Excel generado exitosamente en: {output_path}")

if __name__ == "__main__":
    run_export()
