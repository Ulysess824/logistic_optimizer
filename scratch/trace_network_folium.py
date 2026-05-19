import os
import time
import json
import requests
import folium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 1. Cargar coordenadas desde el archivo locations_smurfit.json
data_path = "data/locations_smurfit.json"
if not os.path.exists(data_path):
    print("Error: No se encuentra el archivo data/locations_smurfit.json")
    exit(1)

with open(data_path, "r", encoding="utf-8") as f:
    locations = json.load(f)

depot = locations["paper_plant"]
plants = locations["carton_plants"]

# 2. Inicializar el mapa de Folium centrado en la peninsula iberica con un diseno gris elegante
# Centrado en el centro geográfico de España
m = folium.Map(location=[39.5, -3.5], zoom_start=6, tiles="cartodb positron")

# Servidores OSRM
OSRM_LOCAL = "http://localhost:5000"
OSRM_PUBLIC = "http://router.project-osrm.org"

print("Consultando rutas via OSRM...")

# 3. Consultar y dibujar las rutas carreteras reales
for plant in plants:
    p_name = plant["name"]
    p_lat = plant["lat"]
    p_lng = plant["lng"]
    
    # Query de OSRM en formato GeoJSON
    path_query = f"/route/v1/driving/{depot['lng']},{depot['lat']};{p_lng},{p_lat}?overview=full&geometries=geojson"
    
    coords = None
    # Intento 1: Servidor Local
    try:
        r = requests.get(f"{OSRM_LOCAL}{path_query}", timeout=5)
        if r.status_code == 200:
            coords = r.json()["routes"][0]["geometry"]["coordinates"]
    except Exception:
        pass
        
    # Intento 2: Fallback al Servidor Publico
    if not coords:
        try:
            r = requests.get(f"{OSRM_PUBLIC}{path_query}", timeout=10)
            if r.status_code == 200:
                coords = r.json()["routes"][0]["geometry"]["coordinates"]
        except Exception as e:
            print(f"No se pudo obtener ruta OSRM para {p_name}: {e}")
            
    # Si tenemos coordenadas, dibujamos la linea sobre el mapa folium
    if coords:
        # IMPORTANTE: GeoJSON devuelve [lng, lat], Folium requiere [lat, lng]
        locations_route = [[pt[1], pt[0]] for pt in coords]
        
        # PolyLine con efecto de brillo (glow)
        folium.PolyLine(
            locations=locations_route,
            color="#3b82f6",
            weight=4,
            opacity=0.8,
            tooltip=f"Ruta: {depot['name']} -> {p_name}"
        ).add_to(m)
        
        # Linea de brillo externa para estetica premium
        folium.PolyLine(
            locations=locations_route,
            color="#60a5fa",
            weight=8,
            opacity=0.2
        ).add_to(m)
    else:
        # Fallback a linea recta discontinua si falla la conexion
        folium.PolyLine(
            locations=[[depot["lat"], depot["lng"]], [p_lat, p_lng]],
            color="#ef4444",
            weight=2,
            opacity=0.5,
            dash_array="5, 5",
            tooltip=f"Conexion directa (Failsafe): {p_name}"
        ).add_to(m)

# 4. Dibujar marcadores elegantes
# 4.1. Depot Central (Estrella dorada personalizada con HTML/CSS)
depot_html = """
<div style="
    background-color: #fbbf24;
    border: 2px solid #ffffff;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    box-shadow: 0 0 10px rgba(0,0,0,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0f172a;
    font-weight: bold;
    font-size: 14px;
">★</div>
"""
folium.Marker(
    location=[depot["lat"], depot["lng"]],
    icon=folium.DivIcon(
        html=depot_html,
        icon_size=(20, 20),
        icon_anchor=(10, 10)
    ),
    popup=folium.Popup(f"<b>Depósito Central:</b> {depot['name']}<br>{depot['address']}", max_width=300)
).add_to(m)

# 4.2. Plantas de Carton (Marcadores circulares verde esmeralda con halo de brillo)
for plant in plants:
    plant_html = f"""
    <div style="
        background-color: #10b981;
        border: 2px solid #ffffff;
        border-radius: 50%;
        width: 14px;
        height: 14px;
        box-shadow: 0 0 8px rgba(0,0,0,0.2);
    "></div>
    """
    folium.Marker(
        location=[plant["lat"], plant["lng"]],
        icon=folium.DivIcon(
            html=plant_html,
            icon_size=(14, 14),
            icon_anchor=(7, 7)
        ),
        popup=folium.Popup(f"<b>Planta de Cartón:</b> {plant['name']}<br>{plant['address']}", max_width=300),
        tooltip=plant["name"]
    ).add_to(m)

# 5. Guardar el mapa interactivo HTML
output_html = "outputs/red_conexiones_depot_folium.html"
m.save(output_html)
print(f"Mapa interactivo HTML guardado en: {output_html}")

# 6. Intentar exportacion estatica PNG automatica usando Selenium
output_png = "outputs/red_conexiones_depot_folium.png"
try:
    print("Iniciando captura de pantalla con Selenium Headless Chrome...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1200,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=options)
    abs_path = os.path.abspath(output_html)
    
    # Cargar el archivo local en el navegador
    driver.get(f"file:///{abs_path}")
    
    # Tiempo de espera optimizado para asegurar la carga completa de las teselas del mapa claro
    time.sleep(3)
    
    driver.save_screenshot(output_png)
    driver.quit()
    print(f"Visualizacion estatica PNG exportada con exito en: {output_png}")
except Exception as e:
    print(f"Nota: No se pudo realizar la captura automatica PNG via Selenium: {e}")
    print("Sin embargo, puede abrir el archivo HTML generado para interactuar o tomar una captura manual.")
