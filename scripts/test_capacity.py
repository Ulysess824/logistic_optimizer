"""
Script de prueba para el Estimador de Capacidad 3D.
Valida la lógica de slots de suelo y capas verticales con datos sintéticos.
"""

import os
import sys

# Asegurar que el core se pueda importar
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logistic_core.utils.capacity_estimator import TruckCapacityEstimator, Pallet

def run_test():
    estimator = TruckCapacityEstimator()
    pallet_std = Pallet() # 1.2 x 0.8 x 1.5
    
    print("--- 1. ESCENARIO BASE: CARGA NO APILABLE ---")
    res_base = estimator.capacity(pallet_std, stackable=False)
    print(f"Capacidad Suelo: {res_base['summary']}")
    # 13.6/1.2 = 11.3 (11) | 2.4/0.8 = 3. Total = 33 pallets.
    
    print("\n--- 2. ESCENARIO APILABLE: CARGA DOBLE ---")
    res_stack = estimator.capacity(pallet_std, stackable=True)
    print(f"Capacidad Total (Stack): {res_stack['summary']}")
    # Altura 2.7 / 1.5 = 1.8 (1 capa). 
    # NOTA: En un camión de 2.7m no caben 2 capas de 1.5m (3.0m).
    
    print("\n--- 3. ESCENARIO APILABLE (PALLETS BAJOS: 1.2m) ---")
    pallet_low = Pallet(height_m=1.2)
    res_low = estimator.capacity(pallet_low, stackable=True)
    print(f"Capacidad con Pallets de 1.2m: {res_low['summary']}")
    # 2.7 / 1.2 = 2.25 (2 capas). Total = 33 * 2 = 66 pallets.

    print("\n--- 4. VALIDACIÓN DE AJUSTE (FITS) ---")
    test_cases = [
        (33, pallet_std, False, "Carga Full Suelo (No Stack)"),
        (34, pallet_std, False, "Exceso 1 Pallet (No Stack)"),
        (60, pallet_low, True, "Carga 60 pallets bajos (Stack)"),
        (70, pallet_low, True, "Exceso 70 pallets bajos (Stack)")
    ]
    
    for n, p, s, desc in test_cases:
        fit_check = estimator.fits(n, p, s)
        print(f"[{desc}] {fit_check['summary']}")

if __name__ == "__main__":
    run_test()
