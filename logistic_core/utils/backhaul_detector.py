import logging
import numpy as np
from typing import List, Dict, Any, Optional
from logistic_core.utils.geo import GeoUtils
from logistic_core.config import (
    BACKHAUL_SEARCH_RADIUS_KM,
    BACKHAUL_MAX_RETURN_PALLETS,
)

logger = logging.getLogger(__name__)


class BackhaulDetector:
    """Detecta nodos candidatos de recogida de retorno para cada ruta VRP.

    Dado el ultimo cliente de entrega de una ruta, busca entre todas las
    plantas de carton disponibles las que esten dentro del radio configurado
    (BACKHAUL_SEARCH_RADIUS_KM). Estas plantas pueden actuar como punto de
    pickup en el camino de regreso al deposito.

    La planta origen de la propia ruta se excluye automaticamente para evitar
    circuitos absurdos.
    """

    def __init__(self, all_carton_plants: List[Dict[str, Any]], geo_engine=None):
        """
        Args:
            all_carton_plants: Lista de dicts con las plantas disponibles en
                               el sistema (formato del JSON de entrada).
            geo_engine: Instancia de GeoUtils. Si no se pasa, se instancia
                        una nueva con Haversine por defecto.
        """
        self.plants = all_carton_plants
        self.geo = geo_engine if geo_engine else GeoUtils(api_type="haversine")

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------
    def find_candidates(
        self,
        route: List[Dict[str, Any]],
        distance_matrix: np.ndarray,
        search_radius_km: Optional[float] = None,
        max_return_pallets: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Devuelve las plantas candidatas de backhauling para una ruta dada.

        Args:
            route:               Lista de nodos de la ruta (formato de solver).
            distance_matrix:     Matriz de distancias completa del sistema.
            search_radius_km:    Radio de busqueda en km. None usa el valor
                                 por defecto de config.
            max_return_pallets:  Limite de pallets de retorno. None usa config.

        Returns:
            Lista de dicts con las plantas candidatas, ordenadas por
            distancia ascendente al ultimo cliente de la ruta.
            Cada dict incluye:
              - id, name, lat, lng  (datos de la planta)
              - dist_to_last_client_km  (distancia haversine al ultimo cliente)
              - dist_to_depot_km        (distancia haversine al deposito)
              - detour_vs_direct_km     (desvio extra vs. regresar directo)
              - return_pallets_capacity (pallets que puede recoger)
        """
        radius = search_radius_km if search_radius_km is not None else BACKHAUL_SEARCH_RADIUS_KM
        max_pallets = max_return_pallets if max_return_pallets is not None else BACKHAUL_MAX_RETURN_PALLETS

        # Identificar nodo origen de la ruta (primera planta de carton visitada)
        origin_plant = next((n for n in route if n["type"] == "carton_plant"), None)
        origin_plant_id = origin_plant["id"] if origin_plant else None

        # Ultimo cliente de entrega
        customers = [n for n in route if n["type"] == "customer"]
        if not customers:
            logger.debug("Ruta sin clientes. No aplica backhauling.")
            return []

        last_client = customers[-1]
        lc_lat = last_client["lat"]
        lc_lng = last_client["lng"]

        # Deposito (primer nodo de la ruta)
        depot = route[0]
        depot_lat = depot["lat"]
        depot_lng = depot["lng"]

        # Distancia directa desde ultimo cliente al deposito (haversine, referencia)
        dist_lc_depot = GeoUtils.haversine_km(lc_lat, lc_lng, depot_lat, depot_lng)

        candidates = []
        for plant in self.plants:
            p_id = plant.get("id", "")

            # Excluir la planta origen de la propia ruta
            if p_id == origin_plant_id:
                continue

            p_lat = plant.get("lat")
            p_lng = plant.get("lng")
            if p_lat is None or p_lng is None:
                continue

            dist_to_lc = GeoUtils.haversine_km(lc_lat, lc_lng, p_lat, p_lng)
            if dist_to_lc > radius:
                continue

            dist_plant_depot = GeoUtils.haversine_km(p_lat, p_lng, depot_lat, depot_lng)
            # Desvio extra = (lc -> planta -> deposito) - (lc -> deposito directo)
            detour = (dist_to_lc + dist_plant_depot) - dist_lc_depot

            candidates.append({
                "id": p_id,
                "name": plant.get("name", p_id),
                "lat": p_lat,
                "lng": p_lng,
                "dist_to_last_client_km": round(dist_to_lc, 2),
                "dist_to_depot_km": round(dist_plant_depot, 2),
                "detour_vs_direct_km": round(detour, 2),
                "return_pallets_capacity": max_pallets,
            })

        candidates.sort(key=lambda x: x["dist_to_last_client_km"])

        if candidates:
            logger.info(
                "Backhauling: %d candidatos encontrados para ruta con ultimo cliente '%s' (radio %.0f km).",
                len(candidates), last_client.get("name", "?"), radius
            )
            for c in candidates:
                logger.debug(
                    "  -> %s | dist_lc=%.1f km | desvio=%.1f km",
                    c["name"], c["dist_to_last_client_km"], c["detour_vs_direct_km"]
                )
        else:
            logger.info(
                "Backhauling: ningun candidato en %.0f km del ultimo cliente '%s'.",
                radius, last_client.get("name", "?")
            )

        return candidates

    def analyze_all_routes(
        self,
        routes: List[List[Dict[str, Any]]],
        distance_matrix: np.ndarray,
        search_radius_km: Optional[float] = None,
        max_return_pallets: Optional[int] = None,
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Aplica find_candidates a todas las rutas y devuelve un dict indexado.

        Returns:
            Dict {route_index: [lista de plantas candidatas]}
        """
        results = {}
        for idx, route in enumerate(routes):
            candidates = self.find_candidates(
                route=route,
                distance_matrix=distance_matrix,
                search_radius_km=search_radius_km,
                max_return_pallets=max_return_pallets,
            )
            if candidates:
                results[idx] = candidates

        logger.info(
            "Backhauling: %d de %d rutas con al menos un candidato de retorno.",
            len(results), len(routes)
        )
        return results
