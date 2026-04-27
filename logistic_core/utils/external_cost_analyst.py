import logging
from typing import Dict, Any
import math
from logistic_core.config import TARIFA_INTERNA_DIESEL, EXTERNAL_PROVIDER_RATE_PER_KM
from logistic_core.utils.fcr_estimator import FCREmissionEstimator

class ExternalCostAnalyst:
    """
    Analiza la viabilidad financiera de las rutas generadas por OSRM VRPB 
    frente a un proveedor externo que cobra por Point-to-Point (Matriz orígenes-destinos).
    """

    def __init__(self, internal_rate: float = TARIFA_INTERNA_DIESEL, external_rate: float = EXTERNAL_PROVIDER_RATE_PER_KM):
        """
        Inicializa el analista financiero comparativo.
        
        Args:
            internal_rate: Coste interno en €/km (TCO unitario propio).
            external_rate: Estructura de costes de compra de transporte (€/km mercado).
        """
        self.internal_rate = internal_rate
        self.external_rate = external_rate or EXTERNAL_PROVIDER_RATE_PER_KM
        self.co2_est = FCREmissionEstimator() # GLEC v3 Motor
        logging.info(f"ExternalCostAnalyst inicializado. Interno: {self.internal_rate} €/km, Externo: {self.external_rate} €/km")

    def analyze_leg(self, linehaul_distance: float, load_tons: float = 25.0) -> Dict[str, Any]:
        """
        Compara los costes de una pierna de entrega específica.
        
        Args:
            linehaul_distance (float): Distancia Planta -> Cliente (km).
            load_tons (float): Toneladas transportadas.
            
        Returns:
            dict: Comparativa de costes y ahorros.
        """
        if linehaul_distance <= 0:
            return {}

        internal_cost = round(linehaul_distance * self.internal_rate, 2)
        external_cost = round(linehaul_distance * self.external_rate, 2)
        savings = round(external_cost - internal_cost, 2)
        
        # El CO2 se calcula según el modelo GLEC/VECTO para tramo cargado.
        # Ref: [DOI: 10.1016/j.trd.2019.08.002]
        co2_emissions = round(self.co2_est.calculate_activity_based(linehaul_distance, load_tons), 2)

        return {
            "distance_km": linehaul_distance,
            "internal_cost": internal_cost,
            "external_cost": external_cost,
            "savings": savings,
            "co2_kg": co2_emissions,
            "internal_rate": self.internal_rate,
            "external_rate": self.external_rate
        }

    def __repr__(self):
        return f"ExternalCostAnalyst(int={self.internal_rate}, ext={self.external_rate})"
