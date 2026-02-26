import json
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from src.utils.geo import GeoUtils
from src.config import MAX_SEARCH_TIME, DIST_LIMIT

class LogisticsSolver:
    def __init__(self, locations_data):
        self.nodes = self._parse_locations(locations_data)
        self.geo = GeoUtils()
        self.distance_matrix, self.is_real_road = self.geo.calculate_distance_matrix(self.nodes)

    def _parse_locations(self, data):
        """Convierte el JSON de entrada en una lista plana de nodos."""
        nodes = []
        # Depósito (Mengíbar) - Nodo 0
        nodes.append({**data['paper_plant'], "id": "DEPOT", "type": "depot", "matrix_idx": 0})
        
        idx = 1
        # Plantas y sus clientes asociados
        for plant in data['carton_plants']:
            plant_id = plant['id']
            # Nodo de Planta
            plant_node = {k: v for k, v in plant.items() if k != 'customers'}
            nodes.append({**plant_node, "type": "carton_plant", "matrix_idx": idx})
            idx += 1
            
            # Nodos de Clientes
            for customer in plant.get('customers', []):
                nodes.append({**customer, "type": "customer", "parent_cp": plant_id, "matrix_idx": idx})
                idx += 1
        return nodes

    def solve(self):
        """Ejecuta el optimizador VRP estratégico."""
        plant_indices = [i for i, n in enumerate(self.nodes) if n['type'] == 'carton_plant']
        customer_indices = [i for i, n in enumerate(self.nodes) if n['type'] == 'customer']
        
        # Validar que tenemos datos
        if not plant_indices:
            print("⚠️ Error: No se detectaron plantas de cartón válidas.")
            return None

        dist_matrix = self.distance_matrix.astype(int).tolist()
        num_vehicles = len(plant_indices)
        depot_idx = 0

        manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_idx)
        routing = pywrapcp.RoutingModel(manager)

        # --- DIMENSIONES ---
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(dist_matrix[from_node][to_node])

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        routing.AddDimension(transit_callback_index, 0, DIST_LIMIT, True, 'Distance')
        dist_dim = routing.GetDimensionOrDie('Distance')
        # 2. Plantas (Contador por vehículo)
        def plant_callback(from_index):
            node_idx = manager.IndexToNode(from_index)
            return 1 if self.nodes[node_idx]['type'] == 'carton_plant' else 0
        
        plant_cb_idx = routing.RegisterUnaryTransitCallback(plant_callback)
        routing.AddDimension(plant_cb_idx, 0, 1, True, 'PlantCount')
        plant_dim = routing.GetDimensionOrDie('PlantCount')

        # --- RESTRICCIONES ESTRATÉGICAS ---
        # 1. Cada camión debe visitar exactamente 1 planta
        for v in range(num_vehicles):
            routing.solver().Add(plant_dim.CumulVar(routing.End(v)) == 1)

        # 2. Todas las plantas obligatorias
        for p_idx in plant_indices:
            p_node = manager.NodeToIndex(p_idx)
            routing.solver().Add(routing.ActiveVar(p_node) == 1)

        # 3. Clientes vinculados a su planta
        for c_idx in customer_indices:
            c_node = manager.NodeToIndex(c_idx)
            routing.AddDisjunction([c_node], 1_000_000)
            
            node = self.nodes[c_idx]
            parent_id = node.get('parent_cp')
            p_idx = next((i for i, n in enumerate(self.nodes) if n['id'] == parent_id), None)
            
            if p_idx is not None:
                p_node = manager.NodeToIndex(p_idx)
                # Link estratégico: Mismo vehículo
                routing.solver().Add(
                    routing.ActiveVar(c_node) * (routing.VehicleVar(c_node) - routing.VehicleVar(p_node)) == 0
                )
                # Precedencia
                routing.solver().Add(dist_dim.CumulVar(p_node) < dist_dim.CumulVar(c_node))

        # --- BÚSQUEDA ---
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = 90

        print(f"Iniciando optimización FINAL ({num_vehicles} vehículos)...")
        solution = routing.SolveWithParameters(search_params)
        if solution:
            return self._extract_routes(manager, routing, solution)
        return None

    def _extract_routes(self, manager, routing, solution):
        all_routes = []
        for vehicle_id in range(routing.vehicles()):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                node_idx = manager.IndexToNode(index)
                route.append(self.nodes[node_idx])
                index = solution.Value(routing.NextVar(index))
            # Añadir el nodo final (Depósito)
            node_idx = manager.IndexToNode(index)
            route.append(self.nodes[node_idx])
            
            if len(route) > 2:
                all_routes.append(route)
        return all_routes
