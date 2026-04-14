import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

# Celdas de markdown y código
md_1 = """# Análisis Financiero de Inversión en Flota (Logistics Optimizer v5.3)

Este notebook contiene el análisis riguroso de modalidades de adquisición de flota 
(**Compra Directa**, **Leasing Financiero** y **Renting Operativo**) para conjuntos 
articulados de 44 toneladas, siguiendo las directrices del **Observatorio de Costes 
del Transporte de Mercancías por Carretera del MITMA (2025/2026)**.

## Parámetros Base 
- **MMA**: 44 toneladas (Semirremolque + Tractora)
- **Kilometraje Anual Base**: 120_000 km
- **Escenario Fiscal**: Gran Empresa (Impuesto de Sociedades 25%)
- **Tratamiento Contable**: IFRS 16 (NIC 17)
"""

code_1 = """import sys
import os
import pandas as pd
from IPython.display import display, Markdown

# Añadimos el path root
sys.path.append(os.path.abspath('..'))
from analisis_inversion import generar_analisis

# Ejecutamos el motor
df_tabla, punto_indiferencia, fig_tco, fig_cf = generar_analisis()
"""

md_2 = """## 1. Evolución del TCO Acumulado (7 años)
El siguiente gráfico muestra la acumulación del TCO (Coste Total de la Propiedad).
Observamos el punto de inflexión donde la alta intensidad de capital inicial de la compra y el leasing se amortiza por sus menores costes fijos a medio plazo comparados con el Renting.
"""

code_2 = """fig_tco.show()"""

md_3 = """## 2. Flujo de Caja Diferencial (Después de Impuestos IS 25%)
Este gráfico detalla el esfuerzo financiero año tras año. Las cuotas del Renting operan como escudo fiscal al 100%, mientras que en la Compra se aprovecha la amortización contable del activo fijo.
"""

code_3 = """fig_cf.show()"""

md_4 = """## 3. Matriz Comparativa y Recomendación Académica
Tabla final con impacto en balance, EBITDA y KPIs financieros (VAN, Payback, TCO/km).
"""

code_4 = """display(Markdown(df_tabla.to_markdown(index=False)))

print(f"\\n✅ PUNTO DE INDIFERENCIA:\\nEl volumen a partir del cual 'Compra Operativa' es financieramente más eficiente que 'Renting Operativo' se sitúa en: {punto_indiferencia['km_indifference_compra_renting']:_.0f} km/año")
"""

nb['cells'] = [
    nbf.v4.new_markdown_cell(md_1),
    nbf.v4.new_code_cell(code_1),
    nbf.v4.new_markdown_cell(md_2),
    nbf.v4.new_code_cell(code_2),
    nbf.v4.new_markdown_cell(md_3),
    nbf.v4.new_code_cell(code_3),
    nbf.v4.new_markdown_cell(md_4),
    nbf.v4.new_code_cell(code_4)
]

os.makedirs("notebooks", exist_ok=True)
with open("notebooks/00_Analisis_Financiero_TFM_v53.ipynb", "w", encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook 00_Analisis_Financiero_TFM_v53.ipynb creado con éxito.")
