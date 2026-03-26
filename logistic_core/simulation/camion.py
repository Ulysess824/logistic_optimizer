import simpy
import pandas as pd
import random
from math import radians, cos, sin, asin, sqrt


class TruckSimulated:
    def __init__(self, origen, rutas, num_muelles=2, num_conductores=30,
                 inicio_operacion_h=6.5, velocidad_kmh=80, tiempo_carga_h=0.5,
                 max_pallets=35, geo_utils=None):
        """
        Simula operaciones de camiones sobre rutas optimizadas via SimPy.

        Parametros
        ----------
        origen : dict
            Depot central con claves 'lat', 'lng', 'name'.
        rutas : list[list[dict]]
            Cada ruta es una lista de nodos (dict con 'lat','lng','name','type',
            y opcionalmente 'demanda_pallets', 'id').
        num_muelles : int
            Cantidad de muelles disponibles para carga simultanea.
        num_conductores : int
            Cantidad de conductores disponibles.
        inicio_operacion_h : float
            Hora de inicio de operaciones (6.5 = 06:30).
        velocidad_kmh : float
            Velocidad media de los camiones.
        tiempo_carga_h : float
            Tiempo de carga/descarga por parada (horas).
        camiones_por_ruta : list[int] | None
            Lista que indica cuantos camiones asignar a cada ruta (por indice).
            Si es None y flota_por_planta tampoco se da, 1 camion por ruta.
        flota_por_planta : dict | None
            Diccionario {plant_id: num_camiones}. Tiene prioridad sobre
            camiones_por_ruta. Asigna camiones segun la planta de cada ruta.
        max_pallets : int
            Capacidad maxima del camion en pallets.
        geo_utils : GeoUtils | None
            Instancia de GeoUtils para obtener distancias y polilineas reales.
        """
        self.origen = origen
        self.rutas = rutas
        self.velocidad_kmh = velocidad_kmh
        self.tiempo_carga_h = tiempo_carga_h
        self.max_pallets = max_pallets
        self.geo_utils = geo_utils

        self.env = simpy.Environment(initial_time=inicio_operacion_h)
        self.muelles = simpy.Resource(self.env, capacity=num_muelles)
        self.conductores = simpy.Resource(self.env, capacity=num_conductores)
        self.log_viajes = []

    # ------------------------------------------------------------------
    #  Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon, dlat = lon2 - lon1, lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 6367 * 2 * asin(sqrt(a))

    @staticmethod
    def _clean_plant_name(name: str) -> str:
        """Elimina sufijos de muelles clonados."""
        return name.upper().replace(' (MUELLE 2)', '').replace(' (MUELLE 3)', '')

    @staticmethod
    def _clean_plant_id(raw_id: str) -> str:
        """Devuelve el plant_id sin el sufijo _clone_X."""
        return raw_id.split('_clone_')[0] if '_clone_' in raw_id else raw_id



    # ------------------------------------------------------------------
    #  Proceso principal
    # ------------------------------------------------------------------
    def proceso_camion(self, id_camion, ruta, momento_llegada):
        yield self.env.timeout(momento_llegada)

        # FASE 1: Carga en Origen
        with self.muelles.request() as req_mue:
            yield req_mue
            yield self.env.timeout(self.tiempo_carga_h)

        with self.conductores.request() as req_cond:
            yield req_cond

            t_salida_base = self.env.now

            if len(ruta) < 2:
                self.log_viajes.append({
                    "id": id_camion, "destino": "Ruta Vacia",
                    "t_salida_origen": t_salida_base,
                    "t_retorno_base": t_salida_base, "tramos": [],
                    "pallets_cargados": 0,
                    "max_pallets": self.max_pallets,
                    "pct_uso": 0.0,
                    "planta": "",
                    "plant_id": "",
                })
                return

            # Calcular carga de pallets
            clientes_ruta = [n for n in ruta if n['type'] == 'customer']
            pallets_cargados = sum(n.get('demanda_pallets', 0) for n in clientes_ruta)
            pct_uso = min((pallets_cargados / self.max_pallets) * 100, 100.0) if self.max_pallets > 0 else 0.0

            # Extraer info de planta
            planta_node = next((n for n in ruta if n['type'] == 'carton_plant'), None)
            planta_name = self._clean_plant_name(planta_node['name']) if planta_node else ""
            plant_id = self._clean_plant_id(planta_node.get('id', '')) if planta_node else ""

            tramos = []
            
            for j in range(len(ruta) - 1):
                origen_nodo = ruta[j]
                destino_nodo = ruta[j+1]

                polyline = None
                duration_h = None
                dist = 0.0

                if self.geo_utils:
                    start = (origen_nodo["lat"], origen_nodo["lng"])
                    end = (destino_nodo["lat"], destino_nodo["lng"])
                    res = self.geo_utils.cache.get_route(start, end)

                    if res and res.get("distance_meters") is not None and res.get("duration_seconds") is not None:
                        dist = res["distance_meters"] / 1000.0
                        duration_h = res["duration_seconds"] / 3600.0
                        polyline = res.get("polyline")

                        if not polyline:
                            polyline = self.geo_utils.get_route_polyline(start, end)
                    else:
                        polyline = self.geo_utils.get_route_polyline(start, end)
                        res_retry = self.geo_utils.cache.get_route(start, end)
                        
                        if res_retry and res_retry.get("distance_meters") is not None:
                            dist = res_retry["distance_meters"] / 1000.0
                            if res_retry.get("duration_seconds") is not None:
                                duration_h = res_retry["duration_seconds"] / 3600.0
                        else:
                            dist = self.haversine(origen_nodo["lng"], origen_nodo["lat"],
                                                  destino_nodo["lng"], destino_nodo["lat"]) * 1.3
                else:
                    dist = self.haversine(origen_nodo["lng"], origen_nodo["lat"],
                                          destino_nodo["lng"], destino_nodo["lat"]) * 1.3

                # Tiempo de viaje: Real de la API o estimado por velocidad fija
                t_viaje = duration_h if (duration_h is not None and duration_h > 0) else (dist / self.velocidad_kmh)

                # Seguridad: evitar "teletransporte"
                if dist > 0.1 and t_viaje < 0.001:
                    t_viaje = dist / self.velocidad_kmh

                yield self.env.timeout(t_viaje)
                t_llegada = self.env.now

                # Anadimos tiempo de carga en todas las paradas que no sean el ultimo retorno al depot
                if j < len(ruta) - 2:
                    yield self.env.timeout(self.tiempo_carga_h)
                
                t_salida = self.env.now

                tramos.append({
                    "nombre": destino_nodo["name"], "tipo": destino_nodo["type"],
                    "lon_origen": origen_nodo["lng"], "lat_origen": origen_nodo["lat"],
                    "lon_destino": destino_nodo["lng"], "lat_destino": destino_nodo["lat"],
                    "t_llegada": t_llegada, "t_salida": t_salida,
                    "polyline": polyline,
                    "demanda_pallets": destino_nodo.get("demanda_pallets", 0),
                })

            t_retorno_base = self.env.now

            self.log_viajes.append({
                "id": id_camion,
                "destino_principal": ruta[1]["name"] if len(ruta) > 1 else "Base",
                "t_salida_origen": t_salida_base,
                "t_retorno_base": t_retorno_base,
                "tramos": tramos,
                "pallets_cargados": pallets_cargados,
                "max_pallets": self.max_pallets,
                "pct_uso": round(pct_uso, 1),
                "planta": planta_name,
                "plant_id": plant_id,
            })

    # ------------------------------------------------------------------
    #  Ejecucion
    # ------------------------------------------------------------------
    def ejecutar(self, desfase_hora=0.4):
        """
        Lanza los procesos de cada camion.
        Todos los camiones llegan al depot al inicio del dia (con un desfase aleatorio).
        Los Resources de SimPy (muelles, conductores) generan los cuellos de
        botella reales: solo N camiones pueden cargar a la vez.
        """
        camion_idx = 0
        todas_las_tareas = []

        for ruta_i, ruta in enumerate(self.rutas):
            camion_idx += 1
            jitter = random.uniform(0, desfase_hora)
            todas_las_tareas.append((f"TRK-{camion_idx}", ruta, jitter))

        # Mezclar el orden de llegada para que no siempre vayan en orden de ruta
        random.shuffle(todas_las_tareas)

        for id_camion, ruta, llegada in todas_las_tareas:
            self.env.process(self.proceso_camion(id_camion, ruta, llegada))

        self.env.run()
        return pd.DataFrame(self.log_viajes)
