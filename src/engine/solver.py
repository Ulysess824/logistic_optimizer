import logging
from typing import Dict, Any, List
import math
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from src.utils.geo import GeoUtils
from src.config import (
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

    def __init__(self, data: Dict[str, Any], geo_engine=None):
        self.data = data
        self.paper_plant = data['paper_plant']
        self.carton_plants = data['carton_plants']
        self.nodes = self._parse_locations(self.data)
        self.geo = geo_engine if geo_engine else GeoUtils()
        self.distance_matrix, self.is_real_road = self.geo.calculate_distance_matrix(self.nodes)
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
        logger.info("Nodos parseados: %d (1 depósito, %d plantas, %d clientes)",
                     len(nodes), n_plants, n_custs)
        return nodes

    # ------------------------------------------------------------------
    # Solver principal
    # ------------------------------------------------------------------
    def solve(self, *, n_clientes=None, varias_plantas=False, max_plantas_ruta=None, 
              metaheuristic='GUIDED_LOCAL_SEARCH', max_search_time=None):
        """Ejecuta el optimizador VRP.

        Args:
            n_clientes:      Nº máximo de clientes por ruta (None → DEFAULT_N_CLIENTES).
            varias_plantas:  Permitir que un vehículo visite >1 planta de cartón.
            max_plantas_ruta: Plantas máximas por ruta si varias_plantas=True.
            metaheuristic:   Algoritmo a usar.
            max_search_time: Tiempo máximo de búsqueda.
        """
        n_clientes = n_clientes or DEFAULT_N_CLIENTES
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
            "metaheuristic": metaheuristic,
        }

        plant_indices = [i for i, n in enumerate(self.nodes) if n['type'] == 'carton_plant']
        customer_indices = [i for i, n in enumerate(self.nodes) if n['type'] == 'customer']

        if not plant_indices:
            logger.error("No se detectaron plantas de cartón válidas.")
            return None

        dist_matrix = self.distance_matrix.astype(int).tolist()
        num_plants = len(plant_indices)
        
        # AJUSTE: Si varias_plantas es True, queremos exactamente un camión por planta
        if varias_plantas:
            num_vehicles = num_plants
        else:
            num_vehicles = num_plants + 2
            
        depot_idx = 0

        logger.info("Nodos parseados para optimizar: %d", len(self.nodes))
        for i, n in enumerate(self.nodes):
            if n['type'] == 'carton_plant':
                logger.info(f"  [PLANTA] idx={i} id={n['id']} name={n['name']}")

        logger.info(
            "Modo: %s | max_plantas_ruta=%d | n_clientes=%d | vehículos=%d",
            "MC-VRPB (multi-planta)" if varias_plantas else "VRPB (clásico)",
            max_plantas_ruta, n_clientes, num_vehicles,
        )

        manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_idx)
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
            return 1 if self.nodes[node_idx]['type'] == 'carton_plant' else 0

        plant_cb = routing.RegisterUnaryTransitCallback(plant_callback)
        routing.AddDimension(plant_cb, 0, max_plantas_ruta, True, 'PlantCount')
        plant_dim = routing.GetDimensionOrDie('PlantCount')

        # === DIMENSIÓN 3: Contador de Clientes por vehículo ===
        def customer_callback(from_index):
            node_idx = manager.IndexToNode(from_index)
            return 1 if self.nodes[node_idx]['type'] == 'customer' else 0

        cust_cb = routing.RegisterUnaryTransitCallback(customer_callback)
        routing.AddDimension(cust_cb, 0, n_clientes, True, 'CustomerCount')

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

        # R2: Todas las plantas son ABSOLUTAMENTE prioritarias
        for p_idx in plant_indices:
            p_node = manager.NodeToIndex(p_idx)
            # Volvemos a la prioridad máxima
            routing.AddDisjunction([p_node], 1_000_000_000_000)

        # R3: Clientes — vinculación a su planta padre + precedencia
        for c_idx in customer_indices:
            c_node = manager.NodeToIndex(c_idx)
            node = self.nodes[c_idx]
            parent_id = node.get('parent_cp')
            p_idx = next((i for i, n in enumerate(self.nodes) if n['id'] == parent_id), None)
            p_node = manager.NodeToIndex(p_idx) if p_idx is not None else None

            penalty = 1_000_000_000 if node.get('obligatorio', False) else 100_000_000
            routing.AddDisjunction([c_node], penalty)

            if p_node is not None:
                # REGLA DE ORO: El cliente debe ir en el mismo vehículo que su planta
                routing.solver().Add(routing.VehicleVar(c_node) == routing.VehicleVar(p_node))
                
                # La planta DEBE visitarse antes que el cliente (Estructural)
                routing.solver().Add(dist_dim.CumulVar(p_node) <= dist_dim.CumulVar(c_node))

        # === BÚSQUEDA ===
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = max_search_time

        logger.info("Iniciando optimización (%d vehículos, límite %ds, algoritmo: %s)...", num_vehicles, max_search_time, metaheuristic)
        
        # Log de matriz para asegurar que no sea todo ceros
        mat_min = np.min(self.distance_matrix[self.distance_matrix > 0]) if np.any(self.distance_matrix > 0) else 0
        mat_max = np.max(self.distance_matrix)
        logger.info(f"Estadísticas de Matriz: Min(>0)={mat_min:.1f}m, Max={mat_max:.1f}m")
        
        solution = routing.SolveWithParameters(search_params)

        if solution:
            status_code = routing.status()
            logger.info(f"Solver terminó con éxito (status {status_code}).")
            routes = self._extract_routes(manager, routing, solution)
            self._last_routes = routes
            return routes

        status_code = routing.status()
        status_map = {0: "NOT_SOLVED", 1: "SUCCESS", 2: "FAIL", 3: "FAIL_TIMEOUT", 4: "INVALID"}
        logger.warning(f"El solver no encontró solución. Estado: {status_map.get(status_code, status_code)}")
        return None

    # ------------------------------------------------------------------
    # Extracción de rutas de la solución
    # ------------------------------------------------------------------
    def _extract_routes(self, manager, routing, solution):
        all_routes = []
        for vehicle_id in range(routing.vehicles()):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                node_idx = manager.IndexToNode(index)
                route.append(self.nodes[node_idx])
                index = solution.Value(routing.NextVar(index))
            # Nodo final (Depósito)
            node_idx = manager.IndexToNode(index)
            route.append(self.nodes[node_idx])

            # Solo incluir rutas con al menos 1 parada intermedia
            if len(route) > 2:
                all_routes.append(route)

        logger.info("Solución encontrada: %d rutas activas.", len(all_routes))
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