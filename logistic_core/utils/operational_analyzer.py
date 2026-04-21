"""
operational_analyzer.py
──────────────────────
Motor de Analítica Operativa Diaria.
Se encarga de evaluar el ahorro directo, retorno evitado, y eficiencia a nivel logístico (viajes/rutas)
en contraposición a la analítica de inversión de largo plazo.
"""
import logging

logger = logging.getLogger(__name__)

class OperationalAnalyzer:
    """
    Gestiona la evaluación operativa diaria de las rutas, incluyendo cálculos
    de rendimiento en tiempo efectivo, kilómetros vacíos evitados y rentabilidad
    del viaje optimizado vs mercado.
    """
    def __init__(self):
        pass

    def calculate_avoided_sunk_cost(self, empty_km_saved: float, internal_tco_rate: float) -> float:
        """
        Calcula el retorno monetario de los kilómetros en vacío evitados.
        
        En el transporte tradicional, los camiones dedicados asumen el costo total de retorno 
        a su base como un "sunk cost" (coste hundido). Si optimizamos y evitamos realizar
        esos kilómetros vacíos, todo ese dinero que se iba a gastar indefectiblemente 
        se transforma en una ganancia neta operativa (ahorro).

        Args:
            empty_km_saved (float): Cantidad de kilómetros vacíos que se han logrado evitar.
            internal_tco_rate (float): Precio técnico interno por kilómetro del camión.

        Returns:
            float: Dinero retenido que suma a la cuenta de resultados de la operación diaria.
        """
        if empty_km_saved <= 0:
            return 0.0
        return empty_km_saved * internal_tco_rate


if __name__ == "__main__":
    # --- SCRIPT DE PRUEBA SINTÉTICO (Validación Rápida) ---
    print("==================================================")
    print("   PRUEBA: OPERATIONAL ANALYZER (DIA A DIA)")
    print("==================================================")
    
    analyzer = OperationalAnalyzer()
    
    # Supongamos que una ruta iba a realizar 150 km vacíos para regresar, y tras optimizar
    # logra enganchar en una fábrica cercana y solo hace 30 km vacíos finales.
    km_vacios_base = 150.0
    km_vacios_optimizados = 30.0
    km_evitados = km_vacios_base - km_vacios_optimizados
    
    tco_interno = 1.05  # €/km
    
    ganancia_neta_dia = analyzer.calculate_avoided_sunk_cost(km_evitados, tco_interno)
    
    print(f"Kilómetros Vacíos Originales : {km_vacios_base} km")
    print(f"Kilómetros Vacíos Finales    : {km_vacios_optimizados} km")
    print(f"Kilómetros Vacíos Evitados   : {km_evitados} km")
    print(f"Tarifa Interna (TCO)         : {tco_interno} €/km")
    print(f"--------------------------------------------------")
    print(f"-> AHORRO / RETORNO GENERADO : {ganancia_neta_dia:.2f} € en este solo viaje\n")
