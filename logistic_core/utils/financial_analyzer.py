"""
financial_analyzer.py
──────────────────────
Motor de Inteligencia Financiera Avanzada para el TFM del IE Business School.
Calcula el Business Case (ROI, Payback) y realiza análisis de sensibilidad
evaluando los escenarios Asset-Light (Subcontratar) y Asset-Heavy (Comprar flota).
"""
import math
import logging
from logistic_core.utils.fleet_estimator import FleetCapexEstimator
from logistic_core.config import (
    CAPEX_TRUCK_UNIT_COST, DEFAULT_CYCLE_TIME_DAYS, 
    DAILY_TRUCK_OUTBOUND, DEFAULT_FLEET_BUFFER,
    SOFTWARE_TMS_CAPEX, INTERNAL_OPERATIONAL_TCO_RATE,
    EXTERNAL_PROVIDER_RATE_PER_KM
)

logger = logging.getLogger(__name__)

class FinancialAnalyzer:
    def __init__(self, days_per_year=250, software_capex=None, 
                 truck_unit_cost=None, cycle_time_days=None, 
                 daily_dispatch=None, fleet_buffer=None):
        """
        :param days_per_year: Días operativos anuales para proyecciones (def: 250).
        :param software_capex: Inversión en software/TMS y consultoría en Euros.
        """
        self.days_per_year = days_per_year
        self.software_capex = software_capex or SOFTWARE_TMS_CAPEX
        
        # Parámetros para Ley de Little
        self.truck_unit_cost = truck_unit_cost or CAPEX_TRUCK_UNIT_COST
        self.cycle_time_days = cycle_time_days or DEFAULT_CYCLE_TIME_DAYS
        self.daily_dispatch = daily_dispatch or DAILY_TRUCK_OUTBOUND
        self.fleet_buffer = fleet_buffer or DEFAULT_FLEET_BUFFER
        
        self.fleet_estimator = FleetCapexEstimator(
            daily_dispatch_rate=self.daily_dispatch,
            unit_truck_cost=self.truck_unit_cost,
            utilization_buffer=self.fleet_buffer
        )

    def calculate_roi(self, capex, annual_savings, horizon_years=3):
        """
        Calcula el Retorno de la Inversión (ROI) a N años.
        ROI = (Beneficio Neto - Inversión) / Inversión * 100
        """
        if capex <= 0:
            return float('inf')
        total_benefit = annual_savings * horizon_years
        roi = ((total_benefit - capex) / capex) * 100.0
        return roi

    def calculate_payback_months(self, capex, annual_savings):
        """
        Calcula el periodo de recuperación de la inversión (Payback) en meses.
        """
        if annual_savings <= 0:
            return float('inf')
        monthly_savings = annual_savings / 12.0
        return capex / monthly_savings

    def generate_business_case(self, daily_km_baseline, daily_km_optimized,
                                internal_eur_per_km=None, external_eur_per_km=None,
                                optimized_routes_count=None):
        """
        Genera el Business Case completo comparando la estrategia Asset-Light vs Asset-Heavy.
        """
        int_rate = internal_eur_per_km or INTERNAL_OPERATIONAL_TCO_RATE
        ext_rate = external_eur_per_km or EXTERNAL_PROVIDER_RATE_PER_KM
        
        # --- Cálculo base anualizado ---
        annual_km_baseline = daily_km_baseline * self.days_per_year
        annual_km_opt = daily_km_optimized * self.days_per_year
        km_saved_per_year = annual_km_baseline - annual_km_opt

        # 1. Coste As-Is (Todo subcontratado tarifa externa)
        cost_baseline_annual = annual_km_baseline * ext_rate

        # 2. Escenario Asset-Light (Software + Subcontratar rutas óptimas)
        # Inversión: Solo Software
        capex_light = self.software_capex
        cost_light_annual = annual_km_opt * ext_rate
        savings_light_annual = cost_baseline_annual - cost_light_annual

        roi_light = self.calculate_roi(capex_light, savings_light_annual, horizon_years=3)
        payback_light = self.calculate_payback_months(capex_light, savings_light_annual)

        # 3. Escenario Asset-Heavy (Software + Comprar camiones = Operar interno)
        # Inversión: Software + Flota (Ley de Little)
        resumen_fleet = self.fleet_estimator.generate_investment_summary(self.cycle_time_days)
        capex_heavy = self.software_capex + resumen_fleet['total_capex_investment']
        
        cost_heavy_annual = annual_km_opt * int_rate
        savings_heavy_annual = cost_baseline_annual - cost_heavy_annual
        
        roi_heavy = self.calculate_roi(capex_heavy, savings_heavy_annual, horizon_years=5) # ROI a 5 años por la amortización de flota
        payback_heavy = self.calculate_payback_months(capex_heavy, savings_heavy_annual)

        return {
            "operational": {
                "annual_km_saved": km_saved_per_year,
                "fleet_size_required": resumen_fleet['final_required_fleet'],
                "theoretical_fleet": resumen_fleet['theoretical_fleet_base'],
                "cycle_time": self.cycle_time_days,
                "daily_dispatch": self.daily_dispatch
            },
            "asset_light": {
                "capex_eur": capex_light,
                "annual_savings_eur": savings_light_annual,
                "roi_3y_pct": roi_light,
                "payback_months": payback_light,
                "desc": "Subcontratar Flota (Software Only)"
            },
            "asset_heavy": {
                "capex_eur": capex_heavy,
                "fleet_capex": resumen_fleet['total_capex_investment'],
                "annual_savings_eur": savings_heavy_annual,
                "roi_5y_pct": roi_heavy,
                "payback_months": payback_heavy,
                "desc": "Flota Propia (+ Margen Absorvido)"
            }
        }

    def fuel_sensitivity_analysis(self, daily_km_optimized, internal_eur_per_km, base_fuel_pct=0.45):
        """
        Calcula cómo impactan las variaciones del precio del combustible en el OPEX de la flota propia.
        base_fuel_pct: porcentaje que representa el combustible dentro de internal_eur_per_km (aprox 45%).
        """
        scenarios = [-15, -5, 5, 15] # Variaciones de precio del combustible en %
        annual_km = daily_km_optimized * self.days_per_year
        base_annual_cost = annual_km * internal_eur_per_km
        base_fuel_cost = base_annual_cost * base_fuel_pct
        base_other_cost = base_annual_cost - base_fuel_cost

        results = []
        for var in scenarios:
            new_fuel_cost = base_fuel_cost * (1 + (var / 100.0))
            new_total_cost = base_other_cost + new_fuel_cost
            variation_eur = new_total_cost - base_annual_cost
            
            results.append({
                "variation_pct": var,
                "new_annual_cost_eur": new_total_cost,
                "impact_eur": variation_eur
            })
            
        return results

    def calculate_avoided_sunk_cost(self, empty_km_saved, tco_rate):
        """
        Calcula el retorno monetario de los kilómetros en vacío evitados.
        Este coste se iba a asumir de todos modos (costo hundido del retorno),
        por lo que evitarlo se traduce directamente en ganancia neta operativa.
        """
        if empty_km_saved <= 0:
            return 0.0
        return empty_km_saved * tco_rate

if __name__ == "__main__":
    # Script de prueba rápida para validar la lógica (Ejemplo TFM)
    analyzer = FinancialAnalyzer()
    
    # Asumimos que antes hacían 5,000 km al día, y ahora 4,000 km.
    # Tarifa externa (mercado) = 1.35 €/km. Coste interno TCO = 1.05 €/km.
    # Necesitamos 8 camiones propios si fuéramos Asset-Heavy.
    bc = analyzer.generate_business_case(5000, 4000, 1.05, 1.35, 8)
    
    # Sensibilidad
    sens = analyzer.fuel_sensitivity_analysis(4000, 1.05)
    
    print("--- PRUEBA DEL MOTOR FINANCIERO ---")
    print(f"Asset-Light ROI (3y): {bc['asset_light']['roi_3y_pct']:.1f}% | Payback: {bc['asset_light']['payback_months']:.1f} meses")
    print(f"Asset-Heavy ROI (5y): {bc['asset_heavy']['roi_5y_pct']:.1f}% | Payback: {bc['asset_heavy']['payback_months']:.1f} meses")
    print("Sensibilidad Combustible:")
    for s in sens:
        sign = "+" if s['variation_pct'] > 0 else ""
        print(f"  Combustible {sign}{s['variation_pct']}% -> Impacto OPEX: {s['impact_eur']:,.0f} €/año")
