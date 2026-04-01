import numpy as np
import pandas as pd
import numpy_financial as npf
import os
import sys

# Añadir raíz del proyecto para importaciones internas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from logistic_core.utils.fleet_estimator import FleetCapexEstimator

class FleetFinancialModel:
    """
    Simulador de Inversión y Modelos de Adquisición de Flota Heavy Duty (44t).
    Compara Compra Financiada, Leasing Financiero y Renting Operativo.
    """
    
    def __init__(self, n_trucks=51, unit_price=140_000, horizon_years=5, wacc=0.09, is_rate=0.25,
                 maint_year=8_500.0, ins_year=3_200.0, tires_year=2_400.0, 
                 admin_purchase=600.0, admin_leasing=300.0, renting_fee=2_800.0,
                 loan_tae=0.055, lease_tae=0.048, residual_val_pct=0.35):
        self.n_trucks = n_trucks
        self.unit_price = unit_price
        self.horizon_years = horizon_years
        self.wacc = wacc
        self.is_rate = is_rate
        
        # Nuevas variables operativas
        self.maint_year = maint_year
        self.ins_year = ins_year
        self.tires_year = tires_year
        self.admin_purchase = admin_purchase
        self.admin_leasing = admin_leasing
        self.renting_fee = renting_fee
        
        # Tasas y residuales
        self.loan_tae = loan_tae
        self.lease_tae = lease_tae
        self.residual_val_pct = residual_val_pct
        
        self.total_investment = n_trucks * unit_price
        
        self.fleet_estimator = FleetCapexEstimator(
            daily_dispatch_rate=51, # No afecta al cálculo financiero directo de este script
            unit_truck_cost=unit_price
        )
        
    def calculate_loan_pmt(self, principal, rate_tae, years):
        """Calcula el pago mensual de un préstamo (Anualidad Francesa)."""
        monthly_rate = rate_tae / 12.0
        n_periods = years * 12
        pmt = npf.pmt(monthly_rate, n_periods, -principal)
        return pmt

    def get_loan_breakdown(self, principal, rate_tae, years):
        """Devuelve desglose anual de Capital e Intereses."""
        monthly_rate = rate_tae / 12.0
        n_periods = years * 12
        
        breakdown = []
        current_balance = principal
        
        for year in range(1, years + 1):
            year_interest = 0
            year_principal = 0
            for _ in range(12):
                interest = current_balance * monthly_rate
                pmt = self.calculate_loan_pmt(principal, rate_tae, years)
                principal_payment = pmt - interest
                year_interest += interest
                year_principal += principal_payment
                current_balance -= principal_payment
            
            breakdown.append({
                "year": year,
                "interest": year_interest,
                "principal": year_principal,
                "balance": max(0, current_balance)
            })
        return breakdown

    def analyze_purchase(self):
        """Opción 1: Compra con financiación bancaria (Down payment configurable)."""
        unit_down = self.unit_price * 0.20
        loan_principal = self.unit_price * 0.80
        
        # Amortización AEAT (16% max anual)
        linear_depr_rate = 0.16
        annual_depr = self.unit_price * linear_depr_rate
        
        loan_data = self.get_loan_breakdown(loan_principal, self.loan_tae, self.horizon_years)
        
        flows = []
        # Año 0: Invesión inicial (Entrada)
        flows.append({"year": 0, "outflow": unit_down * self.n_trucks, "tax_shield": 0, "residual": 0})
        
        for y in range(1, self.horizon_years + 1):
            # Costes Operativos dinámicos
            opex = (self.maint_year + self.ins_year + self.tires_year + self.admin_purchase) * self.n_trucks
            # Servicio deuda
            interest = loan_data[y-1]["interest"] * self.n_trucks
            principal = loan_data[y-1]["principal"] * self.n_trucks
            
            # Escudo Fiscal: (Depreciación + Intereses + Opex) * IS
            # Nota: Solo depreciamos hasta el valor contable residual
            depr_year = annual_depr * self.n_trucks if y <= 6 else 0 
            tax_shield = (depr_year + interest + opex) * self.is_rate
            
            total_outflow = opex + interest + principal
            
            # Año 5: Venta activo
            residual = 0
            if y == self.horizon_years:
                raw_residual = self.unit_price * self.residual_val_pct * self.n_trucks
                book_value = (self.unit_price - (annual_depr * self.horizon_years)) * self.n_trucks
                gain = raw_residual - book_value
                tax_on_gain = gain * self.is_rate
                residual = raw_residual - tax_on_gain # Neto de impuestos
                
            flows.append({
                "year": y, 
                "outflow": total_outflow, 
                "tax_shield": tax_shield, 
                "residual": residual
            })
            
        return flows

    def analyze_leasing(self):
        """Opción 2: Leasing Financiero (10% entrada)."""
        unit_down = self.unit_price * 0.10
        # El principal a financiar es el precio menos la entrada y el valor residual final (opción compra)
        financed_amount = self.unit_price * 0.90
        
        lease_data = self.get_loan_breakdown(financed_amount, self.lease_tae, self.horizon_years)
        
        flows = []
        flows.append({"year": 0, "outflow": unit_down * self.n_trucks, "tax_shield": 0, "residual": 0})
        
        for y in range(1, self.horizon_years + 1):
            opex = (self.maint_year + self.ins_year + self.tires_year + self.admin_leasing) * self.n_trucks
            interest = lease_data[y-1]["interest"] * self.n_trucks
            principal = lease_data[y-1]["principal"] * self.n_trucks
            
            # FISCALIDAD LEASING (Art 106 LIS): 
            # Deducimos carga financiera + principal pagado (limite 2x amort contable)
            linear_depr_limit = self.unit_price * 0.16 * 2 * self.n_trucks
            principal_deductible = min(principal, linear_depr_limit)
            
            tax_shield = (interest + principal_deductible + opex) * self.is_rate
            
            total_outflow = opex + interest + principal
            
            # Año 5: Opción de compra
            residual = 0
            if y == self.horizon_years:
                raw_residual = self.unit_price * self.residual_val_pct * self.n_trucks
                # El valor contable tras leasing acelerado es casi 0
                gain = raw_residual - 0 
                tax_on_gain = gain * self.is_rate
                residual = raw_residual - tax_on_gain
                
            flows.append({
                "year": y, 
                "outflow": total_outflow, 
                "tax_shield": tax_shield, 
                "residual": residual
            })
            
        return flows

    def analyze_renting(self):
        """Opción 3: Renting Operativo (All-Inclusive)."""
        annual_fee = self.renting_fee * 12 * self.n_trucks
        
        flows = []
        flows.append({"year": 0, "outflow": 0, "tax_shield": 0, "residual": 0})
        
        for y in range(1, self.horizon_years + 1):
            # En renting no hay otros costes operativos, ni entrada, ni residual
            tax_shield = annual_fee * self.is_rate
            flows.append({
                "year": y, 
                "outflow": annual_fee, 
                "tax_shield": tax_shield, 
                "residual": 0
            })
            
        return flows

    def get_summary_table(self):
        """Genera la comparativa de los tres modelos."""
        results = {
            "Compra Financiada": self.analyze_purchase(),
            "Leasing Financiero": self.analyze_leasing(),
            "Renting Operativo": self.analyze_renting()
        }
        
        summary = []
        for name, flows in results.items():
            df = pd.DataFrame(flows)
            # TCO Bruto (Suma outflows - residual)
            tco_bruto = df["outflow"].sum() - df["residual"].sum()
            # Escudo Fiscal Total
            total_tax_shield = df["tax_shield"].sum()
            # TCO Neto (Post-Impuestos)
            tco_neto = tco_bruto - total_tax_shield
            
            # Cálculo VAN (Net Cash Flow)
            # Cash Flow Neto = -Outflow + Tax_Shield + Residual
            df["net_cf"] = -df["outflow"] + df["tax_shield"] + df["residual"]
            # En t=0 solo outflow
            df.loc[df['year'] == 0, 'net_cf'] = -df.loc[df['year'] == 0, 'outflow']
            
            van = npf.npv(self.wacc, df["net_cf"])
            
            # TIR (Solo si hay inversión inicial)
            tir = npf.irr(df["net_cf"]) if df.iloc[0]["outflow"] > 0 else np.nan
            
            summary.append({
                "Escenario": name,
                "TCO Flota 5A (Bruto)": tco_bruto,
                "Ahorro Fiscal Acum.": total_tax_shield,
                "Coste Neto Flota (TCO-Fiscal)": tco_neto,
                "Coste Mensual x Unidad": (tco_bruto / self.horizon_years / 12) / self.n_trucks,
                "VAN Project (WACC 9%)": van,
                "TIR (%)": tir * 100 if not np.isnan(tir) else 0
            })
            
        return pd.DataFrame(summary)

    def sensitivity_table(self, base_scenario="Leasing Financiero"):
        """Genera tabla de sensibilidad para el escenario elegido."""
        price_vars = [0.9, 1.0, 1.1] # -10%, Base, +10%
        residual_vars = [0.25, 0.35, 0.45] # -10pp, Base, +10pp
        
        rows = []
        for p in price_vars:
            row = []
            for r in residual_vars:
                # Simulador temporal con precio y residual dinámicos
                temp_model = FleetFinancialModel(unit_price=self.unit_price * p, residual_val_pct=r)
                res = temp_model.get_summary_table()
                van = res.loc[res["Escenario"] == base_scenario, "VAN Project (WACC 9%)"].values[0]
                row.append(f"{van/1e6:.2f}M")
            rows.append(row)
            
        return pd.DataFrame(rows, 
                            index=["Precio -10%", "Precio Base", "Precio +10%"],
                            columns=["Residual 25%", "Residual 35%", "Residual 45%"])

if __name__ == "__main__":
    model = FleetFinancialModel()
    print("--- COMPARATIVA FINANCIERA EJECUTIVA ESPAÑA 2026 ---")
    print(model.get_summary_table().to_string(index=False))
    print("\n--- SENSIBILIDAD VAN (ESCENARIO LEASING) ---")
    print(model.sensitivity_table())
