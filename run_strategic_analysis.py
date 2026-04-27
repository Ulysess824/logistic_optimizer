import os
import pandas as pd
import plotly.graph_objects as go
from logistic_core.utils.strategic_analyzer import StrategicAnalyzer
from logistic_core import config

# =================================================================
# 1. CARGA DE PARÁMETROS DESDE CONFIG
# =================================================================

HORIZONTE_AÑOS = config.TCO_HORIZON_YEARS
WACC_SERIE = config.TCO_WACC
INFLACION_SERIE = config.TCO_INFLACION_ANUAL
TAX_RATE = config.TCO_TAX_RATE
KMS_ANUALES = config.KMS_ANUALES_POR_CAMION

N_DIESEL = config.FLEET_MIX_DIESEL
N_EV = config.FLEET_MIX_EV

# Diccionarios para el motor
D_PARAMS = {
    "capex": config.DIESEL_CAPEX,
    "consumo_l_100km": config.DIESEL_CONSUMO_L_100KM,
    "coste_combustible_l": config.DIESEL_COSTE_COMBUSTIBLE_L,
    "mantenimiento_anual": config.DIESEL_MANT_ANUAL + config.DIESEL_NEUMATICOS_ANUAL,
    "seguro_anual": config.DIESEL_SEGURO_ANUAL,
    "residual_pct": config.DIESEL_RESIDUAL_PCT
}

EV_PARAMS = {
    "capex_truck": config.EV_CAPEX,
    "capex_charger": config.EV_CHARGER_CAPEX,
    "ayuda_moves": config.EV_MOVES_AYUDA,
    "consumo_kwh_km": config.EV_CONSUMO_KWH_KM,
    "coste_kwh": config.EV_COSTE_KWH,
    "mantenimiento_anual": config.EV_MANT_ANUAL,
    "seguro_anual": config.EV_SEGURO_ANUAL,
    "residual_pct": config.EV_RESIDUAL_PCT
}

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
        "diesel_renting": config.DIESEL_RENTING_MENSUAL,
        "diesel_leasing": config.DIESEL_LEASING_MENSUAL,
        "ev_renting": config.EV_RENTING_MENSUAL,
        "ev_leasing": config.EV_LEASING_MENSUAL
    }
)

print("Iniciando análisis estratégico serial (Config Centralizada)...")
resultados = analyzer.generar_tabla_comparativa(n_diesel=N_DIESEL, n_ev=N_EV)

# =================================================================
# 3. PROCESAMIENTO DE DATOS
# =================================================================

df_mixto = pd.DataFrame([
    {
        "Modalidad": m.upper(),
        "Nº Diesel": d['n_diesel'],
        "Nº EV": d['n_ev'],
        "TCO Activos (VAN) (€)": abs(d['tco_activos_subtotal']),
        "TCO Personal (VAN) (€)": abs(d['tco_personal_subtotal']),
        "TCO TOTAL OPERACIÓN (€)": abs(d['tco_total']),
        "Valor Residual Total (€)": d['valor_residual_total'],
        "Coste Medio (€/km)": d['coste_km_medio']
    }
    for m, d in resultados['flota_mixta'].items()
])

output_dir = "results_analysis"
if not os.path.exists(output_dir): os.makedirs(output_dir)

df_mixto.to_excel(f"{output_dir}/resumen_comparativo_modalidades.xlsx", index=False)

# =================================================================
# 4. GENERACIÓN DE FIGURAS (ESCALA UNITARIA)
# =================================================================

# Gráficas eliminadas (anteriormente vinculadas a tab_inversion.html)
print("Proceso finalizado con éxito.")
