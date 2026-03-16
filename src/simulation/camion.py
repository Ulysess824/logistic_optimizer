import simpy
import pandas as pd
import random
from math import radians, cos, sin, asin, sqrt

class TruckSimulated:
    def __init__(self, origen, rutas, num_muelles=2, num_conductores=30, inicio_operacion_h = 6.5,
                 velocidad_kmh=80, tiempo_carga_h=0.5, camiones_por_ruta=None, geo_utils=None):
        """
        origen: dict con {'lat', 'lng', 'name'}
        rutas: lista de rutas. Cada ruta es una lista de nodos (dict con 'lat','lng','name','type').
        camiones_por_ruta: lista de enteros que indica cuántos camiones asignar a cada ruta.
                           Si es None, se asigna 1 camión por ruta.
        geo_utils: Instancia de GeoUtils para obtener distancias y polilíneas reales.
        """
        self.origen = origen
        self.rutas = rutas
        self.velocidad_kmh = velocidad_kmh
        self.tiempo_carga_h = tiempo_carga_h
        self.camiones_por_ruta = camiones_por_ruta
        self.geo_utils = geo_utils

        self.env = simpy.Environment(initial_time=inicio_operacion_h)
        self.muelles = simpy.Resource(self.env, capacity=num_muelles)
        self.conductores = simpy.Resource(self.env, capacity=num_conductores)
        self.log_viajes = []

    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon, dlat = lon2 - lon1, lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6367 * 2 * asin(sqrt(a))

    def proceso_camion(self, id_camion, ruta, momento_llegada):
        yield self.env.timeout(momento_llegada)

        # FASE 1: Carga en Origen
        with self.muelles.request() as req_mue:
            yield req_mue
            yield self.env.timeout(self.tiempo_carga_h)

        with self.conductores.request() as req_cond:
            yield req_cond

            t_salida_base = self.env.now

            paradas = [nodo for nodo in ruta if nodo['type'] != 'depot']

            if not paradas:
                self.log_viajes.append({
                    "id": id_camion, "destino": "Ruta Vacía",
                    "t_salida_origen": t_salida_base,
                    "t_retorno_base": t_salida_base, "tramos": []
                })
                return

            tramos = []
            ubi_actual = self.origen

            for parada in paradas:
                # Intentar obtener duración real (segundos) de la cache
                polyline = None
                duration_h = None
                if self.geo_utils:
                    start = (ubi_actual["lat"], ubi_actual["lng"])
                    end = (parada["lat"], parada["lng"])
                    res = self.geo_utils.cache.get_route(start, end)
                    
                    if res:
                        dist = res["distance_meters"] / 1000.0
                        duration_h = res["duration_seconds"] / 3600.0
                        polyline = res.get("polyline")
                        
                        # Si no hay polilínea en caché (común con OSRM Table), la buscamos
                        if not polyline:
                            polyline = self.geo_utils.get_route_polyline(start, end)
                    else:
                        # Si no hay nada en caché, intentamos obtener la polilínea (que también guarda la ruta en caché)
                        polyline = self.geo_utils.get_route_polyline(start, end)
                        # Re-consultamos caché tras el fetch de polilínea
                        res = self.geo_utils.cache.get_route(start, end)
                        if res:
                            dist = res["distance_meters"] / 1000.0
                            duration_h = res["duration_seconds"] / 3600.0
                        else:
                            dist = self.haversine(ubi_actual["lng"], ubi_actual["lat"], parada["lng"], parada["lat"]) * 1.3
                else:
                    dist = self.haversine(ubi_actual["lng"], ubi_actual["lat"], parada["lng"], parada["lat"]) * 1.3

                # Tiempo de viaje: Real de la API o estimado por velocidad fija
                t_viaje = duration_h if (duration_h is not None and duration_h > 0) else (dist / self.velocidad_kmh)
                
                # Seguridad: si hay distancia pero t_viaje es casi 0, forzamos algo de tiempo para evitar "teletransporte"
                if dist > 0.1 and t_viaje < 0.001:
                    t_viaje = dist / self.velocidad_kmh
                    
                yield self.env.timeout(t_viaje)
                t_llegada = self.env.now

                yield self.env.timeout(self.tiempo_carga_h)
                t_salida = self.env.now

                tramos.append({
                    "nombre": parada["name"], "tipo": parada["type"],
                    "lon_origen": ubi_actual["lng"], "lat_origen": ubi_actual["lat"],
                    "lon_destino": parada["lng"], "lat_destino": parada["lat"],
                    "t_llegada": t_llegada, "t_salida": t_salida,
                    "polyline": polyline
                })

                ubi_actual = parada

            # --- RETORNO AL ORIGEN ---
            polyline_ret = None
            duration_ret_h = None
            dist_retorno = 0.0 # Initialize dist_retorno for safety check
            if self.geo_utils:
                start = (ubi_actual["lat"], ubi_actual["lng"])
                end = (self.origen["lat"], self.origen["lng"])
                res = self.geo_utils.cache.get_route(start, end)
                if res:
                    dist_retorno = res["distance_meters"] / 1000.0
                    duration_ret_h = res["duration_seconds"] / 3600.0
                    polyline_ret = res.get("polyline")
                    if not polyline_ret:
                        polyline_ret = self.geo_utils.get_route_polyline(start, end)
                else:
                    polyline_ret = self.geo_utils.get_route_polyline(start, end)
                    res = self.geo_utils.cache.get_route(start, end)
                    if res:
                        dist_retorno = res["distance_meters"] / 1000.0
                        duration_ret_h = res["duration_seconds"] / 3600.0
                    else:
                        dist_retorno = self.haversine(ubi_actual["lng"], ubi_actual["lat"], self.origen["lng"], self.origen["lat"]) * 1.3
            else:
                dist_retorno = self.haversine(ubi_actual["lng"], ubi_actual["lat"], self.origen["lng"], self.origen["lat"]) * 1.3
            
            # Tiempo de retorno: Real de la API o estimado por velocidad fija
            duration_ret_h = duration_ret_h if (duration_ret_h is not None and duration_ret_h > 0) else (dist_retorno / self.velocidad_kmh)

            # Seguridad: si hay distancia pero duration_ret_h es casi 0, forzamos algo de tiempo para evitar "teletransporte"
            if dist_retorno > 0.1 and duration_ret_h < 0.001:
                duration_ret_h = dist_retorno / self.velocidad_kmh
            
            yield self.env.timeout(duration_ret_h)
            t_retorno_base = self.env.now

            tramos.append({
                "nombre": "Retorno", "tipo": "retorno",
                "lon_origen": ubi_actual["lng"], "lat_origen": ubi_actual["lat"],
                "lon_destino": self.origen["lng"], "lat_destino": self.origen["lat"],
                "t_llegada": t_retorno_base, "t_salida": t_retorno_base,
                "polyline": polyline_ret
            })

            self.log_viajes.append({
                "id": id_camion,
                "destino_principal": paradas[0]["name"] if paradas else "Base",
                "t_salida_origen": t_salida_base,
                "t_retorno_base": t_retorno_base,
                "tramos": tramos
            })

    def ejecutar(self, desfase_hora=0.4):
        """
        Lanza los procesos de cada camión.
        Todos los camiones llegan al depot al inicio del día (con un desfase aleatorio).
        Los Resources de SimPy (muelles, conductores) generan los cuellos de
        botella reales: solo N camiones pueden cargar a la vez.
        """
        camion_idx = 0
        todas_las_tareas = []

        if self.camiones_por_ruta:
            for ruta_i, ruta in enumerate(self.rutas):
                n = self.camiones_por_ruta[ruta_i] if ruta_i < len(self.camiones_por_ruta) else 1
                for j in range(n):
                    camion_idx += 1
                    # Desfase aleatorio para distribuir llegadas y simular variabilidad
                    jitter = random.uniform(0, desfase_hora)
                    todas_las_tareas.append((f"TRK-{camion_idx}", ruta, jitter))
        else:
            for i, ruta in enumerate(self.rutas):
                jitter = random.uniform(0, desfase_hora)
                todas_las_tareas.append((f"TRK-{i + 1}", ruta, jitter))

        # Mezclar el orden de llegada para que no siempre vayan en orden de ruta
        random.shuffle(todas_las_tareas)

        for id_camion, ruta, llegada in todas_las_tareas:
            self.env.process(self.proceso_camion(id_camion, ruta, llegada))

        self.env.run()
        return pd.DataFrame(self.log_viajes)