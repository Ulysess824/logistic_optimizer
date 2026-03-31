import logging
from typing import Dict, Any
from logistic_core.config import (
    CAPEX_TRUCK_UNIT_COST,
    TCO_FIXED_COSTS_ANNUAL,
    TCO_VARIABLE_COSTS_KM,
    TCO_ANNUAL_KM_PER_TRUCK,
    LEASING_MONTHLY_FEE_COIL_TRUCK,
    LEASING_TERM_YEARS,
    INVESTMENT_DISCOUNT_RATE,
    PURCHASE_RESALE_VALUE_PCT,
    PURCHASE_UPFRONT_PCT,
    ANNUAL_MAINTENANCE_SURCHARGE_SPECIALIZED
)

class LeasingInversionAnalyst:
    """
    Analista Financiero para evaluación de inversión en flota (Leasing vs Purchase).
    Especializado en activos de alta intensidad (Transporte de Bobinas).
    """

    def __init__(self):
        self.wacc = INVESTMENT_DISCOUNT_RATE
        self.term_years = LEASING_TERM_YEARS
        self.truck_cost = CAPEX_TRUCK_UNIT_COST
        
        # Mantenimiento anual estimado (Compra)
        base_maint = TCO_VARIABLE_COSTS_KM["mantenimiento_reparacion"] * TCO_ANNUAL_KM_PER_TRUCK
        self.annual_maint_buy = base_maint * (1 + ANNUAL_MAINTENANCE_SURCHARGE_SPECIALIZED)
        
        # Costes fijos anuales excluyendo amortización (ya que se calcula aparte en NPV)
        self.annual_fixed_no_amort = (
            TCO_FIXED_COSTS_ANNUAL["personal_y_dietas"] +
            TCO_FIXED_COSTS_ANNUAL["seguros_y_visados"] +
            TCO_FIXED_COSTS_ANNUAL["costes_indirectos_adm"] +
            TCO_FIXED_COSTS_ANNUAL["fiscalidad_y_otros"]
        )

    def calculate_npv(self, cash_flows: list) -> float:
        """Calcula el Valor Presente Neto de una serie de flujos de caja."""
        npv = 0
        for t, cf in enumerate(cash_flows):
            npv += cf / ((1 + self.wacc) ** t)
        return round(npv, 2)

    def analyze_investment(self) -> Dict[str, Any]:
        """
        Compara financieramente la Compra vs Leasing Full-Service.
        """
        # --- ESCENARIO COMPRA ---
        # Año 0: Desembolso inicial (Entrada + Software/Setup estimado)
        buy_flows = [-self.truck_cost * PURCHASE_UPFRONT_PCT]
        
        # Años 1 a N: Flujos operativos (Mantenimiento + Seguros + Otros)
        # Nota: Simplificamos asumiendo que el personal es igual en ambos.
        # Nos centramos en los diferenciales de propiedad.
        annual_ownership_cost = self.annual_maint_buy + TCO_FIXED_COSTS_ANNUAL["seguros_y_visados"]
        
        for t in range(1, self.term_years + 1):
            flow = -annual_ownership_cost
            if t == self.term_years:
                # Recuperación de valor residual al final
                flow += self.truck_cost * PURCHASE_RESALE_VALUE_PCT
            buy_flows.append(flow)
        
        npv_buy = self.calculate_npv(buy_flows)

        # --- ESCENARIO LEASING FULL-SERVICE ---
        # Año 0: Generalmente 0 o primera cuota
        lease_flows = [0]
        
        # Cuota incluye mantenimiento y gestión. El seguro puede ser aparte o incluido.
        # Asumimos Full-Service típico donde mantenimiento está incluido.
        annual_lease_cost = LEASING_MONTHLY_FEE_COIL_TRUCK * 12
        
        for t in range(1, self.term_years + 1):
            lease_flows.append(-annual_lease_cost)
            
        npv_lease = self.calculate_npv(lease_flows)

        # --- COMPARATIVA ---
        better_option = "LEASING" if npv_lease > npv_buy else "COMPRA"
        savings_abs = abs(npv_lease - npv_buy)

        return {
            "npv_buy": npv_buy,
            "npv_lease": npv_lease,
            "term_years": self.term_years,
            "recommendation": better_option,
            "saving_npv": savings_abs,
            "annual_lease_fee": annual_lease_cost,
            "setup_logic": "Asset Specificity: HIGH (Porta-bobinas)"
        }

    def print_investor_report(self):
        """Imprime un reporte con estilo de inversor profesional."""
        results = self.analyze_investment()
        
        print("\n" + "="*50)
        print(" ESTRATEGIA DE INVERSIÓN: FLOTA PORTA-BOBINAS")
        print("="*50)
        print(f"Horizonte Temporal: {results['term_years']} años")
        print(f"Tasa de Descuento (WACC): {self.wacc*100}%")
        print("-" * 50)
        print(f"VPN Escenario COMPRA:    {results['npv_buy']:,.2f} €")
        print(f"VPN Escenario LEASING:   {results['npv_lease']:,.2f} €")
        print("-" * 50)
        
        rec = results['recommendation']
        color = "\033[92m" if rec == "LEASING" else "\033[94m" # Simple color logic for terminal
        print(f"RECOMENDACIÓN: {rec}")
        print(f"Diferencial de Valor: {results['saving_npv']:,.2f} €")
        print("-" * 50)
        print("Tesis de Inversión:")
        if rec == "LEASING":
            print("=> El leasing preserva el capital de trabajo y mitiga el riesgo")
            print("   de mantenimiento en activos de alta intensidad (bobinas).")
        else:
            print("=> La propiedad es preferible debido al bajo coste de capital")
            print("   y la retención del valor residual del activo.")
        print("="*50 + "\n")

if __name__ == "__main__":
    analyst = LeasingInversionAnalyst()
    analyst.print_investor_report()
