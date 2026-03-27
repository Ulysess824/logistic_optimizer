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

# --- Costes de Explotación (TCO) ---
# Referencia: [docs/Bibliografia.md] (Basado en TCO/Observatorio MITMA)
TCO_FIXED_COSTS_ANNUAL = {
    "amortizacion": 15000,
    "seguro": 3000,
    "personal_fijo": 35000,
    "impuestos_tasas": 1200
}
TCO_VARIABLE_COSTS_KM = {
    "combustible": 0.45,
    "mantenimiento": 0.08,
    "neumaticos": 0.03,
    "adblue": 0.02
}
TCO_ANNUAL_KM_PER_TRUCK = 120000
