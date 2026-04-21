import os
import pandas as pd
import plotly.graph_objects as go
from logistic_core.utils.strategic_analyzer import StrategicAnalyzer

# =================================================================
# 1. PARÁMETROS Y CONFIGURACIÓN (VERSION DINÁMICA)
# =================================================================

# --- Macroeconomía ---
HORIZONTE_AÑOS = 5
WACC_SERIE = [0.07, 0.075, 0.08, 0.085, 0.09]      # Curva de tipos
INFLACION_SERIE = [0.02, 0.03, 0.05, 0.03, 0.02]   # Pico de inflación
TAX_RATE = 0.25
KMS_ANUALES = 130_000

# --- Flota ---
N_DIESEL = 33
N_EV = 18

# --- Diésel ---
D_PARAMS = {
    "capex": 140_000,
    "consumo_l_100km": 33.0,
    "coste_combustible_l": 1.45,
    "mantenimiento_anual": 9_000,
    "seguro_anual": 3_500,
    "residual_pct": 0.30
}
D_RENTING_MES = 2_800
D_LEASING_MES = 2_600

# --- Eléctrico ---
EV_PARAMS = {
    "capex_truck": 350_000,
    "capex_charger": 50_000,
    "ayuda_moves": 90_000,
    "consumo_kwh_km": 1.30,
    "coste_kwh": 0.18,
    "mantenimiento_anual": 4_000,
    "seguro_anual": 4_500,
    "residual_pct": 0.25
}
EV_RENTING_MES = 5_600
EV_LEASING_MES = 5_200

# =================================================================
# 2. EJECUCIÓN DEL MOTOR
# =================================================================

analyzer = StrategicAnalyzer(
    kms_anuales=KMS_ANUALES,
    wacc=WACC_SERIE,
    inflación_anual=INFLACION_SERIE,
    diesel_params=D_PARAMS,
    ev_params=EV_PARAMS,
    financiacion={
        "diesel_renting": D_RENTING_MES,
        "diesel_leasing": D_LEASING_MES,
        "ev_renting": EV_RENTING_MES,
        "ev_leasing": EV_LEASING_MES
    }
)

print("Iniciando análisis estratégico serial...")
resultados = analyzer.generar_tabla_comparativa(n_diesel=N_DIESEL, n_ev=N_EV)

# =================================================================
# 3. PROCESAMIENTO DE DATOS (FORMATO LONG)
# =================================================================

# Tabla de Flota Mixta
df_mixto = pd.DataFrame([
    {
        "Modalidad": m.upper(),
        "Nº Diesel": d['n_diesel'],
        "Nº EV": d['n_ev'],
        "Valor Residual Total (€)": d['valor_residual_total'],
        "TCO Total (VAN) (€)": abs(d['tco_total']),
        "Coste Medio (€/km)": d['coste_km_medio']
    }
    for m, d in resultados['flota_mixta'].items()
])

# Tabla de Flujos Anuales (Formato Long)
rows_flujos = []
for tech, modalities in resultados['por_camion'].items():
    for mod, metrics in modalities.items():
        for año, flujo in enumerate(metrics['flujos_anuales']):
            rows_flujos.append({
                "Tecnología": tech.capitalize(),
                "Modalidad": mod.upper(),
                "Año": año,
                "Flujo_Caja": round(flujo, 2)
            })
df_flujos = pd.DataFrame(rows_flujos)

# =================================================================
# 4. GUARDAR RESULTADOS
# =================================================================

output_dir = "results_analysis"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Guardar Excels/CSVs
df_mixto.to_excel(f"{output_dir}/resumen_comparativo_modalidades.xlsx", index=False)
df_flujos.to_csv(f"{output_dir}/flujos_caja_anuales_long.csv", index=False)

print(f"Tablas guardadas en /{output_dir}")

# =================================================================
# 5. GENERACIÓN Y GUARDADO DE FIGURAS
# =================================================================

# A. Gráfico TCO Comparativo
modos = ["compra", "leasing", "renting"]
nombres = ["Compra Directa", "Leasing Financiero", "Renting Operativo"]
y_diesel = [abs(resultados['flota_mixta'][m]['tco_diesel_subtotal']) for m in modos]
y_ev = [abs(resultados['flota_mixta'][m]['tco_ev_subtotal']) for m in modos]

fig_tco = go.Figure(data=[
    go.Bar(name='TCO Diésel', x=nombres, y=y_diesel, marker_color='#475569'),
    go.Bar(name='TCO Eléctrico', x=nombres, y=y_ev, marker_color='#10b981')
])
fig_tco.update_layout(
    barmode='stack', 
    title='TCO Flota Mixta a 5 Años (Series Dinámicas)',
    yaxis_title='Euros (€)',
    template='plotly_white'
)
fig_tco.write_html(f"{output_dir}/grafico_tco_comparativo.html")

# B. Gráfico Evolución VAN
fig_evolu = analyzer.plot_van_evolution(n_diesel=N_DIESEL, n_ev=N_EV)
fig_evolu.write_html(f"{output_dir}/grafico_evolucion_van.html")

print(f"Figuras interactivas guardadas como HTML en /{output_dir}")
print("Proceso finalizado con éxito.")
