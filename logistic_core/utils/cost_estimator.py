import logging

class CostEstimator:
    """Clase para estimar costes operativos de transporte."""
    
    def __init__(self, price_per_km: float = 1.14):
        """
        Inicializa el estimador con un precio base por kilómetro.
        
        Args:
            price_per_km (float): Precio en euros por cada kilómetro recorrido.
        """
        self.price_per_km = price_per_km
        logging.info(f"CostEstimator inicializado con tarifa: {self.price_per_km} €/km")

    def estimate_cost(self, distance: float) -> float:
        """
        Calcula el coste total de un trayecto basado en la distancia.
        
        Args:
            distance (float): Distancia recorrida en km.
            
        Returns:
            float: Coste estimado en euros.
        """
        if distance < 0:
            logging.warning("Se ha intentado calcular el coste para una distancia negativa.")
            return 0.0
            
        return round(distance * self.price_per_km, 2)

    def __repr__(self):
        return f"CostEstimator(rate={self.price_per_km})"
