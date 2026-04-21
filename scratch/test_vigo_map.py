import sys
import os
import json
import folium
import polyline

# Configurar path para importar logistic_core
sys.path.append(os.getcwd())

from logistic_core.utils.geo import GeoUtils

def create_vigo_test_map():
    routes_path = "outputs/results/optimized_routes.json"
    with open(routes_path, "r", encoding="utf-8") as f:
        routes = json.load(f)

    geo = GeoUtils(api_type="osrm")
    
    # Filtrar rutas de Vigo
    vigo_routes = [r for r in routes if any(n.get("name") == "Vigo" or "Vigo" in n.get("name", "") for n in r)]
    
    m = folium.Map(location=[40.4167, -3.7037], zoom_start=6)
    
    colors = ['magenta', 'purple']
    
    for i, route in enumerate(vigo_routes):
        color = colors[i % len(colors)]
        print(f"Dibujando Ruta Vigo #{i} color {color}")
        
        for j in range(len(route) - 1):
            start = route[j]
            end = route[j+1]
            
            print(f"  Tramo {j}: {start['name']} -> {end['name']}")
            encoded_poly = geo.get_route_polyline((start['lat'], start['lng']), (end['lat'], end['lng']))
            
            if encoded_poly:
                decoded = polyline.decode(encoded_poly)
                folium.PolyLine(decoded, color=color, weight=5, opacity=0.9).add_to(m)
            else:
                print(f"  ! ERROR: No hay polyline para {start['name']} -> {end['name']}")
                folium.PolyLine([[start['lat'], start['lng']], [end['lat'], end['lng']]], 
                               color=color, weight=2, dash_array='5, 10').add_to(m)
            
            # Marcadores
            folium.Marker([start['lat'], start['lng']], popup=start['name']).add_to(m)
        
        # Último marcador
        folium.Marker([route[-1]['lat'], route[-1]['lng']], popup=route[-1]['name']).add_to(m)

    output = "outputs/maps/Test_Vigo_Map.html"
    m.save(output)
    print(f"\nMapa de prueba guardado en: {output}")

if __name__ == "__main__":
    create_vigo_test_map()
