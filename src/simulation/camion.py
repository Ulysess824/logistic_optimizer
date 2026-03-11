import simpy
import pandas as pd
import random
from math import radians, cos, sin, asin, sqrt

class TruckSimulated:
    def __init__(self, origen, rutas, num_muelles=2, num_conductores=30,
                 velocidad_kmh=80, tiempo_carga_h=0.5, camiones_por_ruta=None):
        """
        origen: dict con {'lat', 'lng', 'name'}
        rutas: lista de rutas. Cada ruta es una lista de nodos (dict con 'lat','lng','name','type').
        camiones_por_ruta: lista de enteros que indica cuántos camiones asignar a cada ruta.
                           Si es None, se asigna 1 camión por ruta.
        """
        self.origen = origen
        self.rutas = rutas
        self.velocidad_kmh = velocidad_kmh
        self.tiempo_carga_h = tiempo_carga_h
        self.camiones_por_ruta = camiones_por_ruta

        self.env = simpy.Environment(initial_time=6.0)
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
                dist = self.haversine(
                    ubi_actual["lng"], ubi_actual["lat"],
                    parada["lng"], parada["lat"]
                )
                yield self.env.timeout((dist * 1.3) / self.velocidad_kmh)
                t_llegada = self.env.now

                yield self.env.timeout(self.tiempo_carga_h)
                t_salida = self.env.now

                tramos.append({
                    "nombre": parada["name"], "tipo": parada["type"],
                    "lon_origen": ubi_actual["lng"], "lat_origen": ubi_actual["lat"],
                    "lon_destino": parada["lng"], "lat_destino": parada["lat"],
                    "t_llegada": t_llegada, "t_salida": t_salida
                })

                ubi_actual = parada

            # Retorno al Origen
            dist_retorno = self.haversine(
                ubi_actual["lng"], ubi_actual["lat"],
                self.origen["lng"], self.origen["lat"]
            )
            yield self.env.timeout((dist_retorno * 1.3) / self.velocidad_kmh)
            t_retorno_base = self.env.now

            tramos.append({
                "nombre": "Retorno", "tipo": "retorno",
                "lon_origen": ubi_actual["lng"], "lat_origen": ubi_actual["lat"],
                "lon_destino": self.origen["lng"], "lat_destino": self.origen["lat"],
                "t_llegada": t_retorno_base, "t_salida": t_retorno_base
            })

            self.log_viajes.append({
                "id": id_camion,
                "destino_principal": paradas[0]["name"] if paradas else "Base",
                "t_salida_origen": t_salida_base,
                "t_retorno_base": t_retorno_base,
                "tramos": tramos
            })

    def ejecutar(self):
        """
        Lanza los procesos de cada camión.
        Todos los camiones llegan al depot al inicio del día (con pequeño jitter).
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
                    # Pequeño jitter aleatorio (0-5 min) para que no lleguen exactamente a la vez
                    jitter = random.uniform(0, 5 / 60)
                    todas_las_tareas.append((f"TRK-{camion_idx}", ruta, jitter))
        else:
            for i, ruta in enumerate(self.rutas):
                jitter = random.uniform(0, 5 / 60)
                todas_las_tareas.append((f"TRK-{i + 1}", ruta, jitter))

        # Mezclar el orden de llegada para que no siempre vayan en orden de ruta
        random.shuffle(todas_las_tareas)

        for id_camion, ruta, llegada in todas_las_tareas:
            self.env.process(self.proceso_camion(id_camion, ruta, llegada))

        self.env.run()
        return pd.DataFrame(self.log_viajes)