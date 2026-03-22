import folium
import numpy as np
from src.utils.geo import GeoUtils
import os

def generate_sorting_explanation_map():
    # 1. Configuración de Referencia (Alcalá y Mengíbar)
    depot = {"name": "Mengíbar (DEPOT)", "lat": 37.98148, "lng": -3.80058}
    plant = {"name": "Alcalá (PLANTA)", "lat": 40.48205, "lng": -3.35996}
    
    # 2. Definir Clientes para comparar
    # Cliente 1: Cerca de planta, bajo desvío absoluto (Candidato clásico)
    c1 = {"name": "Loeches (Clásico - Bajo Desvío)", "lat": 40.3850, "lng": -3.4111}
    
    # Cliente 2: Muy lejos de planta, más cerca del depot (Candidato nueva regla)
    c2 = {"name": "Ciudad Real (Nueva Regla - Far Plant/Close Depot)", "lat": 38.9848, "lng": -3.9275}
    
    # Cliente 3: Punto intermedio
    c3 = {"name": "Aranjuez (Intermedio)", "lat": 40.0333, "lng": -3.6000}

    clients = [c1, c2, c3]
    
    # 3. Calcular métricas
    geo = GeoUtils()
    dist_p_d = geo.haversine_km(plant['lat'], plant['lng'], depot['lat'], depot['lng'])
    
    for c in clients:
        d_p_c = geo.haversine_km(plant['lat'], plant['lng'], c['lat'], c['lng'])
        d_c_d = geo.haversine_km(c['lat'], c['lng'], depot['lat'], depot['lng'])
        detour = (d_p_c + d_c_d) - dist_p_d
        score = d_c_d - d_p_c # La nueva regla minimiza esto (Cerca de depot - Lejos de planta)
        
        c['dist_p_c'] = d_p_c
        c['dist_c_d'] = d_c_d
        c['detour'] = detour
        c['score'] = score

    # 4. Crear Mapa
    m = folium.Map(location=[39.2, -3.6], zoom_start=7, tiles="cartodbpositron")
    
    # Dibujar Depot y Planta
    folium.Marker([depot['lat'], depot['lng']], popup=depot['name'], icon=folium.Icon(color='black', icon='home')).add_to(m)
    folium.Marker([plant['lat'], plant['lng']], popup=plant['name'], icon=folium.Icon(color='blue', icon='industry')).add_to(m)
    
    # Dibujar línea base
    folium.PolyLine([[plant['lat'], plant['lng']], [depot['lat'], depot['lng']]], color='gray', weight=2, dash_array='5, 5', opacity=0.5, tooltip="Eje Planta -> Depot").add_to(m)
    
    # Dibujar Clientes y sus lógicas
    for i, c in enumerate(clients):
        # Elegido por nueva regla será el que tiene menor score (C2 en este caso)
        is_chosen = (c == c2) 
        color = 'green' if is_chosen else 'orange'
        
        popup_content = f"""
        <div style="width: 200px; font-family: sans-serif;">
            <b style="color: {color};">{c['name']}</b><br><br>
            <b>Métricas:</b><br>
            • Dist. a Planta: {c['dist_p_c']:.1f} km<br>
            • Dist. a Depot: {c['dist_c_d']:.1f} km<br>
            <hr>
            <b>Lógica Clásica (Detour):</b> {c['detour']:.1f} km<br>
            <b>Nueva Lógica (Score):</b> {c['score']:.1f} <br>
            <br>
            <b style="background: {color}; color: white; padding: 2px 5px; border-radius: 3px;">
                {'SELECCIONADO ✓' if is_chosen else 'RECHAZADO X'}
            </b>
        </div>
        """
        
        folium.CircleMarker(
            location=[c['lat'], c['lng']],
            radius=10 if is_chosen else 7,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=popup_content
        ).add_to(m)
        
        # Líneas de conexión
        folium.PolyLine([[plant['lat'], plant['lng']], [c['lat'], c['lng']], [depot['lat'], depot['lng']]], 
                         color=color, weight=2, opacity=0.4 if not is_chosen else 0.8).add_to(m)

    # 5. Guardar
    os.makedirs('outputs/maps', exist_ok=True)
    out_path = "outputs/maps/visualizacion_sorting_strategy.html"
    m.save(out_path)
    print(f"Mapa de estrategia guardado en: {out_path}")

if __name__ == "__main__":
    generate_sorting_explanation_map()
