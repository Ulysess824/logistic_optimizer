import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import pandas as pd


class AnimadorLogistico:
    def __init__(self, df_resultados, origen):
        """
        df_resultados: DataFrame resultante de simulador.ejecutar()
        origen: dict con {'lat', 'lng', 'name'}
        """
        self.df = df_resultados
        self.origen = origen
        self.fig, self.ax = plt.subplots(figsize=(12, 9))

        # Mapa Iberia
        self.ax.set_xlim(-10, 5)
        self.ax.set_ylim(35.5, 44.5)
        self.ax.set_facecolor('#f0f4f8')
        self.ax.set_title("Simulación Logística · Flotas Diarias", fontsize=14, weight='bold')

        # 1. Dibujar Origen
        self.ax.plot(origen['lng'], origen['lat'], 'g^', markersize=12,
                     label=f"Depot: {origen.get('name', 'Depot')}", zorder=6)

        # Recopilar nodos para el mapa estático
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
                        nombres_planta.append(tramo['nombre'])
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

        # Elementos dinámicos
        self.puntos_camiones = self.ax.scatter([], [], c='crimson', s=50,
                                               edgecolors='black', zorder=7)

        # Panel de información (fondo semi-transparente)
        props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.85, edgecolor='#ccc')
        self.texto_reloj = self.ax.text(
            0.02, 0.97, '', transform=self.ax.transAxes,
            fontsize=12, weight='bold', va='top', bbox=props
        )
        self.texto_stats = self.ax.text(
            0.02, 0.88, '', transform=self.ax.transAxes,
            fontsize=10, va='top', bbox=props
        )

        self.ax.legend(loc='lower right', fontsize=9)

        # Contadores acumulativos
        self.total_camiones = len(self.df)

    def calcular_posicion_activa(self, t):
        x, y = [], []
        en_ruta = 0
        salidos = 0
        retornados = 0

        for _, v in self.df.iterrows():
            tramos = v['tramos']
            t_salida_origen = v['t_salida_origen']
            t_llegada_origen = v['t_retorno_base']

            if t >= t_salida_origen:
                salidos += 1

            if t >= t_llegada_origen:
                retornados += 1

            # Si aún no salió o ya retornó, no dibujar
            if t < t_salida_origen or t > t_llegada_origen:
                continue

            en_ruta += 1

            # Buscar tramo activo
            t_anterior = t_salida_origen

            for tramo in tramos:
                if t_anterior <= t <= tramo['t_llegada']:
                    duracion_viaje = tramo['t_llegada'] - t_anterior
                    prog = (t - t_anterior) / duracion_viaje if duracion_viaje > 0 else 1.0

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

        return x, y, salidos, en_ruta, retornados

    def actualizar(self, frame):
        x, y, salidos, en_ruta, retornados = self.calcular_posicion_activa(frame)

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

        return self.puntos_camiones, self.texto_reloj, self.texto_stats

    def generar_gif(self, nombre_archivo='outputs/simulacion_dinamica.gif', fps=10):
        # Encontrar el tiempo en que el último camión regresa a la base
        t_max = self.df['t_retorno_base'].max() if not self.df.empty else 24.0
        
        # Añadir un margen de 2 horas para que el GIF no se corte justo al llegar
        t_final = t_max + 2.0
        
        # Eliminamos el tope de 30h para permitir rutas de larga distancia (>1000km)
        # que pueden tardar más de un día en completarse (con descansos y esperas).
        tiempos = np.arange(6.0, t_final, 0.2)
        
        ani = animation.FuncAnimation(
            self.fig, self.actualizar, frames=tiempos,
            interval=1000 / fps, blit=True
        )
        ani.save(nombre_archivo, writer='pillow', fps=fps)
        plt.close()
        print(f"GIF guardado: {nombre_archivo}")