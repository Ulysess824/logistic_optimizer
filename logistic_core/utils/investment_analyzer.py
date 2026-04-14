"""
investment_analyzer.py
----------------------
Motor de Analisis TCO para flota mixta de camiones pesados (44t).
Evalua Diesel vs Electrico bajo modalidades de Compra, Leasing y Renting
a un horizonte configurable (por defecto 5 anos).

Todos los parametros se importan desde config.py para facilitar
ajustes futuros (ej: subvencion MOVES, precio kWh, cuotas de mercado).
"""
import numpy as np
import logging
from logistic_core.config import (
    TCO_HORIZON_YEARS, TCO_WACC, TCO_INFLACION_ANUAL, TCO_TAX_RATE,
    KMS_ANUALES_POR_CAMION,
    DIESEL_CAPEX, DIESEL_RESIDUAL_PCT, DIESEL_CONSUMO_L_100KM,
    DIESEL_COSTE_COMBUSTIBLE_L, DIESEL_ADBLUE_L_100KM, DIESEL_COSTE_ADBLUE_L,
    DIESEL_MANT_ANUAL, DIESEL_NEUMATICOS_ANUAL, DIESEL_SEGURO_ANUAL,
    DIESEL_RENTING_MENSUAL, DIESEL_LEASING_MENSUAL,
    EV_CAPEX, EV_MOVES_AYUDA, EV_RESIDUAL_PCT, EV_CONSUMO_KWH_KM,
    EV_COSTE_KWH, EV_MANT_ANUAL, EV_SEGURO_ANUAL,
    EV_RENTING_MENSUAL, EV_LEASING_MENSUAL,
    FLEET_MIX_DIESEL, FLEET_MIX_EV
)

logger = logging.getLogger(__name__)


class InvestmentAnalyzer:
    """
    Analizador financiero para comparar la inversion de camiones pesados (44t).
    Evalua Diesel vs Electrico bajo modalidades de Compra, Leasing y Renting
    a un horizonte de 5 anos.
    """

    def __init__(self, kms_anuales: float = None, wacc: float = None,
                 inflacion_anual: float = None):
        self.kms_anuales = kms_anuales or KMS_ANUALES_POR_CAMION
        self.años = TCO_HORIZON_YEARS
        self.wacc = wacc or TCO_WACC
        self.inflacion = inflacion_anual or TCO_INFLACION_ANUAL
        self.tax_rate = TCO_TAX_RATE

        # Parametros por tecnologia (leidos de config.py)
        self.params = {
            "diesel": {
                "capex": DIESEL_CAPEX,
                "residual_value_pct": DIESEL_RESIDUAL_PCT,
                "consumo_l_100km": DIESEL_CONSUMO_L_100KM,
                "coste_combustible_l": DIESEL_COSTE_COMBUSTIBLE_L,
                "adblue_l_100km": DIESEL_ADBLUE_L_100KM,
                "coste_adblue_l": DIESEL_COSTE_ADBLUE_L,
                "mantenimiento_anual_fijo": DIESEL_MANT_ANUAL + DIESEL_NEUMATICOS_ANUAL,
                "seguro_anual_compra": DIESEL_SEGURO_ANUAL,
            },
            "electrico": {
                "capex": EV_CAPEX,
                "ayuda_moves": EV_MOVES_AYUDA,
                "residual_value_pct": EV_RESIDUAL_PCT,
                "consumo_kwh_km": EV_CONSUMO_KWH_KM,
                "coste_kwh": EV_COSTE_KWH,
                "mantenimiento_anual_fijo": EV_MANT_ANUAL,
                "seguro_anual_compra": EV_SEGURO_ANUAL,
            }
        }

        # Cuotas mensuales de mercado (leidas de config.py)
        self.financiacion = {
            "diesel": {
                "renting_mensual": DIESEL_RENTING_MENSUAL,
                "leasing_mensual": DIESEL_LEASING_MENSUAL
            },
            "electrico": {
                "renting_mensual": EV_RENTING_MENSUAL,
                "leasing_mensual": EV_LEASING_MENSUAL
            }
        }

    # =========================================================================
    # CALCULO OPEX ANUAL (corazon del modelo)
    # =========================================================================
    def _calcular_opex_anual(self, tipo: str, modalidad: str, año: int) -> float:
        """Calcula el OPEX operativo para un ano concreto (aplicando inflacion)"""
        p = self.params[tipo]
        inflacion_factor = (1 + self.inflacion) ** año

        # Coste energetico
        if tipo == "diesel":
            energia = (self.kms_anuales / 100) * p["consumo_l_100km"] * p["coste_combustible_l"]
            adblue = (self.kms_anuales / 100) * p["adblue_l_100km"] * p["coste_adblue_l"]
            coste_energia = energia + adblue
        elif tipo == "electrico":
            coste_energia = self.kms_anuales * p["consumo_kwh_km"] * p["coste_kwh"]

        coste_energia *= inflacion_factor

        # Mantenimiento y Seguro
        if modalidad == "renting":
            mant = 0  # El Renting incluye todo en la cuota
            seguro = 0
        else:  # Compra o Leasing lo pagan aparte
            mant = p["mantenimiento_anual_fijo"] * inflacion_factor
            seguro = p["seguro_anual_compra"] * inflacion_factor

        return coste_energia + mant + seguro

    # =========================================================================
    # EVALUACION POR MODALIDAD (unitario, 1 camion)
    # =========================================================================
    def evaluar_compra(self, tipo: str) -> dict:
        """Flujo de caja para adquisicion en propiedad (al contado)."""
        p = self.params[tipo]
        capex = p["capex"]

        flujos = [-capex]  # Ano 0 (inversion inicial)

        for año in range(1, self.años + 1):
            opex = self._calcular_opex_anual(tipo, "compra", año)

            # Amortizacion lineal a 5 anos (20% anual)
            amortizacion_fiscal = capex / self.años

            # Escudo fiscal
            tax_shield = (opex + amortizacion_fiscal) * self.tax_rate

            flujo_año = -opex + tax_shield

            if año == 1 and tipo == "electrico":
                flujo_año += p["ayuda_moves"]

            if año == self.años:
                valor_residual = capex * p["residual_value_pct"]
                valor_residual_after_tax = valor_residual * (1 - self.tax_rate)
                flujo_año += valor_residual_after_tax

            flujos.append(flujo_año)

        return self._generar_metricas(flujos)

    def evaluar_leasing(self, tipo: str) -> dict:
        """
        Arrendamiento financiero (Leasing). Las cuotas se pagan mensualmente.
        Mantenimiento y seguros van a cuenta de la empresa.
        """
        p = self.params[tipo]
        f = self.financiacion[tipo]
        cuota_anual = f["leasing_mensual"] * 12

        flujos = [0]  # Ano 0 sin desembolso

        for año in range(1, self.años + 1):
            opex = self._calcular_opex_anual(tipo, "leasing", año)

            # Deducibilidad de la cuota de leasing
            tax_shield = (opex + cuota_anual) * self.tax_rate

            flujo_año = -opex - cuota_anual + tax_shield

            if año == 1 and tipo == "electrico":
                flujo_año += p["ayuda_moves"]

            if año == self.años:
                # Ejercer opcion de compra y quedarnos el activo (neutral en TCO)
                valor_residual = p["capex"] * p["residual_value_pct"]
                flujo_año -= valor_residual
                flujo_año += valor_residual

            flujos.append(flujo_año)

        return self._generar_metricas(flujos)

    def evaluar_renting(self, tipo: str) -> dict:
        """
        Renting operativo. El activo nunca es de la empresa.
        Cuotas incluyen OPEX fijo, mantenimiento y seguro.
        """
        p = self.params[tipo]
        f = self.financiacion[tipo]
        cuota_anual = f["renting_mensual"] * 12

        flujos = [0]  # Ano 0 sin desembolso

        for año in range(1, self.años + 1):
            # Solo se paga energia (combustible/kwh)
            if tipo == "diesel":
                energia = (self.kms_anuales / 100) * p["consumo_l_100km"] * p["coste_combustible_l"]
                energia += (self.kms_anuales / 100) * p["adblue_l_100km"] * p["coste_adblue_l"]
            elif tipo == "electrico":
                energia = self.kms_anuales * p["consumo_kwh_km"] * p["coste_kwh"]

            inflacion_factor = (1 + self.inflacion) ** año
            opex_energia = energia * inflacion_factor

            # La cuota de renting al 100% es gasto deducible
            tax_shield = (opex_energia + cuota_anual) * self.tax_rate

            flujo_año = -opex_energia - cuota_anual + tax_shield

            # En renting la ayuda MOVES la cobra la financiera (descontada en cuota)
            # No hay valor residual. Al ano 5 se devuelven las llaves.

            flujos.append(flujo_año)

        return self._generar_metricas(flujos)

    # =========================================================================
    # METRICAS FINANCIERAS (VAN, Coste/km)
    # =========================================================================
    def _generar_metricas(self, flujos: list) -> dict:
        flujos_np = np.array(flujos)
        # NPV manual: sum(flujo / (1 + r)^t)
        van = sum(cf / (1 + self.wacc) ** t for t, cf in enumerate(flujos))
        van = float(van)
        return {
            "flujos_anuales": flujos_np.tolist(),
            "tco_van_acumulado": van,
            "coste_neto_por_km": abs(van) / (self.kms_anuales * self.años)
        }

    # =========================================================================
    # EVALUACION CONSOLIDADA DE FLOTA MIXTA
    # =========================================================================
    def generar_tabla_comparativa(self, n_diesel: int = None, n_ev: int = None) -> dict:
        """
        Genera la tabla comparativa completa:
        - TCO unitario por tecnologia y modalidad
        - TCO consolidado de la flota mixta por modalidad
        - Recomendacion de la modalidad optima
        """
        n_d = n_diesel if n_diesel is not None else FLEET_MIX_DIESEL
        n_e = n_ev if n_ev is not None else FLEET_MIX_EV
        n_total = n_d + n_e

        modalidades = {
            "compra": self.evaluar_compra,
            "leasing": self.evaluar_leasing,
            "renting": self.evaluar_renting
        }

        por_camion = {"diesel": {}, "electrico": {}}
        flota_mixta = {}

        for mod_name, mod_fn in modalidades.items():
            res_d = mod_fn("diesel")
            res_e = mod_fn("electrico")

            por_camion["diesel"][mod_name] = res_d
            por_camion["electrico"][mod_name] = res_e

            # TCO consolidado (negativo = salida de caja)
            tco_diesel_total = res_d["tco_van_acumulado"] * n_d
            tco_ev_total = res_e["tco_van_acumulado"] * n_e
            tco_flota = tco_diesel_total + tco_ev_total

            km_totales_flota = self.kms_anuales * self.años * n_total

            flota_mixta[mod_name] = {
                "tco_total": tco_flota,
                "tco_diesel_subtotal": tco_diesel_total,
                "tco_ev_subtotal": tco_ev_total,
                "coste_km_medio": abs(tco_flota) / km_totales_flota if km_totales_flota > 0 else 0,
                "n_diesel": n_d,
                "n_ev": n_e,
                "n_total": n_total
            }

        # Recomendacion: modalidad con menor coste absoluto (mayor VAN, que es negativo)
        mejor = max(flota_mixta.items(), key=lambda x: x[1]["tco_total"])
        peor = min(flota_mixta.items(), key=lambda x: x[1]["tco_total"])
        ahorro_vs_peor = abs(peor[1]["tco_total"]) - abs(mejor[1]["tco_total"])
        pct_ahorro = (ahorro_vs_peor / abs(peor[1]["tco_total"])) * 100 if peor[1]["tco_total"] != 0 else 0

        return {
            "horizonte_anos": self.años,
            "kms_anuales": self.kms_anuales,
            "wacc": self.wacc,
            "por_camion": por_camion,
            "flota_mixta": flota_mixta,
            "recomendacion": {
                "modalidad": mejor[0],
                "ahorro_vs_peor_eur": ahorro_vs_peor,
                "ahorro_pct": pct_ahorro,
                "vs_modalidad": peor[0]
            }
        }


# =============================================================================
# SCRIPT DE PRUEBA CON DATOS SINTETICOS
# =============================================================================
if __name__ == "__main__":
    analyzer = InvestmentAnalyzer()

    print("=" * 70)
    print(" ANALISIS TCO FLOTA MIXTA 44T (5 ANOS)")
    print("=" * 70)
    print(f"Parametros: {analyzer.kms_anuales:,} km/ano | WACC {analyzer.wacc*100}%"
          f" | Inflacion {analyzer.inflacion*100}%".replace(",", "."))
    print("-" * 70)

    tabla = analyzer.generar_tabla_comparativa()

    # Tabla unitaria
    print(f"\n{'TECNOLOGIA & MODO':<35} | {'TCO (VAN) EUR':>18} | {'EUR/KM':>10}")
    print("-" * 70)

    for tec in ["diesel", "electrico"]:
        label = "DIESEL" if tec == "diesel" else "ELECTRICO (BEV)"
        print(f"  {label}")
        for mod in ["compra", "leasing", "renting"]:
            data = tabla["por_camion"][tec][mod]
            van = f"{-data['tco_van_acumulado']:>14,.0f} EUR".replace(",", ".")
            km = f"{data['coste_neto_por_km']:.3f}"
            mod_label = {"compra": "Propiedad (Compra)", "leasing": "Leasing Financiero", "renting": "Renting Operativo"}
            print(f"    {mod_label[mod]:<31} | {van:>18} | {km:>10}")
        print()

    # Tabla consolidada
    print("=" * 70)
    print(f" FLOTA MIXTA: {tabla['flota_mixta']['compra']['n_diesel']}x Diesel"
          f" + {tabla['flota_mixta']['compra']['n_ev']}x Electrico"
          f" = {tabla['flota_mixta']['compra']['n_total']} camiones")
    print("=" * 70)
    print(f"{'MODALIDAD':<20} | {'TCO DIESEL':>15} | {'TCO EV':>15} | {'TCO TOTAL':>15} | {'EUR/KM':>8}")
    print("-" * 70)

    for mod in ["compra", "leasing", "renting"]:
        m = tabla["flota_mixta"][mod]
        d = f"{abs(m['tco_diesel_subtotal']):>12,.0f}".replace(",", ".")
        e = f"{abs(m['tco_ev_subtotal']):>12,.0f}".replace(",", ".")
        t = f"{abs(m['tco_total']):>12,.0f}".replace(",", ".")
        k = f"{m['coste_km_medio']:.3f}"
        mod_label = {"compra": "Compra", "leasing": "Leasing", "renting": "Renting"}
        marker = " <--" if mod == tabla["recomendacion"]["modalidad"] else ""
        print(f"  {mod_label[mod]:<18} | {d:>15} | {e:>15} | {t:>15} | {k:>8}{marker}")

    rec = tabla["recomendacion"]
    print("-" * 70)
    print(f"RECOMENDACION: {rec['modalidad'].upper()}"
          f" (ahorro de {rec['ahorro_vs_peor_eur']:,.0f} EUR"
          f" vs {rec['vs_modalidad'].upper()}"
          f" = -{rec['ahorro_pct']:.1f}%)".replace(",", "."))
    print("=" * 70)
