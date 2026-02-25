import googlemaps
import numpy as np
from src.config import GOOGLE_MAPS_API_KEY

class GeoUtils:
    _api_disabled = False

    def __init__(self):
        self.gmaps = None
        if GOOGLE_MAPS_API_KEY:
            self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    def calculate_distance_matrix(self, nodes):
        """
        Calcula la matriz de distancias (en metros) entre todos los nodos.
        Utiliza Google Maps API con optimización de lotes por origen.
        """
        num_nodes = len(nodes)
        matrix = np.zeros((num_nodes, num_nodes))
        
        # Primero intentamos con Google Maps
        use_roadmap = self.gmaps is not None and not GeoUtils._api_disabled
        
        if use_roadmap:
            print("Fetching Real Road Distances from Google Maps (Origin-by-Origin Batching)...")
            try:
                for i in range(num_nodes):
                    # Google Matrix API permite hasta 25 destinos por origen
                    origins = [(nodes[i]['lat'], nodes[i]['lng'])]
                    destinations = [(n['lat'], n['lng']) for n in nodes]
                    
                    response = self.gmaps.distance_matrix(
                        origins, 
                        destinations, 
                        mode="driving"
                    )
                    
                    if response['status'] == 'OK':
                        row_results = response['rows'][0]['elements']
                        for j, result in enumerate(row_results):
                            if result['status'] == 'OK':
                                matrix[i][j] = result['distance']['value']
                            else:
                                if result.get('status') == 'REQUEST_DENIED' or 'billing' in str(result).lower():
                                    raise Exception("BILLING_ERROR")
                                matrix[i][j] = self.haversine_distance(nodes[i], nodes[j])
                    else:
                        raise Exception("API_ERROR")
                return matrix, True
            except Exception as e:
                if "BILLING" in str(e).upper():
                    print("AVISO: Google Maps Billing no activo. Usando estimación Haversine (Línea recta).")
                    GeoUtils._api_disabled = True
                else:
                    print(f"Error en API Google: {e}. Usando estimación Haversine.")
        
        # Fallback a Haversine
        for i in range(num_nodes):
            for j in range(num_nodes):
                matrix[i][j] = self.haversine_distance(nodes[i], nodes[j])
        return matrix, False

    def haversine_distance(self, node_a, node_b):
        """Calcula la distancia en línea recta (metros) entre dos puntos GPS."""
        R = 6371000 # Radio Tierra en metros
        lat1, lon1 = np.radians(node_a['lat']), np.radians(node_a['lng'])
        lat2, lon2 = np.radians(node_b['lat']), np.radians(node_b['lng'])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c

    def get_route_polyline(self, start_coords, end_coords):
        """Obtiene la geometría de la carretera entre dos puntos."""
        if not self.gmaps or GeoUtils._api_disabled:
            return None
        try:
            result = self.gmaps.directions(
                start_coords, end_coords, mode="driving"
            )
            if result:
                return result[0]['overview_polyline']['points']
        except Exception:
            return "BILLING_ERROR"
        return None
