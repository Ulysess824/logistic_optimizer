import math
from typing import Dict, Any

class FleetCapexEstimator:
    """
    Clase para estimar el tamaño de flota logística utilizando la Ley de Little (L = lambda * W)
    y calcular el CAPEX total de la inversión en vehículos pesados (Heavy Fleet).
    """

    def __init__(self, daily_dispatch_rate: float, unit_truck_cost: float, utilization_buffer: float = 1.15):
        """
        Inicializa el estimador de flota.
        
        Args:
            daily_dispatch_rate (float): Tasa de salida diaria (lambda). Ej. 38 camiones al día.
            unit_truck_cost (float): Costo unitario de adquisición por camión pesado (CAPEX).
            utilization_buffer (float): Margen de seguridad para cubrir mantenimientos preventivos, 
                                        averías e inactividad (Ej: 1.15 = 15% extra de flota puente).
        """
        self.daily_dispatch_rate = daily_dispatch_rate
        self.unit_truck_cost = unit_truck_cost
        self.utilization_buffer = utilization_buffer

    def estimate_fleet_size(self, average_cycle_time_days: float) -> int:
        """
        Calcula el tamaño de flota operativa requerida basado en la Ley de Little.
        
        Args:
            average_cycle_time_days (float): Tiempo promedio total del ciclo de un viaje (W) en días.
            
        Returns:
            int: Cantidad de camiones físicos requeridos (redondeado hacia arriba al entero más cercano).
        """
        # Ley de Little (Estado Teórico Estacionario): L = lambda * W
        theoretical_fleet = self.daily_dispatch_rate * average_cycle_time_days
        
        # Ajuste al mundo real aplicando el buffer de utilización
        real_fleet = theoretical_fleet * self.utilization_buffer
        
        # Es imposible adquirir fracciones de de camión, redondeamos siempre hacia arriba (Techo)
        return math.ceil(real_fleet)

    def calculate_total_capex(self, average_cycle_time_days: float) -> float:
        """
        Calcula el CAPEX (Capital Expenditure) total requerido para la flota configurada.
        """
        required_fleet = self.estimate_fleet_size(average_cycle_time_days)
        return required_fleet * self.unit_truck_cost

    def generate_investment_summary(self, average_cycle_time_days: float) -> Dict[str, Any]:
        """
        Genera un diccionario analítico estructurado con todos los KPI de la estimación.
        Ideal para inyectar directamente en el pipeline de simulación o log de reporte.
        """
        theoretical_base = self.daily_dispatch_rate * average_cycle_time_days
        required_fleet = self.estimate_fleet_size(average_cycle_time_days)
        total_capex = required_fleet * self.unit_truck_cost
        
        return {
            "daily_dispatch_rate": self.daily_dispatch_rate,
            "average_cycle_time_days": average_cycle_time_days,
            "theoretical_fleet_base": round(theoretical_base, 2),
            "utilization_buffer_applied": self.utilization_buffer,
            "final_required_fleet": required_fleet,
            "unit_truck_cost": self.unit_truck_cost,
            "total_capex_investment": total_capex
        }

# ==============================================================================
# SCRIPT DE EJEMPLO DE USO Y VALIDACIÓN AISLADA
# ==============================================================================
if __name__ == "__main__":
    from logistic_core.config import (
        CAPEX_TRUCK_UNIT_COST, DEFAULT_CYCLE_TIME_DAYS, 
        DAILY_TRUCK_OUTBOUND, DEFAULT_FLEET_BUFFER
    )
    
    # 2. Instanciación del módulo de cálculo importando de config.py
    capex_estimator = FleetCapexEstimator(
        daily_dispatch_rate=DAILY_TRUCK_OUTBOUND,
        unit_truck_cost=CAPEX_TRUCK_UNIT_COST,
        utilization_buffer=DEFAULT_FLEET_BUFFER
    )

    # 3. Ejecución del cálculo
    resumen = capex_estimator.generate_investment_summary(average_cycle_time_days=DEFAULT_CYCLE_TIME_DAYS)

    # 4. Impresión de Resultados en formato limpio (Clean Output)
    print("--- VALIDACION AISLADA: ESTIMACION CAPEX (LEY DE LITTLE) ---")
    print(f"Salidas diarias (lambda): {resumen['daily_dispatch_rate']} viajes/dia")
    print(f"Tiempo de ciclo logistico (W): {resumen['average_cycle_time_days']} dias")
    print(f"Flota minima teorica requerida: {resumen['theoretical_fleet_base']} vehiculos")
    print(f"Flota instalada final (real): {resumen['final_required_fleet']} vehiculos fisicos")
    print(f"INVERSION TOTAL CAPEX: ${resumen['total_capex_investment']:,.2f}")
