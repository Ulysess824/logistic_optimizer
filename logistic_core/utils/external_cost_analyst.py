import logging
from typing import Dict, Any

from logistic_core.utils.fcr_estimator import FCREmissionEstimator

class ExternalCostAnalyst:
    """
    Analista de comparación de costes: Flota Propia vs Empresa Externa (Outsourcing).
    Compara el tramo de entrega (Linehaul) bajo mimas condiciones de distancia.
    """
    
    def __init__(self, internal_rate: float = 1.14, external_rate: float = 1.35):
        """
        Args:
            internal_rate (float): Coste interno por km (€). Default: 1.14.
            external_rate (float): Tarifa externa por km (€). Default: 1.35.
        """
        self.internal_rate = internal_rate
        self.external_rate = external_rate
        self.co2_est = FCREmissionEstimator() # GLEC v3 Motor
        logging.info(f"ExternalCostAnalyst inicializado. Interno: {internal_rate} €/km, Externo: {external_rate} €/km")

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
