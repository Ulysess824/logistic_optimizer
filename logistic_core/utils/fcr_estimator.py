"""
CO2 Emission Estimator for VRP based on Fuel Consumption Rate (FCR) model.
 
Reference:
    * Xiao et al. (2012) - DOI: 10.1016/j.cor.2011.08.010 (Linear interpolation Eq.3)
    * Grigoratos et al. (2019) - DOI: 10.1016/j.trd.2019.08.002 (VECTO 5-LH Factors)
    * See also: docs/Bibliografia.md
 
Formula applied:
    CO2_total = d * (FE_vacuo + (FE_carregado - FE_vacuo) * (carga / max_carga))
    where:
        FE_vacuo (Euro VI 40t) = 0.652 kg CO2/km
        FE_carregado (25t load) = 1.085 kg CO2/km

Reference:
    * GLEC Framework v3.0 / ISO 14083
    * docs/Bibliografia.md (Ref: Grigoratos et al. 2019)
 
Methodologies:
    1. Fuel-based (Primary): CO2 = Liters * 2.68 kg/L (GLEC v3)
    2. Activity-based (Default): CO2 = d * (FE_empty + (FE_loaded - FE_empty) * (load / max_load))
"""
 
from dataclasses import dataclass, field
from typing import Dict, Any
 
 
class FCREmissionEstimator:
    """
    GLEC-compliant Emission Estimator supporting dual methodologies.
    
    Attributes:
        co2_per_liter: kg CO2/L for diesel (Standard GLEC v3: 2.68).
        intensity_gtkm: g CO2/tkm incremental (Standard 40t: 17.32g).
        empty_floor_kgkm: kg CO2/km when empty (Standard: 0.652).
    """
 
    def __init__(
        self,
        co2_per_liter: float = 2.68,
        intensity_gtkm: float = 17.32,
        empty_floor_kgkm: float = 0.652,
        max_load_t: float = 25.0,
        **kwargs # Captura y descarta parámetros obsoletos (fcr_loaded, alpha, etc.)
    ):
        # FIX: Unificado a 2.68 según estándar GLEC v3
        self.co2_per_liter = co2_per_liter
        # FIX: Alineado a 17.32g/tkm para que coincida con FE_empty(0.652) y FE_loaded(1.085)
        self.intensity_gtkm = intensity_gtkm
        self.empty_floor_kgkm = empty_floor_kgkm
        self.max_load_t = max_load_t
 
    def calculate_fuel_based(self, liters: float) -> float:
        """Calculates CO2 based on actual fuel consumption (Primary GLEC)."""
        return liters * self.co2_per_liter
 
    def calculate_activity_based(self, distance_km: float, weight_t: float) -> float:
        """
        Calculates CO2 based on logistics activity (Default GLEC).
        Formula matches Xiao et al. linear interpolation.
        """
        # FIX: Implementación alineada explícitamente con el modelo de interpolación lineal
        emissions_empty_base = distance_km * self.empty_floor_kgkm
        emissions_cargo = (weight_t * distance_km * self.intensity_gtkm) / 1000.0
        return emissions_empty_base + emissions_cargo
 
    def calculate(self, distance_km: float, weight_t: float, liters: float = None) -> float:
        """
        Main entry point. Defaults to activity-based if liters are missing.
        """
        if liters is not None and liters > 0:
            return self.calculate_fuel_based(liters)
        return self.calculate_activity_based(distance_km, weight_t)
 
    def co2_partial_load(
        self,
        distance_km: float,
        current_load: float,
        max_load: float = None, # Ignorado (para compatibilidad)
        unit_is_kg: bool = True
    ) -> float:
        """Backwards compatibility: maps to activity-based."""
        weight_t = current_load / 1000.0 if unit_is_kg else current_load
        return self.calculate_activity_based(distance_km, weight_t)
 
    def co2_total_trip(
        self,
        dist_loaded: float,
        dist_empty: float,
        weight_tons: float
    ) -> float:
        """
        Calcula el CO2 total de un viaje con tramos cargados y vacíos.
        """
        # FIX: Eliminado parámetro max_tons inconsistente y corregida llamada directa a actividad
        co2_loaded = self.calculate_activity_based(dist_loaded, weight_tons)
        co2_empty = self.calculate_activity_based(dist_empty, 0)
        return co2_loaded + co2_empty
