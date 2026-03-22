import folium
import numpy as np
import math

# --- FUNCIONES AUXILIARES (Standalone) ---
def haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia en km entre dos puntos."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_ellipse_points(lat_p, lon_p, lat_d, lon_d, threshold_km, n_points=100):
    """Genera puntos de una elipse definida por el desvío máximo."""
    # Distancia entre focos (Planta y Depósito)
    dist_foci = haversine(lat_p, lon_p, lat_d, lon_d)
    
    # Propiedades de la elipse: dist1 + dist2 = constante (dist_foci + threshold)
    major_axis_km = dist_foci + threshold_km
    
    # Centro de la elipse
    c_lat, c_lon = (lat_p + lat_d) / 2, (lon_p + lon_d) / 2
    
    # Ángulo de rotación de la elipse
    angle = math.atan2(lat_d - lat_p, lon_d - lon_p)
    
    # Semi-ejes (aproximación en grados para visualización simple)
    # Nota: 1 grado lat ~ 111km. Esto es una aproximación visual.
    a = (major_axis_km / 111.0) / 2
    c = (dist_foci / 111.0) / 2
    b = math.sqrt(max(0, a**2 - c**2))
    
    points = []
    for i in range(n_points + 1):
        theta = 2 * math.pi * i / n_points
        # Elipse sin rotar
        x = a * math.cos(theta)
        y = b * math.sin(theta)
        # Rotar y trasladar
        rot_x = x * math.cos(angle) - y * math.sin(angle)
        rot_y = x * math.sin(angle) + y * math.cos(angle)
        points.append([c_lat + rot_y, c_lon + rot_x])
    return points

def create_visual_explanation():
    # 1. COORDENADAS REALES
    depot = {"name": "Mengíbar (DEPOT)", "lat": 37.98148, "lng": -3.80058}
    
    plants = [
        {"name": "Alcalá", "lat": 40.48205, "lng": -3.35996, "color": "blue"},
        {"name": "Vigo", "lat": 42.13338, "lng": -8.62150, "color": "purple"},
        {"name": "Canovelles", "lat": 41.62479, "lng": 2.27453, "color": "darkred"}
    ]
    
    # PARÁMETROS DEL DATAMANAGER
    max_radius_km = 200    # Restricción 1: Radio desde la planta
    threshold_km = 60      # Restricción 2: Desvío máximo hacia el depósito
    
    # 2. INICIALIZAR MAPA
    m = folium.Map(location=[39.2, -3.5], zoom_start=6, tiles="cartodbpositron")
    
    # Depot Marker (Always visible)
    folium.Marker(
        [depot['lat'], depot['lng']], 
        popup="DEPÓSITO FINAL (Mengíbar)", 
        icon=folium.Icon(color='black', icon='home', prefix='fa')
    ).add_to(m)

    from folium.plugins import FastMarkerCluster, MarkerCluster
    
    # 3. CARGAR CLIENTES REALES
    import json
    clients_data = []
    try:
        with open('data/cliente_ubi.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            for zip_code, points in raw_data.items():
                for p in points:
                    clients_data.append({
                        "lat": p["latitude"],
                        "lng": p["longitude"],
                        "name": p.get("municipio_destino", "Desconocido")
                    })
    except Exception as e:
        print(f"Error cargando clientes reales: {e}")
        clients_data = []

    # 4. CAPA GLOBAL DE CLIENTES (MarkerCluster para rendimiento)
    global_cluster = MarkerCluster(name="Todos los Clientes (Cluster)").add_to(m)
    for c in clients_data:
        folium.CircleMarker(
            [c['lat'], c['lng']], 
            radius=2, 
            color='gray', 
            fill=True, 
            opacity=0.4,
            popup=f"<b>{c['name']}</b>"
        ).add_to(global_cluster)

    # 5. PROCESAR CADA PLANTA
    for p_info in plants:
        group = folium.FeatureGroup(name=f"Evaluación: {p_info['name']}")
        p_lat, p_lng = p_info['lat'], p_info['lng']
        p_color = p_info['color']
        
        # Marcador de Planta
        folium.Marker(
            [p_lat, p_lng], 
            popup=f"PLANTA: {p_info['name']}", 
            icon=folium.Icon(color=p_color, icon='industry', prefix='fa')
        ).add_to(group)
        
        # Filtro 1: Radio
        folium.Circle(
            location=[p_lat, p_lng],
            radius=max_radius_km * 1000,
            color=p_color,
            fill=True,
            fill_opacity=0.08,
            weight=1,
            popup=f"Radio {max_radius_km}km ({p_info['name']})"
        ).add_to(group)
        
        # Filtro 2: Elipse de Desvío
        ellipse_pts = get_ellipse_points(p_lat, p_lng, depot['lat'], depot['lng'], threshold_km)
        folium.Polygon(
            locations=ellipse_pts,
            color='green',
            fill=True,
            fill_opacity=0.12,
            weight=2,
            popup=f"Zona de Eficiencia ({p_info['name']} -> Mengíbar)"
        ).add_to(group)
        
        # Línea de retorno directo
        folium.PolyLine(
            [[p_lat, p_lng], [depot['lat'], depot['lng']]], 
            color=p_color, weight=1, dash_array='5, 5', opacity=0.4
        ).add_to(group)
        
        # Filtrar clientes reales que caen dentro de los criterios de esta planta
        # Limitamos el renderizado de EVALUACIÓN a los aceptados + algunos fallos cercanos para no saturar
        for c in clients_data:
            c_lat, c_lng = c['lat'], c['lng']
            d_p_c = haversine(p_lat, p_lng, c_lat, c_lng)
            
            # Solo evaluamos individualmente si está en un entorno razonable de la planta
            if d_p_c < max_radius_km * 1.5:
                d_c_d = haversine(c_lat, c_lng, depot['lat'], depot['lng'])
                d_p_d = haversine(p_lat, p_lng, depot['lat'], depot['lng'])
                detour = (d_p_c + d_c_d) - d_p_d
                
                in_radius = d_p_c <= max_radius_km
                in_detour = detour <= threshold_km
                
                if in_radius and in_detour:
                    color, status = 'green', "ACEPTADO"
                    # Renderizamos todos los aceptados
                    folium.CircleMarker(
                        [c_lat, c_lng], radius=3, color=color, fill=True, fill_opacity=0.8,
                        popup=f"<b>{c['name']}</b><br>Status: <b>{status}</b><br>Desvío: {detour:.1f}km"
                    ).add_to(group)
                elif in_radius or in_detour:
                    # Renderizamos una fracción de los fallos parciales para ver la lógica sin colapsar
                    import random
                    if random.random() < 0.1: # 10% de los descartados parciales
                        color = 'orange' if in_radius else 'purple'
                        status = "RECHAZADO (Desvío)" if in_radius else "RECHAZADO (Radio)"
                        folium.CircleMarker(
                            [c_lat, c_lng], radius=2, color=color, fill=True, fill_opacity=0.5,
                            popup=f"<b>{c['name']}</b><br>Status: <b>{status}</b><br>Desvío: {detour:.1f}km"
                        ).add_to(group)

        group.add_to(m)

    # 4. CONTROLES Y LEYENDA
    folium.LayerControl().add_to(m)
    
    legend_html = f'''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 320px; height: 210px; 
     border:2px solid grey; z-index:9999; font-size:12px;
     background-color: white; padding: 10px; opacity: 0.95; border-radius: 8px;">
     <b style="color: #1e3a8a;">Análisis Multi-Planta de Clientes</b><br>
     <i class="fa fa-circle" style="color:green"></i> Potencial Aceptado<br>
     <i class="fa fa-circle" style="color:orange"></i> Descartado: Retorno Ineficiente<br>
     <i class="fa fa-circle" style="color:purple"></i> Descartado: Exceso Dist. Planta<br>
     <i class="fa fa-circle" style="color:red"></i> Descartado: Punto Inviable<br>
     <hr style="margin: 5px 0;">
     <b>Límite Geográfico:</b> Radio Circunferencia<br>
     <b>Límite Eficiencia:</b> Elipse de Desvío<br>
     <p style="font-size: 10px; color: #666; margin-top:5px;">ℹ️ Cada planta tiene su propia capa con clientes de ejemplo.<br>Activa/Desactiva capas arriba a la derecha.</p>
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    out_file = "outputs/maps/visualizacion_logica_datamanager.html"
    m.save(out_file)
    print(f"Mapa interactivo multi-planta generado: {out_file}")

if __name__ == "__main__":
    create_visual_explanation()
