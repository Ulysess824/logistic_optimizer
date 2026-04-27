"""
run_investment_analysis.py
--------------------------
Script de ejecución para el análisis de inversión (Break-Even).
Genera métricas JSON y gráficos para el dashboard.
"""
import os
import json
import plotly.graph_objects as go
from logistic_core.utils.investment_engine import InvestmentEngine

def run():
    print("Ejecutando análisis de Punto de Equilibrio (Compra)...")
    engine = InvestmentEngine()
    resultados = engine.generar_matriz_resumen()

    output_dir = "results_analysis"
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    # 1. Guardar métricas
    with open(f"{output_dir}/investment_metrics.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2)

    # 2. Generar Gráfico de Barras (Tiempo de Recuperación)
    tipos = ["Diésel Euro VI", "Eléctrico BEV"]
    anos = [resultados["diesel"]["anos"], resultados["electrico"]["anos"]]
    
    fig_anos = go.Figure(data=[
        go.Bar(
            x=tipos, 
            y=anos,
            marker_color=["#475569", "#10b981"],
            text=[f"{a} años" for a in anos],
            textposition='auto'
        )
    ])
    fig_anos.update_layout(
        title="Tiempo de Recuperación de Capital (Años)",
        yaxis_title="Años",
        template="plotly_white",
        margin=dict(t=50, b=50, l=50, r=50)
    )
    fig_anos.write_html(f"{output_dir}/investment_be_years.html")

    # 3. Gráfico de Comparativa MCA vs CAPEX
    capex = [resultados["diesel"]["capex_neto"], resultados["electrico"]["capex_neto"]]
    mca = [resultados["diesel"]["mca"], resultados["electrico"]["mca"]]

    fig_comp = go.Figure(data=[
        go.Bar(name='CAPEX Neto', x=tipos, y=capex, marker_color='#94a3b8'),
        go.Bar(name='Margen Anual (MCA)', x=tipos, y=mca, marker_color='#3b82f6')
    ])
    fig_comp.update_layout(
        title="Esfuerzo de Inversión vs Retorno Anual",
        barmode='group',
        template="plotly_white",
        yaxis_title="Euros (€)"
    )
    fig_comp.write_html(f"{output_dir}/investment_capex_mca.html")

    print(f"Análisis completado. Resultados en {output_dir}")

if __name__ == "__main__":
    run()
