import json
import os
from pathlib import Path
from logistic_core.utils.report_generator import generate_dashboard

# Rutas de datos persistidos
summary_json = "outputs/results/optimization_summary.json"
routes_json = "outputs/results/optimized_routes.json"
presentation_path = "outputs/Presentacion_Logistica.html"

if os.path.exists(summary_json) and os.path.exists(routes_json):
    print(f"Inyectando datos desde {summary_json}...")
    try:
        generate_dashboard(summary_json, routes_json, presentation_path, is_baseline=False)
        print("Dashboard actualizado con éxito (9 columnas).")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error al inyectar: {e}")
else:
    print("Archivos de datos no encontrados.")
