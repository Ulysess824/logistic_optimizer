import json
import polars as pl
from pathlib import Path

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSON = BASE_DIR / "data" / "yearly_demand_real.json"
OUTPUT_EXCEL = BASE_DIR / "outputs" / "demanda_diaria_2025.xlsx"

def export_json_to_excel():
    print(f"Leyendo datos desde {INPUT_JSON}...")
    
    if not INPUT_JSON.exists():
        print(f"Error: No se encuentra el archivo {INPUT_JSON}. Ejecuta primero ingest_real_data.py.")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    
    print("Aplanando estructura de datos...")
    # Estructura: Fecha -> Planta -> Lista de Clientes
    for date_str, plants in data.items():
        for plant_id, clients in plants.items():
            for client in clients:
                # Creamos una fila plana para Excel
                row = {
                    "fecha": date_str,
                    "planta_id": plant_id,
                    "nombre_cliente": client.get("name", ""),
                    "codigo_postal": client.get("codigo_postal", ""),
                    "municipio": client.get("municipio_destino", ""),
                    "pais": client.get("pais_destino", ""),
                    "latitud": client.get("latitude"),
                    "longitud": client.get("longitude"),
                    "pallets": client.get("n_pallets", 0),
                    "remontar": client.get("remontar", 0)
                }
                rows.append(row)

    print(f"Total de registros a exportar: {len(rows)}")
    
    # Crear DataFrame de Polars
    df = pl.DataFrame(rows)

    # Intentar guardar como Excel (requiere xlsxwriter o openpyxl en el entorno)
    try:
        print(f"Guardando archivo en {OUTPUT_EXCEL}...")
        # Polars recomienda xlsxwriter para mayor compatibilidad
        df.write_excel(str(OUTPUT_EXCEL))
        print("¡Exportación completada exitosamente!")
    except ImportError:
        print("Aviso: 'xlsxwriter' no detectado. Intentando exportar a CSV como alternativa segura...")
        OUTPUT_CSV = OUTPUT_EXCEL.with_suffix(".csv")
        df.write_csv(str(OUTPUT_CSV))
        print(f"¡Exportación completada como CSV en: {OUTPUT_CSV}!")
    except Exception as e:
        print(f"Error al exportar: {e}")

if __name__ == "__main__":
    export_json_to_excel()
