"""
chained_dispatcher.py
---------------------
Segunda pasada del solver para la logistica multi-planta encadenada.

Responsabilidad unica: dado el resultado de la Pasada 1 (rutas del solver
estandar), calcula los clientes remanentes de la Planta B (los que NO fueron
cubiertos por los camiones directos de B) y lanza una segunda ejecucion del
solver exclusivamente para asignarlos al camion encadenado (A -> B).

Patron: Two-Pass Chain Dispatch (equivalente al BackhaulDetector para la
logistica de retorno, pero orientado a la carga de entrega encadenada).
"""

import logging
import copy
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ChainedClientDispatcher:
    """
    Gestiona la segunda pasada del solver para asignar clientes remanentes
    de la Planta B al camion encadenado (A -> B).

    La primera pasada del solver asigna todos los clientes de B a los
    camiones directos de B. Esta clase detecta cuales quedaron fuera
    (remanentes) y construye un sub-problema reducido para re-enrutarlos
    en el camion que ya paso por A.

    Args:
        enriched_data:      Datos completos originales (paper_plant + carton_plants).
        geo_engine:         Instancia de GeoUtils para el sub-solver.
        distance_matrix:    Matriz de distancias precalculada (np.ndarray).
                            Reutilizada en la segunda pasada sin llamadas a API.
    """

    def __init__(self, enriched_data: Dict[str, Any], geo_engine, distance_matrix,
                 solver_nodes: Optional[List[Dict]] = None):
        self.enriched_data = enriched_data
        self.geo_engine = geo_engine
        self.distance_matrix = distance_matrix
        # Mapa {customer_id: matrix_idx} construido desde los nodos del solver P1.
        # Permite inyectar el matrix_idx correcto en los remanentes extraidos
        # del enriched_data original (que no han pasado por _parse_locations).
        self._node_idx_map: Dict[str, int] = {}
        if solver_nodes:
            for n in solver_nodes:
                if n.get('type') == 'customer' and 'id' in n:
                    self._node_idx_map[n['id']] = n['matrix_idx']

    # ------------------------------------------------------------------
    # Metodo 1: Deteccion de clientes remanentes
    # ------------------------------------------------------------------
    def get_remaining_clients(
        self,
        routes_pass1: List[List[Dict]],
        plant_b_id: str,
    ) -> List[Dict]:
        """
        Devuelve los clientes de plant_b que NO aparecen en ninguna ruta
        directa de la Pasada 1 asignada a camiones exclusivos de plant_b.

        Un camion es "directo de B" si contiene la planta B y NO contiene
        ninguna otra planta de carton distinta de B. Los clientes de B que
        aparecen en rutas encadenadas (que tambien contienen planta A) no
        se consideran cubiertos directamente.

        Args:
            routes_pass1: Lista de rutas de la Pasada 1.
            plant_b_id:   ID canonico de la Planta B (ej. "CP_HUELVA").

        Returns:
            Lista de dicts de clientes remanentes (formato identico a
            enriched_data['carton_plants'][i]['customers']).
        """
        # Rutas directas de B: contienen planta B y NO contienen ninguna otra planta
        direct_b_routes = []
        for route in routes_pass1:
            plant_nodes_in_route = [
                n for n in route if n.get("type") == "carton_plant"
            ]
            plant_ids_in_route = {
                n.get("id", "").split("_clone_")[0].split("_chain_")[0]
                for n in plant_nodes_in_route
            }

            has_b = plant_b_id in plant_ids_in_route
            only_b = len(plant_ids_in_route) == 1  # Solo B, sin otras plantas

            if has_b and only_b:
                direct_b_routes.append(route)

        logger.info(
            "[cyan]ChainDispatch:[/cyan] Rutas directas de %s detectadas: %d",
            plant_b_id,
            len(direct_b_routes),
        )

        # Clientes cubiertos por las rutas directas de B
        covered_ids = {
            n["id"]
            for route in direct_b_routes
            for n in route
            if n.get("type") == "customer"
        }

        logger.info(
            "[cyan]ChainDispatch:[/cyan] Clientes cubiertos por directas de %s: %s",
            plant_b_id,
            covered_ids,
        )

        # Todos los clientes de B en el enriched_data original
        all_b_clients = []
        for plant in self.enriched_data.get("carton_plants", []):
            if plant.get("id") == plant_b_id:
                all_b_clients = plant.get("customers", [])
                break

        # Remanentes = los que no estan cubiertos por rutas directas.
        # Se inyecta el matrix_idx correcto desde el mapa del solver P1 si esta disponible.
        remaining = []
        for c in all_b_clients:
            if c['id'] not in covered_ids:
                c_copy = copy.deepcopy(c)
                if self._node_idx_map and c['id'] in self._node_idx_map:
                    c_copy['matrix_idx'] = self._node_idx_map[c['id']]
                remaining.append(c_copy)

        logger.info(
            "[cyan]ChainDispatch:[/cyan] Clientes remanentes de %s: %d/%d",
            plant_b_id,
            len(remaining),
            len(all_b_clients),
        )

        return remaining

    # ------------------------------------------------------------------
    # Metodo 2: Construccion del sub-problema reducido
    # ------------------------------------------------------------------
    def build_chain_subproblem(
        self,
        plant_a_id: str,
        plant_b_id: str,
        remaining_clients: List[Dict],
        routes_pass1: List[List[Dict]],
    ) -> Optional[Dict]:
        """
        Construye el enriched_data minimo para el solver de la Pasada 2.

        El sub-problema incluye:
        - paper_plant: el deposito original (Mengibar).
        - carton_plants:
            * Planta A con los MISMOS clientes que tenia en el camion
              encadenado de la Pasada 1 (extraidos de routes_pass1).
            * Planta B con SOLO los clientes remanentes.

        Este diseno garantiza que la ruta de la Pasada 2 sea coherente:
        el camion hace A -> Clientes(A) -> B -> Clientes_remanentes(B).

        Args:
            plant_a_id:         ID de la Planta A.
            plant_b_id:         ID de la Planta B.
            remaining_clients:  Lista de clientes remanentes de B.
            routes_pass1:       Rutas de la Pasada 1 para extraer clientes de A.

        Returns:
            Dict con la estructura enriched_data del sub-problema,
            o None si no hay clientes remanentes.
        """
        if not remaining_clients:
            logger.info(
                "[cyan]ChainDispatch:[/cyan] Sin remanentes para %s. "
                "Pasada 2 omitida.",
                plant_b_id,
            )
            return None

        # Extraer clientes de A que el camion encadenado llevaba en la Pasada 1.
        # El camion encadenado es la ruta que contiene ambas plantas (A y B).
        clients_a_in_chain = []
        for route in routes_pass1:
            plant_ids = {
                n.get("id", "").split("_clone_")[0].split("_chain_")[0]
                for n in route
                if n.get("type") == "carton_plant"
            }
            if plant_a_id in plant_ids and plant_b_id in plant_ids:
                clients_a_in_chain = [
                    n for n in route if n.get("type") == "customer"
                    and n.get("parent_cp") == plant_a_id
                ]
                break

        # Si no se encontro ruta encadenada, usar todos los clientes de A originales
        if not clients_a_in_chain:
            logger.warning(
                "[yellow]ChainDispatch:[/yellow] No se encontro ruta encadenada "
                "de %s en Pasada 1. Usando clientes originales de A.",
                plant_a_id,
            )
            for plant in self.enriched_data.get("carton_plants", []):
                if plant.get("id") == plant_a_id:
                    clients_a_in_chain = copy.deepcopy(plant.get("customers", []))
                    break

        # Encontrar los nodos de planta A y B del enriched_data original
        plant_a_node = None
        plant_b_node = None
        for plant in self.enriched_data.get("carton_plants", []):
            if plant.get("id") == plant_a_id:
                plant_a_node = {k: v for k, v in plant.items() if k != "customers"}
            if plant.get("id") == plant_b_id:
                plant_b_node = {k: v for k, v in plant.items() if k != "customers"}

        if not plant_a_node or not plant_b_node:
            logger.error(
                "[red]ChainDispatch:[/red] Planta A (%s) o B (%s) no encontradas en enriched_data.",
                plant_a_id,
                plant_b_id,
            )
            return None

        # Conservar matrix_idx y original_matrix_idx en los clientes del sub-problema.
        # El sub-solver necesita estos indices para extraer correctamente las distancias
        # desde la matriz precalculada (9x9 original). Si se borran, el sub-solver
        # asigna indices secuenciales (0..N-1) que no corresponden a la posicion real
        # en la matriz -> distancias erroneas -> remanentes descartados por MIN_FILL_RATE.
        def clean_customer(c):
            cleaned = copy.deepcopy(c)
            cleaned.pop("dist_to_plant", None)  # Solo eliminar el campo calculado en runtime
            return cleaned

        subproblem = {
            "paper_plant": copy.deepcopy(self.enriched_data["paper_plant"]),
            "carton_plants": [
                {
                    **plant_a_node,
                    "customers": [clean_customer(c) for c in clients_a_in_chain],
                },
                {
                    **plant_b_node,
                    "customers": [clean_customer(c) for c in remaining_clients],
                },
            ],
        }

        logger.info(
            "[cyan]ChainDispatch:[/cyan] Sub-problema construido: "
            "Planta A (%s) con %d clientes, Planta B (%s) con %d remanentes.",
            plant_a_id,
            len(clients_a_in_chain),
            plant_b_id,
            len(remaining_clients),
        )

        return subproblem

    # ------------------------------------------------------------------
    # Metodo 3: Orquestacion completa de la segunda pasada
    # ------------------------------------------------------------------
    def run_chain_pass(
        self,
        routes_pass1: List[List[Dict]],
        plant_a_id: str,
        plant_b_id: str,
        flota_chain: Dict[str, int],
        max_pallets: int,
        max_search_time: int,
    ) -> List[List[Dict]]:
        """
        Orquesta la segunda pasada y devuelve las rutas combinadas finales.

        Flujo:
        1. Detecta clientes remanentes de B (fuera de directas de B).
        2. Construye el sub-problema A + B(remanentes).
        3. Llama al solver con plant_chain_map activo.
        4. Fusiona: sustituye la ruta encadenada de Pasada 1 por la nueva
           y mantiene el resto intactas.

        Args:
            routes_pass1:     Rutas completas de la Pasada 1.
            plant_a_id:       ID de la Planta A (origen de la cadena).
            plant_b_id:       ID de la Planta B (destino de la cadena).
            flota_chain:      {plant_a_id: 1, plant_b_id: N_directas}.
            max_pallets:      Capacidad maxima del camion (pallets).
            max_search_time:  Tiempo limite del solver en segundos.

        Returns:
            Lista de rutas fusionadas. Si no hay remanentes o el solver
            falla, devuelve routes_pass1 sin modificar.
        """
        # Paso 1: detectar remanentes
        remaining_clients = self.get_remaining_clients(routes_pass1, plant_b_id)

        if not remaining_clients:
            logger.info(
                "[cyan]ChainDispatch:[/cyan] Sin clientes remanentes para %s. "
                "Pasada 2 no necesaria.",
                plant_b_id,
            )
            return routes_pass1

        # Paso 1.5: Identificar la ruta de la Planta A que sera reemplazada por el chain
        route_a = None
        for r in routes_pass1:
            p_ids = {n.get("id", "").split("_clone_")[0].split("_chain_")[0] for n in r if n.get("type") == "carton_plant"}
            if plant_a_id in p_ids:
                route_a = r
                break

        # Paso 2: construir sub-problema
        subproblem = self.build_chain_subproblem(
            plant_a_id=plant_a_id,
            plant_b_id=plant_b_id,
            remaining_clients=remaining_clients,
            routes_pass1=routes_pass1,
        )

        if subproblem is None:
            return routes_pass1

        # Paso 3: lanzar el sub-solver con la matriz precalculada.
        # CRITICO: flota de Planta B = 0 en el sub-problema.
        # Si se asigna 1+ vehiculo directo a B, el solver los ruteara directamente
        # (Depot -> B -> Remanentes -> Depot), dejando el camion encadenado sin carga de B.
        # Con flota_B=0, los remanentes solo pueden ir al camion de A (el encadenado).
        from logistic_core.engine.solver import LogisticsSolver

        flota_subproblem = {plant_a_id: 1, plant_b_id: 0}  # Solo el camion encadenado; B sin directos

        sub_solver = LogisticsSolver(
            data=subproblem,
            geo_engine=self.geo_engine,
            precomputed_matrix=self.distance_matrix,
        )

        chain_map = {plant_a_id: [plant_b_id]}

        routes_pass2 = sub_solver.solve(
            n_clientes=max(len(remaining_clients), 10),
            varias_plantas=False,
            max_pallets_ruta=max_pallets,  # Capacidad fisica real
            max_search_time=max_search_time,
            flota_por_planta=flota_subproblem,
            plant_chain_map=chain_map,
        )

        if not routes_pass2:
            logger.warning(
                "[yellow]ChainDispatch:[/yellow] Pasada 2 sin solucion para "
                "%s -> %s. Manteniendo rutas de Pasada 1.",
                plant_a_id,
                plant_b_id,
            )
            return routes_pass1

        # Paso 4: fusion de rutas
        # Separar las rutas por tipo en la Pasada 2
        chain_route_p2 = None
        direct_b_routes_p2 = []
        for route in routes_pass2:
            plant_ids = {
                n.get("id", "").split("_clone_")[0].split("_chain_")[0]
                for n in route
                if n.get("type") == "carton_plant"
            }
            if plant_a_id in plant_ids and plant_b_id in plant_ids:
                chain_route_p2 = route
            elif plant_b_id in plant_ids:
                direct_b_routes_p2.append(route)

        if chain_route_p2 is None:
            logger.warning(
                "[yellow]ChainDispatch:[/yellow] No se encontro ruta encadenada "
                "en la Pasada 2. Manteniendo Pasada 1.",
            )
            return routes_pass1

        # Rutas directas de B de la Pasada 1 (sin cambio, las conservamos)
        direct_b_routes_p1 = []
        other_routes_p1 = []
        for route in routes_pass1:
            # Si esta es la ruta exacta de A que usamos para el sub-problema, NO la incluimos
            # comparamos por identidad o contenido ya que route_a es una referencia a un elemento de routes_pass1
            if route is route_a:
                continue

            plant_ids = {
                n.get("id", "").split("_clone_")[0].split("_chain_")[0]
                for n in route
                if n.get("type") == "carton_plant"
            }
            has_b = plant_b_id in plant_ids
            has_a = plant_a_id in plant_ids

            if has_b and not has_a:
                direct_b_routes_p1.append(route)
            elif not (has_a and has_b):
                # Otras rutas (plantas distintas de A y B, o rutas de A que no se usaron para el chain)
                other_routes_p1.append(route)
            # La ruta encadenada de P1 (si ya existiera una A->B) se descarta -> sustituida por P2

        # Ensamblar resultado final
        merged_routes = [chain_route_p2] + direct_b_routes_p1 + other_routes_p1

        n_clients_p2 = sum(
            1 for n in chain_route_p2 if n.get("type") == "customer"
        )
        logger.info(
            "[green]ChainDispatch:[/green] Fusion completada. "
            "Ruta encadenada P2: %d clientes. Total rutas: %d.",
            n_clients_p2,
            len(merged_routes),
        )

        return merged_routes
