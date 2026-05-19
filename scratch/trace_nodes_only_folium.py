import os
import time
import json
import folium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 1. Cargar datos del depot y de las plantas de carton
smurfit_path = "data/locations_smurfit.json"
if not os.path.exists(smurfit_path):
    print("Error: No se encuentra data/locations_smurfit.json")
    exit(1)

with open(smurfit_path, "r", encoding="utf-8") as f:
    locations = json.load(f)

depot = locations["paper_plant"]
plants = locations["carton_plants"]

# 2. Cargar datos de los clientes (usamos cliente_ubi_test.json para una densidad de puntos optima y estetica)
client_path = "data/cliente_ubi_test.json"
if not os.path.exists(client_path):
    # Si por alguna razon no esta el test, buscamos el principal
    client_path = "data/cliente_ubi.json"
    
if not os.path.exists(client_path):
    print("Error: No se encuentra ningun archivo de ubicacion de clientes.")
    exit(1)

with open(client_path, "r", encoding="utf-8") as f:
    client_data = json.load(f)

# Extraer coordenadas de clientes unicas para evitar duplicados visuales encimados
unique_customers = {}
for code, client_list in client_data.items():
    for c in client_list:
        lat = c.get("latitude")
        lng = c.get("longitude")
        mun = c.get("municipio_destino", "Cliente")
        if lat and lng:
            # Agrupar por coordenada redondeada para evitar duplicar marcas en el mismo punto exacto
            coord_key = (round(lat, 4), round(lng, 4))
            if coord_key not in unique_customers:
                unique_customers[coord_key] = mun

print(f"Cargados: 1 Depot, {len(plants)} Plantas de Carton y {len(unique_customers)} Clientes unicos.")

# 3. Inicializar el mapa de Folium centrado en la peninsula iberica con diseno gris premium (positron)
m = folium.Map(location=[39.5, -3.5], zoom_start=6, tiles="cartodb positron")

# 4. Inyectar marcadores con jerarquia visual elegante
# 4.1. Depot Central (Estrella dorada ★ - 20px)
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
    popup=folium.Popup(f"<b>Depósito Central (Origen):</b> {depot['name']}<br>{depot['address']}", max_width=300)
).add_to(m)

# 4.2. Plantas de Carton (Puntos verde esmeralda - 14px)
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

# 4.3. Clientes (Pequeños puntos azul brillante - 8px)
for coords_pair, municipio in unique_customers.items():
    c_lat, c_lng = coords_pair
    client_html = """
    <div style="
        background-color: #3b82f6;
        border: 1.5px solid #ffffff;
        border-radius: 50%;
        width: 8px;
        height: 8px;
        box-shadow: 0 0 5px rgba(0,0,0,0.15);
    "></div>
    """
    folium.Marker(
        location=[c_lat, c_lng],
        icon=folium.DivIcon(
            html=client_html,
            icon_size=(8, 8),
            icon_anchor=(4, 4)
        ),
        popup=folium.Popup(f"<b>Cliente (Destino final):</b> {municipio}", max_width=250),
        tooltip=municipio
    ).add_to(m)

# 5. Guardar el mapa interactivo HTML de solo nodos
output_html = "outputs/nodos_logistica_folium.html"
m.save(output_html)
print(f"Mapa interactivo HTML guardado en: {output_html}")

# 6. Exportar mapa estatico a PNG usando Selenium
output_png = "outputs/nodos_logistica_folium.png"
try:
    print("Iniciando captura de pantalla con Selenium Headless Chrome...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1200,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=options)
    abs_path = os.path.abspath(output_html)
    
    driver.get(f"file:///{abs_path}")
    
    # Tiempo de espera para la carga completa de las teselas del mapa claro
    time.sleep(3)
    
    driver.save_screenshot(output_png)
    driver.quit()
    print(f"Visualizacion estatica PNG exportada con exito en: {output_png}")
except Exception as e:
    print(f"Nota: No se pudo realizar la captura automatica PNG via Selenium: {e}")
    print("Sin embargo, el mapa interactivo se guardo en el archivo HTML.")
