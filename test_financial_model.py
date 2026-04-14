"""
test_financial_model.py
───────────────────────
Script sencillo para probar la clase FleetInvestmentModel con datos sintéticos.
"""

from financial_model import FleetInvestmentModel

def run_test():
    # 1. Instanciar con datos sintéticos cercanos a la realidad (MITMA 44t)
    model = FleetInvestmentModel(
        vehicle_price=150_000,
        km_annual=120_000,
        horizon_years=5,
        wacc=0.08,
        driver_annual_cost=42_000
    )

    print("--- TEST DE MODELO FINANCIERO (44t) ---\n")
    
    # 2. Análisis Compra
    compra = model.analyze_purchase()
    print(f"MODALIDAD: {compra['modality']}")
    print(f"  Inversión Inicial: {compra['initial_disbursement']:_.2f} €")
    print(f"  TCO Total (5 años): {compra['tco_total']:_.2f} €")
    print(f"  TCO por km: {compra['tco_km']:.4f} €/km")
    print(f"  VAN @8%: {compra['van']:_.2f} €")
    print(f"  TIR: {compra['tir']*100:.2f}%")
    print("-" * 40)

    # 3. Análisis Leasing
    leasing = model.analyze_leasing(down_payment_pct=0.15, tae=0.05)
    print(f"MODALIDAD: {leasing['modality']}")
    print(f"  Entrada (15%): {leasing['initial_disbursement']:_.2f} €")
    print(f"  Cuota Mensual (Leasing): {leasing['monthly_fee']:_.2f} €")
    print(f"  TCO Total (5 años): {leasing['tco_total']:_.2f} €")
    print(f"  TCO por km: {leasing['tco_km']:.4f} €/km")
    print("-" * 40)

    # 4. Análisis Renting
    renting = model.analyze_renting(monthly_rent_fee=3_400)
    print(f"MODALIDAD: {renting['modality']}")
    print(f"  Cuota Mensual (Renting All-in): {renting['monthly_rent_only']:_.2f} €")
    print(f"  TCO Total (5 años): {renting['tco_total']:_.2f} €")
    print(f"  TCO por km: {renting['tco_km']:.4f} €/km")
    print("-" * 40)

    # 5. Punto de Indiferencia
    punto = model.get_indifference_point(renting_fee=3_400)
    km_indiff = punto['km_indifference_compra_renting']
    print(f"PUNTO DE INDIFERENCIA (Compra vs Renting):")
    print(f"  Umbral: {km_indiff:_.0f} km/año")
    if 120_000 > km_indiff:
        print("  Resultado: La Compra es más eficiente para el kilometraje actual.")
    else:
        print("  Resultado: El Renting es más eficiente para el kilometraje actual.")

if __name__ == "__main__":
    run_test()
