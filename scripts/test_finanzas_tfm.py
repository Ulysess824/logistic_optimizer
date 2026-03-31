import os
import sys
from pathlib import Path

# Asegurar que podemos importar desde el núcleo
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from logistic_core.utils.financial_analyzer import FinancialAnalyzer

def main():
    analyzer = FinancialAnalyzer(
        days_per_year=250, 
        software_capex=25000, 
        truck_unit_cost=125000 # Camión + Semi + Equipamiento
    )

    # DATOS DE PRUEBA (Caso Realista Smurfit Westrock)
    # ---------------------------------------------
    km_diarios_base = 12500    # Escenario sin optimización (mucho retorno vacío)
    km_diarios_opt  = 10125    # Escenario optimizado (ahorro del 19%)
    tarifa_externa  = 1.35     # Lo que pagamos hoy a transportistas externos (€/km)
    coste_tco_propio = 1.05    # Lo que nos cuesta operar si compramos la flota (€/km)
    total_rutas_activas = 30   # Necesidad de flota según el simulador

    # Analizar
    bc = analyzer.generate_business_case(
        km_diarios_base, 
        km_diarios_opt, 
        coste_tco_propio, 
        tarifa_externa, 
        total_rutas_activas
    )

    # Mostrar Resultados para el TFM
    print("="*60)
    print("      REPORTE FINANCIERO: LOGISTICS OPTIMIZER (TFM IE)      ")
    print("="*60)
    print(f"Días operados / año: {analyzer.days_per_year}")
    print(f"Kms salvados / año:  {bc['operational']['annual_km_saved']:,} km")
    print(f"Flota necesaria:     {bc['operational']['fleet_size_required']} camiones")
    print("-" * 60)

    # Escenario A: Asset-Light
    light = bc['asset_light']
    print(f"ESTRATEGIA A: {light['desc']}")
    print(f"  > Inversión Inicial (Software/IA): {light['capex_eur']:,} €")
    print(f"  > Ahorro Anual Neto:               {light['annual_savings_eur']:,.0f} €")
    print(f"  > ROI Proyectado (3 años):         {light['roi_3y_pct']:,.1f} %")
    print(f"  > Recuperación (Payback):         {light['payback_months']:.1f} meses")
    print("-" * 60)

    # Escenario B: Asset-Heavy
    heavy = bc['asset_heavy']
    print(f"ESTRATEGIA B: {heavy['desc']}")
    print(f"  > Inversión Inicial (Flota + Soft): {heavy['capex_eur']:,.0f} €")
    print(f"  > Ahorro Anual Neto (Margen+Km):    {heavy['annual_savings_eur']:,.0f} €")
    print(f"  > ROI Proyectado (5 años):         {heavy['roi_5y_pct']:,.1f} %")
    print(f"  > Recuperación (Payback):         {heavy['payback_months']:.1f} meses")
    print("="*60)

    # Análisis de Sensibilidad (Combustible)
    sens = analyzer.fuel_sensitivity_analysis(km_diarios_opt, coste_tco_propio)
    print("\nANÁLISIS DE SENSIBILIDAD (OPEX FLOTA PROPIA):")
    print(f"{'Variación Combustible':<25} | {'Coste Anual Proyectado':<25} | {'Impacto ROI'}")
    print("-" * 75)
    for s in sens:
        sign = "+" if s['variation_pct'] > 0 else ""
        print(f"Fuel {sign}{s['variation_pct']:>3}% {' ':<15} | {s['new_annual_cost_eur']:,.0f} € {' ':<13} | {s['impact_eur']:,.0f} €")

if __name__ == "__main__":
    main()
