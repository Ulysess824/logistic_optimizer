"""
strategic_analyzer.py
----------------------
Motor de Analisis Estrategico y TCO para flota logística.
Evalua el business case (Asset-Light vs Heavy) y transiciones de flota
a largo plazo (Compra, Leasing, Renting).
"""
import numpy as np
import logging
import plotly.graph_objects as go

from logistic_core.utils.fleet_estimator import FleetCapexEstimator
from logistic_core.config import (
    SOFTWARE_TMS_CAPEX, INTERNAL_OPERATIONAL_TCO_RATE, EXTERNAL_PROVIDER_RATE_PER_KM,
    CAPEX_TRUCK_UNIT_COST, DEFAULT_CYCLE_TIME_DAYS, DAILY_TRUCK_OUTBOUND, DEFAULT_FLEET_BUFFER,
    TCO_HORIZON_YEARS, TCO_WACC, TCO_INFLACION_ANUAL, TCO_TAX_RATE,
    KMS_ANUALES_POR_CAMION,
    DIESEL_CAPEX, DIESEL_RESIDUAL_PCT, DIESEL_CONSUMO_L_100KM,
    DIESEL_COSTE_COMBUSTIBLE_L, DIESEL_ADBLUE_L_100KM, DIESEL_COSTE_ADBLUE_L,
    DIESEL_MANT_ANUAL, DIESEL_NEUMATICOS_ANUAL, DIESEL_SEGURO_ANUAL,
    DIESEL_RENTING_MENSUAL, DIESEL_LEASING_MENSUAL,
    EV_CAPEX, EV_MOVES_AYUDA, EV_RESIDUAL_PCT, EV_CONSUMO_KWH_KM,
    EV_COSTE_KWH, EV_MANT_ANUAL, EV_SEGURO_ANUAL, EV_CHARGER_CAPEX,
    EV_RENTING_MENSUAL, EV_LEASING_MENSUAL,
    FLEET_MIX_DIESEL, FLEET_MIX_EV
)

logger = logging.getLogger(__name__)

class StrategicAnalyzer:
    """
    Analizador financiero estratégico de largo plazo.
    Permite inyección total de parámetros para análisis de sensibilidad.
    """

    def __init__(self, days_per_year=250, software_capex=None, 
                 truck_unit_cost=None, cycle_time_days=None, 
                 daily_dispatch=None, fleet_buffer=None,
                 kms_anuales=None, wacc=None, inflación_anual=None,
                 diesel_params=None, ev_params=None, financiacion=None):
        
        # Base de operaciones
        self.days_per_year = days_per_year
        self.software_capex = software_capex if software_capex is not None else SOFTWARE_TMS_CAPEX
        
        # Parámetros para Ley de Little
        self.truck_unit_cost = truck_unit_cost if truck_unit_cost is not None else CAPEX_TRUCK_UNIT_COST
        self.cycle_time_days = cycle_time_days if cycle_time_days is not None else DEFAULT_CYCLE_TIME_DAYS
        self.daily_dispatch = daily_dispatch if daily_dispatch is not None else DAILY_TRUCK_OUTBOUND
        self.fleet_buffer = fleet_buffer if fleet_buffer is not None else DEFAULT_FLEET_BUFFER
        
        self.fleet_estimator = FleetCapexEstimator(
            daily_dispatch_rate=self.daily_dispatch,
            unit_truck_cost=self.truck_unit_cost,
            utilization_buffer=self.fleet_buffer
        )

        # Variables TCO Financiero (Largo Plazo)
        self.kms_anuales = kms_anuales if kms_anuales is not None else KMS_ANUALES_POR_CAMION
        self.años = TCO_HORIZON_YEARS
        
        # Normalización de WACC e Inflación (Escalar o Lista)
        self.wacc = self._prepare_sequence(wacc if wacc is not None else TCO_WACC, "wacc")
        self.inflación = self._prepare_sequence(inflación_anual if inflación_anual is not None else TCO_INFLACION_ANUAL, "inflación")
        self.tax_rate = TCO_TAX_RATE

        # Parámetros por tecnología con posibilidad de Overrides desde el Notebook
        self.params = {
            "diesel": {
                "capex": diesel_params.get("capex", DIESEL_CAPEX) if diesel_params else DIESEL_CAPEX,
                "residual_value_pct": diesel_params.get("residual_pct", DIESEL_RESIDUAL_PCT) if diesel_params else DIESEL_RESIDUAL_PCT,
                "consumo_l_100km": diesel_params.get("consumo_l_100km", DIESEL_CONSUMO_L_100KM) if diesel_params else DIESEL_CONSUMO_L_100KM,
                "coste_combustible_l": diesel_params.get("coste_combustible_l", DIESEL_COSTE_COMBUSTIBLE_L) if diesel_params else DIESEL_COSTE_COMBUSTIBLE_L,
                "adblue_l_100km": DIESEL_ADBLUE_L_100KM,
                "coste_adblue_l": DIESEL_COSTE_ADBLUE_L,
                "mantenimiento_anual_fijo": diesel_params.get("mantenimiento_anual", DIESEL_MANT_ANUAL + DIESEL_NEUMATICOS_ANUAL) if diesel_params else DIESEL_MANT_ANUAL + DIESEL_NEUMATICOS_ANUAL,
                "seguro_anual_compra": diesel_params.get("seguro_anual", DIESEL_SEGURO_ANUAL) if diesel_params else DIESEL_SEGURO_ANUAL,
            },
            "electrico": {
                "capex": (ev_params.get("capex_truck", EV_CAPEX) + ev_params.get("capex_charger", EV_CHARGER_CAPEX)) if ev_params else EV_CAPEX + EV_CHARGER_CAPEX,
                "ayuda_moves": ev_params.get("ayuda_moves", EV_MOVES_AYUDA) if ev_params else EV_MOVES_AYUDA,
                "residual_value_pct": ev_params.get("residual_pct", EV_RESIDUAL_PCT) if ev_params else EV_RESIDUAL_PCT,
                "consumo_kwh_km": ev_params.get("consumo_kwh_km", EV_CONSUMO_KWH_KM) if ev_params else EV_CONSUMO_KWH_KM,
                "coste_kwh": ev_params.get("coste_kwh", EV_COSTE_KWH) if ev_params else EV_COSTE_KWH,
                "mantenimiento_anual_fijo": ev_params.get("mantenimiento_anual", EV_MANT_ANUAL) if ev_params else EV_MANT_ANUAL,
                "seguro_anual_compra": ev_params.get("seguro_anual", EV_SEGURO_ANUAL) if ev_params else EV_SEGURO_ANUAL,
            }
        }

        # Modelos Financieros As a Service con Overrides
        self.financiacion = {
            "diesel": {
                "renting_mensual": financiacion.get("diesel_renting", DIESEL_RENTING_MENSUAL) if financiacion else DIESEL_RENTING_MENSUAL,
                "leasing_mensual": financiacion.get("diesel_leasing", DIESEL_LEASING_MENSUAL) if financiacion else DIESEL_LEASING_MENSUAL
            },
            "electrico": {
                "renting_mensual": financiacion.get("ev_renting", EV_RENTING_MENSUAL) if financiacion else EV_RENTING_MENSUAL,
                "leasing_mensual": financiacion.get("ev_leasing", EV_LEASING_MENSUAL) if financiacion else EV_LEASING_MENSUAL
            }
        }
    
    def _prepare_sequence(self, value, name: str) -> list:
        """Convierte un escalar a lista o valida una lista existente."""
        if isinstance(value, (int, float)):
            return [float(value)] * self.años
        if isinstance(value, (list, np.ndarray)):
            if len(value) < self.años:
                # El usuario solicitó explícitamente un error si la longitud es insuficiente
                raise ValueError(f"La secuencia '{name}' debe tener al menos {self.años} elementos.")
            return [float(x) for x in value[:self.años]]
        raise TypeError(f"El parámetro '{name}' debe ser un escalar (float) o una lista/array.")

    def _get_inflacion_factor(self, año: int) -> float:
        """Calcula el factor de inflación acumulado hasta el año especificado."""
        if año == 0: return 1.0
        return float(np.prod(1 + np.array(self.inflación[:año])))

    def _get_discount_factor(self, t: int) -> float:
        """Calcula el factor de descuento acumulado (WACC) para el año t."""
        if t == 0: return 1.0
        return 1.0 / float(np.prod(1 + np.array(self.wacc[:t])))

    def _calcular_opex_anual(self, tipo: str, modalidad: str, año: int) -> float:
        p = self.params[tipo]
        inflación_factor = self._get_inflacion_factor(año)

        if tipo == "diesel":
            energia = (self.kms_anuales / 100) * p["consumo_l_100km"] * p["coste_combustible_l"]
            adblue = (self.kms_anuales / 100) * p["adblue_l_100km"] * p["coste_adblue_l"]
            coste_energia = energia + adblue
        elif tipo == "electrico":
            coste_energia = self.kms_anuales * p["consumo_kwh_km"] * p["coste_kwh"]

        coste_energia *= inflación_factor

        if modalidad == "renting":
            mant = 0
            seguro = 0
        else:
            mant = p["mantenimiento_anual_fijo"] * inflación_factor
            seguro = p["seguro_anual_compra"] * inflación_factor

        return coste_energia + mant + seguro

    def evaluar_compra(self, tipo: str) -> dict:
        p = self.params[tipo]
        capex = p["capex"]
        flujos = [-capex]
        
        for año in range(1, self.años + 1):
            opex = self._calcular_opex_anual(tipo, "compra", año)
            amortizacion_fiscal = capex / self.años
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
        p = self.params[tipo]
        f = self.financiacion[tipo]
        cuota_anual = f["leasing_mensual"] * 12
        flujos = [0]
        
        for año in range(1, self.años + 1):
            opex = self._calcular_opex_anual(tipo, "leasing", año)
            tax_shield = (opex + cuota_anual) * self.tax_rate
            flujo_año = -opex - cuota_anual + tax_shield
            
            if año == 1 and tipo == "electrico":
                flujo_año += p["ayuda_moves"]
                
            if año == self.años:
                valor_residual = p["capex"] * p["residual_value_pct"]
                # Impacto fiscal neto tras ejercer opción de compra y venta inmediata
                flujo_año -= valor_residual * self.tax_rate
                
            flujos.append(flujo_año)
            
        return self._generar_metricas(flujos)

    def evaluar_renting(self, tipo: str) -> dict:
        p = self.params[tipo]
        f = self.financiacion[tipo]
        cuota_anual = f["renting_mensual"] * 12
        flujos = [0]
        
        for año in range(1, self.años + 1):
            if tipo == "diesel":
                energia = (self.kms_anuales / 100) * p["consumo_l_100km"] * p["coste_combustible_l"]
                energia += (self.kms_anuales / 100) * p["adblue_l_100km"] * p["coste_adblue_l"]
            elif tipo == "electrico":
                energia = self.kms_anuales * p["consumo_kwh_km"] * p["coste_kwh"]
                
            inflación_factor = self._get_inflacion_factor(año)
            opex_energia = energia * inflación_factor
            
            tax_shield = (opex_energia + cuota_anual) * self.tax_rate
            flujo_año = -opex_energia - cuota_anual + tax_shield
            
            flujos.append(flujo_año)
            
        return self._generar_metricas(flujos)

    def _generar_metricas(self, flujos: list) -> dict:
        flujos_np = np.array(flujos)
        van = sum(float(cf) * self._get_discount_factor(t) for t, cf in enumerate(flujos))
        return {
            "flujos_anuales": flujos_np.tolist(),
            "tco_van_acumulado": van,
            "coste_neto_por_km": abs(van) / (self.kms_anuales * self.años)
        }

    def generar_tabla_comparativa(self, n_diesel: int = None, n_ev: int = None) -> dict:
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
        p_d = self.params["diesel"]
        p_e = self.params["electrico"]

        for mod_name, mod_fn in modalidades.items():
            res_d = mod_fn("diesel")
            res_e = mod_fn("electrico")
            por_camion["diesel"][mod_name] = res_d
            por_camion["electrico"][mod_name] = res_e

            vr_d = p_d["capex"] * p_d["residual_value_pct"] * n_d if mod_name != "renting" else 0
            vr_e = p_e["capex"] * p_e["residual_value_pct"] * n_e if mod_name != "renting" else 0
            vr_total = vr_d + vr_e

            tco_diesel_total = res_d["tco_van_acumulado"] * n_d
            tco_ev_total = res_e["tco_van_acumulado"] * n_e
            tco_flota = tco_diesel_total + tco_ev_total

            km_totales_flota = self.kms_anuales * self.años * n_total
            flota_mixta[mod_name] = {
                "tco_total": tco_flota,
                "tco_diesel_subtotal": tco_diesel_total,
                "tco_ev_subtotal": tco_ev_total,
                "valor_residual_total": vr_total,  # nominal bruto, no descontado; solo informativo
                "coste_km_medio": abs(tco_flota) / km_totales_flota if km_totales_flota > 0 else 0,
                "n_diesel": n_d,
                "n_ev": n_e,
                "n_total": n_total
            }

        mejor = max(flota_mixta.items(), key=lambda x: x[1]["tco_total"])
        peor = min(flota_mixta.items(), key=lambda x: x[1]["tco_total"])
        ahorro_vs_peor = abs(peor[1]["tco_total"]) - abs(mejor[1]["tco_total"])
        pct_ahorro = (ahorro_vs_peor / abs(peor[1]["tco_total"])) * 100 if peor[1]["tco_total"] != 0 else 0

        return {
            "horizonte_anos": self.años,
            "por_camion": por_camion,
            "flota_mixta": flota_mixta,
            "recomendacion": {
                "modalidad": mejor[0],
                "ahorro_vs_peor_eur": ahorro_vs_peor,
                "ahorro_pct": pct_ahorro,
                "vs_modalidad": peor[0]
            }
        }

    def plot_van_evolution(self, n_diesel: int, n_ev: int) -> go.Figure:
        """Genera un grafico de Plotly con la evolucion del VAN acumulado."""
        fig = go.Figure()
        años_eje = [f"Año {i}" for i in range(self.años + 1)]
        colores = {"COMPRA": "#ef4444", "LEASING": "#10b981", "RENTING": "#3b82f6"}

        for mod in ["compra", "leasing", "renting"]:
            res_d = self.evaluar_compra("diesel") if mod == "compra" else (self.evaluar_leasing("diesel") if mod == "leasing" else self.evaluar_renting("diesel"))
            res_e = self.evaluar_compra("electrico") if mod == "compra" else (self.evaluar_leasing("electrico") if mod == "leasing" else self.evaluar_renting("electrico"))
            
            flujos_d = np.array(res_d["flujos_anuales"]) * n_diesel
            flujos_e = np.array(res_e["flujos_anuales"]) * n_ev
            flujos_totales = flujos_d + flujos_e
            
            van_acumulado = []
            acumulado = 0
            for t, flujo in enumerate(flujos_totales):
                valor_actual = flujo * self._get_discount_factor(t)
                acumulado += valor_actual
                van_acumulado.append(acumulado)
            
            fig.add_trace(go.Scatter(
                x=años_eje, y=van_acumulado, name=mod.upper(),
                line=dict(width=4, color=colores[mod.upper()]),
                mode='lines+markers'
            ))

        fig.update_layout(
            title='Evolución del VAN Acumulado de la Inversión',
            xaxis_title='Horizonte Temporal',
            yaxis_title='VAN Neto (€)',
            template='plotly_white',
            hovermode='x unified'
        )
        return fig
