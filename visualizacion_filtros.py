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
    # Mengíbar (Depósito Central)
    depot = {"name": "Mengíbar (DEPOT)", "lat": 37.98148, "lng": -3.80058}
    # Alcalá de Henares (Planta de Cartón)
    plant = {"name": "Alcalá (PLANTA)", "lat": 40.48205, "lng": -3.35996}
    
    # PARÁMETROS DEL DATAMANAGER
    max_radius_km = 120    # Restricción 1: Radio desde la planta
    threshold_km = 40      # Restricción 2: Desvío máximo hacia el depósito
    
    # 2. INICIALIZAR MAPA
    m = folium.Map(location=[39.2, -3.5], zoom_start=7, tiles="cartodbpositron")
    
    # 3. DIBUJAR RESTRICCIÓN 1: EL RADIO (Círculo)
    folium.Circle(
        location=[plant['lat'], plant['lng']],
        radius=max_radius_km * 1000,
        color='blue',
        fill=True,
        fill_opacity=0.1,
        weight=2,
        popup=f"RESTRICCIÓN 1: Radio Máximo ({max_radius_km}km)<br>Solo clientes 'cerca' de la planta."
    ).add_to(m)
    
    # 4. DIBUJAR RESTRICCIÓN 2: EL DESVÍO (Elipse)
    # Matemáticamente, los puntos con desvío constante d1+d2 = K forman una elipse.
    ellipse_pts = get_ellipse_points(plant['lat'], plant['lng'], depot['lat'], depot['lng'], threshold_km)
    folium.Polygon(
        locations=ellipse_pts,
        color='green',
        fill=True,
        fill_opacity=0.1,
        weight=2,
        popup=f"RESTRICCIÓN 2: Zona de Desvío ({threshold_km}km)<br>Cualquier punto fuera de aquí añade demasiados km al retorno."
    ).add_to(m)
    
    # 5. MARCADORES PRINCIPALES
    folium.Marker(
        [depot['lat'], depot['lng']], 
        popup="DEPÓSITO FINAL (Mengíbar)", 
        icon=folium.Icon(color='black', icon='home', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        [plant['lat'], plant['lng']], 
        popup="PLANTA DE ORIGEN (Alcalá)", 
        icon=folium.Icon(color='blue', icon='industry', prefix='fa')
    ).add_to(m)
    
    # Línea directa Planta -> Depósito
    folium.PolyLine(
        [[plant['lat'], plant['lng']], [depot['lat'], depot['lng']]], 
        color='gray', weight=2, dash_array='10, 10', opacity=0.6,
        popup="Ruta Directa (Camión vacío)"
    ).add_to(m)
    
    # 6. SIMULAR CLIENTES PARA EJEMPLO
    np.random.seed(10)
    samples = 60
    # Clientes aleatorios en un área amplia
    lats = plant['lat'] + (np.random.rand(samples) - 0.4) * 4
    lngs = plant['lng'] + (np.random.rand(samples) - 0.5) * 6
    
    for i in range(samples):
        d_p_c = haversine(plant['lat'], plant['lng'], lats[i], lngs[i])
        d_c_d = haversine(lats[i], lngs[i], depot['lat'], depot['lng'])
        d_p_d = haversine(plant['lat'], plant['lng'], depot['lat'], depot['lng'])
        
        detour = (d_p_c + d_c_d) - d_p_d
        
        in_radius = d_p_c <= max_radius_km
        in_detour = detour <= threshold_km
        
        # Color según cumplimiento
        if in_radius and in_detour:
            color = 'green'
            status = "ACEPTADO (Cumple ambas)"
        elif in_radius:
            color = 'orange'
            status = "RECHAZADO: Desvío alto (Se aleja de la ruta al depósito)"
        elif in_detour:
            color = 'purple'
            status = "RECHAZADO: Muy lejos de la planta"
        else:
            color = 'red'
            status = "RECHAZADO: Fuera de ambos límites"
            
        folium.CircleMarker(
            [lats[i], lngs[i]],
            radius=4,
            color=color,
            fill=True,
            popup=f"Cliente {i}<br>Dist. Planta: {d_p_c:.1f}km<br>Desvío: {detour:.1f}km<br><b>{status}</b>"
        ).add_to(m)

    # 7. LEYENDA (HTML)
    legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 300px; height: 180px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color: white; padding: 10px; opacity: 0.9;">
     <b>Lógica de Selección DataManager</b><br>
     <i class="fa fa-circle" style="color:green"></i> Aceptado (En Radio y Bajo Desvío)<br>
     <i class="fa fa-circle" style="color:orange"></i> Rechazado: Desvío excesivo<br>
     <i class="fa fa-circle" style="color:red"></i> Rechazado: Fuera de radio<br>
     <i class="fa fa-circle" style="color:purple"></i> Rechazado: Lejos de planta<br>
     <hr>
     <b>Azul:</b> Filtro Geográfico (Radio)<br>
     <b>Verde:</b> Filtro de Eficiencia (Elipse de Desvío)
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    out_file = "outputs/maps/visualizacion_logica_datamanager.html"
    m.save(out_file)
    print(f"Mapa interactivo generado: {out_file}")

if __name__ == "__main__":
    create_visual_explanation()
