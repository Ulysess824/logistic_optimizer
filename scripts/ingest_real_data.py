import polars as pl
import json
import random
import datetime
import calendar
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

EXCEL_PATH = BASE_DIR / "data" / "raw" / "Transporte (1).xlsx"
ES_CP_PATH = BASE_DIR / "data" / "raw" / "ES.txt"
PT_CP_PATH = BASE_DIR / "data" / "raw" / "PT.txt"
OUTPUT_JSON = BASE_DIR / "data" / "yearly_demand_real.json"

def cargar_referencia_postal(path_archivo):
    columnas = [
        "country_code", "postal_code", "place_name", 
        "admin_name1", "admin_code1", "admin_name2", "admin_code2", 
        "admin_name3", "admin_code3", "latitude", "longitude", "accuracy"
    ]
    return pl.read_csv(
        path_archivo, separator="\t", has_header=False, new_columns=columnas,
        encoding="utf8", infer_schema_length=0,
    ).with_columns([
        pl.col("latitude").cast(pl.Float64),
        pl.col("longitude").cast(pl.Float64),
        pl.col("postal_code").cast(pl.String).str.strip_chars().alias("cp_ref")
    ])

def get_working_days_in_month(year, month):
    num_days = calendar.monthrange(year, month)[1]
    days = [datetime.date(year, month, day) for day in range(1, num_days + 1)]
    return [d for d in days if d.weekday() < 5]

def ingest_data():
    print(f"Cargando el archivo excel: {EXCEL_PATH}")
    df_raw = pl.read_excel(source=str(EXCEL_PATH), engine="calamine", table_name="Tabla1")
    
    new_name_columns = {
        "SPEC405   [#]   Trips": "n_envios",
        "SPEC402   [#]   Drops": "n_entregas",
        "SPECT1     [#]   Transport days": "dias_transporte",
        "SPEC407   [KM]   Paid KM": "kilometros_recorridos",
        "SPEC801   [#]   Base Pallets Units": "n_pallets",
        "SPEC409   [EUR]   Total Trip Cost": "coste"
    }
    
    df = df_raw.lazy().with_columns(
        pl.col("Planta").str.replace("SK ", ""),
        pl.when(pl.col("Destino").str.contains("To-ES")).then(pl.lit("España"))
        .when(pl.col("Destino").str.contains("To-PT")).then(pl.lit("Portugal"))
        .otherwise("Destino").alias("pais_destino"),
        
        pl.col("Destino").str.extract(r"(\d{4}-\d{3}|\d{5})").alias("codigo_postal"),
        
        pl.col("Destino").str.strip_chars()
        .str.extract(r"^\S+\s+\S+\s+(.*)") 
        .str.to_titlecase()
        .alias("municipio_destino"),
        
        pl.col("Fecha").str.to_date(format="%B %Y").alias("Fecha")
    ).filter(
        pl.col("tipo_envio").str.strip_chars() == "TM Third-party_FTL/CTL",
        pl.col("SPEC402   [#]   Drops") == 1
    ).rename(new_name_columns)
    
    print("Filtrando el año 2025 y limpiando viajes...")
    # Filtro de 2025 y clip de viajes (n_envios debe ser int >= 1)
    df_filtered = df.collect().filter(
        pl.col("Fecha").dt.year() == 2025
    ).with_columns(
        pl.col("n_envios").fill_null(1).round(0).cast(pl.Int32).clip(lower_bound=1).alias("n_envios"),
        pl.when(pl.col("n_pallets") > 35).then(1).otherwise(0).alias("remontar"),
        pl.col("codigo_postal").cast(pl.String).str.strip_chars().alias("cp_join")
    )

    print("Geocodificando con ES.txt y PT.txt...")
    es_cp = cargar_referencia_postal(str(ES_CP_PATH))
    pt_cp = cargar_referencia_postal(str(PT_CP_PATH))
    iberia_cp = pl.concat([es_cp, pt_cp])
    
    df_final = df_filtered.join(
        iberia_cp,
        left_on="cp_join",
        right_on="cp_ref",
        how="left"
    ).drop("cp_join")

    # Quitar los que no hicieron match
    df_final = df_final.filter(pl.col("latitude").is_not_null())
    
    records = df_final.to_dicts()
    print(f"Total registros mensuales en 2025: {len(records)}")
    
    random.seed(42)  # Semilla restaurada para reproducibilidad
    daily_demand = {} # Formato: YYYY-MM-DD -> { Planta: [clientes...] }
    
    total_pallets_distribuidos = 0
    total_trips_generados = 0

    print("Distribuyendo palets aleatoriamente a lo largo de los meses...")
    for row in records:
        date = row["Fecha"]
        year, month = date.year, date.month
        working_days = get_working_days_in_month(year, month)
        if not working_days: continue
        
        trips = row["n_envios"]
        total_pallets = row["n_pallets"]
        if total_pallets is None or total_pallets <= 0: continue
        
        total_pallets_distribuidos += total_pallets
        total_trips_generados += trips

        # Seleccionar dias aleatorios para los viajes de este cliente este mes
        selected_days = random.sample(working_days, min(trips, len(working_days)))
        if trips > len(working_days):
            selected_days.extend(random.choices(working_days, k=trips - len(working_days)))
        
        # Reparto de pallets
        base_pal = total_pallets // trips
        rem_pal = total_pallets % trips
        
        # Normalizacion de ID de Planta (para que cruce con smurfit locations)
        pname = row["Planta"].upper()
        if "ALCAL" in pname: planta_id = "CP_ALCALA"
        elif "CORDOVILLA" in pname: planta_id = "CP_NAVARRA"
        elif "CELPACK" in pname: planta_id = "CP_CELPACK"
        elif "ALMER" in pname: planta_id = "CP_ALMERIA"
        elif "BURGOS" in pname: planta_id = "CP_BURGOS"
        elif "CANOVELLES" in pname: planta_id = "CP_CANOVELLES"
        elif "ALICANTE" in pname: planta_id = "CP_ALICANTE"
        elif "HUELVA" in pname: planta_id = "CP_HUELVA"
        elif "VALENCIA" in pname: planta_id = "CP_VALENCIA"
        elif "VIGO" in pname: planta_id = "CP_VIGO"
        elif "CORDOBA" in pname: planta_id = "CP_CORDOBA"
        else: planta_id = f"CP_{pname}"
        
        for i, d in enumerate(selected_days):
            d_str = d.isoformat()
            if d_str not in daily_demand:
                daily_demand[d_str] = {}
            if planta_id not in daily_demand[d_str]:
                daily_demand[d_str][planta_id] = []
                
            pals_today = base_pal + (1 if i < rem_pal else 0)
            if pals_today <= 0: pals_today = 1
            
            client_data = {
                "codigo_postal": row["codigo_postal"],
                "municipio_destino": row["municipio_destino"],
                "pais_destino": row["pais_destino"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "n_pallets": pals_today,
                "remontar": row["remontar"],
                "name": row["municipio_destino"]
            }
            daily_demand[d_str][planta_id].append(client_data)
            
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(daily_demand, f, indent=2, ensure_ascii=False)
        
    print(f"\n¡Completado!")
    print(f"Días laborales generados: {len(daily_demand)}")
    print(f"Total pallets procesados: {int(total_pallets_distribuidos)}")
    print(f"Rutas/Envios proyectados: {total_trips_generados}")

if __name__ == "__main__":
    ingest_data()
