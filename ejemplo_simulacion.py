"""
Ejemplo de simulación de rutas optimizadas.
Lee las rutas de optimized_routes.json y el número de camiones por planta
de n_camiones_a_plantas_diarios.xlsx. NO es necesario ejecutar el optimizador.
"""
import sys
import os
import json

import pandas as pd

sys.path.append(os.path.join(os.getcwd(), 'src'))

from simulation import TruckSimulated, AnimadorLogistico
from utils.geo import GeoUtils

# --- Archivos de entrada ---
RUTAS_JSON   = os.path.join('outputs', 'results', 'optimized_routes.json')
CAMIONES_XLS = os.path.join('data', 'n_camiones_a_plantas_diarios.xlsx')

# Especificaciones de Camión (Sincronizado con main.py para acertar en la caché)
TRUCK_SPECS = {
    "emissionType": "DIESEL",
    "heightCm": 400,
    "weightKg": 40_000,
}

# Mapeo de nombres del Excel → nombres en el JSON de rutas
ALIAS_PLANTAS = {
    "Cordovilla": "Navarra",      # Cordovilla es la planta de Navarra
    "Cordoba":    "Córdoba",      # Acentos
    "Quart":      "Valencia",     # Quart de Poblet es la planta de Valencia
}


def cargar_rutas(ruta_json: str) -> tuple:
    """Carga rutas optimizadas y devuelve (origen, rutas, nombre_planta_por_ruta)."""
    if not os.path.exists(ruta_json):
        raise FileNotFoundError(
            f"No se encontró '{ruta_json}'. Ejecuta main.py primero."
        )

    with open(ruta_json, 'r', encoding='utf-8') as f:
        rutas_raw = json.load(f)

    depot = rutas_raw[0][0]
    origen = {
        "name": depot.get("name", "Depot"),
        "lat": depot["lat"],
        "lng": depot["lng"],
        "type": "depot"
    }

    rutas = []
    nombres_planta = []
    for ruta in rutas_raw:
        paradas = [n for n in ruta if n["type"] in ("carton_plant", "customer")]
        if paradas:
            rutas.append(paradas)
            # Nombre de la primera planta de la ruta
            planta = next((n["name"] for n in paradas if n["type"] == "carton_plant"), None)
            nombres_planta.append(planta)

    return origen, rutas, nombres_planta


def cargar_camiones_por_planta(xls_path: str) -> dict:
    """Lee el Excel y devuelve un dict {nombre_planta_normalizado: n_camiones}."""
    if not os.path.exists(xls_path):
        print(f"⚠ No se encontró '{xls_path}'. Se usará 1 camión por ruta.")
        return {}

    df = pd.read_excel(xls_path)
    resultado = {}
    for _, row in df.iterrows():
        nombre = str(row['plantas']).strip()
        n = int(row['avg_camiones'])
        # Normalizar alias
        nombre_norm = ALIAS_PLANTAS.get(nombre, nombre)
        resultado[nombre_norm] = n

    return resultado


def main():
    print("=" * 60)
    print("  Simulación de Rutas Optimizadas con Flota Real")
    print("=" * 60)

    # 1. Cargar rutas
    print(f"\n📦 Cargando rutas desde: {RUTAS_JSON}")
    origen, rutas, nombres_planta = cargar_rutas(RUTAS_JSON)
    print(f"   Depot: {origen['name']}")
    print(f"   Rutas cargadas: {len(rutas)}")

    # 2. Cargar camiones por planta
    print(f"\n🚚 Cargando flota desde: {CAMIONES_XLS}")
    camiones_dict = cargar_camiones_por_planta(CAMIONES_XLS)

    # Asignar camiones a cada ruta según la planta principal
    camiones_por_ruta = []
    total_camiones = 0
    for i, (ruta, planta) in enumerate(zip(rutas, nombres_planta)):
        # Normalizar el nombre quitando 'Smurfit Westrock ' si existe
        nombre_corto = planta.replace("Smurfit Westrock ", "").strip() if planta else ""
        n = camiones_dict.get(nombre_corto, 1)
        camiones_por_ruta.append(n)
        total_camiones += n
        destinos = [p["name"] for p in ruta]
        print(f"   Ruta {i+1} ({nombre_corto}): {n} camiones → {' → '.join(destinos)}")

    print(f"\n   Total camiones a simular: {total_camiones}")

    # 3. Ejecutar simulación
    print("\n⚙ Ejecutando simulación con rutas REALES (carretera)...")
    
    # Inicializamos GeoUtils para que el simulador pueda consultar polilíneas reales
    geo_utils = GeoUtils(api_type="routes_api")
    geo_utils.set_truck_specs(**TRUCK_SPECS)

    simulador = TruckSimulated(
        origen=origen,
        rutas=rutas,
        num_muelles=2,              # Cuello de botella real: solo 2 muelles de carga
        num_conductores=total_camiones,
        velocidad_kmh=80,
        inicio_operacion_h = 6.5,
        camiones_por_ruta=camiones_por_ruta,
        tiempo_carga_h = (0.66 + 0.5), # 40 min de carga de bobinas + 30 min de atado de bobinas
        geo_utils=geo_utils) # Inyectamos GeoUtils para carreteras reales
        
    df_resultados = simulador.ejecutar(desfase_hora=0.4)


    # 4. Resumen
    print(f"\n📊 Simulación completada: {len(df_resultados)} viajes registrados")
    for _, row in df_resultados.iterrows():
        print(f"   🚚 {row['id']}: {row.get('destino_principal','?')} "
              f"| Salida {row['t_salida_origen']:.1f}h → Retorno {row['t_retorno_base']:.1f}h")

    # 5. Generar GIF
    print("\n🎬 Generando animación GIF...")
    animador = AnimadorLogistico(df_resultados, origen)
    nombre_gif = os.path.join('outputs', 'simulacion_rutas_optimizadas.gif')
    os.makedirs('outputs', exist_ok=True)
    animador.generar_gif(nombre_archivo=nombre_gif, fps=10)
    print(f"✅ Animación guardada en: {nombre_gif}")


if __name__ == "__main__":
    main()
