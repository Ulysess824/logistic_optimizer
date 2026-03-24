"""
CO2 Emission Estimator for VRP based on Fuel Consumption Rate (FCR) model.
 
Reference:
    Xiao et al. (2012) - "Development of a fuel consumption optimization
    model for the capacitated vehicle routing problem"
    Computers & Operations Research 39, 1419–1431
    Equation (3): ρ(Q1) = ρ0 + ((ρ* - ρ0) / Q) * Q1
 
Formula applied:
    CO2_total = n * d * fcr_loaded * (1 + alpha)
    where alpha = ρ0 / ρ* ≈ 0.5 (empty/loaded FCR ratio, Xiao et al. Fig.1)
"""
 
from dataclasses import dataclass, field
 
 
@dataclass
class FCREmissionEstimator:
    """
    Estimates CO2 emissions for a VRP route leg including return trip empty.
 
    Attributes:
        fcr_loaded:   CO2 per km when fully loaded (kg CO2/km)
        alpha:        Ratio of empty FCR to loaded FCR (default 0.5, Xiao et al.)
        empty_ratio_range: Sensitivity range for alpha (min, max)
    """
 
    fcr_loaded: float
    alpha: float = 0.5
    empty_ratio_range: tuple[float, float] = field(default=(0.45, 0.60))
 
    @property
    def fcr_empty(self) -> float:
        """FCR when returning empty (kg CO2/km)."""
        return self.fcr_loaded * self.alpha
 
    def co2_one_trip(self, distance_km: float) -> float:
        """
        CO2 for a single trip (one way, loaded).
            CO2 = d * fcr_loaded
        """
        return distance_km * self.fcr_loaded
 
    def co2_round_trip(self, distance_km: float) -> float:
        """
        CO2 for a full round trip (loaded out + empty return).
            CO2 = d * fcr_loaded * (1 + alpha)
        """
        return distance_km * self.fcr_loaded * (1 + self.alpha)
 
    def co2_route(self, distance_km: float, n_trips: int) -> dict:
        """
        CO2 for n_trips over a given distance, with empty return each time.
 
        Args:
            distance_km: One-way distance of the route leg (km)
            n_trips:     Number of loaded trips (cargas)
 
        Returns:
            dict with loaded, empty and total CO2 in tonnes.
        """
        co2_loaded = n_trips * distance_km * self.fcr_loaded
        co2_empty  = n_trips * distance_km * self.fcr_empty
        co2_total  = co2_loaded + co2_empty
 
        return {
            "distance_km":   distance_km,
            "n_trips":       n_trips,
            "fcr_loaded":    self.fcr_loaded,
            "fcr_empty":     round(self.fcr_empty, 4),
            "alpha":         self.alpha,
            "co2_loaded_t":  round(co2_loaded / 1000, 2),
            "co2_empty_t":   round(co2_empty  / 1000, 2),
            "co2_total_t":   round(co2_total  / 1000, 2),
        }
 
    def co2_sensitivity(self, distance_km: float, n_trips: int) -> dict:
        """
        Sensitivity analysis over the alpha range (empty_ratio_range).
        Useful when real empty-return data is unavailable.
 
        Returns:
            dict with CO2 total (tonnes) for low, base and high alpha.
        """
        results = {}
        alphas = {
            "low":  self.empty_ratio_range[0],
            "base": self.alpha,
            "high": self.empty_ratio_range[1],
        }
        for label, a in alphas.items():
            co2 = n_trips * distance_km * self.fcr_loaded * (1 + a)
            results[label] = round(co2 / 1000, 2)
        return results
 
    def co2_partial_load(
        self,
        distance_km: float,
        current_load: float,
        max_load: float,
    ) -> float:
        """
        CO2 for a leg with partial load using Xiao et al. Eq.(3).
        Useful inside VRP route evaluation when load varies per arc.
 
            ρ(Q1) = ρ0 + ((ρ* - ρ0) / Q) * Q1
            CO2   = d  * ρ(Q1)
 
        Args:
            distance_km:   Arc distance (km)
            current_load:  Load carried on this arc (same units as max_load)
            max_load:      Vehicle max capacity
 
        Returns:
            CO2 in kg for this arc.
        """
        fcr_arc = self.fcr_empty + (
            (self.fcr_loaded - self.fcr_empty) / max_load
        ) * current_load
        return distance_km * fcr_arc