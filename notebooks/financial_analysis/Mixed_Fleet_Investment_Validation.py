"""
Mixed_Fleet_Investment_Validation.py
====================================
Script de validacion academica del modelo de inversion mixta.
Genera la misma tabla comparativa que el dashboard para verificar
que los calculos son reproducibles fuera del pipeline.

Ejecutar: py notebooks/financial_analysis/Mixed_Fleet_Investment_Validation.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from logistic_core.utils.investment_analyzer import InvestmentAnalyzer
from logistic_core.config import (
    DIESEL_CAPEX, EV_CAPEX, EV_MOVES_AYUDA,
    FLEET_MIX_DIESEL, FLEET_MIX_EV,
    KMS_ANUALES_POR_CAMION, TCO_HORIZON_YEARS,
    TCO_WACC, TCO_INFLACION_ANUAL, TCO_TAX_RATE,
    DIESEL_RENTING_MENSUAL, DIESEL_LEASING_MENSUAL,
    EV_RENTING_MENSUAL, EV_LEASING_MENSUAL
)


def main():
    print("=" * 75)
    print(" VALIDACION ACADEMICA: MODELO DE INVERSION MIXTA (TCO a 5 anos)")
    print("=" * 75)

    # --- 1. Parametros ---
    print("\n--- PARAMETROS DE ENTRADA ---")
    print(f"  Horizonte:          {TCO_HORIZON_YEARS} anos")
    print(f"  Km anuales/camion:  {KMS_ANUALES_POR_CAMION:,} km".replace(",", "."))
    print(f"  WACC:               {TCO_WACC*100:.1f}%")
    print(f"  Inflacion:          {TCO_INFLACION_ANUAL*100:.1f}%")
    print(f"  Tipo IS:            {TCO_TAX_RATE*100:.0f}%")
    print(f"  Composicion Flota:  {FLEET_MIX_DIESEL} Diesel + {FLEET_MIX_EV} BEV = {FLEET_MIX_DIESEL + FLEET_MIX_EV} camiones")
    print(f"  CAPEX Diesel:       {DIESEL_CAPEX:,} EUR".replace(",", "."))
    print(f"  CAPEX BEV:          {EV_CAPEX:,} EUR (MOVES: -{EV_MOVES_AYUDA:,} EUR)".replace(",", "."))

    # --- 2. Calculo ---
    analyzer = InvestmentAnalyzer()
    tabla = analyzer.generar_tabla_comparativa()

    # --- 3. Tabla unitaria ---
    print("\n--- TCO UNITARIO (1 CAMION) ---")
    print(f"{'':35} | {'COMPRA':>15} | {'LEASING':>15} | {'RENTING':>15}")
    print("-" * 87)

    for tec, label in [("diesel", "Diesel (Euro VI)"), ("electrico", "Electrico (BEV 44t)")]:
        vals = []
        for mod in ["compra", "leasing", "renting"]:
            v = tabla["por_camion"][tec][mod]["tco_van_acumulado"]
            vals.append(f"{abs(v):>12,.0f} EUR".replace(",", "."))
        print(f"  {label:<33} | {vals[0]:>15} | {vals[1]:>15} | {vals[2]:>15}")

    print()

    for tec, label in [("diesel", "Diesel (EUR/km)"), ("electrico", "BEV (EUR/km)")]:
        vals = []
        for mod in ["compra", "leasing", "renting"]:
            v = tabla["por_camion"][tec][mod]["coste_neto_por_km"]
            vals.append(f"{v:>12.3f}")
        print(f"  {label:<33} | {vals[0]:>15} | {vals[1]:>15} | {vals[2]:>15}")

    # --- 4. Flujos de caja detallados (Compra como ejemplo) ---
    print("\n--- FLUJOS DE CAJA DETALLADOS (Compra) ---")
    print(f"{'Ano':<6} | {'Diesel':>15} | {'Electrico':>15}")
    print("-" * 42)
    fd = tabla["por_camion"]["diesel"]["compra"]["flujos_anuales"]
    fe = tabla["por_camion"]["electrico"]["compra"]["flujos_anuales"]
    for t in range(len(fd)):
        d_val = f"{fd[t]:>12,.0f} EUR".replace(",", ".")
        e_val = f"{fe[t]:>12,.0f} EUR".replace(",", ".")
        print(f"  t={t:<3} | {d_val:>15} | {e_val:>15}")

    # --- 5. Consolidado Flota Mixta ---
    print("\n--- TCO CONSOLIDADO FLOTA MIXTA ---")
    print(f"{'MODALIDAD':<18} | {'DIESEL (7x)':>15} | {'BEV (4x)':>15} | {'TOTAL':>15} | {'EUR/km':>8}")
    print("-" * 80)

    for mod, label in [("compra", "Compra"), ("leasing", "Leasing"), ("renting", "Renting")]:
        m = tabla["flota_mixta"][mod]
        is_best = (mod == tabla["recomendacion"]["modalidad"])
        marker = " <-- OPTIMO" if is_best else ""
        d = f"{abs(m['tco_diesel_subtotal']):>12,.0f}".replace(",", ".")
        e = f"{abs(m['tco_ev_subtotal']):>12,.0f}".replace(",", ".")
        t = f"{abs(m['tco_total']):>12,.0f}".replace(",", ".")
        k = f"{m['coste_km_medio']:.3f}"
        print(f"  {label:<16} | {d:>15} | {e:>15} | {t:>15} | {k:>8}{marker}")

    # --- 6. Recomendacion ---
    rec = tabla["recomendacion"]
    print("-" * 80)
    print(f"\n  RECOMENDACION: {rec['modalidad'].upper()}")
    print(f"  Ahorro vs {rec['vs_modalidad'].upper()}: {rec['ahorro_vs_peor_eur']:,.0f} EUR ({rec['ahorro_pct']:.1f}%)".replace(",", "."))

    # --- 7. Sensibilidad: que pasa si quitamos MOVES? ---
    print("\n--- SENSIBILIDAD: SIN SUBVENCION MOVES ---")
    from logistic_core import config
    original_moves = config.EV_MOVES_AYUDA
    # Simulamos temporalmente sin ayuda
    # (No modificamos config, solo recalculamos)
    analyzer_no_moves = InvestmentAnalyzer()
    # Forzar ayuda a 0
    analyzer_no_moves.params["electrico"]["ayuda_moves"] = 0
    tabla_no_moves = analyzer_no_moves.generar_tabla_comparativa()

    for mod, label in [("compra", "Compra"), ("leasing", "Leasing"), ("renting", "Renting")]:
        m_con = tabla["flota_mixta"][mod]
        m_sin = tabla_no_moves["flota_mixta"][mod]
        delta = abs(m_sin["tco_total"]) - abs(m_con["tco_total"])
        print(f"  {label:<16}: TCO sin MOVES = {abs(m_sin['tco_total']):>12,.0f} EUR"
              f" (incremento: +{delta:,.0f} EUR)".replace(",", "."))

    print("\n" + "=" * 75)
    print(" FIN DE VALIDACION")
    print("=" * 75)


if __name__ == "__main__":
    main()
