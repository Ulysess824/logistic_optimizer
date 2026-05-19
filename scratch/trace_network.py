import os
import json
import requests
import matplotlib.pyplot as plt

# 1. Cargar coordenadas desde el archivo locations_smurfit.json
data_path = "data/locations_smurfit.json"
if not os.path.exists(data_path):
    print("Error: No se encuentra el archivo data/locations_smurfit.json")
    exit(1)

with open(data_path, "r", encoding="utf-8") as f:
    locations = json.load(f)

depot = locations["paper_plant"]
plants = locations["carton_plants"]

# 2. Configurar la estetica premium del grafico (Dark Mode estilo Dashboard)
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0f172a")
ax.set_facecolor("#0f172a")

# URL base para OSRM (primero intentamos local, si no, fallback al publico)
OSRM_LOCAL = "http://localhost:5000"
OSRM_PUBLIC = "http://router.project-osrm.org"

# Listas para almacenar coordenadas de plantas para limites del mapa
plant_lats = []
plant_lngs = []

print("Consultando rutas via OSRM...")

# 3. Trazar conexiones (rutas de OSRM) entre depot y plantas
for plant in plants:
    p_name = plant["name"]
    p_lat = plant["lat"]
    p_lng = plant["lng"]
    
    plant_lats.append(p_lat)
    plant_lngs.append(p_lng)
    
    # Construir ruta con OSRM usando geometrias GeoJSON para facil ploteo
    path_query = f"/route/v1/driving/{depot['lng']},{depot['lat']};{p_lng},{p_lat}?overview=full&geometries=geojson"
    
    coords = None
    # Intento 1: Servidor Local
    try:
        r = requests.get(f"{OSRM_LOCAL}{path_query}", timeout=5)
        if r.status_code == 200:
            coords = r.json()["routes"][0]["geometry"]["coordinates"]
    except Exception:
        pass
        
    # Intento 2: Fallback al Servidor Publico de OSRM
    if not coords:
        try:
            r = requests.get(f"{OSRM_PUBLIC}{path_query}", timeout=10)
            if r.status_code == 200:
                coords = r.json()["routes"][0]["geometry"]["coordinates"]
        except Exception as e:
            print(f"No se pudo obtener ruta OSRM para {p_name}: {e}")
            
    # Graficar la ruta por carretera si se obtuvo con exito
    if coords:
        # coords viene en formato [[lng, lat], ...]
        xs = [pt[0] for pt in coords]
        ys = [pt[1] for pt in coords]
        
        # Linea de la carretera (azul brillante semitransparente con efecto de brillo)
        ax.plot(xs, ys, color="#3b82f6", alpha=0.6, linewidth=2.5, zorder=2)
        ax.plot(xs, ys, color="#60a5fa", alpha=0.2, linewidth=5.0, zorder=1)
    else:
        # Fallback a linea recta geodesica si falla OSRM
        ax.plot([depot["lng"], p_lng], [depot["lat"], p_lat], 
                color="#ef4444", linestyle="--", alpha=0.4, linewidth=1.5, zorder=2)

# 4. Graficar los nodos (Plantas y Depot)
# 4.1. Dibujar plantas de carton
ax.scatter(plant_lngs, plant_lats, color="#10b981", s=120, edgecolors="#ffffff", 
           linewidths=1.5, label="Plantas de Carton (Destinos)", zorder=4)

# 4.2. Dibujar el Depot central (Mengibar)
ax.scatter(depot["lng"], depot["lat"], color="#fbbf24", s=300, marker="*", 
           edgecolors="#ffffff", linewidths=1.5, label=f"Depot Central ({depot['name']})", zorder=5)

# 4.3. Agregar etiquetas de texto para las plantas y depot
# Depot
ax.text(depot["lng"] + 0.15, depot["lat"] - 0.05, depot["name"].upper(), 
        color="#fbbf24", fontsize=11, fontweight="bold", zorder=6)

# Plantas
for plant in plants:
    ax.text(plant["lng"] + 0.15, plant["lat"] + 0.05, plant["name"], 
            color="#e2e8f0", fontsize=9, fontweight="medium", zorder=6)

# 5. Formatear y embellecer el grafico
ax.set_title("Red de Conexiones Logisticas | Smurfit Westrock", 
             color="#ffffff", fontsize=16, fontweight="bold", pad=20)
ax.set_xlabel("Longitud", color="#94a3b8", fontsize=11, labelpad=10)
ax.set_ylabel("Latitud", color="#94a3b8", fontsize=11, labelpad=10)

# Personalizacion de rejilla y ejes
ax.grid(True, linestyle=":", alpha=0.15, color="#94a3b8")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#334155")
ax.spines["bottom"].set_color("#334155")
ax.tick_params(colors="#94a3b8", labelsize=9)

# Ajustar limites del mapa automaticos con un margen de seguridad
all_lngs = [depot["lng"]] + plant_lngs
all_lats = [depot["lat"]] + plant_lats
margin = 1.0
ax.set_xlim(min(all_lngs) - margin, max(all_lngs) + margin)
ax.set_ylim(min(all_lats) - margin, max(all_lats) + margin)

# Agregar leyenda flotante elegante
ax.legend(facecolor="#1e293b", edgecolor="#334155", loc="upper left", 
          fontsize=10, labelcolor="#e2e8f0")

# Guardar la imagen en alta definicion (300 DPI) para maxima nitidez
output_img = "outputs/red_conexiones_depot.png"
plt.tight_layout()
plt.savefig(output_img, dpi=300, facecolor="#0f172a", edgecolor="none")
plt.close()

print(f"Visualizacion guardada con exito en: {output_img}")
