import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import pandas as pd
import polyline


class AnimadorLogistico:
    def __init__(self, df_resultados, origen, usar_rutas_reales=True):
        """
        Genera una animacion GIF de los camiones sobre un mapa de la
        Peninsula Iberica.

        Parametros
        ----------
        df_resultados : pd.DataFrame
            DataFrame resultante de TruckSimulated.ejecutar().
            Columnas esperadas: id, destino_principal, t_salida_origen,
            t_retorno_base, tramos, pallets_cargados, max_pallets, pct_uso,
            planta, plant_id.
        origen : dict
            Depot central con claves 'lat', 'lng', 'name'.
        usar_rutas_reales : bool
            True = polilineas de carretera. False = lineas rectas.
        """
        self.df = df_resultados
        self.origen = origen
        self.usar_rutas_reales = usar_rutas_reales

        # Pre-decodificar polilineas para optimizar la animacion
        for _, row in self.df.iterrows():
            for tramo in row['tramos']:
                if tramo.get('polyline'):
                    try:
                        pts = polyline.decode(tramo['polyline'])
                        tramo['decoded_path'] = [(p[1], p[0]) for p in pts]
                    except Exception:
                        tramo['decoded_path'] = None
                else:
                    tramo['decoded_path'] = None

        self.fig, self.ax = plt.subplots(figsize=(12, 9))

        # Mapa Iberia
        self.ax.set_xlim(-10, 5)
        self.ax.set_ylim(35.5, 44.5)
        self.ax.set_facecolor('#f0f4f8')
        self.ax.set_title("Simulacion Logistica - Flotas Diarias", fontsize=14, weight='bold')

        # 1. Dibujar Origen
        self.ax.plot(origen['lng'], origen['lat'], 'g^', markersize=12,
                     label=f"Depot: {origen.get('name', 'Depot')}", zorder=6)

        # Recopilar nodos para el mapa estatico
        nodos_planta_lon, nodos_planta_lat, nombres_planta = [], [], []
        nodos_cliente_lon, nodos_cliente_lat = [], []
        seen_plantas = set()

        for _, row in self.df.iterrows():
            for tramo in row['tramos']:
                if tramo['tipo'] == 'carton_plant':
                    key = (round(tramo['lon_destino'], 3), round(tramo['lat_destino'], 3))
                    if key not in seen_plantas:
                        seen_plantas.add(key)
                        nodos_planta_lon.append(tramo['lon_destino'])
                        nodos_planta_lat.append(tramo['lat_destino'])
                        nombre_limpio = re.sub(r"\s*\(Muelle \d+\)", "", tramo['nombre'])
                        nombres_planta.append(nombre_limpio)
                elif tramo['tipo'] == 'customer':
                    nodos_cliente_lon.append(tramo['lon_destino'])
                    nodos_cliente_lat.append(tramo['lat_destino'])

        # 2. Dibujar Plantas
        if nodos_planta_lon:
            self.ax.scatter(nodos_planta_lon, nodos_planta_lat,
                            color='royalblue', s=40, alpha=0.6, label='Plantas', zorder=4)
            for px, py, nombre in zip(nodos_planta_lon, nodos_planta_lat, nombres_planta):
                self.ax.annotate(nombre, (px, py), fontsize=6, alpha=0.7,
                                 xytext=(4, 4), textcoords='offset points')

        # 3. Dibujar Clientes
        if nodos_cliente_lon:
            self.ax.scatter(nodos_cliente_lon, nodos_cliente_lat,
                            marker='s', color='orange', s=25, alpha=0.5, label='Clientes', zorder=4)

        # Elementos dinamicos
        self.puntos_camiones = self.ax.scatter([], [], c='crimson', s=50,
                                               edgecolors='black', zorder=7)

        # Panel de informacion (fondo semi-transparente)
        props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.85, edgecolor='#ccc')
        self.texto_reloj = self.ax.text(
            0.02, 0.97, '', transform=self.ax.transAxes,
            fontsize=11, weight='bold', va='top', bbox=props
        )
        self.texto_stats = self.ax.text(
            0.20, 0.97, '', transform=self.ax.transAxes,
            fontsize=9, va='top', bbox=props
        )
        # Panel de carga / pallets
        self.texto_pallets = self.ax.text(
            0.55, 0.97, '', transform=self.ax.transAxes,
            fontsize=9, va='top', bbox=props
        )

        self.ax.legend(loc='lower right', fontsize=9)

        # Contadores acumulativos
        self.total_camiones = len(self.df)

        # Calcular estadisticas de pallets
        if 'pallets_cargados' in self.df.columns and 'max_pallets' in self.df.columns:
            self.total_pallets = int(self.df['pallets_cargados'].sum())
            max_p = self.df['max_pallets'].iloc[0] if len(self.df) > 0 else 35
            self.capacidad_total = int(self.total_camiones * max_p)
            self.pct_uso_global = round(
                (self.total_pallets / self.capacidad_total) * 100, 1
            ) if self.capacidad_total > 0 else 0.0
        else:
            self.total_pallets = 0
            self.capacidad_total = 0
            self.pct_uso_global = 0.0

    def calcular_posicion_activa(self, t):
        x, y = [], []
        en_ruta = 0
        salidos = 0
        retornados = 0
        pallets_en_ruta = 0

        for _, v in self.df.iterrows():
            tramos = v['tramos']
            t_salida_origen = v['t_salida_origen']
            t_llegada_origen = v['t_retorno_base']

            if t >= t_salida_origen:
                salidos += 1

            if t >= t_llegada_origen:
                retornados += 1

            # Si aun no salio o ya retorno, no dibujar
            if t < t_salida_origen or t > t_llegada_origen:
                continue

            en_ruta += 1
            pallets_en_ruta += v.get('pallets_cargados', 0)

            # Buscar tramo activo
            t_anterior = t_salida_origen

            for tramo in tramos:
                if t_anterior <= t <= tramo['t_llegada']:
                    duracion_viaje = tramo['t_llegada'] - t_anterior
                    prog = (t - t_anterior) / duracion_viaje if duracion_viaje > 0 else 1.0

                    path = tramo.get('decoded_path') if self.usar_rutas_reales else None
                    if path:
                        f_idx = prog * (len(path) - 1)
                        i0 = int(f_idx)
                        i1 = min(i0 + 1, len(path) - 1)
                        alpha = f_idx - i0

                        p0 = path[i0]
                        p1 = path[i1]

                        x_pos = p0[0] + (p1[0] - p0[0]) * alpha
                        y_pos = p0[1] + (p1[1] - p0[1]) * alpha
                    else:
                        x_pos = tramo['lon_origen'] + (tramo['lon_destino'] - tramo['lon_origen']) * prog
                        y_pos = tramo['lat_origen'] + (tramo['lat_destino'] - tramo['lat_origen']) * prog

                    x.append(x_pos)
                    y.append(y_pos)
                    break

                elif tramo['t_llegada'] < t <= tramo['t_salida']:
                    x.append(tramo['lon_destino'])
                    y.append(tramo['lat_destino'])
                    break

                t_anterior = tramo['t_salida']

        return x, y, salidos, en_ruta, retornados, pallets_en_ruta

    def actualizar(self, frame):
        x, y, salidos, en_ruta, retornados, pallets_en_ruta = self.calcular_posicion_activa(frame)

        if x and y:
            self.puntos_camiones.set_offsets(np.c_[x, y])
        else:
            self.puntos_camiones.set_offsets(np.empty((0, 2)))

        horas = int(frame)
        minutos = int((frame % 1) * 60)
        self.texto_reloj.set_text(f"Hora: {horas:02d}:{minutos:02d} h")

        self.texto_stats.set_text(
            f"Salidos: {salidos}/{self.total_camiones}\n"
            f"En ruta: {en_ruta}\n"
            f"Retornados: {retornados}"
        )

        self.texto_pallets.set_text(
            f"Pallets totales: {self.total_pallets}\n"
            f"Capacidad flota: {self.capacidad_total} P\n"
            f"Carga promedio global: {self.pct_uso_global}%"
        )

        return self.puntos_camiones, self.texto_reloj, self.texto_stats, self.texto_pallets,

    def generar_gif(self, nombre_archivo='outputs/simulacion_dinamica.gif', fps=40):
        # Encontrar el tiempo en que el primer camion sale y el ultimo regresa
        t_min = self.df['t_salida_origen'].min() if not self.df.empty else 6.5
        t_max = self.df['t_retorno_base'].max() if not self.df.empty else 24.0

        # Ajustar inicio para evitar segundos de camiones parados al principio
        t_start = max(6.0, t_min - 0.2)
        t_final = min(t_max + 0.5, 48.0)

        # Paso de tiempo: 0.05h = 3 min
        tiempos = np.arange(t_start, t_final, 0.05)

        ani = animation.FuncAnimation(
            self.fig, self.actualizar, frames=tiempos,
            interval=1000 / fps, blit=True
        )
        ani.save(nombre_archivo, writer='pillow', fps=fps)
        plt.close()
        print(f"GIF guardado: {nombre_archivo}")