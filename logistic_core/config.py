import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from logistic_core.utils.logging_setup import LogManager
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
ALLOW_ROUTE_SPLITTING = True      # Permite fragmentar pedidos entre varios camiones

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
LogManager.setup_logging(LOGS_DIR)

if not GOOGLE_MAPS_API_KEY:
    logging.getLogger("config").warning(
        "[bold yellow]GOOGLE_MAPS_API_KEY no detectada. Se utilizará OSRM o Haversine para cálculos geográficos.[/bold yellow]"
    )

# --- Tarifas de Mercado y Costes Operativos (€/km) ---
# Datos actualizados 2026 (Ref: [Observatorio MITMA / FENADISMER])
# Vehículo Articulado de Carga General (44 Toneladas Euro VI)
EXTERNAL_PROVIDER_RATE_PER_KM = 1.70    # Tarifa de mercado del proveedor externo por km (Punto a Punto)
# Costes de Explotación Base (Punto de equilibrio TCO)
BASE_TCO_DIESEL = 1.35
BASE_TCO_EV = 1.36

# Tarifas de Transferencia Interna (Ingreso de la división logística)
TARIFA_INTERNA_DIESEL = 1.50
TARIFA_INTERNA_EV = 1.60

# --- Estimación de Flota y CAPEX (Ley de Little) ---
CAPEX_TRUCK_UNIT_COST = 145_000.0  # Euros por cabeza tractora heavy duty
MIN_FILL_RATE_PCT = 10.0           # Llenado mínimo (%) para que una ruta sea rentable
DEFAULT_CYCLE_TIME_DAYS = 1.2     # Tiempo de ciclo logístico promedio en días (W)
DAILY_TRUCK_OUTBOUND = 38.0       # Viajes o despachos diarios constantes (lambda)
DEFAULT_FLEET_BUFFER = 1.10       # 10% margen operativo de seguridad (averías, descansos)
SOFTWARE_TMS_CAPEX = 25_000.0     # Inversión inicial en Software y Transformación Digital

# --- Métricas Financieras y Leasing (Modelo de Bobinas) ---
LEASING_MONTHLY_FEE_COIL_TRUCK = 2650.0  # Cuota mensual "Full-Service" (Incl. Mantenimiento)
LEASING_TERM_YEARS = 5                   # Horizonte de inversión estándar
INVESTMENT_DISCOUNT_RATE = 0.08          # WACC (8% Coste de Capital / Tasa de Descuento)
PURCHASE_RESALE_VALUE_PCT = 0.25         # Valor residual conservador (Activo especializado bobinas)
PURCHASE_UPFRONT_PCT = 0.15              # Entrada mínima para compra financiada
ANNUAL_MAINTENANCE_SURCHARGE_SPECIALIZED = 0.057 # Sobrecoste anual por desgaste carga pesada

# --- Escenario Flota Híbrida / Eléctrica ---
ELECTRIC_PLANTS_LIST = ["HUELVA", "ALMERIA", "CÓRDOBA"] # Plantas piloto para electrificación (Zero Direct Emissions)
EV_CONS_EMPTY = 1.05                          # Consumo kWh/km en vacío (HD 44t BEV)
EV_CONS_FULL = 1.70                           # Consumo kWh/km a plena carga (25t carga)

# =============================================================================
# PARÁMETROS TCO POR TECNOLOGÍA Y MODALIDAD DE ADQUISICIÓN (Horizonte: 5 años)
# Ref: Observatorio MITMA 2025, ACEA 2024, ANFAC/MOVES III
# =============================================================================

TCO_HORIZON_YEARS = 5
TCO_WACC = [0.07, 0.075, 0.08, 0.085, 0.09]             # Curva de tipos / Tasa de descuento (WACC)
TCO_INFLACION_ANUAL = [0.02, 0.03, 0.05, 0.03, 0.02]  # Pico de inflación (Inflación interanual proyectada)
TCO_TAX_RATE = 0.25                           # Impuesto de Sociedades (España)
KMS_ANUALES_POR_CAMION = 130_000              # Distancia anual por unidad (intensivo)

# --- Camión Diésel 44t (Euro VI) ---
DIESEL_CAPEX = 140_000                        # Precio de adquisición (cabeza tractora)
DIESEL_RESIDUAL_PCT = 0.30                    # Valor residual a 5 años (30%)
DIESEL_CONSUMO_L_100KM = 33.0                # Consumo medio (L/100km)
DIESEL_COSTE_COMBUSTIBLE_L = 1.45             # Precio gasoil profesional (€/L)
DIESEL_ADBLUE_L_100KM = 1.5                  # Consumo AdBlue (L/100km)
DIESEL_COSTE_ADBLUE_L = 0.50                 # Precio AdBlue (€/L)
DIESEL_MANT_ANUAL = 6_000                     # Mantenimiento preventivo/correctivo anual
DIESEL_NEUMATICOS_ANUAL = 3_000               # Sustitución de neumáticos anual
DIESEL_SEGURO_ANUAL = 3_500                   # Seguro anual (Compra/Leasing)
DIESEL_RENTING_MENSUAL = 2_800                # Renting Full-Service (incl. mant+seguro)
DIESEL_LEASING_MENSUAL = 2_600                # Leasing financiero (mant+seguro aparte)

# --- Camión Eléctrico 44t (BEV HD) ---
EV_CAPEX = 350_000                            # Precio de adquisición (cabeza tractora BEV actualizado)
EV_CHARGER_CAPEX = 50_000                     # Inversión por cargador ultra-rápido (Behind-the-meter)
EV_MOVES_AYUDA = 90_000                       # Subvención MOVES III reinstaurada para TCO
EV_RESIDUAL_PCT = 0.25                        # Valor residual a 5 años (25%)
EV_CONSUMO_KWH_KM = 1.30                     # Consumo medio ponderado (kWh/km)
EV_COSTE_KWH = 0.18                          # Precio medio kWh (depot + ruta)
EV_MANT_ANUAL = 4_000                        # Mantenimiento anual (35% menos que diésel)
EV_SEGURO_ANUAL = 4_500                       # Seguro anual (Compra/Leasing)
EV_RENTING_MENSUAL = 5_600                    # Renting Full-Service BEV
EV_LEASING_MENSUAL = 5_200                    # Leasing financiero BEV

# --- Composición de Flota Mixta (Distribución 51 camiones Excel) ---
FLEET_MIX_DIESEL = 33                          # Camiones diésel requeridos
FLEET_MIX_EV = 18                              # Camiones eléctricos requeridos
ANNUAL_DRIVER_COST_PER_TRUCK = 42_000          # Coste total empresa por conductor (Salario + SS + Dietas)

# =============================================================================
# PARÁMETROS DE BREAK-EVEN (PUNTO DE EQUILIBRIO)
# =============================================================================
BE_TARIFA_MERCADO_KM = 1.70        # Tarifa de mercado por km (€/km)
BE_INGRESO_MEDIO_VIAJE = 850.0     # Ingreso promedio por trayecto completo (€)
BE_VIAJES_ANUALES_CAMION = 250.0   # Productividad anual esperada (Viajes)
BE_PALLETS_POR_VIAJE = 33          # Capacidad de carga estándar (Euro-pallets)
BE_COBERTURA_KM2_MEDIA = 4500.0    # Área media de influencia logística (km2)

# =============================================================================
# PARÁMETROS DE BACKHAULING (Logística Inversa / Pickup and Delivery)
# =============================================================================

# Activación del módulo de recogida en retorno
BACKHAUL_ENABLED = False           # True activa el modo Pickup & Delivery en el solver

# Radio máximo (km) desde el último cliente de entrega para buscar
# plantas candidatas a la recogida de retorno
BACKHAUL_SEARCH_RADIUS_KM = 80.0

# Pallets máximos que el camión puede recoger en el viaje de vuelta.
# No puede superar la capacidad física menos lo que ya lleva cargado
# al inicio. El solver lo respeta como restricción dura.
BACKHAUL_MAX_RETURN_PALLETS = 20

# =============================================================================
# RUTAS MULTI-PLANTA ENCADENADAS (Chained Plant VRP)
# =============================================================================

# Activacion del encadenamiento dirigido entre plantas
CHAINED_PLANT_ENABLED = False

# Diccionario de encadenamiento: {planta_origen: [planta_destino, ...]}
# El camion que va a planta_origen, tras entregar a sus clientes,
# continua a planta_destino y entrega a los clientes de esta.
# Ejemplo: {"CP_ALCALA": ["CP_VALENCIA"]}
PLANT_CHAIN_MAP = {"CP_VIGO": ["CP_ALCALA"]}
