import json
import logging
from pathlib import Path

# Importar modulos del proyecto
from src.simulation.camion import TruckSimulated
from src.simulation.animador import AnimadorLogistico
from src.utils.geo import GeoUtils
from src.config import DATA_DIR, RESULTS_DIR, OUTPUT_DIR

# Configuración de logs básica para la simulación
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("Simulacion")

def run_simulation(routes_file=None, plants_file=None):
    """
    Lee las rutas generadas por main.py y ejecuta la simulación dinámica.
    """
    
    # 1. Definir rutas de archivos si no se pasan por parámetro
    if routes_file is None:
        routes_file = RESULTS_DIR / "optimized_routes.json"
    if plants_file is None:
        plants_file = DATA_DIR / "locations_smurfit.json"
    
    summary_file = RESULTS_DIR / "optimization_summary.json"

    # Verificar existencia
    if not Path(routes_file).exists():
        logger.error(f"No se encontró el archivo de rutas: {routes_file}. ¿Ejecutaste main.py primero?")
        return
    if not Path(plants_file).exists():
        logger.error(f"No se encontró el archivo de plantas: {plants_file}")
        return

    # 2. Cargar datos
    logger.info(f"Cargando rutas desde {routes_file}...")
    with open(routes_file, 'r', encoding='utf-8') as f:
        routes = json.load(f)

    logger.info(f"Cargando ubicaciones desde {plants_file}...")
    with open(plants_file, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)

    # Cargar parámetros del optimizador para sincronización dinámica
    max_pallets_param = 35
    if summary_file.exists():
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
                max_pallets_param = summary.get("parameters", {}).get("max_pallets", 35)
                logger.info(f"Sincronizados max_pallets = {max_pallets_param} desde el resumen de optimización.")
        except Exception as e:
            logger.warning(f"No se pudo leer el resumen de optimización para sincronizar parámetros: {e}")

    # 3. Inicializar motor geográfico (para polilíneas reales en la simulación)
    # Por defecto intentamos OSRM para que el GIF sea preciso
    geo_engine = GeoUtils(api_type="osrm")

    # 4. Inicializar el simulador
    logger.info("Inicializando motor de simulación SimPy...")
    sim = TruckSimulated(
        origen=plants_data['paper_plant'],
        rutas=routes,
        inicio_operacion_h=6.5,
        velocidad_kmh=80,
        tiempo_carga_h=(0.5 + 0.3),
        num_muelles=2,
        num_conductores=38,
        max_pallets=max_pallets_param,
        geo_utils=geo_engine,
        num_muelles = 2
    )

    # 6. Ejecutar simulación
    logger.info("Simulando jornada logística (esto puede tardar unos segundos)...")
    df_resultados = sim.ejecutar(desfase_hora=0.5)
    
    # 7. Generar el GIF animado para el Dashboard
    gif_path = OUTPUT_DIR / "simulacion_rutas_optimizadas.gif"
    logger.info(f"Generando GIF en {gif_path}...")
    
    animador = AnimadorLogistico(
        df_resultados, 
        plants_data['paper_plant'], 
        usar_rutas_reales=True
    )
    
    animador.generar_gif(str(gif_path), fps=40)
    logger.info("Simulación completada con éxito.")

if __name__ == "__main__":
    run_simulation()
