import sys
import os
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("refresh_dashboard")

# Añadimos la carpeta src al path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.utils.report_generator import generate_dashboard
except ImportError:
    # Fallback si no está en el path esperado
    from utils.report_generator import generate_dashboard

# Definimos las rutas de los archivos
SUMMARY_JSON = os.path.join('outputs', 'results', 'optimization_summary.json')
ROUTES_JSON  = os.path.join('outputs', 'results', 'optimized_routes.json')
HTML_OUTPUT  = os.path.join('outputs', 'Presentacion_Logistica.html')

def main():
    if not os.path.exists(SUMMARY_JSON) or not os.path.exists(ROUTES_JSON):
        logger.error("❌ No se encontraron los archivos de resultados en 'outputs/results/'.")
        logger.info("Ejecuta 'python main.py' primero para generar los datos.")
        return

    logger.info("🔄 Sincronizando Dashboard HTML con los últimos resultados...")
    
    try:
        generate_dashboard(SUMMARY_JSON, ROUTES_JSON, HTML_OUTPUT)
        logger.info(f"✅ Dashboard actualizado correctamente en: {HTML_OUTPUT}")
    except Exception as e:
        logger.error(f"❌ Error al actualizar el dashboard: {e}")

if __name__ == "__main__":
    main()
