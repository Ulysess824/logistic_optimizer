import nbformat as nbf
import os
from nbformat.v4 import new_code_cell, new_markdown_cell

nb_path = "notebooks/Estimación Tarifa propia.ipynb"
with open(nb_path, "r", encoding='utf-8') as f:
    nb = nbf.read(f, as_version=4)

# 1. Corrección AdBlue (Celda 1 -> Code)
code_1 = nb.cells[1].source
code_1_new = code_1.replace('"adblue_y_aditivos": 0.015', '"adblue_y_aditivos": 0.007, # 38L/100km diésel -> 1.9L/100km AdBlue @ 0.35€/L')
nb.cells[1].source = code_1_new

# Buscar la celda "electric_header" para insertar detrás los nuevos bloques
idx_elec_header = -1
for i, cell in enumerate(nb.cells):
    if cell.cell_type == 'markdown' and 'Escenario: Camión Eléctrico' in cell.source:
        idx_elec_header = i
        break

# Bloques nuevos
code_capex = """# =====================================================================
# ESCENARIOS DE CAPEX — CAMIÓN ELÉCTRICO 44t (2026)
# =====================================================================
# Precio lista (Volvo FH Electric / Mercedes eActros 600): 380.000-460.000€
# Ayudas MOVES III + PERTE VEC: 40.000-80.000€ según comunidad autónoma

CAPEX_SCENARIOS = {
    "optimista":   {"capex_neto": 300000, "descripcion": "Precio lista 380k€ - ayudas máximas 80k€"},
    "central":     {"capex_neto": 370000, "descripcion": "Precio lista 420k€ - ayudas medias 50k€"},
    "conservador": {"capex_neto": 450000, "descripcion": "Precio lista 460k€ - sin ayudas"},
}

VIDA_UTIL_ELECTRICO = 7  # años (batería como factor limitante)

# Escenario seleccionado para el modelo base
CAPEX_SELECCIONADO = "central"
capex_neto = CAPEX_SCENARIOS[CAPEX_SELECCIONADO]["capex_neto"]
amortizacion_anual = capex_neto / VIDA_UTIL_ELECTRICO

print(f"Escenario CAPEX: {CAPEX_SELECCIONADO.upper()}")
print(f"CAPEX Neto: {capex_neto:,.0f} €")
print(f"Amortización Anual: {amortizacion_anual:,.0f} €/año")
"""

code_energy = """# =====================================================================
# PARÁMETROS ENERGÉTICOS — SENSIBILIDAD
# =====================================================================
# Fuente consumo: Volvo FH Electric spec sheet (condiciones ideales)
# Ajuste operativo: +20-30% por orografía española y carga real

CONSUMO_KWH_KM = {
    "ideal":      1.10,  # Volvo FH Electric, ruta plana, carga optimizada
    "operativo":  1.35,  # Ajuste +23% por condiciones reales España
    "pesimista":  1.80,  # Orografía adversa, carga máxima constante
}

PRECIO_KWH = {
    "nocturno_propio":   0.08,   # Tarifa valle con instalación propia
    "industrial_medio":  0.22,   # Tarifa industrial referencia Repsol 2026
    "red_publica":       0.45,   # Recarga en puntos públicos ultra-rápidos
}

# Escenario seleccionado para el modelo base
consumo_sel = "operativo"
precio_sel  = "industrial_medio"

coste_energia_km = CONSUMO_KWH_KM[consumo_sel] * PRECIO_KWH[precio_sel]
print(f"Consumo: {CONSUMO_KWH_KM[consumo_sel]} kWh/km | Precio: {PRECIO_KWH[precio_sel]} €/kWh")
print(f"Coste energía: {coste_energia_km:.3f} €/km")
"""

electric_data_old_idx = idx_elec_header + 1
# La celda electric_data original de estimacion tarifa propia se modificará
code_elect_data = """# =====================================================================
# DATOS ESCENARIO ELÉCTRICO (REFERENCIAS SOTA 2026)
# =====================================================================

fixed_costs_electric = {
    "personal_y_dietas": 62500.0,    # Estructura idéntica al diésel
    "amortizacion_vehiculo": amortizacion_anual, # Integrado desde el escenario de CAPEX
    "seguros_y_visados": 5500.0,      # +22% vs diésel. Rango real 2026: 5.000-7.500€
                                      # Riesgo al alza: escasa estadística siniestralidad 
                                      # en pesados eléctricos + prima incendio baterías Li-ion
    "infraestructura_carga": 4500.0,  # Amortización cargador 150kW + instalación eléctrica
                                      # Rango real: 3.000-8.000€/año según instalación compartida
                                      # Valor central conservador para flota multi-camión
    "costes_indirectos": 14500.0,
    "fiscalidad_y_otros": 2000.0
}

variable_costs_electric = {
    "energia_electrica": coste_energia_km,       # Integrado desde la parametrización de energía
    "mantenimiento_y_tires": 0.110,  # Reducción operativa del 33% por simplicidad mecánica
    "adblue_y_aditivos": 0.0          # Emisiones cero
}

from logistic_core.utils.cost_estimator import CostEstimator
est_elect = CostEstimator(
    fixed_costs_annual=fixed_costs_electric,
    variable_costs_km=variable_costs_electric,
    annual_km_per_truck=110000
)
print(f"Tarifa Técnica Eléctrico (Línea Base Escenario Central): {est_elect.price_per_km:.4f} €/km")
"""

# Reconstruir lista de celdas
new_cells = nb.cells[:idx_elec_header+1]
new_cells.append(new_code_cell(code_capex))
new_cells.append(new_code_cell(code_energy))
new_cells.append(new_code_cell(code_elect_data))

# Ahora buscamos si hay las celdas viejas (electric_opt y bibliography) y las reemplazamos por el analisis
idx_opt_header = -1
for i, cell in enumerate(nb.cells):
    if cell.cell_type == 'markdown' and 'Optimización de la Tarifa' in cell.source:
        idx_opt_header = i
        break

# El bloque de sensibilidad
md_sensibilidad = """### 🔍 Análisis de Sensibilidad — Tarifa Eléctrico (Matriz Operativa)

Sustituyendo el enfoque de retrofitting, realizamos un cálculo iterativo paramétrico combinando consumos reales operativos y costes variables de energía para situar nuestro modelo en la matriz del mercado."""

code_sensibilidad = """# =====================================================================
# ANÁLISIS DE SENSIBILIDAD — TARIFA ELÉCTRICO
# Variamos consumo y precio de energía para mostrar rango real
# =====================================================================

import pandas as pd
import itertools

consumos = [1.10, 1.35, 1.80]       # kWh/km: ideal, operativo, pesimista
precios  = [0.08, 0.22, 0.45]       # €/kWh: nocturno, industrial, público
KM_ANUALES_REF = 110000

resultados = []
for c, p in itertools.product(consumos, precios):
    coste_energia = c * p
    fixed_total = sum(fixed_costs_electric.values())  # ya con infra carga corregida
    variable_total = coste_energia + 0.110  # mantenimiento sin AdBlue
    tarifa = (fixed_total / KM_ANUALES_REF) + variable_total
    resultados.append({
        "Consumo (kWh/km)": c,
        "Precio (€/kWh)": p,
        "Energía (€/km)": round(coste_energia, 3),
        "Tarifa (€/km)": round(tarifa, 4)
    })

df_sens = pd.DataFrame(resultados)
print("=== ANÁLISIS DE SENSIBILIDAD — TARIFA ELÉCTRICO ===")
print(df_sens.to_string(index=False))
print(f"\\nReferencia diésel (ajustada): 1.5684 €/km")
print(f"Rango eléctrico integral:   {df_sens['Tarifa (€/km)'].min():.4f} — {df_sens['Tarifa (€/km)'].max():.4f} €/km")
"""

md_comparacion = """### ⚖️ Matriz Comparativa Final: Diésel vs Eléctrico (Escenarios Centrales)
Resumen consolidado para incorporar a la presentación académica del TFM."""

code_comparacion = """# =====================================================================
# TABLA COMPARATIVA FINAL — DIÉSEL vs ELÉCTRICO (Escenario Central)
# =====================================================================

# Re-calcular los fijos y variables del diésel del primer bloque (corregido adblue)
fixed_diesel = 62500 + 19500 + 4500 + 14500 + 2000
var_diesel = 0.460 + 0.165 + 0.007
rate_diesel = (fixed_diesel / KM_ANUALES_REF) + var_diesel

# Valores electrico escenario seleccionado
fixed_elec = sum(fixed_costs_electric.values())
var_elec = coste_energia_km + 0.110
rate_elec = (fixed_elec / KM_ANUALES_REF) + var_elec

comparativa = {
    "Partida": [
        "Personal y dietas",
        "Amortización vehículo",
        "Seguros y visados",
        "Infraestructura carga",
        "Costes indirectos",
        "Fiscalidad y otros",
        "TOTAL FIJOS ANUALES",
        "",
        "Energía / Combustible (€/km)",
        "Mantenimiento y neumáticos (€/km)",
        "AdBlue / Aditivos (€/km)",
        "TOTAL VARIABLES (€/km)",
        "",
        "TARIFA TÉCNICA (€/km)",
        "Diferencia vs diésel"
    ],
    "Diésel 44t": [
        "62,500 €",
        "19,500 €",
        "4,500 €",
        "0 €",
        "14,500 €",
        "2,000 €",
        f"{fixed_diesel:,.0f} €",
        "",
        "0.460 €",
        "0.165 €",
        "0.007 €",
        f"{var_diesel:.3f} €",
        "",
        f"{rate_diesel:.4f} €/km",
        "BASE"
    ],
    "Eléctrico 44t": [
        f"{fixed_costs_electric['personal_y_dietas']:,.0f} €",
        f"{fixed_costs_electric['amortizacion_vehiculo']:,.0f} €",
        f"{fixed_costs_electric['seguros_y_visados']:,.0f} €",
        f"{fixed_costs_electric['infraestructura_carga']:,.0f} €",
        f"{fixed_costs_electric['costes_indirectos']:,.0f} €",
        f"{fixed_costs_electric['fiscalidad_y_otros']:,.0f} €",
        f"{fixed_elec:,.0f} €",
        "",
        f"{coste_energia_km:.3f} €",
        f"{variable_costs_electric['mantenimiento_y_tires']:.3f} €",
        f"{variable_costs_electric['adblue_y_aditivos']:.3f} €",
        f"{var_elec:.3f} €",
        "",
        f"{rate_elec:.4f} €/km",
        f"{(rate_elec - rate_diesel):+.4f} €/km ({(rate_elec/rate_diesel - 1)*100:+.2f}%)"
    ]
}

df_comp = pd.DataFrame(comparativa)
from IPython.display import display, Markdown
display(Markdown(df_comp.to_markdown(index=False)))
"""

new_cells.append(new_markdown_cell(md_sensibilidad))
new_cells.append(new_code_cell(code_sensibilidad))
new_cells.append(new_markdown_cell(md_comparacion))
new_cells.append(new_code_cell(code_comparacion))

# Finalmente añadir la ultima celda si es bibliografía
if cell.cell_type == 'markdown' and 'Bibliografía' in nb.cells[-1].source:
    new_cells.append(nb.cells[-1])

nb.cells = new_cells

with open(nb_path, "w", encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook modificado con éxito.")
