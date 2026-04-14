"""
generate_yearly_data.py
-----------------------
Generador de demanda anual basado en datos reales del Excel 'Transporte (1).xlsx'.
Transforma la demanda mensual agrupada en un calendario diario (2025)
asegurando que Lunes y Viernes siempre tengan pedidos.
"""

import os
import json
import random
import datetime
from pathlib import Path
import polars as pl

# Configuración de Rutas
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_EXCEL_PATH = BASE_DIR / "data" / "raw" / "Transporte (1).xlsx"
ES_CP_PATH = BASE_DIR / "data" / "raw" / "ES.txt"
PT_CP_PATH = BASE_DIR / "data" / "raw" / "PT.txt"
OUTPUT_JSON_PATH = BASE_DIR / "data" / "yearly_demand.json"

def cargar_referencia_postal(path_archivo):
    """Carga y normaliza los datos CP de GeoNames."""
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
        infer_schema_length=0
    ).with_columns([
        pl.col("latitude").cast(pl.Float64, strict=False),
        pl.col("longitude").cast(pl.Float64, strict=False)
    ])

def limpiar_y_enriquecer_datos():
    """Lee el Excel, limpia según la lógica del notebook y añade coordenadas."""
    print("Cargando y procesando base de datos de transporte...")
    
    # Mapeo de columnas original -> legible
    new_name_columns = {
        "SPEC405   [#]   Trips": "n_envios",
        "SPEC402   [#]   Drops": "n_entregas",
        "SPECT1     [#]   Transport days": "dias_transporte",
        "SPEC407   [KM]   Paid KM": "kilometros_recorridos",
        "SPEC801   [#]   Base Pallets Units": "n_pallets",
        "SPEC409   [EUR]   Total Trip Cost": "coste"
    }

    # Leemos el Excel
    # Nota: Usamos calamine como motor por defecto
    df_raw = pl.read_excel(
        source=RAW_EXCEL_PATH,
        engine="calamine",
        table_name="Tabla1"
    )

    # Transformación Estilo Notebook
    df = df_raw.lazy().with_columns(
        # 1. Hallar país
        pl.col("Planta").str.replace("SK ", ""),
        pl.when(pl.col("Destino").str.contains("To-ES"))
        .then(pl.lit("España"))
        .when(pl.col("Destino").str.contains("To-PT"))
        .then(pl.lit("Portugal"))
        .otherwise("Destino").alias("pais_destino"),
        
        # 2. Código Postal
        pl.col("Destino").str.extract(r"(\d{4}-\d{3}|\d{5})").alias("codigo_postal"),

        # 3. Municipio
        pl.col("Destino").str.strip_chars()
        .str.extract(r"^\S+\s+\S+\s+(.*)")
        .str.to_titlecase()
        .alias("municipio_destino"),
        
        # 4. Mes/Año
        pl.col("Fecha").str.to_date(format="%B %Y").alias("Fecha")
    ).filter(
        pl.col("tipo_envio").str.strip_chars() == "TM Third-party_FTL/CTL",
        pl.col("SPEC402   [#]   Drops") == 1
    ).rename(new_name_columns).collect()

    # Cargar coordenadas IBERIA
    es_cp = cargar_referencia_postal(ES_CP_PATH)
    pt_cp = cargar_referencia_postal(PT_CP_PATH)
    iberia_cp = pl.concat([es_cp, pt_cp]).select([
        pl.col("postal_code").alias("cp_ref"),
        pl.col("latitude"),
        pl.col("longitude")
    ]).unique(subset=["cp_ref"])

    # Unir con datos logísticos
    df_final = df.join(
        iberia_cp,
        left_on="codigo_postal",
        right_on="cp_ref",
        how="left"
    ).filter(pl.col("latitude").is_not_null())

    return df_final

def distribuir_demanda(df):
    """
    Distribuye los pedidos mensuales en el calendario diario 2025.
    Regla: Lunes y Viernes obligatorio. Resto aleatorio.
    """
    print("Iniciando distribución diaria (L/V obligatorio)...")
    
    # Extraer meses disponibles
    meses_disponibles = df["Fecha"].dt.month().unique().to_list()
    yearly_data = {}
    
    # Generar calendario laboral 2025 (Excluir Sábado=5, Domingo=6)
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    
    current = start_date
    while current <= end_date:
        if current.weekday() < 5: # Lunes a Viernes
            m = current.month
            if m in meses_disponibles:
                # Filtrar pool de pedidos para este mes
                pool = df.filter(pl.col("Fecha").dt.month() == m).to_dicts()
                
                # Para facilitar, guardamos los días laborales del mes para distribución proporcional
                month_days = []
                temp_date = current.replace(day=1)
                while temp_date.month == m:
                    if temp_date.weekday() < 5:
                        month_days.append(temp_date.isoformat())
                    temp_date += datetime.timedelta(days=1)
                
                # Solo procesamos si no hemos inicializado este mes
                month_key = f"M{m}"
                if month_key not in yearly_data:
                    yearly_data[month_key] = True # Flag para no repetir lógica por cada día del mismo mes
                    
                    # Identificar Lunes (0) y Viernes (4) del mes
                    mondays_fridays = [d for d in month_days if datetime.date.fromisoformat(d).weekday() in [0, 4]]
                    other_days = [d for d in month_days if d not in mondays_fridays]
                    
                    # Inicializar diccionario diario
                    for d in month_days:
                        yearly_data[d] = {}
                    
                    # 1. Asegurar Lunes y Viernes
                    random.shuffle(pool)
                    for d in mondays_fridays:
                        if pool:
                            pedido = pool.pop()
                            _add_to_day(yearly_data[d], pedido)
                    
                    # 2. Distribuir el resto aleatoriamente entre todos los días laborales del mes
                    while pool:
                        pedido = pool.pop()
                        target_day = random.choice(month_days)
                        _add_to_day(yearly_data[target_day], pedido)

        current += datetime.timedelta(days=1)
    
    # Limpiar flags temporales
    final_output = {k: v for k, v in yearly_data.items() if not k.startswith("M")}
    return final_output

def _add_to_day(day_dict, pedido):
    """Helper para estructurar el JSON como espera el sistema."""
    cp = pedido["codigo_postal"]
    if cp not in day_dict:
        day_dict[cp] = []
    
    entry = {
        "municipio_destino": pedido["municipio_destino"],
        "pais_destino": pedido["pais_destino"],
        "latitude": pedido["latitude"],
        "longitude": pedido["longitude"],
        "n_pallets": pedido["n_pallets"],
        "remontar": 1 if pedido["n_pallets"] > 35 else 0
    }
    day_dict[cp].append(entry)

def main():
    try:
        df_logistica = limpiar_y_enriquecer_datos()
        yearly_demand = distribuir_demanda(df_logistica)
        
        print(f"Guardando {len(yearly_demand)} días de demanda real en {OUTPUT_JSON_PATH}")
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(yearly_demand, f, indent=2, ensure_ascii=False)
            
        print("¡Proceso de Generación Anual Realista finalizado!")
    except Exception as e:
        print(f"Error durante la generación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
