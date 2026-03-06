import json
from src.utils.geo import GeoUtils
from src.engine.solver import LogisticsSolver

# =====================================================================
# EJEMPLO DE USO: Nuevas funciones de Routes API y Solver Summary
# =====================================================================

def main():
    print("Demostración de Inicialización de GeoUtils y LogisticsSolver...")
    
    # 1. Configurar GeoUtils con la nueva Routes API
    # (Por defecto ya usa 'routes_api')
    geo = GeoUtils(api_type="routes_api")
    
    # 2. Configurar las especificaciones del camión
    # NOTA: Los modificadores de vehículo para Routes API pueden requerir
    # formato específico según la documentación de Google. 
    # Ejemplos: emissionType ("DIESEL", "GASOLINE", "ELECTRIC")
    print("Configurando especificaciones de camión...")
    geo.set_truck_specs(
        emissionType="DIESEL"
    )
    
    # 3. Datos de prueba (simplificados)
    test_data = {
        "paper_plant": {
            "name": "Instalación de Prueba Central",
            "lat": 38.03,
            "lng": -3.81
        },
        "carton_plants": [
            {
                "id": "CP_1",
                "name": "Planta Norte",
                "lat": 38.50,
                "lng": -3.50,
                "customers": [
                    {"id": "C_1", "name": "Cliente A", "lat": 38.60, "lng": -3.40}
                ]
            }
        ]
    }
    
    # 4. Inicializar y resolver
    print("Inicializando Solver...")
    solver = LogisticsSolver(test_data)
    
    # Importante: Como le hemos pasado el objeto GeoUtils internamente en LogisticsSolver,
    # si queremos que el solver use nuestras specs, podemos asignarlo después:
    # (Opcionalmente, LogsticsSolver podría aceptar instanciar el geo de fuera).
    solver.geo = geo 
    
    print("Calculando rutas...")
    routes = solver.solve(n_clientes=1, varias_plantas=False, metaheuristic="GUIDED_LOCAL_SEARCH")
    
    # 5. Imprimir el resumen
    print("\n")
    print(solver.summary())
    
if __name__ == "__main__":
    main()
