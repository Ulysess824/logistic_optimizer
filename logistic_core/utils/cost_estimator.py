import logging

import logging
from typing import Dict, List

class CostEstimator:
    """Clase para estimar costes operativos de transporte (TCO)."""
    
    def __init__(self, 
                 price_per_km: float = 1.14,
                 fixed_costs_annual: Dict[str, float] = None,
                 variable_costs_km: Dict[str, float] = None,
                 annual_km_per_truck: float = 120000):
        """
        Inicializa el estimador con parámetros de TCO o un precio base.
        
        Args:
            price_per_km (float): Tarifa por km (usada si no se definen costes detallados).
            fixed_costs_annual (dict): Costes fijos anuales (Seguros, Amortización, etc.).
            variable_costs_km (dict): Costes variables por km (Combustible, Neumáticos, etc.).
            annual_km_per_truck (float): Kilometraje anual para distribuir costes fijos.
        """
        self.fixed_costs_annual = fixed_costs_annual or {}
        self.variable_costs_km = variable_costs_km or {}
        self.annual_km_per_truck = annual_km_per_truck
        
        if self.fixed_costs_annual and self.variable_costs_km:
            total_fixed = sum(self.fixed_costs_annual.values())
            self.price_per_km = (total_fixed / self.annual_km_per_truck) + sum(self.variable_costs_km.values())
        else:
            self.price_per_km = price_per_km
            
        logging.info(f"CostEstimator (TCO) inicializado con tarifa calculada: {self.price_per_km:.4f} €/km")

    def estimate_cost(self, distance: float) -> float:
        """Calcula el coste total de un trayecto basado en la distancia."""
        if distance < 0:
            logging.warning("Distancia negativa en cálculo de coste.")
            return 0.0
        return round(distance * self.price_per_km, 2)

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Devuelve el desglose de costes en €/km."""
        if not self.fixed_costs_annual:
            return {"tarifa_fija": self.price_per_km}
            
        breakdown = {k: v / self.annual_km_per_truck for k, v in self.fixed_costs_annual.items()}
        breakdown.update(self.variable_costs_km)
        return breakdown

    def __repr__(self):
        return f"CostEstimator(rate={self.price_per_km:.2f} €/km)"


class FleetSizer:
    """Calcula el número objetivo de vehículos necesarios."""

    @staticmethod
    def calculate_fleet_size(daily_departures: List[Dict], 
                             avg_speed_kmh: float = 75, 
                             handling_time_h: float = 3.0, 
                             work_hours_day: float = 9.0,
                             availability: float = 0.9) -> Dict:
        """
        Calcula la flota necesaria basándose en el tiempo de ciclo.
        
        Args:
            daily_departures (list): Lista de dicts [{'plant': str, 'dist_km': float, 'demand': int}]
            avg_speed_kmh (float): Velocidad media incluyendo paradas cortas.
            handling_time_h (float): Tiempo total de carga/descarga por ciclo.
            work_hours_day (float): Horas de conducción/trabajo por día.
            availability (float): Factor de disponibilidad (0.0 a 1.0).
        """
        total_active_trucks = 0
        details = []

        for route in daily_departures:
            dist = route['dist_km']
            demand = route['demand']
            
            # Ciclo: Ida y vuelta (2 * dist) / velocidad + tiempos muertos
            cycle_time = (2 * dist / avg_speed_kmh) + handling_time_h
            
            # Camiones necesarios: Demanda * (Tiempo Ciclo / Horas Trabajo)
            needed = demand * (cycle_time / work_hours_day)
            total_active_trucks += needed
            
            details.append({
                "plant": route['plant'],
                "cycle_time": round(cycle_time, 2),
                "active_trucks": round(needed, 2)
            })

        total_fleet = total_active_trucks / availability
        
        return {
            "total_active_trucks": round(total_active_trucks, 2),
            "total_objective_fleet": round(total_fleet, 2),
            "availability_factor": availability,
            "details": details
        }
