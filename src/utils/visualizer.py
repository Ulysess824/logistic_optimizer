import folium
import os
import polyline
from src.utils.geo import GeoUtils
from src.config import MAPS_DIR

class Visualizer:
    def __init__(self, routes, distance_matrix=None):
        self.routes = routes
        self.distance_matrix = distance_matrix
        self.geo = GeoUtils()

    def create_map(self, filename="optimized_map.html"):
        """Genera un mapa interactivo de Folium con las rutas calculadas."""
        if not self.routes:
            print("No hay rutas para visualizar.")
            return None
            
        output_path = MAPS_DIR / filename
        depot = self.routes[0][0]
        m = folium.Map(location=[depot['lat'], depot['lng']], zoom_start=6)

        # Colores para las líneas de las rutas
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'darkpurple', 'darkgreen']
        api_disabled = False

        for r_idx, route in enumerate(self.routes):
            route_color = colors[r_idx % len(colors)]
            
            # --- Markers ---
            for i, node in enumerate(route):
                # Determinar color por tipo
                if node['type'] == "depot":
                    marker_color = "black"
                    icon = "star"
                elif node['type'] == "carton_plant":
                    marker_color = "orange"
                    icon = "industry"
                else: # customer
                    marker_color = "cadetblue"
                    icon = "user"

                folium.Marker(
                    [node['lat'], node['lng']],
                    popup=f"Ruta {r_idx+1}, Parada {i}: {node['name']}<br>Tipo: {node['type']}",
                    tooltip=f"{node['name']} (Ruta {r_idx+1})",
                    icon=folium.Icon(color=marker_color, icon=icon, prefix='fa')
                ).add_to(m)

            # --- Trazado de Caminos ---
            full_path_points = []
            for i in range(len(route) - 1):
                start = route[i]
                end = route[i+1]
                
                encoded_poly = None
                if not api_disabled:
                    encoded_poly = self.geo.get_route_polyline((start['lat'], start['lng']), (end['lat'], end['lng']))
                
                if encoded_poly == "BILLING_ERROR":
                    api_disabled = True
                    encoded_poly = None
                
                if encoded_poly:
                    try:
                        decoded_points = polyline.decode(encoded_poly)
                        full_path_points.extend(decoded_points)
                    except Exception:
                        full_path_points.append([start['lat'], start['lng']])
                        full_path_points.append([end['lat'], end['lng']])
                else:
                    # Fallback a línea recta
                    full_path_points.append([start['lat'], start['lng']])
                    full_path_points.append([end['lat'], end['lng']])

            # Añadir la polilínea con el color de la ruta
            folium.PolyLine(
                full_path_points, 
                color=route_color, 
                weight=4, 
                opacity=0.8, 
                tooltip=f"Ruta {r_idx+1}"
            ).add_to(m)

        m.save(str(output_path))
        return output_path
