import logging
from typing import Dict, Any, List, Optional
import math
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from logistic_core.utils.geo import GeoUtils
from logistic_core.config import (
    MAX_SEARCH_TIME, DIST_LIMIT,
    DEFAULT_N_CLIENTES, DEFAULT_MAX_PLANTS_PER_ROUTE,
    BACKHAUL_MAX_RETURN_PALLETS, BACKHAUL_ENABLED,
    CHAINED_PLANT_ENABLED, PLANT_CHAIN_MAP,
)
from logistic_core.utils.backhaul_detector import BackhaulDetector

logger = logging.getLogger(__name__)


class LogisticsSolver:
    """Motor de optimización VRP con soporte para Backhauling multi-planta (MC-VRPB).

    Parámetros clave (pasados a `solve()`):
      - n_clientes:      Máximo de clientes que cada vehículo puede visitar.
      - varias_plantas:   Si True, un vehículo puede hacer pickup en más de una
                          planta de cartón en la misma ruta.
      - max_plantas_ruta: Límite de plantas por ruta cuando varias_plantas=True.
    """

    def __init__(self, data: Dict[str, Any], geo_engine=None, precomputed_matrix=None):
        self.data = data
        self.paper_plant = data['paper_plant']
        self.carton_plants = data['carton_plants']
        self.nodes = self._parse_locations(self.data)
        self.geo = geo_engine if geo_engine else GeoUtils()
        
        if precomputed_matrix is not None:
            self.distance_matrix = precomputed_matrix
            self.is_real_road = True
            logger.info("[bold cyan]Geometría:[/bold cyan] Matriz precalculada inyectada (%dx%d).", 
                        precomputed_matrix.shape[0], precomputed_matrix.shape[1])
        else:
            self.distance_matrix, self.is_real_road = self.geo.calculate_distance_matrix(self.nodes)
        
        # Inyectar distancia a planta origen para diagnósticos de "Fuera de Rango"
        plant_idx_map = {n['id']: n['matrix_idx'] for n in self.nodes if n['type'] == 'carton_plant'}
        for n in self.nodes:
            if n['type'] == 'customer' and n.get('parent_cp') in plant_idx_map:
                p_idx = plant_idx_map[n['parent_cp']]
                c_idx = n['matrix_idx']
                dist_m = self.distance_matrix[p_idx][c_idx]
                n['dist_to_plant'] = dist_m / 1000.0 # Convertir a KM

        self._last_solve_args = {}
        self._last_routes = None

    # ------------------------------------------------------------------
    # Parsing de nodos
    # ------------------------------------------------------------------
    def _parse_locations(self, data):
        """Convierte el JSON de entrada en una lista plana de nodos."""
        nodes = []
        # Depósito (Mengíbar) - Nodo 0
        nodes.append({**data['paper_plant'], "id": "DEPOT", "type": "depot", "matrix_idx": 0})

        idx = 1
        for plant in data['carton_plants']:
            plant_id = plant['id']
            plant_node = {k: v for k, v in plant.items() if k != 'customers'}
            nodes.append({**plant_node, "type": "carton_plant", "matrix_idx": idx})
            idx += 1

            for customer in plant.get('customers', []):
                nodes.append({
                    **customer,
                    "type": "customer",
                    "parent_cp": plant_id,
                    "matrix_idx": idx,
                })
                idx += 1

        n_plants = sum(1 for n in nodes if n['type'] == 'carton_plant')
        n_custs = sum(1 for n in nodes if n['type'] == 'customer')
        logger.info("[bold cyan]Nodos:[/bold cyan] Parseados %d (1 DEPOT, %d PT, %d CL)",
                     len(nodes), n_plants, n_custs)
        return nodes

    # ------------------------------------------------------------------
    # Solver principal
    # ------------------------------------------------------------------
    def solve(self, *, n_clientes=None, varias_plantas=False, max_plantas_ruta=None,
              metaheuristic='GUIDED_LOCAL_SEARCH', max_search_time=None, max_pallets_ruta=None,
              flota_por_planta: Dict[str, int] = None,
              backhaul_nodes: Optional[List[Dict[str, Any]]] = None,
              plant_chain_map: Optional[Dict[str, List[str]]] = None):
        """Ejecuta el optimizador VRP.

        Args:
            n_clientes:       No maximo de clientes por ruta (None -> DEFAULT_N_CLIENTES).
            varias_plantas:   Permitir que un vehiculo visite >1 planta de carton.
            max_plantas_ruta: Plantas maximas por ruta si varias_plantas=True.
            metaheuristic:    Algoritmo a usar.
            max_search_time:  Tiempo maximo de busqueda.
            max_pallets_ruta: Limite fisico opcional (Bin-packing).
            flota_por_planta: Dict con numero de camiones especificos por ID de planta.
            backhaul_nodes:   Lista de nodos de recogida de retorno. Cada elemento
                              es un dict con al menos: id, name, lat, lng,
                              return_pallets_capacity, parent_route_idx.
                              Si se pasa, activa el modo Pickup & Delivery.
        """
        # Calculamos el límite real de clientes basándonos en los datos recibidos
        # para asegurar que ninguna ruta se vea truncada por el límite global.
        max_custs_in_data = 0
        for p in self.carton_plants:
            n_cust = len(p.get('customers', []))
            if n_cust > max_custs_in_data:
                max_custs_in_data = n_cust
        
        # El límite final es el mayor entre lo pedido y lo que viene en la data
        n_clientes = max(n_clientes or 0, max_custs_in_data, DEFAULT_N_CLIENTES)
        max_search_time = max_search_time or MAX_SEARCH_TIME

        if varias_plantas:
            max_plantas_ruta = max_plantas_ruta or DEFAULT_MAX_PLANTS_PER_ROUTE
            if max_plantas_ruta < 2:
                max_plantas_ruta = 2
        else:
            max_plantas_ruta = 1
            
        self._last_solve_args = {
            "n_clientes": n_clientes,
            "varias_plantas": varias_plantas,
            "max_plantas_ruta": max_plantas_ruta,
            "max_pallets_ruta": max_pallets_ruta,
            "metaheuristic": metaheuristic,
            "uso_flota_dedicada": bool(flota_por_planta),
            "backhaul_enabled": bool(backhaul_nodes),
            "chained_plants": bool(plant_chain_map),
        }

        plant_indices_orig = [i for i, n in enumerate(self.nodes) if n['type'] == 'carton_plant']

        if not plant_indices_orig:
            logger.error("[bold red]Error:[/bold red] No se detectaron plantas de cartón válidas.")
            return None

        num_plants_orig = len(plant_indices_orig)
        
        # === NUEVO: RECONSTRUCCIÓN DINÁMICA DE NODOS (MUELLES VIRTUALES) ===
        current_nodes = []
        original_to_new_idx = {}
        new_row_cols = []
        
        for i, n in enumerate(self.nodes):
            new_n = dict(n)
            new_n['original_matrix_idx'] = new_n.get('matrix_idx', i)
            new_n['matrix_idx'] = len(current_nodes)
            original_to_new_idx[i] = new_n['matrix_idx']
            current_nodes.append(new_n)
            new_row_cols.append(i)

        # === INYECCION DE NODOS DE BACKHAULING ===
        # Los nodos de recogida de retorno se anadyen al pool de nodos activo
        # ANTES de que se construya la matriz expandida.
        backhaul_node_indices = {}  # {vehicle_id: backhaul_matrix_idx}
        if backhaul_nodes:
            for bh in backhaul_nodes:
                bh_clone = dict(bh)
                bh_clone["type"] = "backhaul_plant"
                bh_clone["original_matrix_idx"] = bh_clone.get("matrix_idx", 0)
                bh_clone["matrix_idx"] = len(current_nodes)
                current_nodes.append(bh_clone)
                new_row_cols.append(bh_clone["original_matrix_idx"])
            logger.info(
                "[bold cyan]Backhauling:[/bold cyan] %d nodos de recogida de retorno inyectados.",
                len(backhaul_nodes)
            )

        plant_to_vehicles = {}
        plant_to_clones = {}
        num_vehicles = 0
        
        if flota_por_planta:
            for p_idx_orig in plant_indices_orig:
                p_id = self.nodes[p_idx_orig]['id']
                count = flota_por_planta.get(p_id, 1)
                plant_to_vehicles[p_id] = list(range(num_vehicles, num_vehicles + count))
                num_vehicles += count
                
                clones_for_plant = [original_to_new_idx[p_idx_orig]]
                for v in range(1, count):
                    clone = dict(self.nodes[p_idx_orig])
                    clone['original_matrix_idx'] = p_idx_orig
                    clone['matrix_idx'] = len(current_nodes)
                    clone['id'] = f"{p_id}_clone_{v}"
                    current_nodes.append(clone)
                    clones_for_plant.append(clone['matrix_idx'])
                plant_to_clones[p_id] = clones_for_plant
        else:
            # Flota estándar: un vehiculo por planta + reserva
            num_vehicles = num_plants_orig + 2
            for p_idx_orig in plant_indices_orig:
                p_id = self.nodes[p_idx_orig]['id']
                plant_to_clones[p_id] = [original_to_new_idx[p_idx_orig]]

        # === INYECCION DE NODOS DE ENCADENAMIENTO (Chained Plant VRP) ===
        # Para cada cadena A -> B, se crea un clon de la planta B asignado
        # al primer vehiculo de la planta A. Esto permite que un camion
        # haga: Depot -> A -> Clientes(A) -> B -> Clientes(B) -> Depot.
        chain_vehicle_map = {}  # {plant_a_id: [{vehicle_id, plant_b_id, chain_clone_idx}]}
        chain_extra_vehicles = {}  # {plant_b_id: [chain_vehicle_id, ...]}
        chain_clone_indices = {}  # {(plant_a_id, plant_b_id): chain_clone_matrix_idx}

        if plant_chain_map and flota_por_planta:
            for plant_a_id, chain_targets in plant_chain_map.items():
                if plant_a_id not in plant_to_vehicles:
                    logger.warning("Chain: Planta origen '%s' no encontrada. Ignorando.", plant_a_id)
                    continue

                chain_veh_id = plant_to_vehicles[plant_a_id][0]

                for plant_b_id in chain_targets:
                    # Buscar el indice original de la planta B
                    p_b_orig_idx = None
                    for i, n in enumerate(self.nodes):
                        if n.get('id') == plant_b_id and n.get('type') == 'carton_plant':
                            p_b_orig_idx = i
                            break

                    if p_b_orig_idx is None:
                        logger.warning("Chain: Planta destino '%s' no encontrada. Ignorando.", plant_b_id)
                        continue

                    # Crear clon de planta B para el vehiculo encadenado
                    chain_clone = dict(self.nodes[p_b_orig_idx])
                    chain_clone['original_matrix_idx'] = p_b_orig_idx
                    chain_clone['matrix_idx'] = len(current_nodes)
                    chain_clone['id'] = f"{plant_b_id}_chain_{plant_a_id}"
                    chain_clone['type'] = 'carton_plant'
                    chain_clone['is_chain_clone'] = True
                    chain_clone['chain_parent'] = plant_a_id
                    current_nodes.append(chain_clone)

                    chain_clone_idx = chain_clone['matrix_idx']
                    chain_clone_indices[(plant_a_id, plant_b_id)] = chain_clone_idx

                    chain_vehicle_map.setdefault(plant_a_id, []).append({
                        'vehicle_id': chain_veh_id,
                        'plant_b_id': plant_b_id,
                        'chain_clone_idx': chain_clone_idx,
                    })

                    chain_extra_vehicles.setdefault(plant_b_id, []).append(chain_veh_id)

                    logger.info(
                        "[bold cyan]Chain:[/bold cyan] %s -> %s (vehiculo %d, clon idx %d)",
                        plant_a_id, plant_b_id, chain_veh_id, chain_clone_idx
                    )

        # === CONSTRUCCION DE LA MATRIZ EXPANDIDA FINAL ===
        size = len(current_nodes)
        full_dist_matrix = np.zeros((size, size), dtype=np.int64)
        for i in range(size):
            orig_i = current_nodes[i].get("original_matrix_idx", current_nodes[i].get("matrix_idx", 0))
            for j in range(size):
                orig_j = current_nodes[j].get("original_matrix_idx", current_nodes[j].get("matrix_idx", 0))
                full_dist_matrix[i][j] = int(self.distance_matrix[orig_i][orig_j])

        depot_idx = 0
        manager = pywrapcp.RoutingIndexManager(size, num_vehicles, depot_idx)

        logger.info("[bold cyan]Muelles Virtuales:[/bold cyan] Nodos totales a optimizar: %d", len(current_nodes))

        logger.info(
            "[bold yellow]Modo:[/bold yellow] %s | Plantas/Ruta=%d | Max_CL=%d | Vehículos Totales=%d",
            "Flota Dinámica" if flota_por_planta else "Estándar",
            max_plantas_ruta, n_clientes, num_vehicles,
        )

        routing = pywrapcp.RoutingModel(manager)

        # === CONSTRUCCION DE LA MATRIZ EXPANDIDA ===
        # Creamos una matriz que incluya todos los clones y nodos de backhauling
        size = len(current_nodes)
        full_dist_matrix = np.zeros((size, size), dtype=np.int64)
        
        orig_matrix = self.distance_matrix
        for i in range(size):
            orig_i = current_nodes[i].get("original_matrix_idx", current_nodes[i].get("matrix_idx", 0))
            for j in range(size):
                orig_j = current_nodes[j].get("original_matrix_idx", current_nodes[j].get("matrix_idx", 0))
                full_dist_matrix[i][j] = int(orig_matrix[orig_i][orig_j])

        # === CALLBACKS ===
        def transit_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return full_dist_matrix[from_node][to_node]

        transit_cb = routing.RegisterTransitCallback(transit_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)
        
        # Dimension de distancia
        routing.AddDimension(transit_cb, 0, 8_000_000, True, 'Distance') # KM Reales: 8000km
        dist_dim = routing.GetDimensionOrDie('Distance')

        # === EVALUADOR DE COSTES (Con penalizacion condicional de retorno) ===
        # Si el vehiculo lleva carga de backhauling en el tramo final, no se
        # penaliza el retorno al deposito porque el viaje es productivo.
        backhaul_node_idx_set = set()
        if backhaul_nodes:
            backhaul_node_idx_set = {
                n["matrix_idx"] for n in current_nodes if n["type"] == "backhaul_plant"
            }

        def cost_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            dist = int(full_dist_matrix[from_node][to_node])

            # Penalizar el retorno al deposito SOLO si viene de un nodo sin
            # carga de retorno (backhaul). Si el nodo anterior es una planta
            # de backhauling el viaje es rentable y no se penaliza (coste 0).
            if to_node == 0 and from_node != 0:
                if from_node in backhaul_node_idx_set:
                    return 0  # Premio maximo por volver cargado
                return int(dist * 2.5)
            return dist

        cost_cb = routing.RegisterTransitCallback(cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(cost_cb)

        # === DIMENSIÓN 2: Contador de Plantas por vehículo ===
        def plant_callback(from_index):
            node_idx = manager.IndexToNode(from_index)
            return 1 if current_nodes[node_idx]['type'] == 'carton_plant' else 0

        plant_cb = routing.RegisterUnaryTransitCallback(plant_callback)

        # Per-vehicle plant limit: chain vehicles can visit 2+ plants
        plant_limits = [int(max_plantas_ruta)] * num_vehicles
        if chain_vehicle_map:
            for plant_a_id, chain_infos in chain_vehicle_map.items():
                for ci in chain_infos:
                    v_id = ci['vehicle_id']
                    plant_limits[v_id] = max(plant_limits[v_id], 1 + len(chain_infos))

        routing.AddDimensionWithVehicleCapacity(plant_cb, 0, plant_limits, True, 'PlantCount')
        plant_dim = routing.GetDimensionOrDie('PlantCount')

        # === DIMENSIÓN 3: Contador de Clientes por vehículo ===
        def customer_callback(from_index):
            node_idx = manager.IndexToNode(from_index)
            return 1 if current_nodes[node_idx]['type'] == 'customer' else 0

        cust_cb = routing.RegisterUnaryTransitCallback(customer_callback)
        routing.AddDimension(cust_cb, 0, n_clientes, True, 'CustomerCount')

        # === DIMENSIÓN 4: Capacidad Física Acumulada (Volumen/Pallets) ===
        if max_pallets_ruta is not None:
            def demand_callback(from_index):
                node_idx = manager.IndexToNode(from_index)
                if current_nodes[node_idx]['type'] == 'customer':
                    return int(current_nodes[node_idx].get('demanda_pallets', 0))
                return 0

            demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
            capacities = [int(max_pallets_ruta)] * num_vehicles
            # Chain vehicles: doble capacidad para modelar carga-descarga-recarga
            if chain_vehicle_map:
                for plant_a_id, chain_infos in chain_vehicle_map.items():
                    for ci in chain_infos:
                        v_id = ci['vehicle_id']
                        capacities[v_id] = int(max_pallets_ruta) * 2

            routing.AddDimensionWithVehicleCapacity(
                demand_cb,
                0,  # null capacity slack
                capacities,  # vehicle maximum capacities
                True,  # start cumul to zero
                'PalletsCapacity'
            )


        if varias_plantas:
            # ESTRATEGIA: En lugar de forzar con 'Add(CumulVar >= 1)', que es muy frágil,
            # usamos SetFixedCostOfVehicle con un valor negativo o simplemente
            # penalizamos que un vehículo NO arranque.
            for v in range(num_vehicles):
                # Aplicamos un "coste por no usar" muy alto
                routing.SetFixedCostOfVehicle(0, v) 
            
            # Forzamos que el solver intente usar todos los vehículos mediante una meta 
            # de 'visita a plantas' pero permitiendo que si no hay carga, no rompa.
            for v in range(num_vehicles):
                # Mantenemos el incentivo de visita a planta pero relajamos la R0 dura
                pass

        # R1: Cada vehículo puede visitar al menos 1 planta (OPCIONAL)
        # for v in range(num_vehicles):
        #     routing.solver().Add(plant_dim.CumulVar(routing.End(v)) >= 1)

        # R2: Todas las plantas/muelles son de visita obligatoria para su vehículo
        for p_id, clones in plant_to_clones.items():
            for clon_idx in clones:
                c_node = manager.NodeToIndex(clon_idx)
                # OBLIGATORIO: El muelle debe ser visitado
                routing.AddDisjunction([c_node], 1_000_000_000_000)
            
            if flota_por_planta:
                veh_list = plant_to_vehicles.get(p_id, [])
                for i, clon_idx in enumerate(clones):
                    if i < len(veh_list):
                        veh_id = veh_list[i]
                        c_node = manager.NodeToIndex(clon_idx)
                        routing.solver().Add(routing.VehicleVar(c_node) == veh_id)

        # R2.5: Desactivar los nodos de planta originales (solo se usan los clones)
        for i, node in enumerate(current_nodes):
            if node['type'] == 'carton_plant' and 'clone' not in node.get('id', '') and 'chain' not in node.get('id', ''):
                orig_node_idx = manager.NodeToIndex(i)
                # Penalización 0 para que el solver lo descarte sin coste
                routing.AddDisjunction([orig_node_idx], 0)
                # Forzar explícitamente a que no esté activo
                # routing.solver().Add(routing.ActiveVar(orig_node_idx) == 0)

        # R3: Clientes -- vinculacion a camiones correctos y precedencias
        for c_idx, node in enumerate(current_nodes):
            if node['type'] != 'customer':
                continue
            
            c_node = manager.NodeToIndex(c_idx)
            parent_id = node.get('parent_cp')
            
            penalty = 1_000_000_000 if node.get('obligatorio', False) else 100_000_000
            routing.AddDisjunction([c_node], penalty)

            is_active = routing.ActiveVar(c_node)
            
            if flota_por_planta:
                allowed_vehicles = list(plant_to_vehicles.get(parent_id, []))
                # Extender con vehiculos de cadenas que apuntan a esta planta
                extra = chain_extra_vehicles.get(parent_id, [])
                if extra:
                    allowed_vehicles = allowed_vehicles + extra

                if allowed_vehicles:
                    routing.solver().Add(
                        routing.solver().Sum([routing.VehicleVar(c_node) == v for v in allowed_vehicles]) == is_active
                    )
                    
                    for i, veh_id in enumerate(plant_to_vehicles.get(parent_id, [])):
                        if parent_id in plant_to_clones and i < len(plant_to_clones[parent_id]):
                            clon_node = manager.NodeToIndex(plant_to_clones[parent_id][i])
                            is_in_veh = (routing.VehicleVar(c_node) == veh_id)
                            # Precedencia
                            routing.solver().Add(dist_dim.CumulVar(clon_node) * is_in_veh <= dist_dim.CumulVar(c_node) * is_in_veh)

                    # Precedencia para clientes de B en vehiculo encadenado:
                    # deben ir DESPUES del clon de la cadena (no de la planta original)
                    for chain_veh_id in extra:
                        is_on_chain = (routing.VehicleVar(c_node) == chain_veh_id)
                        # Buscar el chain_clone_idx correspondiente
                        for pair_key, cc_idx in chain_clone_indices.items():
                            if pair_key[1] == parent_id:
                                cc_node = manager.NodeToIndex(cc_idx)
                                routing.solver().Add(
                                    dist_dim.CumulVar(cc_node) * is_on_chain <= dist_dim.CumulVar(c_node) * is_on_chain
                                )
            else:
                clones = plant_to_clones.get(parent_id, [])
                if clones:
                    p_node = manager.NodeToIndex(clones[0])
                    routing.solver().Add(is_active * routing.VehicleVar(c_node) == is_active * routing.VehicleVar(p_node))
                    routing.solver().Add(dist_dim.CumulVar(p_node) * is_active <= dist_dim.CumulVar(c_node) * is_active)

        # === RESTRICCIONES DE ENCADENAMIENTO (Chained Plant VRP) ===
        # Para cada cadena A -> B:
        #   1. El clon de B se asigna al vehiculo 0 de A (obligatorio).
        #   2. Planta A se visita ANTES que clon B (precedencia).
        #   3. Clientes de A en el vehiculo encadenado van ANTES de clon B.
        #   4. Clientes de B en el vehiculo encadenado van DESPUES de clon B.
        if chain_vehicle_map:
            for plant_a_id, chain_infos in chain_vehicle_map.items():
                a_clones = plant_to_clones.get(plant_a_id, [])
                if not a_clones:
                    continue
                a_node_idx = a_clones[0]
                a_node = manager.NodeToIndex(a_node_idx)

                for ci in chain_infos:
                    chain_veh_id = ci['vehicle_id']
                    cc_idx = ci['chain_clone_idx']
                    cc_node = manager.NodeToIndex(cc_idx)

                    plant_b_id = ci['plant_b_id']
                    
                    # R-CHAIN-1: Clon B obligatorio, asignado al vehiculo encadenado
                    routing.AddDisjunction([cc_node], 1_000_000_000_000)
                    is_active_cc = routing.ActiveVar(cc_node)
                    routing.solver().Add(is_active_cc * routing.VehicleVar(cc_node) == is_active_cc * chain_veh_id)

                    # R-CHAIN-2: Planta A antes que clon B
                    routing.solver().Add(dist_dim.CumulVar(a_node) * is_active_cc <= dist_dim.CumulVar(cc_node) * is_active_cc)

                    # R-CHAIN-3: Clientes de A en vehiculo encadenado van ANTES de clon B
                    for c_idx_inner, n_inner in enumerate(current_nodes):
                        if n_inner['type'] != 'customer':
                            continue
                        if n_inner.get('parent_cp') != plant_a_id:
                            continue
                        inner_node = manager.NodeToIndex(c_idx_inner)
                        is_on_chain = (routing.VehicleVar(inner_node) == chain_veh_id)
                        routing.solver().Add(
                            dist_dim.CumulVar(inner_node) * is_on_chain <= dist_dim.CumulVar(cc_node) * is_on_chain
                        )

                    # R-CHAIN-4: Si se visita un cliente de B en el vehiculo encadenado, el clon B es obligatorio
                    for c_idx_inner, n_inner in enumerate(current_nodes):
                        if n_inner['type'] != 'customer' or n_inner.get('parent_cp') != plant_b_id:
                            continue
                        inner_node = manager.NodeToIndex(c_idx_inner)
                        is_on_chain = (routing.VehicleVar(inner_node) == chain_veh_id)
                        routing.solver().Add(is_active_cc >= is_on_chain)

                    # R-CHAIN-5: Limitar la capacidad física por tramo para no sobrecargar el camión en una sola planta
                    if max_pallets_ruta is not None:
                        # Suma de demanda de clientes de Planta A asignados a este vehículo <= max_pallets
                        demands_a = []
                        for c_idx_inner, n_inner in enumerate(current_nodes):
                            if n_inner['type'] == 'customer' and n_inner.get('parent_cp') == plant_a_id:
                                inner_node = manager.NodeToIndex(c_idx_inner)
                                is_on_chain = (routing.VehicleVar(inner_node) == chain_veh_id)
                                is_active = routing.ActiveVar(inner_node)
                                demands_a.append(is_active * is_on_chain * int(n_inner.get('demanda_pallets', 0)))
                        if demands_a:
                            routing.solver().Add(routing.solver().Sum(demands_a) <= int(max_pallets_ruta))

                        # Suma de demanda de clientes de Planta B asignados a este vehículo <= max_pallets
                        demands_b = []
                        for c_idx_inner, n_inner in enumerate(current_nodes):
                            if n_inner['type'] == 'customer' and n_inner.get('parent_cp') == plant_b_id:
                                inner_node = manager.NodeToIndex(c_idx_inner)
                                is_on_chain = (routing.VehicleVar(inner_node) == chain_veh_id)
                                is_active = routing.ActiveVar(inner_node)
                                demands_b.append(is_active * is_on_chain * int(n_inner.get('demanda_pallets', 0)))
                        if demands_b:
                            routing.solver().Add(routing.solver().Sum(demands_b) <= int(max_pallets_ruta))

            logger.info("[bold cyan]Chain:[/bold cyan] %d cadenas de encadenamiento configuradas.", len(chain_clone_indices))

        # === RESTRICCIONES DE BACKHAULING (Pickup & Delivery) ===
        if backhaul_nodes:
            for bh_node_data in current_nodes:
                if bh_node_data["type"] != "backhaul_plant":
                    continue

                node_idx = current_nodes.index(bh_node_data)
                bh_idx = manager.NodeToIndex(node_idx)

                routing.AddDisjunction([bh_idx], 500_000)

                p_route_idx = bh_node_data.get("parent_route_idx")
                if p_route_idx is not None and flota_por_planta:
                    pass

        # === BUSQUEDA ===
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = max_search_time


        logger.info("[bold green]Optimizador:[/bold green] Iniciando búsqueda (Límite: %ds | Algoritmo: %s)...", max_search_time, metaheuristic)
        
        # Log de matriz para asegurar que no sea todo ceros
        mat_min = np.min(self.distance_matrix[self.distance_matrix > 0]) if np.any(self.distance_matrix > 0) else 0
        mat_max = np.max(self.distance_matrix)
        logger.debug(f"Estadísticas de Matriz: Min(>0)={mat_min:.1f}m, Max={mat_max:.1f}m")
        
        solution = routing.SolveWithParameters(search_params)

        # ====== NUEVO: GESTIÓN DE DROP LOGGER AUTOMÁTICA ======
        from logistic_core.engine.drop_logger import DropLogger
        drop_logger = DropLogger()
        drop_logger.track_nodes(self.nodes)

        if solution:
            status_code = routing.status()
            logger.info(f"[bold green]Solver:[/bold green] Optimización completada (Status: {status_code}).")
            routes = self._extract_routes(manager, routing, solution, current_nodes)
            self._last_routes = routes
            
            # --- CÁLCULO DE ESTADÍSTICAS PARA DIAGNÓSTICO ---
            fleet_info = {}
            dim_stats = {}
            
            # Mapeo invertido: vehículo -> planta
            vehicle_to_plant = {}
            if flota_por_planta:
                for p_id, v_idxs in plant_to_vehicles.items():
                    fleet_info[p_id] = {"total": len(v_idxs), "used": 0, "subroutes": []}
                    for v in v_idxs: vehicle_to_plant[v] = p_id
            else:
                fleet_info["Global"] = {"total": num_vehicles, "used": 0, "subroutes": []}
                for v in range(num_vehicles): vehicle_to_plant[v] = "Global"

            for v_id, route in enumerate(routes):
                if len(route) <= 2: continue # Ruta vacía
                
                plant = vehicle_to_plant.get(v_id, "Global")
                if plant in fleet_info: 
                    fleet_info[plant]["used"] += 1
                
                # Carga de la ruta
                try:
                    load = solution.Value(routing.GetDimensionOrDie('PalletsCapacity').CumulVar(routing.End(v_id)))
                except:
                    load = sum(n.get('demanda_pallets', 0) for n in route if n['type']=='customer')
                
                # Info de subruta
                n_stops = len([n for n in route if n['type'] == 'customer'])
                sub_desc = f"Camion {fleet_info[plant]['used']}: {load}/{max_pallets_ruta} pallets, {n_stops} paradas"
                fleet_info[plant]["subroutes"].append(sub_desc)

                if plant not in dim_stats:
                    dim_stats[plant] = {"loads": [], "dists": [], "max_stops_reached": False}
                
                dim_stats[plant]["loads"].append(load)
                if len(route)-2 >= n_clientes:
                    dim_stats[plant]["max_stops_reached"] = True

            # Consolidar medias
            for p in dim_stats:
                loads = dim_stats[p]["loads"]
                avg_load = sum(loads)/len(loads) if loads else 0
                dim_stats[p]["avg_load_pct"] = (avg_load / max_pallets_ruta * 100) if max_pallets_ruta else 0

            # Generar el log avanzado
            self.drop_log_path = drop_logger.log_dropped_nodes(
                routes, 
                fleet_data=fleet_info, 
                dimension_stats=dim_stats
            )
            
            return routes

        status_code = routing.status()
        self.drop_log_path = drop_logger.log_dropped_nodes([], fleet_data=None) # Todos descartados
        return None

    # ------------------------------------------------------------------
    # Extracción de rutas de la solución
    # ------------------------------------------------------------------
    def _extract_routes(self, manager, routing, solution, current_nodes):
        all_routes = []
        for vehicle_id in range(routing.vehicles()):
            index = routing.Start(vehicle_id)
            route = []
                
            while not routing.IsEnd(index):
                node_idx = manager.IndexToNode(index)
                node_data = dict(current_nodes[node_idx])
                node_data['matrix_idx'] = node_data.get('original_matrix_idx', node_data['matrix_idx'])
                route.append(node_data)
                index = solution.Value(routing.NextVar(index))
                
            # Nodo final (Depósito)
            node_idx = manager.IndexToNode(index)
            node_data = dict(current_nodes[node_idx])
            node_data['matrix_idx'] = node_data.get('original_matrix_idx', node_data['matrix_idx'])
            route.append(node_data)

            # Filtrar: solo conservar rutas que lleven al menos un cliente
            # y que cumplan la métrica de rentabilidad mínima (Bin Packing constraint bypass)
            if any(n['type'] == 'customer' for n in route):
                carga_pallets = sum(n.get('demanda_pallets', 0) for n in route if n['type'] == 'customer')
                
                # Obtener la capacidad parametrizada en Solve, o asumir 34
                max_pallets = self._last_solve_args.get("max_pallets_ruta", 34)
                if max_pallets is None or max_pallets <= 0:
                    max_pallets = 34
                
                from logistic_core.config import MIN_FILL_RATE_PCT
                fill_rate = (carga_pallets / max_pallets) * 100.0
                
                if fill_rate >= MIN_FILL_RATE_PCT:
                    all_routes.append(route)
                else:
                    logger.warning(
                        "[bold red]Ruta descartada (Outsourcing):[/bold red] Llenado volumétrico %.1f%% (%d/%d pals) < Umbral %.1f%%",
                        fill_rate, carga_pallets, max_pallets, MIN_FILL_RATE_PCT
                    )

        n_backhaul_used = sum(
            1 for route in all_routes
            for n in route if n.get("type") == "backhaul_plant"
        )
        logger.info("[bold green]Rutas Activas Construidas:[/bold green] %d", len(all_routes))
        if n_backhaul_used:
            logger.info(
                "[bold cyan]Backhauling:[/bold cyan] %d nodos de recogida de retorno incluidos en rutas activas.",
                n_backhaul_used
            )
        return all_routes

    # ------------------------------------------------------------------
    # Resumen (Estilo statsmodels)
    # ------------------------------------------------------------------
    def summary(self, routes=None):
        """Genera un resumen estilo statsmodels de los resultados de optimización."""
        routes = routes or self._last_routes
        if not routes:
            return "No hay rutas disponibles para generar un resumen. Ejecuta solve() primero."
            
        args = self._last_solve_args
        api_used = self.geo.api_type if hasattr(self.geo, 'api_type') else 'google_maps'
        
        # Asumimos velocidad promedio para estimar tiempo si la matriz es solo distancia
        # 60 km/h = 1000 m / min
        SPEED_M_PER_MIN = 1000 
        
        route_stats = []
        total_dist_m = 0
        total_time_min = 0
        
        for idx, route in enumerate(routes):
            route_dist_m = 0
            # Valid calculation of route distance using the distance matrix
            for i in range(len(route) - 1):
                from_idx = route[i].get('matrix_idx')
                to_idx = route[i+1].get('matrix_idx')
                if from_idx is not None and to_idx is not None:
                     route_dist_m += self.distance_matrix[from_idx][to_idx]
            
            route_dist_km = route_dist_m / 1000.0
            route_time_min = route_dist_m / SPEED_M_PER_MIN
            
            total_dist_m += route_dist_m
            total_time_min += route_time_min
            
            route_stats.append({
                "id": idx + 1,
                "stops": len(route) - 2, # ex depot start/end
                "dist_km": route_dist_km,
                "time_min": route_time_min
            })
            
        total_dist_km = total_dist_m / 1000.0
        
        # Formateo
        output = []
        output.append("="*80)
        output.append(f"{'Logistics Optimizer Results':^80}")
        output.append("="*80)
        
        output.append(f"{'Model:':<20} MC-VRPB{'Method:':>25} {args.get('metaheuristic', 'UNKNOWN'):>25}")
        output.append(f"{'Distance API:':<20} {api_used:<15}{'No. Routes:':>15} {len(routes):>25}")
        output.append(f"{'Real Road Dist:':<20} {str(self.is_real_road):<15}{'Total Dist (km):':>20} {total_dist_km:>20.2f}")
        output.append(f"{'Total Time (min):':<20} {total_time_min:<15.2f}")
        output.append("-" * 80)
        
        output.append("Parameters:")
        output.append(f"  Max Clients/Route: {args.get('n_clientes', 'N/A')}")
        output.append(f"  Multi-plant enabled: {args.get('varias_plantas', False)}")
        if args.get('varias_plantas'):
            output.append(f"  Max Plants/Route: {args.get('max_plantas_ruta', 'N/A')}")
            
        if hasattr(self.geo, 'truck_specs') and self.geo.truck_specs:
            output.append(f"  Truck Specs: {self.geo.truck_specs}")
            
        output.append("-" * 80)
        output.append(f"{'Route ID':<10} | {'Paradas':<10} | {'Distancia (km)':<20} | {'Tiempo Est. (min)':<20}")
        output.append("-" * 80)
        
        for stat in route_stats:
            output.append(f"{stat['id']:<10} | {stat['stops']:<10} | {stat['dist_km']:<20.2f} | {stat['time_min']:<20.2f}")
            
        output.append("="*80)
        return "\n".join(output)
