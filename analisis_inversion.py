"""
analisis_inversion.py
──────────────────────
Script principal para generar el reporte visual de inversión (TFM Logistics Optimizer v5.3).
Genera gráficos interactivos con Plotly y tablas comparativas para 44t alineado a MITMA e IFRS 16.
"""

import plotly.graph_objects as go
import pandas as pd
from financial_model import FleetInvestmentModel
import os

def generar_analisis():
    # Parámetros base del proyecto MITMA 44t
    VEHICLE_PRICE = 145_000.0
    KM_ANNUAL = 120_000.0
    WACC = 0.08
    RENTING_FEE = 3_400.0

    # 1. Instanciar modelos para horizontes 5 y 7 años
    model_5 = FleetInvestmentModel(vehicle_price=VEHICLE_PRICE, km_annual=KM_ANNUAL, horizon_years=5, wacc=WACC)
    model_7 = FleetInvestmentModel(vehicle_price=VEHICLE_PRICE, km_annual=KM_ANNUAL, horizon_years=7, wacc=WACC)

    res_5_compra = model_5.analyze_purchase()
    res_5_leasing = model_5.analyze_leasing()
    res_5_renting = model_5.analyze_renting(monthly_rent_fee=RENTING_FEE)

    res_7_compra = model_7.analyze_purchase()
    res_7_leasing = model_7.analyze_leasing()
    res_7_renting = model_7.analyze_renting(monthly_rent_fee=RENTING_FEE)

    # --- GRAFICO 1: TCO ACUMULADO (Horizonte 7 años) ---
    fig_tco = go.Figure()

    years = list(range(1, 8))
    
    # Calculamos acumulados puro
    def get_accumulated(cash_flows):
        acc = []
        current = -cash_flows[0] # Desembolso inicial
        for i in range(1, len(cash_flows)):
            current += -cash_flows[i]
            acc.append(current)
        return acc

    acc_compra = get_accumulated(res_7_compra['cash_flows'])
    acc_leasing = get_accumulated(res_7_leasing['cash_flows'])
    acc_renting = get_accumulated(res_7_renting['cash_flows'])

    fig_tco.add_trace(go.Scatter(x=years, y=acc_compra, name='Compra Directa', line=dict(color='#2E86C1', width=3)))
    fig_tco.add_trace(go.Scatter(x=years, y=acc_leasing, name='Leasing Financiero', line=dict(color='#F39C12', width=3)))
    fig_tco.add_trace(go.Scatter(x=years, y=acc_renting, name='Renting Operativo', line=dict(color='#27AE60', width=3)))

    fig_tco.update_layout(
        title='Evolución del TCO Acumulado (7 años) — Camión 44t',
        xaxis_title='Año',
        yaxis_title='Coste Total Acumulado (€)',
        template='plotly_dark',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    # --- GRAFICO 2: FLUJO DE CAJA DIFERENCIAL DESPUÉS DE IMPUESTOS ---
    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(x=list(range(8)), y=res_7_compra['cash_flows_after_tax'], name='Compra', marker_color='#2E86C1'))
    fig_cf.add_trace(go.Bar(x=list(range(8)), y=res_7_leasing['cash_flows_after_tax'], name='Leasing', marker_color='#F39C12'))
    fig_cf.add_trace(go.Bar(x=list(range(8)), y=res_7_renting['cash_flows_after_tax'], name='Renting', marker_color='#27AE60'))

    fig_cf.update_layout(
        title='Flujo de Caja Anual por Modalidad (Después de IS 25%)',
        xaxis_title='Año',
        yaxis_title='Flujo Neto (€)',
        template='plotly_dark',
        barmode='group'
    )

    # Guardar gráficos (HTML para dashboard)
    os.makedirs('outputs/results/finanzas', exist_ok=True)
    fig_tco.write_html('outputs/results/finanzas/tco_comparativo.html')
    fig_cf.write_html('outputs/results/finanzas/cashflow_comparativo.html')
    # Omitimos exportar a .png para no depender de kaleido engine

    # --- TABLA COMPARATIVA FINAL ---
    tabla_data = [
        ["Desembolso inicial", f"{res_5_compra['initial_disbursement']:_.0f} €", f"{res_5_leasing['initial_disbursement']:_.0f} €", "0 €"],
        ["Cuota mensual (Ref)", "-", f"{res_5_leasing['monthly_fee']:_.0f} €", f"{RENTING_FEE:_.0f} €"],
        ["TCO 5 años (€)", f"{res_5_compra['tco_total']:_.0f} €", f"{res_5_leasing['tco_total']:_.0f} €", f"{res_5_renting['tco_total']:_.0f} €"],
        ["TCO 7 años (€)", f"{res_7_compra['tco_total']:_.0f} €", f"{res_7_leasing['tco_total']:_.0f} €", f"{res_7_renting['tco_total']:_.0f} €"],
        ["TCO en €/km (5y)", f"{res_5_compra['tco_km']:.3f} €/km", f"{res_5_leasing['tco_km']:.3f} €/km", f"{res_5_renting['tco_km']:.3f} €/km"],
        ["VAN Después de Impuestos (5y)", f"{res_5_compra['van_after_tax']:_.0f} €", f"{res_5_leasing['van_after_tax']:_.0f} €", f"{res_5_renting['van_after_tax']:_.0f} €"],
        ["Payback Period (Años)", f"{res_5_compra['payback_years']:.2f}", f"{res_5_leasing['payback_years']:.2f}", f"{res_5_renting['payback_years']:.2f}"],
        ["Status en Balance (IFRS 16)", res_5_compra['ifrs_balance_impact'], res_5_leasing['ifrs_balance_impact'], res_5_renting['ifrs_balance_impact']],
        ["Riesgo Obsolescencia 44t", "Alto (Red. Vida Útil)", "Medio", "Bajo transferido"],
        ["Recomendación MITMA", "Óptima uso ultra-intensivo", "Equilibrio Financiero", "Máxima Flexibilidad"]
    ]

    df_tabla = pd.DataFrame(tabla_data, columns=["Criterio", "Compra", "Leasing", "Renting"])
    
    # Punto de indiferencia
    punto = model_5.get_indifference_point(renting_fee=RENTING_FEE)
    
    return df_tabla, punto, fig_tco, fig_cf

if __name__ == "__main__":
    df, p, _, _ = generar_analisis()
    print("\n" + "="*70)
    print("RESUMEN COMPARATIVO DE INVERSIÓN (TFM)")
    print("="*70)
    print(df.to_string(index=False))
    print("\n" + "="*70)
    print(f"Punto de Indiferencia (Compra vs Renting): {p['km_indifference_compra_renting']:_.0f} km/año")
