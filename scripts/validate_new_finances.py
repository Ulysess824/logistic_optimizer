import sys
import os

# Asegurar que podemos importar los módulos del core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logistic_core.utils.fleet_estimator import FleetCapexEstimator
from logistic_core.config import (
    CAPEX_TRUCK_UNIT_COST, DEFAULT_CYCLE_TIME_DAYS, 
    DAILY_TRUCK_OUTBOUND, DEFAULT_FLEET_BUFFER,
    SOFTWARE_TMS_CAPEX, INTERNAL_OPERATIONAL_TCO_RATE,
    EXTERNAL_PROVIDER_RATE_PER_KM
)

def test_new_financial_logic():
    print("=== TEST DE NUEVA LÓGICA FINANCIERA (RUTAS OPTIMIZADAS) ===\n")
    
    # 1. Parámetros Anuales y CAPEX
    days_per_year = 250
    software_capex = 25000
    
    # Inversión de Flota (Ley de Little para 38 rutas diarias)
    fleet_estimator = FleetCapexEstimator(
        daily_dispatch_rate=38,
        unit_truck_cost=CAPEX_TRUCK_UNIT_COST,
        utilization_buffer=DEFAULT_FLEET_BUFFER
    )
    resumen_fleet = fleet_estimator.generate_investment_summary(DEFAULT_CYCLE_TIME_DAYS)
    capex_fleet = resumen_fleet['total_capex_investment']
    
    # CAPEX Total
    capex_light = software_capex
    capex_heavy = software_capex + capex_fleet
    
    # 2. Datos Sintéticos (Diarios) extraídos de un escenario tipo
    daily_ahorro_sistemico = 8080.0  # (Tarifa Externa - Tarifa Interna) * KM Linehaul
    daily_ahorro_vacios = 3500.0     # (KM Vacíos Evitados) * Tarifa Interna
    
    print(f"--- VARIABLES DIARIAS DE ENTRADA ---")
    print(f"Ahorro Sistémico (Backhauling): {daily_ahorro_sistemico:,.2f} €/día")
    print(f"Ahorro Físico (Vacíos):         {daily_ahorro_vacios:,.2f} €/día")
    print(f"------------------------------------\n")
    
    # 3. Escenario Asset-Light (Subcontratar)
    # Ahorro Light = (KM Vacíos Evitados) * Tarifa Externa
    km_vacios_evitados = daily_ahorro_vacios / INTERNAL_OPERATIONAL_TCO_RATE
    daily_savings_light = km_vacios_evitados * EXTERNAL_PROVIDER_RATE_PER_KM
    annual_savings_light = daily_savings_light * days_per_year
    
    roi_light = ((annual_savings_light * 3 - capex_light) / capex_light) * 100
    payback_light = capex_light / (annual_savings_light / 12)
    
    # 4. Escenario Asset-Heavy (Flota Propia)
    # Ahorro Heavy = Ahorro Sistémico (margen) + Ahorro Vacíos (TCO)
    daily_savings_heavy = daily_ahorro_vacios + daily_ahorro_sistemico
    annual_savings_heavy = daily_savings_heavy * days_per_year
    
    roi_heavy = ((annual_savings_heavy * 5 - capex_heavy) / capex_heavy) * 100
    payback_heavy = capex_heavy / (annual_savings_heavy / 12)
    
    # --- RESULTADOS ---
    print(f"🏢 ESTRATEGIA A: ASSET-LIGHT (Subcontratar rutas optimizadas)")
    print(f"  CAPEX Inicial (TMS):         {capex_light:,.0f} €")
    print(f"  Ahorro Anual (Distan. Ext.): +{annual_savings_light:,.0f} €")
    print(f"  ROI (3 años):                {roi_light:,.1f} %")
    print(f"  Payback:                     {payback_light:,.1f} meses\n")

    print(f"🚚 ESTRATEGIA B: ASSET-HEAVY (Flota Propia conectada a TMS)")
    print(f"  CAPEX Total (Flota+TMS):     {capex_heavy:,.0f} €")
    print(f"  Ahorro Anual Total:          +{annual_savings_heavy:,.0f} €")
    print(f"    └ Sistémico (Margen):      +{(daily_ahorro_sistemico * days_per_year):,.0f} €")
    print(f"    └ Físico (Vacíos en TCO):  +{(daily_ahorro_vacios * days_per_year):,.0f} €")
    print(f"  ROI (5 años):                {roi_heavy:,.1f} %")
    print(f"  Payback:                     {payback_heavy:,.1f} meses")

if __name__ == "__main__":
    test_new_financial_logic()
