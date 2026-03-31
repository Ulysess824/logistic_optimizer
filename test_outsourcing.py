
import sys
import os

# Asegurar que podemos importar los módulos del core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from logistic_core.utils.external_cost_analyst import ExternalCostAnalyst
from logistic_core.config import INTERNAL_OPERATIONAL_TCO_RATE, EXTERNAL_PROVIDER_RATE_PER_KM

def test_outsourcing_logic():
    print("=== TEST DE LÓGICA DE OUTSOURCING ===")
    
    # 1. Definir los datos dinámicos (los que deberían salir de config.py)
    # Forzamos los valores del usuario si no están en config
    int_rate = INTERNAL_OPERATIONAL_TCO_RATE # Probablemente ~1.31
    ext_rate = EXTERNAL_PROVIDER_RATE_PER_KM # Debería ser 2.22
    
    print(f"Tarifa Interna (TCO): {int_rate} €/km")
    print(f"Tarifa Externa (Mkt): {ext_rate} €/km")
    
    # 2. Inicializar el analista con estos datos
    analyst = ExternalCostAnalyst(internal_rate=int_rate, external_rate=ext_rate)
    
    # 3. Datos sintéticos de una ruta (ejemplo: Alcalá de la captura)
    distancia_linehaul = 173.64 # km
    
    # 4. Procesar
    resultados = analyst.analyze_leg(distancia_linehaul)
    
    print("\n--- RESULTADOS PARA RUTA SINTÉTICA (173.64 km) ---")
    print(f"Coste Propio:  {resultados['internal_cost']} € (Esperado: {round(distancia_linehaul * int_rate, 2)})")
    print(f"Coste Externo: {resultados['external_cost']} € (Esperado: {round(distancia_linehaul * ext_rate, 2)})")
    print(f"Ahorro Neto:   {resultados['savings']} €")
    print(f"CO2 Estimado:  {resultados['co2_kg']} kg")

    # Verificación final
    if abs(resultados['external_cost'] - (distancia_linehaul * 2.22)) < 1.0:
        print("\n✅ ÉXITO: El motor está usando los 2.22 €/km correctamente.")
    else:
        print("\n❌ ERROR: El motor sigue usando la tarifa vieja.")

if __name__ == "__main__":
    test_outsourcing_logic()
