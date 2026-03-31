import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Base project path
BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Data Paths
DATA_DIR = BASE_DIR / "data"

# Output Paths
OUTPUT_DIR = BASE_DIR / "outputs"
RESULTS_DIR = OUTPUT_DIR / "results"
MAPS_DIR = OUTPUT_DIR / "maps"
LOGS_DIR = BASE_DIR / "logs"

# Solver config
MAX_SEARCH_TIME = 90          # Segundos máximos de búsqueda del solver
OSRM_URL = os.getenv("OSRM_URL", "http://localhost:5000")
ROAD_CORRECTION_FACTOR = 1.25 # Factor de "asfalto" para Haversine (GABM Std)
DIST_LIMIT = 4_000_000        # Límite de distancia por vehículo (metros)
DEFAULT_N_CLIENTES = 4        # Máximo de clientes por ruta (dimensión del solver)
DEFAULT_MAX_PLANTS_PER_ROUTE = 1  # Plantas por ruta (1=VRPB clásico, >1=MC-VRPB)

# Data Manager config
DEFAULT_MAX_CUSTOMERS = 4     # Valor de respaldo si no se define N_CLIENTES o un dict
DEFAULT_THRESHOLD_KM = 100    # Umbral de desvío en km para filtro de retorno

# Emisiones y Pesos (Modelo GLEC v3.0 / VECTO Euro VI)
# Referencia: [DOI: 10.1016/j.trd.2019.08.002] (Grigoratos et al. 2019)
GLEC_CO2_PER_LITER = 2.68        # kg CO2/L (Estándar GLEC v3 Diesel)
GLEC_INTENSITY_GTKM = 17.32      # g CO2/tkm incremental (40t truck)
GLEC_EMPTY_FLOOR_KGKM = 0.652    # kg CO2/km suelo vacío (Euro VI)
PAPER_LOAD_KG = 25_000           # Carga de bobinas PP -> CP (kg)
PALLET_WEIGHT_KG = 145           # Peso promedio por pallet (kg)
VEHICLE_MAX_LOAD_KG = 25_000     # Capacidad máxima del vehículo (kg)para cálculo ratio FCR

# --- Dimensiones Físicas (Capacidad 3D) ---
TRAILER_LENGTH_M = 13.6
TRAILER_WIDTH_M = 2.4
TRAILER_HEIGHT_M = 2.7
PALLET_LENGTH_M = 1.2
PALLET_WIDTH_M = 0.8
PALLET_HEIGHT_M = 1.5
LOAD_STACKABLE = False           # Por defecto la carga no es apilable

# Create folders if they don't exist
for folder in [OUTPUT_DIR, RESULTS_DIR, MAPS_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# --- Logging Configuration ---
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_FILE = LOGS_DIR / "optimizer.log"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Warn if API key is missing
if not GOOGLE_MAPS_API_KEY:
    logging.getLogger("config").warning(
        "GOOGLE_MAPS_API_KEY no está configurada. Se usará estimación Haversine."
    )

# --- Tarifas de Mercado y Costes Operativos (€/km) ---
# Datos actualizados 2026 (Ref: [Observatorio MITMA / FENADISMER])
# Vehículo Articulado de Carga General (44 Toneladas Euro VI)
EXTERNAL_PROVIDER_RATE_PER_KM = 1.61    # Tarifa de mercado del proveedor externo por km (Punto a Punto)
INTERNAL_OPERATIONAL_TCO_RATE = 1.157   # Tarifa técnica propia (Totalmente cargado TCO)

TCO_FIXED_COSTS_ANNUAL = {
    "personal_y_dietas": 56967.0,      # Chófer, SS y dietas (33.8% del coste total)
    "amortizacion_vehiculo": 16450.0,    # Depreciación tractora + semi (8 años)
    "seguros_y_visados": 4200.0,        # Responsabilidad civil y mercancía
    "costes_indirectos_adm": 12840.0,    # Gestión de flota, planners y alquileres
    "fiscalidad_y_otros": 1850.0        # ITVs, Impuesto Tracción Mecánica e IAE
}

TCO_VARIABLE_COSTS_KM = {
    "combustible_diesel": 0.395,       # Consumo aprox 34L/100km (44t)
    "mantenimiento_reparacion": 0.092,  # Correctivo y preventivo
    "neumaticos": 0.038,               # Desgaste por rodadura (alto impacto en 44t)
    "adblue_y_lubricantes": 0.015       # Consumibles Euro VI
}

# Distancia de referencia anual para amortización de costes fijos
TCO_ANNUAL_KM_PER_TRUCK = 120000

# --- Estimación de Flota y CAPEX (Ley de Little) ---
CAPEX_TRUCK_UNIT_COST = 145_000.0  # Euros por cabeza tractora heavy duty
DEFAULT_CYCLE_TIME_DAYS = 1.2     # Tiempo de ciclo logístico promedio en días (W)
DAILY_TRUCK_OUTBOUND = 38.0       # Viajes o despachos diarios constantes (lambda)
DEFAULT_FLEET_BUFFER = 1.10       # 10% margen operativo de seguridad (averías, descansos)
SOFTWARE_TMS_CAPEX = 25_000.0     # Inversión inicial en Software y Transformación Digital

# --- Métricas Finacieras y Leasing (Modelo de Bobinas) ---
LEASING_MONTHLY_FEE_COIL_TRUCK = 2650.0  # Cuota mensual "Full-Service" (Incl. Mantenimiento)
LEASING_TERM_YEARS = 5                   # Horizonte de inversión estándar
INVESTMENT_DISCOUNT_RATE = 0.08          # WACC (8% Coste de Capital / Tasa de Descuento)
PURCHASE_RESALE_VALUE_PCT = 0.25         # Valor residual conservador (Activo especializado bobinas)
PURCHASE_UPFRONT_PCT = 0.15              # Entrada mínima para compra financiada
ANNUAL_MAINTENANCE_SURCHARGE_SPECIALIZED = 0.057 # Sobrecoste anual por desgaste carga pesada
