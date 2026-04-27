import os
import sys
from pathlib import Path

# Añadir el root al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logistic_core.utils.report_generator import generate_dashboard

# Rutas correctas basadas en config.py
summary_json = "outputs/results/optimization_summary.json"
routes_json = "outputs/results/optimized_routes.json"
output_html = "outputs/Presentacion_Logistica.html"

if os.path.exists(summary_json) and os.path.exists(routes_json):
    print("Actualizando Dashboard con nuevo motor dinámico e ingresos indexados...")
    generate_dashboard(summary_json, routes_json, output_html)
    print("Dashboard actualizado exitosamente.")
else:
    print(f"Error: No se encontraron los archivos")
