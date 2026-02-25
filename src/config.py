import os
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
LOCATIONS_FILE = DATA_DIR / "locations.json"

# Output Paths
OUTPUT_DIR = BASE_DIR / "outputs"
RESULTS_DIR = OUTPUT_DIR / "results"
MAPS_DIR = OUTPUT_DIR / "maps"
LOGS_DIR = BASE_DIR / "logs"

# Solver config
MAX_SEARCH_TIME = 40
DIST_LIMIT = 4000000

# Create folders if they don't exist
for folder in [OUTPUT_DIR, RESULTS_DIR, MAPS_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
