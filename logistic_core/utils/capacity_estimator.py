"""
Estimador de Capacidad de Pallets para contenedores de camión (Modelo 3D).

Dimensiones de referencia (Estándar Europeo):
    - Contenedor: 13.6m x 2.4m x 2.7m (Semirremolque estándar)
    - Pallet EUR (EPAL): 1.2m x 0.8m x 1.5m (Cargado)
"""

from dataclasses import dataclass
import math
from typing import Dict, Tuple


@dataclass
class Pallet:
    """Dimensiones físicas de un pallet (cargado)."""
    length_m: float = 1.2    # Estándar EUR/EPAL
    width_m: float  = 0.8    # Estándar EUR/EPAL
    height_m: float = 1.5    # Altura típica cargada


@dataclass
class TruckCapacityEstimator:
    """
    Estima la capacidad de pallets de un contenedor de camión en 3D.

    Lógica de apilamiento:
        - stackable=False → Una sola capa (layers=1)
        - stackable=True  → floor(container_height / pallet_height) capas

    Atributos:
        container_length_m: Longitud interna utilizable.
        container_width_m:  Anchura interna utilizable.
        container_height_m: Altura interna utilizable.
    """

    container_length_m: float = 13.6
    container_width_m:  float = 2.4
    container_height_m: float = 2.7

    def _floor_slots(self, pallet: Pallet) -> Tuple[int, int, int]:
        """Calcula slots en el suelo probando ambas orientaciones y eligiendo la mejor."""
        EPS = 1e-9
        
        # Orientación A: Largo del pallet con Largo del camión
        cols_a = math.floor((self.container_length_m + EPS) / pallet.length_m)
        rows_a = math.floor((self.container_width_m + EPS) / pallet.width_m)
        total_a = cols_a * rows_a
        
        # Orientación B: Ancho del pallet con Largo del camión
        cols_b = math.floor((self.container_length_m + EPS) / pallet.width_m)
        rows_b = math.floor((self.container_width_m + EPS) / pallet.length_m)
        total_b = cols_b * rows_b
        
        if total_a >= total_b:
            return cols_a, rows_a, total_a
        else:
            return cols_b, rows_b, total_b

    def _layers(self, pallet: Pallet, stackable: bool) -> int:
        """Capas verticales que caben. Siempre >= 1."""
        if not stackable:
            return 1
        return max(math.floor(self.container_height_m / pallet.height_m), 1)

    def capacity(self, pallet: Pallet, stackable: bool = False) -> Dict:
        """
        Número máximo de pallets que caben en el contenedor.

        Args:
            pallet:    Dimensiones del pallet a usar.
            stackable: Si la carga es apilable.

        Returns:
            dict con floor_slots, layers, total_pallets y resumen.
        """
        cols, rows, floor = self._floor_slots(pallet)
        layers = self._layers(pallet, stackable)
        total  = floor * layers

        return {
            "cols_along_length": cols,
            "rows_along_width":  rows,
            "floor_slots":       floor,
            "layers":            layers,
            "total_pallets":     total,
            "stackable":         stackable,
            "summary": (
                f"{cols} columnas × {rows} filas × {layers} capas = {total} pallets"
            ),
        }

    def fits(self, n_pallets: int, pallet: Pallet, stackable: bool = False) -> Dict:
        """
        Comprueba si n_pallets caben en el contenedor.

        Args:
            n_pallets: Número de pallets a cargar.
            pallet:    Dimensiones del pallet.
            stackable: Si el grupo es apilable.

        Returns:
            dict con fits (bool), detalles de capacidad y excedente/déficit.
        """
        cap = self.capacity(pallet, stackable)
        total = cap["total_pallets"]
        delta = total - n_pallets

        return {
            "fits":          delta >= 0,
            "requested":     n_pallets,
            "max_capacity":  total,
            "surplus":       max(delta, 0),
            "deficit":       max(-delta, 0),
            "stackable":     stackable,
            "summary": (
                f"{'✓ Cabe' if delta >= 0 else '✗ No cabe'}: "
                f"{n_pallets} solicitados, {total} disponibles "
                f"({'excedente' if delta >= 0 else 'déficit'} {abs(delta)})"
            ),
        }
