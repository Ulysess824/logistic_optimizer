"""
investment_engine.py
--------------------
Motor de cálculo para el Punto de Equilibrio (Break-Even) en modalidad de compra.
Calcula el retorno de capital en años, km y pallets para Diésel y Eléctrico.
"""
import logging
from logistic_core import config

logger = logging.getLogger(__name__)

class InvestmentEngine:
    """
    Calculador de métricas de inversión para flota pesada (44t).
    Enfocado exclusivamente en la modalidad de Compra Directa.
    """

    def __init__(self):
        # Parámetros operativos base
        self.kms_anuales = config.KMS_ANUALES_POR_CAMION
        self.viajes_anuales = config.BE_VIAJES_ANUALES_CAMION
        self.pallets_viaje = config.BE_PALLETS_POR_VIAJE
        self.coste_conductor = config.ANNUAL_DRIVER_COST_PER_TRUCK

    def get_capex_neto(self, tipo: str) -> float:
        """Calcula la inversión inicial neta."""
        if tipo == "diesel":
            return float(config.DIESEL_CAPEX)
        elif tipo == "electrico":
            # Inversión = Camión + Cargador - Ayudas
            return float(config.EV_CAPEX + config.EV_CHARGER_CAPEX - config.EV_MOVES_AYUDA)
        return 0.0

    def calcular_mca(self, tipo: str) -> float:
        """
        Calcula el Margen de Contribución Anual (MCA) Pre-Tax (EBITDA).
        MCA = Ingresos - OPEX (Energía + Mant + Seguro + Conductor)
        """
        if tipo == "diesel":
            ingresos = config.TARIFA_INTERNA_DIESEL * self.kms_anuales
            cons_l = (self.kms_anuales / 100) * config.DIESEL_CONSUMO_L_100KM
            coste_diesel = cons_l * config.DIESEL_COSTE_COMBUSTIBLE_L
            coste_adblue = (self.kms_anuales / 100) * config.DIESEL_ADBLUE_L_100KM * config.DIESEL_COSTE_ADBLUE_L
            mantenimiento = config.DIESEL_MANT_ANUAL + config.DIESEL_NEUMATICOS_ANUAL
            seguro = config.DIESEL_SEGURO_ANUAL
            opex = coste_diesel + coste_adblue + mantenimiento + seguro
        else:
            ingresos = config.TARIFA_INTERNA_EV * self.kms_anuales
            coste_energia = self.kms_anuales * config.EV_CONSUMO_KWH_KM * config.EV_COSTE_KWH
            mantenimiento = config.EV_MANT_ANUAL
            seguro = config.EV_SEGURO_ANUAL
            opex = coste_energia + mantenimiento + seguro

        return ingresos - opex - self.coste_conductor

    def analizar_recuperacion(self, tipo: str) -> dict:
        """Genera el set completo de métricas usando el motor dinámico StrategicAnalyzer."""
        from logistic_core.utils.strategic_analyzer import StrategicAnalyzer
        
        # Inicializar el analizador estratégico
        analyzer = StrategicAnalyzer(kms_anuales=self.kms_anuales, driver_cost=self.coste_conductor)
        
        # Obtener tarifa de ingresos según tipo
        tarifa = config.TARIFA_INTERNA_DIESEL if tipo == "diesel" else config.TARIFA_INTERNA_EV
        
        # Ejecutar análisis dinámico (DCF)
        res = analyzer.evaluar_rentabilidad_compra(tipo, tarifa)
        
        # Calcular el MCA medio para el pie de página del dashboard
        mca_medio = sum(res["flujos"][1:]) / (len(res["flujos"]) - 1)
        
        return {
            "anos": res["anos"],
            "km": res["km"],
            "mca": round(mca_medio, 1),
            "capex_neto": round(analyzer.params[tipo]["capex"] - (analyzer.params[tipo].get("ayuda_moves", 0) if tipo == "electrico" else 0), 1),
            "roi": res["roi"],
            "tir": res["tir"]
        }

    def _calcular_tir_simple(self, cash_flows, iterations=1000):
        """Calcula la TIR usando el método de Newton-Raphson."""
        rate = 0.1 # Estimación inicial (10%)
        for i in range(iterations):
            npv = sum(cf / (1 + rate)**t for t, cf in enumerate(cash_flows))
            d_npv = sum(-t * cf / (1 + rate)**(t + 1) for t, cf in enumerate(cash_flows))
            if abs(d_npv) < 1e-6: break
            new_rate = rate - npv / d_npv
            if abs(new_rate - rate) < 1e-6: return new_rate
            rate = new_rate
        return rate

    def generar_matriz_resumen(self) -> dict:
        """Devuelve comparativa Diésel vs Eléctrico."""
        return {
            "diesel": self.analizar_recuperacion("diesel"),
            "electrico": self.analizar_recuperacion("electrico")
        }
