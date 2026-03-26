import math
import logging

logger = logging.getLogger(__name__)

class Pallet:
    """
    Representa una unidad de carga (Pallet) con sus dimensiones físicas.
    """
    def __init__(self, largo: float, ancho: float, alto: float, remontable: bool = False, nombre: str = "Pallet"):
        """
        Inicializa un pallet con sus dimensiones y propiedad de remontabilidad.

        Parametros
        ----------
        largo : float
            Longitud del pallet en metros.
        ancho : float
            Anchura del pallet en metros.
        alto : float
            Altura total del pallet (incluyendo la carga) en metros.
        remontable : bool
            True si se pueden apilar otros pallets encima de este.
        nombre : str
            Identificador descriptivo del pallet.
        """
        self.largo = largo
        self.ancho = ancho
        self.alto = alto
        self.remontable = remontable
        self.nombre = nombre

class Container:
    """
    Representa el espacio de carga (Contenedor o Caja de Camión).
    """
    def __init__(self, largo: float, ancho: float, alto: float, nombre: str = "Contenedor"):
        """
        Inicializa un contenedor con sus dimensiones internas.

        Parametros
        ----------
        largo : float
            Longitud interna en metros.
        ancho : float
            Anchura interna en metros.
        alto : float
            Altura interna en metros.
        nombre : str
            Identificador del contenedor (ej. '20ft', 'Caja Camión Rígido').
        """
        self.largo = largo
        self.ancho = ancho
        self.alto = alto
        self.nombre = nombre

    def calcular_capacidad_maxima(self, pallet: Pallet) -> int:
        """
        Calcula cuántos pallets caben físicamente en el contenedor, 
        según si el pallet permite remontabilidad o no.
        
        Usa redondeo hacia abajo (math.floor) para garantizar que los
        pallets quepan físicamente en las dimensiones dadas.
        """
        # 1. Calcular cuántos caben en la superficie (planta)
        filas = math.floor(self.largo / pallet.largo)
        columnas = math.floor(self.ancho / pallet.ancho)
        unidades_suelo = filas * columnas

        # 2. Determinar niveles de altura según remontabilidad
        if pallet.remontable:
            # Si es remontable, aprovechamos la altura total (volumen)
            niveles = math.floor(self.alto / pallet.alto)
            logger.info(f"Carga remontable detectada para {pallet.nombre}. Niveles calculados: {niveles}")
        else:
            # Si no es remontable, solo se usa el primer nivel (área base)
            niveles = 1
            logger.info(f"Carga NO remontable para {pallet.nombre}. Solo se usará el suelo.")

        # 3. Resultado final (siempre entero)
        capacidad_total = unidades_suelo * niveles
        
        return int(capacidad_total)
