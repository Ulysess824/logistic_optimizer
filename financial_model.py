"""
financial_model.py
──────────────────
Motor de cálculo financiero para la inversión en flota de 44t.
Sigue estándares MITMA y ofrece análisis TCO, VAN, TIR, Payback y Cash Flow.
Incluye impacto fiscal (IS) el impacto contable (IFRS 16).
"""

import numpy as np
import numpy_financial as npf
from typing import Dict, Any

class FleetInvestmentModel:
    def __init__(self, 
                 vehicle_price: float = 145_000.0,
                 km_annual: float = 120_000.0,
                 horizon_years: int = 5,
                 wacc: float = 0.08,
                 residual_pct: float = 0.20, # Valor ajustado según petición (20%)
                 driver_annual_cost: float = 42_000.0 * 1.04, # +4% MITMA 44t
                 fuel_eur_km: float = 0.462 * 1.078,  # +7.8% MITMA 44t
                 maintenance_eur_km: float = 0.09,
                 insurance_annual: float = 3_500.0,
                 itv_taxes_annual: float = 800.0,
                 tax_rate: float = 0.25): # Gran Empresa 25%
        
        self.params = {
            "vehicle_price": vehicle_price,
            "km_annual": km_annual,
            "horizon_years": horizon_years,
            "wacc": wacc,
            "residual_pct": residual_pct,
            "driver_annual_cost": driver_annual_cost,
            "fuel_eur_km": fuel_eur_km,
            "maintenance_eur_km": maintenance_eur_km,
            "insurance_annual": insurance_annual,
            "itv_taxes_annual": itv_taxes_annual,
            "tax_rate": tax_rate
        }

    def _get_annual_operating_costs(self) -> float:
        """Calcula los costes operativos variables y fijos anuales."""
        variable = (self.params["fuel_eur_km"] + self.params["maintenance_eur_km"]) * self.params["km_annual"]
        fixed = self.params["driver_annual_cost"] + self.params["insurance_annual"] + self.params["itv_taxes_annual"]
        return variable + fixed
        
    def _calculate_payback(self, cash_flows: list[float], discount_rate: float = 0.0) -> float:
        """Calcula el Payback descontado usando una tarifa de mercado de 1.70 €/km."""
        market_revenue = 1.70 * self.params["km_annual"]
        cumulative = 0.0
        
        for i, cf in enumerate(cash_flows):
            if i == 0:
                cumulative += cf
            else:
                net_flow = cf + market_revenue
                discounted_flow = net_flow / ((1 + discount_rate) ** i)
                cumulative += discounted_flow
            
            if cumulative >= 0:
                prev_cumulative = cumulative - discounted_flow
                fraction = abs(prev_cumulative) / discounted_flow if discounted_flow != 0 else 0
                return (i - 1) + fraction
        return float('inf')

    def analyze_purchase(self) -> Dict[str, Any]:
        """Análisis de modalidad COMPRA DIRECTA."""
        opex_annual = self._get_annual_operating_costs()
        invest_0 = self.params["vehicle_price"]
        residual = invest_0 * self.params["residual_pct"]
        t = self.params["tax_rate"]
        
        annual_depreciation = (invest_0 - residual) / self.params["horizon_years"]
        
        cash_flows = [-invest_0]
        cf_after_tax = [-invest_0]
        tco_total = invest_0 - residual + (opex_annual * self.params["horizon_years"])
        
        for year in range(1, self.params["horizon_years"] + 1):
            cf = -opex_annual
            tax_shield = (opex_annual + annual_depreciation) * t
            cf_at = cf + tax_shield
            
            if year == self.params["horizon_years"]:
                cf += residual
                cf_at += residual
                
            cash_flows.append(cf)
            cf_after_tax.append(cf_at)
            
        van = npf.npv(self.params["wacc"], cf_after_tax)
        payback = self._calculate_payback(cash_flows, self.params["wacc"])
        
        return {
            "modality": "Compra",
            "cash_flows": cash_flows,
            "cash_flows_after_tax": cf_after_tax,
            "van_after_tax": van,
            "payback_years": payback,
            "tco_total": tco_total,
            "tco_km": tco_total / (self.params["km_annual"] * self.params["horizon_years"]),
            "initial_disbursement": invest_0,
            "ifrs_balance_impact": "On-Balance (Activo Fijo)",
            "tax_shield_annual": (opex_annual + annual_depreciation) * t
        }

    def analyze_leasing(self, down_payment_pct: float = 0.15, tae: float = 0.05) -> Dict[str, Any]:
        """Análisis de modalidad LEASING FINANCIERO."""
        price = self.params["vehicle_price"]
        down_payment = price * down_payment_pct
        financed_amount = price - down_payment
        months = self.params["horizon_years"] * 12
        monthly_rate = (1 + tae)**(1/12) - 1
        t = self.params["tax_rate"]
        
        monthly_fee = (financed_amount * monthly_rate) / (1 - (1 + monthly_rate)**(-months))
        annual_fee = monthly_fee * 12
        
        opex_annual = self._get_annual_operating_costs()
        residual = price * 0.01
        annual_depreciation = (price - residual) / self.params["horizon_years"]
        
        cash_flows = [-down_payment]
        cf_after_tax = [-down_payment]
        
        tco_total = (opex_annual * self.params["horizon_years"]) + down_payment + (annual_fee * self.params["horizon_years"]) + residual - (price * self.params["residual_pct"])
        
        remaining_principal = financed_amount
        for year in range(1, self.params["horizon_years"] + 1):
            
            # Aproximación del interés anual usando el principal restante
            interest_annual = remaining_principal * ((1+tae) - 1)
            principal_payment = annual_fee - interest_annual
            remaining_principal -= principal_payment
            
            tax_shield = (opex_annual + annual_depreciation + interest_annual) * t
            
            cf = -opex_annual - annual_fee
            cf_at = cf + tax_shield
            
            if year == self.params["horizon_years"]:
                cf -= residual
                cf += price * self.params["residual_pct"]
                
                cf_at -= residual
                cf_at += price * self.params["residual_pct"]
                
            cash_flows.append(cf)
            cf_after_tax.append(cf_at)
            
        van = npf.npv(self.params["wacc"], cf_after_tax)
        payback = self._calculate_payback(cash_flows, self.params["wacc"])
            
        return {
            "modality": "Leasing",
            "cash_flows": cash_flows,
            "cash_flows_after_tax": cf_after_tax,
            "van_after_tax": van,
            "monthly_fee": monthly_fee,
            "payback_years": payback,
            "tco_total": tco_total,
            "tco_km": tco_total / (self.params["km_annual"] * self.params["horizon_years"]),
            "initial_disbursement": down_payment,
            "ifrs_balance_impact": "On-Balance (Right of Use Asset + Lease Liability)"
        }

    def analyze_renting(self, monthly_rent_fee: float = 3_350.0) -> Dict[str, Any]:
        """Análisis de modalidad RENTING OPERATIVO (Full Service)."""
        rent_variable_costs = self.params["fuel_eur_km"] * self.params["km_annual"]
        rent_fixed_costs = self.params["driver_annual_cost"]
        t = self.params["tax_rate"]
        
        annual_rent_payment = monthly_rent_fee * 12
        total_annual_opex = rent_variable_costs + rent_fixed_costs + annual_rent_payment
        
        cash_flows = [0.0]
        cf_after_tax = [0.0]
        
        for year in range(1, self.params["horizon_years"] + 1):
            cf = -total_annual_opex
            tax_shield = total_annual_opex * t
            cf_at = cf + tax_shield
            
            cash_flows.append(cf)
            cf_after_tax.append(cf_at)
            
        van = npf.npv(self.params["wacc"], cf_after_tax)
        payback = self._calculate_payback(cash_flows, self.params["wacc"])
        tco_total = total_annual_opex * self.params["horizon_years"]
        
        return {
            "modality": "Renting",
            "cash_flows": cash_flows,
            "cash_flows_after_tax": cf_after_tax,
            "van_after_tax": van,
            "payback_years": payback,
            "monthly_rent_only": monthly_rent_fee,
            "tco_total": tco_total,
            "tco_km": tco_total / (self.params["km_annual"] * self.params["horizon_years"]),
            "initial_disbursement": 0.0,
            "ifrs_balance_impact": "On-Balance (IFRS 16 > 12 Meses)"
        }

    def get_indifference_point(self, renting_fee: float = 3_350.0) -> Dict[str, float]:
        """Calcula el kilometraje anual donde Compra y Renting se igualan en coste."""
        invest_0 = self.params["vehicle_price"]
        residual = invest_0 * self.params["residual_pct"]
        annual_depreciation = (invest_0 - residual) / self.params["horizon_years"]
        fixed_compra = annual_depreciation + self.params["insurance_annual"] + self.params["itv_taxes_annual"] + self.params["driver_annual_cost"]
        var_compra = self.params["fuel_eur_km"] + self.params["maintenance_eur_km"]
        
        fixed_renting = (renting_fee * 12) + self.params["driver_annual_cost"]
        var_renting = self.params["fuel_eur_km"]
        
        if (var_compra - var_renting) == 0: return {"km_indiff": 0.0}
        
        km_indiff = (fixed_renting - fixed_compra) / (var_compra - var_renting)
        
        return {
            "km_indifference_compra_renting": km_indiff
        }

    def run_sensitivity(self, test_variable: str, range_pct: list[float]) -> list[Dict[str, Any]]:
        """Corre análisis de sensibilidad iterando una variable en porcentajes (+/-)."""
        original_val = self.params[test_variable]
        results = []
        for pct in range_pct:
            self.params[test_variable] = original_val * (1 + pct)
            res = {
                "pct_change": pct,
                "value": self.params[test_variable],
                "compra": self.analyze_purchase()["tco_km"],
                "leasing": self.analyze_leasing()["tco_km"],
                "renting": self.analyze_renting()["tco_km"]
            }
            results.append(res)
        
        self.params[test_variable] = original_val # Restore
        return results

if __name__ == "__main__":
    # Script de prueba simple con datos sintéticos
    model = FleetInvestmentModel()
    results = {
        "Compra": model.analyze_purchase(),
        "Leasing": model.analyze_leasing(),
        "Renting": model.analyze_renting()
    }
    
    for mod, data in results.items():
        print(f"Modality: {mod}")
        print(f"  TCO Total (5yr): {data['tco_total']:_,.2f} €")
        print(f"  TCO/km: {data['tco_km']:.4f} €/km")
        print(f"  Payback: {data['payback_years']:.2f} años")
        print("-" * 30)
