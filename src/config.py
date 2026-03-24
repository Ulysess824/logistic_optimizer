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

# Emisiones y Pesos (Modelo FCR Xiao et al.)
DEFAULT_CO2_PER_KM = 1.57        # kg CO2/km a plena carga
DEFAULT_ALPHA_FCR = 0.5          # Ratio de consumo vacío/cargado
PAPER_LOAD_KG = 25_000           # Carga de bobinas PP -> CP (kg)
PALLET_WEIGHT_KG = 145           # Peso promedio por pallet (kg)
VEHICLE_MAX_LOAD_KG = 25_000     # Capacidad máxima del vehículo (kg)para cálculo ratio FCR

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
