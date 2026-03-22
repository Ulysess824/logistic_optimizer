import logging
import googlemaps
import numpy as np
import requests
from src.config import GOOGLE_MAPS_API_KEY, OSRM_URL
from src.utils.geo_cache import GeoCache

logger = logging.getLogger(__name__)


class GeoUtils:
    _api_disabled = False

    def __init__(self, api_type="osrm"):
        """Inicializa GeoUtils con la API especificada ('routes_api', 'google_maps', 'osrm' o 'haversine')."""
        self.gmaps = None
        self.api_type = api_type
        self.truck_specs = {}  # Para Routes API
        self.cache = GeoCache()
        
        if GOOGLE_MAPS_API_KEY:
            # Cliente clásico de Directions / Distance Matrix API
            self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
            
    def set_truck_specs(self, **kwargs):
        """
        Configura los parámetros del camión para la Google Routes API.
        Ejemplo: .set_truck_specs(emissionType="DIESEL", heightCm=365, weightKg=10000)
        """
        self.truck_specs = kwargs
        if self.truck_specs:
            logger.info("Especificaciones de camión configuradas: %s", self.truck_specs)

    # ------------------------------------------------------------------
    # Haversine — versión "nodo dict" (metros)
    # ------------------------------------------------------------------
    def haversine_distance(self, node_a, node_b):
        """Distancia en línea recta (metros) entre dos nodos {'lat', 'lng'}."""
        return self.haversine_km(
            node_a['lat'], node_a['lng'],
            node_b['lat'], node_b['lng']
        ) * 1000

    # ------------------------------------------------------------------
    # Haversine — versión vectorizada (km). Acepta escalares o np.arrays.
    # ------------------------------------------------------------------
    @staticmethod
    def haversine_km(lat1, lon1, lat2, lon2):
        """Calcula la distancia Haversine en **km**.

        Acepta escalares o arrays de NumPy para cálculos vectorizados.
        """
        R = 6371  # Radio de la Tierra en km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (np.sin(dlat / 2) ** 2
             + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
             * np.sin(dlon / 2) ** 2)
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # ------------------------------------------------------------------
    # Matriz de distancias
    # ------------------------------------------------------------------
    def calculate_distance_matrix(self, nodes):
        """
        Calcula la matriz de distancias (en metros) entre todos los nodos,
        seleccionando el proveedor configurado en self.api_type.
        """
        if self.api_type == "haversine" or GeoUtils._api_disabled:
            return self._fallback_haversine_matrix(nodes)
        
        if self.api_type == "routes_api":
            return self._calculate_distance_matrix_routes_api(nodes)
            
        if self.api_type == "osrm":
            return self._calculate_distance_matrix_osrm(nodes)
            
        # Fallback a la implementación clásica (Distance Matrix v1)
        return self._calculate_distance_matrix_google_maps(nodes)

    def _fallback_haversine_matrix(self, nodes):
        num_nodes = len(nodes)
        logger.info("Calculando matriz de distancias con Haversine vectorizado (%d nodos)...", num_nodes)
        
        lats = np.array([n['lat'] for n in nodes])
        lngs = np.array([n['lng'] for n in nodes])
        
        # Broadcasting: cada fila i contra cada columna j
        lat1 = np.radians(lats[:, None])
        lat2 = np.radians(lats[None, :])
        dlat = lat2 - lat1
        dlon = np.radians(lngs[None, :] - lngs[:, None])
        
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        matrix = 6371000 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))  # En metros
        
        return matrix, False

    def _calculate_distance_matrix_routes_api(self, nodes):
        """Calcula distancias usando la nueva Routes API de Google Maps (v2) con soporte para camiones."""
        num_nodes = len(nodes)
        matrix = np.zeros((num_nodes, num_nodes))
        
        # 1. Intentar llenar lo máximo posible desde caché
        missing_pairs = []
        for i in range(num_nodes):
            for j in range(num_nodes):
                if i == j:
                    matrix[i][j] = 0
                    continue
                cached = self.cache.get_route(
                    (nodes[i]['lat'], nodes[i]['lng']),
                    (nodes[j]['lat'], nodes[j]['lng']),
                    truck_specs=self.truck_specs
                )
                if cached:
                    matrix[i][j] = cached['distance_meters']
                else:
                    missing_pairs.append((i, j))

        if not missing_pairs:
            logger.info("Matriz de distancias recuperada íntegramente de la caché.")
            return matrix, True

        if not GOOGLE_MAPS_API_KEY:
            logger.warning("Falta GOOGLE_MAPS_API_KEY para Routes API. Usando Haversine para pares faltantes.")
            for i, j in missing_pairs:
                matrix[i][j] = self.haversine_distance(nodes[i], nodes[j])
            return matrix, False

        logger.info("Obteniendo %d pares faltantes de Google Routes API...", len(missing_pairs))
        # Para simplificar, si faltan pares, relanzamos la matriz completa o por lotes como estaba.
        # (Routes API es eficiente en matrices). En el futuro se podría optimizar para pedir solo los missing.
        
        url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters,duration,status"
        }
        
        try:
            origins_full = [{"waypoint": {"location": {"latLng": {"latitude": n['lat'], "longitude": n['lng']}}}} for n in nodes]
            destinations_full = [{"waypoint": {"location": {"latLng": {"latitude": n['lat'], "longitude": n['lng']}}}} for n in nodes]

            
            # Sanitizar payload de camiones
            valid_vehicle_info = {}
            if self.truck_specs and "emissionType" in self.truck_specs:
                valid_vehicle_info["emissionType"] = self.truck_specs["emissionType"]
                
            if valid_vehicle_info:
                for origin in origins_full:
                    origin["routeModifiers"] = {"vehicleInfo": valid_vehicle_info}
            
            destinations_full = [{"waypoint": {"location": {"latLng": {"latitude": n['lat'], "longitude": n['lng']}}}} for n in nodes]
            
            BATCH_SIZE = 25
            for i in range(0, num_nodes, BATCH_SIZE):
                batch_origins = origins_full[i:i+BATCH_SIZE]
                for j in range(0, num_nodes, BATCH_SIZE):
                    batch_destinations = destinations_full[j:j+BATCH_SIZE]
                    
                    payload = {
                        "origins": batch_origins,
                        "destinations": batch_destinations,
                        "travelMode": "DRIVE",
                        "routingPreference": "TRAFFIC_AWARE",
                    }
        
                    response = requests.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        for element in data:
                            o_idx = i + element.get('originIndex', 0)
                            d_idx = j + element.get('destinationIndex', 0)
                            dist = element.get('distanceMeters')
                            status = element.get('status', {}).get('code', 0)
                            
                            # Validar que si la llave status existe, sea 0 (OK)
                            has_error = False
                            if isinstance(status, dict) and status.get('code', 0) != 0:
                                has_error = True
                            elif isinstance(element.get('status'), dict):
                                if element.get('status', {}).get('code') not in [None, 0]:
                                    has_error = True

                            if has_error:
                                 matrix[o_idx][d_idx] = self.haversine_distance(nodes[o_idx], nodes[d_idx])
                            else:
                                 # Parsear duración de Google (e.g. "123s" o "123.4s")
                                 dur_str = element.get('duration', '0s')
                                 try:
                                     dur_val = float(dur_str.rstrip('s'))
                                 except:
                                     dur_val = 0
                                     
                                 val = dist if dist is not None else self.haversine_distance(nodes[o_idx], nodes[d_idx])
                                 matrix[o_idx][d_idx] = val
                                 # Guardar en caché
                                 self.cache.store_route(
                                     (nodes[o_idx]['lat'], nodes[o_idx]['lng']),
                                     (nodes[d_idx]['lat'], nodes[d_idx]['lng']),
                                     val, duration=dur_val, truck_specs=self.truck_specs
                                 )
                    else:
                        if response.status_code in [403, 401] or "bill" in response.text.lower() or "not enabled" in response.text.lower():
                            logger.warning("Google Maps Billing/Auth/API no activo (Routes API). Usando Haversine.")
                            GeoUtils._api_disabled = True
                            return self._fallback_haversine_matrix(nodes)
                        else:
                            logger.warning(f"Error Routes API HTTP {response.status_code}: {response.text}")
                            # fallback de este bloque a haversine
                            for o in range(i, min(i+BATCH_SIZE, num_nodes)):
                                for d in range(j, min(j+BATCH_SIZE, num_nodes)):
                                    matrix[o][d] = self.haversine_distance(nodes[o], nodes[d])
                                    
            return matrix, True
        except Exception as e:
            logger.error(f"Excepción al llamar a Routes API: {e}")
            return self._fallback_haversine_matrix(nodes)

    def _calculate_distance_matrix_osrm(self, nodes):
        """Calcula distancias usando el servidor gratuito de OpenStreetMap (OSRM)."""
        num_nodes = len(nodes)
        matrix = np.zeros((num_nodes, num_nodes))
        
        # 1. Intentar llenar desde caché (Ignoramos truck_specs para OSM)
        missing_pairs = []
        for i in range(num_nodes):
            for j in range(num_nodes):
                if i == j:
                    matrix[i][j] = 0
                    continue
                cached = self.cache.get_route(
                    (nodes[i]['lat'], nodes[i]['lng']),
                    (nodes[j]['lat'], nodes[j]['lng']),
                    truck_specs={} # OSM ignora specs
                )
                if cached:
                    matrix[i][j] = cached['distance_meters']
                else:
                    missing_pairs.append((i, j))

        if not missing_pairs:
            logger.info("Matriz OSM recuperada íntegramente de la caché.")
            return matrix, True

        # 2. Llamada a la API de OSRM (Table API)
        # Formato: lon,lat;lon,lat...
        coords_str = ";".join([f"{n['lng']},{n['lat']}" for n in nodes])
        
        # Intentar servidor local (OSRM_URL) o fallback al público
        urls_to_try = [
            f"{OSRM_URL}/table/v1/driving/{coords_str}?sources=all&destinations=all&annotations=distance,duration",
            f"http://router.project-osrm.org/table/v1/driving/{coords_str}?sources=all&destinations=all&annotations=distance,duration"
        ]

        for url in urls_to_try:
            try:
                logger.info(f"Consultando OSRM en: {url}...")
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'distances' in data and 'durations' in data:
                        # OSRM devuelve una matriz [origen][destino]
                        for i in range(num_nodes):
                            for j in range(num_nodes):
                                dist_val = data['distances'][i][j]
                                dur_val = data['durations'][i][j]
                                if dist_val is not None:
                                    matrix[i][j] = dist_val
                                    # Guardar en caché para futuras ejecuciones
                                    if i != j:
                                        self.cache.store_route(
                                            (nodes[i]['lat'], nodes[i]['lng']),
                                            (nodes[j]['lat'], nodes[j]['lng']),
                                            dist_val, duration=dur_val, truck_specs={}
                                        )
                                else:
                                    matrix[i][j] = self.haversine_distance(nodes[i], nodes[j])
                        return matrix, True
            except Exception as e:
                logger.debug(f"Servidor OSRM {url} no disponible: {e}")
                continue
        
        logger.warning(f"Ningún servidor OSRM respondió. Usando Haversine.")
        return self._fallback_haversine_matrix(nodes)
            
    def _calculate_distance_matrix_google_maps(self, nodes):
        """
        Implementación original usando la clásica Google Maps Distance Matrix API.
        """
        num_nodes = len(nodes)
        matrix = np.zeros((num_nodes, num_nodes))
        
        use_roadmap = self.gmaps is not None and not GeoUtils._api_disabled

        if use_roadmap:
            BATCH_SIZE = 25  # Límite de Google Maps Distance Matrix API
            logger.info("Obteniendo distancias reales de Google Maps Clásico (lotes de %d)...", BATCH_SIZE)
            try:
                all_destinations = [(n['lat'], n['lng']) for n in nodes]
                for i in range(num_nodes):
                    origins = [(nodes[i]['lat'], nodes[i]['lng'])]
                    # Partir destinos en lotes de BATCH_SIZE
                    for batch_start in range(0, num_nodes, BATCH_SIZE):
                        batch_end = min(batch_start + BATCH_SIZE, num_nodes)
                        batch_destinations = all_destinations[batch_start:batch_end]

                        response = self.gmaps.distance_matrix(
                            origins,
                            batch_destinations,
                            mode="driving"
                        )

                        if response['status'] == 'OK':
                            row_results = response['rows'][0]['elements']
                            for k, result in enumerate(row_results):
                                j = batch_start + k
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
                    logger.warning("Google Maps Billing no activo. Usando estimación Haversine.")
                    GeoUtils._api_disabled = True
                else:
                    logger.warning("Error en API Google: %s. Usando estimación Haversine.", e)

        # Fallback a Haversine si no se hizo arriba
        return self._fallback_haversine_matrix(nodes)

    # ------------------------------------------------------------------
    # Polyline para carreteras
    # ------------------------------------------------------------------
    def get_route_polyline(self, start_coords, end_coords):
        """Obtiene la geometría de la carretera entre dos puntos basándose en la API configurada."""
        # Check cache
        cached = self.cache.get_polyline(start_coords, end_coords, truck_specs=self.truck_specs)
        if cached:
            return cached
        
        if self.api_type == 'haversine':
            # En modo haversine, podemos devolver una línea recta opcionalmente
            # o simplemente None para que el visualizador use líneas geodésicas.
            return None
        elif self.api_type == "routes_api":
            res = self._get_route_polyline_routes_api(start_coords, end_coords)
        elif self.api_type == "osrm":
            res = self._get_route_polyline_osrm(start_coords, end_coords)
        else:
            res = self._get_route_polyline_google_maps(start_coords, end_coords)
        
        # Store in cache
        if res and res != "BILLING_ERROR":
            self.cache.store_polyline(start_coords, end_coords, res, truck_specs=self.truck_specs)
        
        return res
        
    def _get_route_polyline_routes_api(self, start_coords, end_coords):
        """Obtiene polyline usando Routes API."""
        if GeoUtils._api_disabled or not GOOGLE_MAPS_API_KEY:
            return None
            
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline"
        }
        
        payload = {
            "origin": {"location": {"latLng": {"latitude": start_coords[0], "longitude": start_coords[1]}}},
            "destination": {"location": {"latLng": {"latitude": end_coords[0], "longitude": end_coords[1]}}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        }
        
        valid_vehicle_info = {}
        if self.truck_specs and "emissionType" in self.truck_specs:
            valid_vehicle_info["emissionType"] = self.truck_specs["emissionType"]
            
        if valid_vehicle_info:
            payload["routeModifiers"] = {"vehicleInfo": valid_vehicle_info}
            
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if "routes" in data and len(data["routes"]) > 0:
                    return data["routes"][0].get("polyline", {}).get("encodedPolyline")
            elif response.status_code in [403, 401] or "bill" in response.text.lower():
                GeoUtils._api_disabled = True
                return "BILLING_ERROR"
        except Exception as e:
            logger.error(f"Error consultando Routes API Polyline: {e}")
        return None

    def _get_route_polyline_google_maps(self, start_coords, end_coords):
        """Obtiene la geometría de la carretera usando la API clásica."""
        if not self.gmaps:
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

    def _get_route_polyline_osrm(self, start_coords, end_coords):
        """Obtiene polyline usando OSRM."""
        path = f"/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=polyline"
        urls_to_try = [f"{OSRM_URL}{path}", f"http://router.project-osrm.org{path}"]

        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if "routes" in data and len(data["routes"]) > 0:
                        return data["routes"][0].get("geometry")
            except Exception:
                continue
        return None
