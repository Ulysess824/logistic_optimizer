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
        """Convierte el JSON de entrada en una lista plana de nodos (Sede primero)."""
        nodes = []
        # El depósito siempre es el primero (Nodo 0)
        # En el JSON se llama 'paper_plant'
        nodes.append({**data['paper_plant'], "id": "DEPOT", "type": "depot"})
        
        # Plantas y sus clientes asociados
        for plant in data['carton_plants']:
            plant_id = plant['id']
            # Copiar datos excluyendo la sublista de clientes
            plant_node = {k: v for k, v in plant.items() if k != 'customers'}
            nodes.append({**plant_node, "type": "carton_plant"})
            
            # Navegar por la lista de clientes real del JSON
            for customer in plant.get('customers', []):
                nodes.append({**customer, "type": "customer", "parent_cp": plant_id})
        return nodes

    def solve(self):
        """Ejecuta el optimizador VRP SOTA."""
        plant_indices = [i for i, n in enumerate(self.nodes) if n['type'] == 'carton_plant']
        customer_indices = [i for i, n in enumerate(self.nodes) if n['type'] == 'customer']
        
        # Forzar distancias a enteros (OR-Tools requirement)
        dist_matrix = self.distance_matrix.astype(int).tolist()
        num_vehicles = len(plant_indices)
        depot_idx = 0

        manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_idx)
        routing = pywrapcp.RoutingModel(manager)

        # Callback de distancia (Simple y rápido)
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return dist_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Dimensión de Distancia
        routing.AddDimension(transit_callback_index, 0, DIST_LIMIT, True, 'Distance')
        dist_dim = routing.GetDimensionOrDie('Distance')

        # Callback de Plantas (Para contar 1 por vehículo)
        def plant_callback(from_index):
            node_idx = manager.IndexToNode(from_index)
            return 1 if self.nodes[node_idx]['type'] == 'carton_plant' else 0
        
        plant_cb_idx = routing.RegisterUnaryTransitCallback(plant_callback)
        routing.AddDimension(plant_cb_idx, 0, 1, True, 'PlantCount')
        plant_dim = routing.GetDimensionOrDie('PlantCount')

        # --- RESTRICCIONES ---
        # 1. Cada camión debe tocar 1 planta exactamente
        for v in range(num_vehicles):
            routing.solver().Add(plant_dim.CumulVar(routing.End(v)) == 1)

        # 2. Distribución de plantas (1 por camión)
        for v, p_idx in enumerate(plant_indices):
            p_node = manager.NodeToIndex(p_idx)
            routing.solver().Add(routing.ActiveVar(p_node) == 1)
            routing.VehicleVar(p_node).SetValues([v])

        # 3. Vinculación backhauling (Cliente con su planta y DESPUÉS de ella)
        for c_idx in customer_indices:
            node = self.nodes[c_idx]
            parent_id = node.get('parent_cp')
            p_idx = next((i for i, n in enumerate(self.nodes) if n['id'] == parent_id), None)
            
            if p_idx is not None:
                c_node = manager.NodeToIndex(c_idx)
                p_node = manager.NodeToIndex(p_idx)
                routing.solver().Add(routing.ActiveVar(c_node) == 1)
                routing.solver().Add(routing.VehicleVar(c_node) == routing.VehicleVar(p_node))
                routing.solver().Add(dist_dim.CumulVar(p_node) < dist_dim.CumulVar(c_node))

        # --- PARÁMETROS ---
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = MAX_SEARCH_TIME

        print(f"Iniciando optimización SOTA para {num_vehicles} rutas estratégicas...")
        solution = routing.SolveWithParameters(search_params)

        if solution:
            return self._extract_routes(manager, routing, solution)
        return None

        if solution:
            return self._extract_routes(manager, routing, solution)
        else:
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
            route.append(self.nodes[manager.IndexToNode(index)])
            if len(route) > 2:
                all_routes.append(route)
        return all_routes
