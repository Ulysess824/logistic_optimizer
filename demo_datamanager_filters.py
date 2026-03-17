import folium
import numpy as np
from src.utils.geo import GeoUtils

def visualize_datamanager_logic():
    # 1. Configuración Real
    depot = {"name": "Mengíbar (DEPOT)", "lat": 37.98148, "lng": -3.80058}
    plant = {"name": "Alcalá (PLANTA)", "lat": 40.48205, "lng": -3.35996}
    
    # Parámetros de filtrado
    max_radius_km = 100
    threshold_km = 100
    num_samples = 50
    
    # 2. Generar Clientes Aleatorios (Simulación)
    np.random.seed(42)
    # Generar puntos alrededor de Alcalá en un radio de ~3 grados
    c_lats = plant['lat'] + (np.random.rand(num_samples) - 0.5) * 4
    c_lngs = plant['lng'] + (np.random.rand(num_samples) - 0.5) * 4
    
    # Calcular Distancias Haversine (Simplificado para el demo)
    dist_p_c = GeoUtils.haversine_km(plant['lat'], plant['lng'], c_lats, c_lngs)
    dist_c_d = GeoUtils.haversine_km(c_lats, c_lngs, depot['lat'], depot['lng'])
    dist_p_d = GeoUtils.haversine_km(plant['lat'], plant['lng'], depot['lat'], depot['lng'])
    
    # 3. Aplicar Filtros
    # Filtro 1: Radio Máximo
    mask_radius = dist_p_c <= max_radius_km
    
    # Filtro 2: Desvío (Detour)
    detours = (dist_p_c + dist_c_d) - dist_p_d
    mask_detour = detours <= threshold_km
    
    # 4. Crear Mapa
    m = folium.Map(location=[40, -3.5], zoom_start=6, tiles="cartodbpositron")
    
    # Dibujar Mengíbar y Alcalá
    folium.Marker([depot['lat'], depot['lng']], popup="Depósito (Mengíbar)", icon=folium.Icon(color='black', icon='home')).add_to(m)
    folium.Marker([plant['lat'], plant['lng']], popup="Planta (Alcalá)", icon=folium.Icon(color='blue', icon='industry')).add_to(m)
    
    # Dibujar círculo de Radio Máximo
    folium.Circle(
        location=[plant['lat'], plant['lng']],
        radius=max_radius_km * 1000,
        color='blue',
        fill=True,
        fill_opacity=0.1,
        popup=f"Radio Máximo ({max_radius_km}km)"
    ).add_to(m)
    
    # Dibujar línea Planta -> Depósito (Referencia)
    folium.PolyLine([[plant['lat'], plant['lng']], [depot['lat'], depot['lng']]], color='gray', weight=2, dash_array='5, 5', opacity=0.5).add_to(m)
    
    # Dibujar Clientes
    for i in range(num_samples):
        lat, lng = c_lats[i], c_lngs[i]
        d_p_c = dist_p_c[i]
        detour = detours[i]
        
        in_radius = mask_radius[i]
        in_detour = mask_detour[i]
        
        color = 'green' if (in_radius and in_detour) else ('orange' if in_radius else 'red')
        reason = "ACEPTADO" if (in_radius and in_detour) else ("RECHAZADO: Desvío excesivo" if in_radius else "RECHAZADO: Fuera de radio")
        
        popup_text = f"Cliente {i}<br>Dist a Planta: {d_p_c:.1f}km<br>Desvío: {detour:.1f}km<br><b>{reason}</b>"
        
        folium.CircleMarker(
            location=[lat, lng],
            radius=5,
            color=color,
            fill=True,
            popup=popup_text
        ).add_to(m)
        
        # Si está aceptado, dibujamos la ruta Planta -> Cliente -> Depósito
        if in_radius and in_detour:
             folium.PolyLine(
                 [[plant['lat'], plant['lng']], [lat, lng], [depot['lat'], depot['lng']]],
                 color='green', weight=1, opacity=0.3
             ).add_to(m)

    # Guardar mapa
    out_path = "explicacion_filtros_datamanager.html"
    m.save(out_path)
    print(f"Mapa generado en: {out_path}")
    print(f"Estadísticas: Aceptados {sum(mask_radius & mask_detour)}, Total {num_samples}")

if __name__ == "__main__":
    visualize_datamanager_logic()
