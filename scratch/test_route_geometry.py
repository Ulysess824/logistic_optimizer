import sys
import os
import json

# Configurar path para importar logistic_core
sys.path.append(os.getcwd())

from logistic_core.utils.geo import GeoUtils

def test_vigo_route_geometry():
    routes_path = "outputs/results/optimized_routes.json"
    if not os.path.exists(routes_path):
        print(f"No se encontró el archivo {routes_path}")
        return

    with open(routes_path, "r", encoding="utf-8") as f:
        routes = json.load(f)

    # Solo usamos GeoUtils, OSRM no necesita API key
    geo = GeoUtils(api_type="osrm")
    
    # Vamos a buscar las rutas de Vigo (las últimas usualmente)
    vigo_routes = [r for r in routes if any(n.get("name") == "Vigo" or "Vigo" in n.get("name", "") for n in r)]
    
    if not vigo_routes:
        print("No se encontraron rutas que pasen por Vigo.")
        return

    for i, route in enumerate(vigo_routes):
        print(f"\n--- Analizando Ruta de Vigo #{i} ---")
        for j in range(len(route) - 1):
            start = route[j]
            end = route[j+1]
            
            print(f"Tramo {j}: {start['name']} -> {end['name']}")
            
            # 1. Probar distancia
            dist = geo.get_route_distance((start['lat'], start['lng']), (end['lat'], end['lng']))
            print(f"  - Distancia: {dist/1000:.2f} km")
            
            # 2. Probar Polyline
            poly = geo.get_route_polyline((start['lat'], start['lng']), (end['lat'], end['lng']))
            if poly:
                if poly == "BILLING_ERROR":
                    print("  - Polyline: ERROR DE FACTURACIÓN (Google)")
                else:
                    print(f"  - Polyline: EXITOSO (Longitud: {len(poly)} caracteres)")
            else:
                print(f"  - Polyline: FALLIDO (Ninguna geometría devuelta)")

if __name__ == "__main__":
    # Desactivar todos los loggers para evitar PermissionError en Windows
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).setLevel(logging.CRITICAL)
    
    test_vigo_route_geometry()
