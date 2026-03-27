import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path para importar logistic_core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logistic_core.utils.cost_estimator import CostEstimator, FleetSizer

def demo():
    print("=== DEMOSTRACIÓN DE CÁLCULO DE TCO ===")
    
    # Configuración de costes propios (Euros)
    fixed_costs = {
        "amortizacion_anual": 15000,
        "seguro_anual": 3000,
        "salario_fijo_conductor": 35000,
        "impuestos_tasas": 1200
    }
    
    variable_costs = {
        "combustible_km": 0.45,   # Euros por km
        "mantenimiento_km": 0.08,
        "neumaticos_km": 0.03,
        "adblue_km": 0.02
    }
    
    # Inicializar estimador con TCO
    estimator = CostEstimator(
        fixed_costs_annual=fixed_costs,
        variable_costs_km=variable_costs,
        annual_km_per_truck=120000
    )
    
    distancia = 450 # km (ej. Mengíbar -> Alcalá)
    coste = estimator.estimate_cost(distancia)
    breakdown = estimator.get_cost_breakdown()
    
    print(f"Distancia: {distancia} km")
    print(f"Tarifa Calculada: {estimator.price_per_km:.4f} €/km")
    print(f"Coste Total Trayecto: {coste:.2f} €")
    print("\nDesglose de Costes (€/km):")
    for concepto, valor in breakdown.items():
        print(f"  - {concepto:<25}: {valor:.4f} €/km")
        
    print("\n" + "="*40)
    print("=== DEMOSTRACIÓN DE DIMENSIONAMIENTO DE FLOTA ===")
    
    # Datos de salidas diarias (ejemplo simplificado)
    salidas_diarias = [
        {"plant": "Alcalá", "dist_km": 310, "demand": 4},
        {"plant": "Córdoba", "dist_km": 80, "demand": 3},
        {"plant": "Vigo", "dist_km": 680, "demand": 2},
        {"plant": "Huelva", "dist_km": 280, "demand": 5}
    ]
    
    fleet_info = FleetSizer.calculate_fleet_size(
        daily_departures=salidas_diarias,
        avg_speed_kmh=75,
        handling_time_h=3.0,
        work_hours_day=9.0,
        availability=0.9
    )
    
    print(f"Total Camiones Activos Necesarios: {fleet_info['total_active_trucks']}")
    print(f"Flota Objetivo (90% disponibilidad): {fleet_info['total_objective_fleet']}")
    print("\nDetalle por Planta:")
    for d in fleet_info['details']:
        print(f"  - {d['plant']:<15}: Ciclo {d['cycle_time']}h | Camiones: {d['active_trucks']}")

if __name__ == "__main__":
    demo()
