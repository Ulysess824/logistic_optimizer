from logistic_core.utils.financial_analyzer import FinancialAnalyzer
from logistic_core.config import FLEET_MIX_DIESEL, FLEET_MIX_EV, KMS_ANUALES_POR_CAMION

def test_tco():
    analyzer = FinancialAnalyzer()
    
    # Datos de configuración
    n_diesel = FLEET_MIX_DIESEL
    n_ev = FLEET_MIX_EV
    kms_anuales = KMS_ANUALES_POR_CAMION
    
    print("\n=======================================================")
    print("      EVALUACIÓN TCO: FLOTA MIXTA VS 100% DIÉSEL")
    print("=======================================================\n")
    print(f"Flota Diésel: {n_diesel} camiones")
    print(f"Flota Eléctrica: {n_ev} camiones")
    print(f"Kilómetros Anuales por camión: {kms_anuales:,.0f} km\n".replace(',', '_'))
    
    results = analyzer.evaluate_mixed_fleet_transition(n_diesel, n_ev, kms_anuales)
    
    baseline = results['baseline_100_diesel']
    mixed = results['mixed_fleet']
    comp = results['comparative']
    
    print("--- 1. ESCENARIO BASELINE (100% DIÉSEL) ---")
    print(f"Total Camiones: {baseline['n_trucks']}")
    print(f"CapEx Inicial: {baseline['capex']:>15,.0f} €".replace(',', '_'))
    print(f"OpEx Anual:    {baseline['opex_anual']:>15,.0f} €".replace(',', '_'))
    print(f"TCO 5 Años:    {baseline['tco_5y']:>15,.0f} €\n".replace(',', '_'))
    
    print("--- 2. ESCENARIO FLOTA MIXTA ---")
    print(f"CapEx Bruto:   {mixed['capex_bruto']:>15,.0f} €".replace(',', '_'))
    print(f"Subvenciones:  {mixed['incentivos']:>15,.0f} €".replace(',', '_'))
    print(f"CapEx Neto:    {mixed['capex_neto']:>15,.0f} €".replace(',', '_'))
    print(f"OpEx Anual:    {mixed['opex_anual']:>15,.0f} €".replace(',', '_'))
    print(f"TCO 5 Años:    {mixed['tco_5y']:>15,.0f} €\n".replace(',', '_'))
    
    print("--- 3. COMPARATIVA Y TOMA DE DECISIÓN ---")
    print(f"Sobrecoste CapEx: {comp['sobrecoste_capex_neto']:>15,.0f} €".replace(',', '_'))
    print(f"Ahorro OpEx/Año:  {comp['ahorro_opex_anual']:>15,.0f} €".replace(',', '_'))
    
    if comp['ahorro_tco_5y'] > 0:
        print(f"Ahorro en 5 Años: {comp['ahorro_tco_5y']:>15,.0f} €  ✅ VIABLE".replace(',', '_'))
    else:
        print(f"Pérdida en 5 Años: {comp['ahorro_tco_5y']:>15,.0f} € ❌ NO VIABLE".replace(',', '_'))
        
    print(f"Payback (Años):   {comp['payback_years']:>15.1f} años")
    print("=======================================================\n")

if __name__ == "__main__":
    test_tco()
