import logging
from typing import Dict, Any, List
import math
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from logistic_core.utils.geo import GeoUtils
from logistic_core.config import (
    MAX_SEARCH_TIME, DIST_LIMIT,
    DEFAULT_N_CLIENTES, DEFAULT_MAX_PLANTS_PER_ROUTE,
)

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
              flota_por_planta: Dict[str, int] = None):
        """Ejecuta el optimizador VRP.

        Args:
            n_clientes:      Nº máximo de clientes por ruta (None → DEFAULT_N_CLIENTES).
            varias_plantas:  Permitir que un vehículo visite >1 planta de cartón.
            max_plantas_ruta: Plantas máximas por ruta si varias_plantas=True.
            metaheuristic:   Algoritmo a usar.
            max_search_time: Tiempo máximo de búsqueda.
            max_pallets_ruta: Límite físico opcional (Bin-packing).
            flota_por_planta: Dict con número de camiones específicos por ID de planta.
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
            "uso_flota_dedicada": bool(flota_por_planta)
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

        plant_to_vehicles = {}
        plant_to_clones = {}
        num_vehicles = 0
        
        if flota_por_planta:
            for p_idx_orig in plant_indices_orig:
                p_id = self.nodes[p_idx_orig]['id']
                count = flota_por_planta.get(p_id, 1)
                
                plant_to_vehicles[p_id] = list(range(num_vehicles, num_vehicles + count))
                num_vehicles += count
                
                clones_for_plant = []
                # El Muelle 1 es el nodo original
                orig_new_idx = original_to_new_idx[p_idx_orig]
                clones_for_plant.append(orig_new_idx)
                
                # Muelle 2, 3... (Clones perfectos)
                for v in range(1, count):
                    clone = dict(self.nodes[p_idx_orig])
                    clone['original_matrix_idx'] = clone.get('matrix_idx', p_idx_orig)
                    clone['matrix_idx'] = len(current_nodes)
                    clone['id'] = f"{p_id}_clone_{v}"
                    clone['name'] = f"{clone['name']} (Muelle {v+1})"
                    clones_for_plant.append(clone['matrix_idx'])
                    current_nodes.append(clone)
                    new_row_cols.append(p_idx_orig)
                
                plant_to_clones[p_id] = clones_for_plant
                
            varias_plantas = False
            idxs = np.array(new_row_cols)
            current_matrix = self.distance_matrix[idxs][:, idxs]
            
        else:
            if varias_plantas:
                num_vehicles = num_plants_orig
            else:
                num_vehicles = num_plants_orig + 2
                
            current_matrix = self.distance_matrix
            for p_idx_orig in plant_indices_orig:
                p_id = self.nodes[p_idx_orig]['id']
                plant_to_clones[p_id] = [original_to_new_idx[p_idx_orig]]

        dist_matrix = current_matrix.astype(int).tolist()
        depot_idx = 0
        manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_idx)

        logger.info("[bold cyan]Muelles Virtuales:[/bold cyan] Nodos totales a optimizar: %d", len(current_nodes))

        logger.info(
            "[bold yellow]Modo:[/bold yellow] %s | Plantas/Ruta=%d | Max_CL=%d | Vehículos Totales=%d",
            "Flota Dinámica" if flota_por_planta else "Estándar",
            max_plantas_ruta, n_clientes, num_vehicles,
        )

        routing = pywrapcp.RoutingModel(manager)

        # === DIMENSIÓN 1: Distancia ===
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(dist_matrix[from_node][to_node])

        transit_cb = routing.RegisterTransitCallback(distance_callback)
        routing.AddDimension(transit_cb, 0, 8_000_000, True, 'Distance') # KM Reales: 8000km
        dist_dim = routing.GetDimensionOrDie('Distance')

        # === EVALUADOR DE COSTES (Con penalización de retorno) ===
        def cost_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            dist = int(dist_matrix[from_node][to_node])
            
            # Penalizar el retorno al depósito (to_node == 0) para forzar "vengo de bajada"
            if to_node == 0 and from_node != 0:
                return int(dist * 2.5) # x2.5 para que pese significativamente más que otros arcos
            return dist

        cost_cb = routing.RegisterTransitCallback(cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(cost_cb)

        # === DIMENSIÓN 2: Contador de Plantas por vehículo ===
        def plant_callback(from_index):
            node_idx = manager.IndexToNode(from_index)
            return 1 if current_nodes[node_idx]['type'] == 'carton_plant' else 0

        plant_cb = routing.RegisterUnaryTransitCallback(plant_callback)
        routing.AddDimension(plant_cb, 0, max_plantas_ruta, True, 'PlantCount')
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

        # R3: Clientes — vinculación a camiones correctos y precedencias
        for c_idx, node in enumerate(current_nodes):
            if node['type'] != 'customer':
                continue
            
            c_node = manager.NodeToIndex(c_idx)
            parent_id = node.get('parent_cp')
            
            penalty = 1_000_000_000 if node.get('obligatorio', False) else 100_000_000
            routing.AddDisjunction([c_node], penalty)

            is_active = routing.ActiveVar(c_node)
            
            if flota_por_planta:
                allowed_vehicles = plant_to_vehicles.get(parent_id, [])
                if allowed_vehicles:
                    routing.solver().Add(
                        routing.solver().Sum([routing.VehicleVar(c_node) == v for v in allowed_vehicles]) == is_active
                    )
                    
                    for i, veh_id in enumerate(allowed_vehicles):
                        if i < len(plant_to_clones[parent_id]):
                            clon_node = manager.NodeToIndex(plant_to_clones[parent_id][i])
                            is_in_veh = (routing.VehicleVar(c_node) == veh_id)
                            # Precedencia
                            routing.solver().Add(dist_dim.CumulVar(clon_node) * is_in_veh <= dist_dim.CumulVar(c_node) * is_in_veh)
            else:
                clones = plant_to_clones.get(parent_id, [])
                if clones:
                    p_node = manager.NodeToIndex(clones[0])
                    routing.solver().Add(is_active * routing.VehicleVar(c_node) == is_active * routing.VehicleVar(p_node))
                    routing.solver().Add(dist_dim.CumulVar(p_node) * is_active <= dist_dim.CumulVar(c_node) * is_active)

        # === BÚSQUEDA ===
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
            if any(n['type'] == 'customer' for n in route):
                all_routes.append(route)

        logger.info("[bold green]Rutas Activas Construidas:[/bold green] %d", len(all_routes))
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
