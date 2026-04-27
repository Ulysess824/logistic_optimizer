from logistic_core.utils.strategic_analyzer import StrategicAnalyzer
from logistic_core import config

# Forzamos los parámetros del dashboard para la auditoría
ana = StrategicAnalyzer(kms_anuales=130000, driver_cost=42000)
res = ana.evaluar_rentabilidad_compra('diesel', 1.5)

inv = res['flujos'][0]
flujos = res['flujos'][1:]
beneficio_total = sum(flujos) + inv

print(f"1. Inversión Inicial: {inv:,.0f} €")
print(f"2. Flujos de Caja (Años 1-5):")
for i, f in enumerate(flujos):
    print(f"   Año {i+1}: {f:,.0f} €")
print(f"3. Beneficio Neto Total (Suma - Inversión): {beneficio_total:,.0f} €")
print(f"4. Cálculo ROI: ({beneficio_total:,.0f} / {abs(inv):,.0f}) * 100 = {res['roi']}%")
