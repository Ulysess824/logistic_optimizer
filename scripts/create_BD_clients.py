import polars as pl
import json
import os
from pathlib import Path

# =====================================================================
# Parámetros de Extracción (TFM Echandi) - Histórico Completo
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
EXCEL_PATH = RAW_DIR / "Transporte (1).xlsx"
ES_CP_PATH = RAW_DIR / "ES.txt"
PT_CP_PATH = RAW_DIR / "PT.txt"

# Redirigimos al archivo maestro que consume main.py
MASTER_JSON = BASE_DIR / "data" / "cliente_ubi.json"

def cargar_referencia_postal(path_archivo):
    columnas = [
        "country_code", "postal_code", "place_name", 
        "admin_name1", "admin_code1", "admin_name2", "admin_code2", 
        "admin_name3", "admin_code3", "latitude", "longitude", "accuracy"
    ]
    return pl.read_csv(
        path_archivo,
        separator="\t",
        has_header=False,
        new_columns=columnas,
        encoding="utf8",
        infer_schema_length=0,
    ).with_columns([
        pl.col("latitude").cast(pl.Float64),
        pl.col("longitude").cast(pl.Float64),
        pl.col("postal_code").cast(pl.String).str.strip_chars().alias("cp_ref")
    ])

def generate_database():
    print(f">>> Generando Base de Datos Histórica desde {EXCEL_PATH.name}...")
    
    if not EXCEL_PATH.exists():
        print(f"Error: No se encuentra el archivo Excel en {EXCEL_PATH}")
        return

    # 1. Cargar Excel
    df_raw = pl.read_excel(source=str(EXCEL_PATH), engine="calamine", table_name="Tabla1")
    
    new_name_columns = {
        "SPEC405   [#]   Trips": "n_envios",
        "SPEC402   [#]   Drops": "n_entregas",
        "SPECT1     [#]   Transport days": "dias_transporte",
        "SPEC407   [KM]   Paid KM": "kilometros_recorridos",
        "SPEC801   [#]   Base Pallets Units": "n_pallets",
        "SPEC409   [EUR]   Total Trip Cost": "coste"
    }

    # 2. Transformación y Etiquetado temporal
    # Mantenemos todos los meses y años
    df = df_raw.lazy().with_columns(
        pl.when(pl.col("Destino").str.contains("To-ES")).then(pl.lit("España"))
        .when(pl.col("Destino").str.contains("To-PT")).then(pl.lit("Portugal"))
        .otherwise("Destino").alias("pais_destino"),
        
        pl.col("Destino").str.extract(r"(\d{4}-\d{3}|\d{5})").alias("codigo_postal"),
        
        pl.col("Destino").str.strip_chars()
        .str.extract(r"^\S+\s+\S+\s+(.*)") 
        .str.to_titlecase()
        .alias("municipio_destino"),
        
        pl.col("Fecha").str.to_date(format="%B %Y").alias("Fecha_dt")
    ).with_columns([
        pl.col("Fecha_dt").dt.year().alias("year"),
        pl.col("Fecha_dt").dt.month().alias("month")
    ]).filter(
        pl.col("tipo_envio").str.strip_chars() == "TM Third-party_FTL/CTL",
        pl.col("SPEC402   [#]   Drops") == 1,
        pl.col("SPEC801   [#]   Base Pallets Units") > 20,
        pl.col("SPEC801   [#]   Base Pallets Units") < 35
    ).rename(new_name_columns)

    print("Procesando histórico completo...")
    df_history = df.collect().with_columns(
        pl.when(pl.col("n_pallets") > 35).then(1).otherwise(0).alias("remontar"),
        pl.col("codigo_postal").cast(pl.String).str.strip_chars().alias("cp_join")
    )

    # 3. Geocodificación
    print("Geocodificando con maestros de Iberia...")
    iberia_cp = pl.concat([
        cargar_referencia_postal(str(ES_CP_PATH)),
        cargar_referencia_postal(str(PT_CP_PATH))
    ])
    
    df_final = df_history.join(
        iberia_cp,
        left_on="cp_join",
        right_on="cp_ref",
        how="left"
    ).filter(pl.col("latitude").is_not_null())

    # 4. Construcción del JSON jerárquico por código postal pero conservando el periodo
    print("Estructurando JSON histórico...")
    json_data = df_final.select([
        "municipio_destino", "pais_destino", "codigo_postal", 
        "latitude", "longitude", "n_pallets", "remontar", "year", "month"
    ])

    agrupado = json_data.group_by("codigo_postal").agg(
        pl.struct([
            "municipio_destino", "pais_destino", "latitude", "longitude", 
            "n_pallets", "remontar", "year", "month"
        ]).alias("datos")
    )

    resultado_final = {
        row["codigo_postal"]: row["datos"] 
        for row in agrupado.to_dicts()
    }

    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, indent=2, ensure_ascii=False)
    
    print(f"¡Éxito! BBDD histórica actualizada: {MASTER_JSON}")
    detected_periods = df_final.select(["year", "month"]).unique().sort(["year", "month"])
    print(f"Periodos detectados: {len(detected_periods)}")
    print(f"Total registros únicos de entrega: {len(df_final)}")

if __name__ == "__main__":
    generate_database()
