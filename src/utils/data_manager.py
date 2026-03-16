import json
import logging
import numpy as np
import unicodedata
import polars as pl
from pathlib import Path
from src.utils.geo import GeoUtils
from src.config import DEFAULT_MAX_CUSTOMERS, DEFAULT_THRESHOLD_KM

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self, paper_plant, carton_plants, clients_file, geo_utils=None):
        self.paper_plant = paper_plant
        self.carton_plants = carton_plants
        self.clients_file = Path(clients_file)
        self.geo = geo_utils if geo_utils else GeoUtils()

    @staticmethod
    def _normalize_text(s):
        """Elimina acentos, convierte a minúsculas y limpia espacios."""
        if not s:
            return ""
        return "".join(
            c for c in unicodedata.normalize('NFD', str(s))
            if unicodedata.category(c) != 'Mn'
        ).lower().strip()

    # ------------------------------------------------------------------
    # Validación de un registro de cliente
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_client(dest, zip_code):
        """Valida que un registro de cliente tenga los campos requeridos y numéricos."""
        required = ['municipio_destino', 'latitude', 'longitude']
        for key in required:
            if key not in dest:
                logger.warning("Cliente en CP %s sin campo '%s'. Omitido.", zip_code, key)
                return None
        try:
            lat = float(dest['latitude'])
            lng = float(dest['longitude'])
        except (ValueError, TypeError):
            logger.warning(
                "Cliente '%s' (CP %s) con coordenadas no numéricas. Omitido.",
                dest.get('municipio_destino', '?'), zip_code
            )
            return None

        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            logger.warning(
                "Cliente '%s' (CP %s) con coordenadas fuera de rango (%.4f, %.4f). Omitido.",
                dest.get('municipio_destino', '?'), zip_code, lat, lng
            )
            return None

        return {
            "id": f"C_{zip_code}_{dest['municipio_destino'][:3]}".upper(),
            "name": dest['municipio_destino'],
            "lat": lat,
            "lng": lng
        }

    # ------------------------------------------------------------------
    # Selección inteligente de clientes (Filtro de Retorno)
    # ------------------------------------------------------------------
    def get_optimized_locations(self, max_customers_per_plant=None, threshold_km=None, max_radius_km=None, mandatory_customers=None):
        """
        Selecciona clientes mediante doble filtro:
        1. Filtro local (Haversine): Clientes dentro de max_radius_km.
        2. Filtro de desvío (API Real): Quedarse con los que supongan el menor desvío
           hacia Mengíbar usando distancias por carretera de la Google Routes API.
        """
        max_customers_per_plant = max_customers_per_plant or DEFAULT_MAX_CUSTOMERS
        threshold_km = threshold_km or DEFAULT_THRESHOLD_KM
        max_radius_km = max_radius_km or 1000  # Default grande si no se especifica
        mandatory_customers = mandatory_customers or {}

        logger.info("Procesando clientes de %s (Radio Max: %skm)...", self.clients_file.name, max_radius_km)

        with open(self.clients_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        flattened_clients = []
        for zip_code, destinations in raw_data.items():
            for dest in destinations:
                validated = self._validate_client(dest, zip_code)
                if validated:
                    flattened_clients.append(validated)

        if not flattened_clients:
            logger.error("No se encontraron clientes válidos.")
            return {"paper_plant": self.paper_plant, "carton_plants": []}

        df_clients = pl.DataFrame(flattened_clients).unique(subset=["lat", "lng"])
        logger.info("Clientes únicos en base de datos: %d", len(df_clients))

        m_lat, m_lng = self.paper_plant['lat'], self.paper_plant['lng']
        final_carton_plants = []

        for plant in self.carton_plants:
            p_lat, p_lng = plant['lat'], plant['lng']
            
            # --- FASE 1: Pre-filtro Haversine (Ahorro de API) ---
            c_lats = df_clients["lat"].to_numpy()
            c_lngs = df_clients["lng"].to_numpy()
            dist_haversine = GeoUtils.haversine_km(p_lat, p_lng, c_lats, c_lngs)
            
            df_temp = df_clients.with_columns(pl.Series("hav_dist", dist_haversine))
            
            # Cogemos candidatos a < max_radius_km, y un máximo absoluto inicial (ej. 150) para no saturar Routes API
            df_candidates = df_temp.filter(pl.col("hav_dist") <= max_radius_km).sort("hav_dist").head(150)
            
            # --- MEJORA: Asegurar que los obligatorios se incluyan incluso si están lejos ---
            # Normalizamos el nombre de la planta para el matching
            p_name_plain = self._normalize_text(plant['name'].replace("Smurfit Westrock ", ""))
            
            mandatory_for_plant = []
            if mandatory_customers:
                # Buscamos en el dict normalizando también sus llaves
                norm_mandatory_dict = {self._normalize_text(k): v for k, v in mandatory_customers.items()}
                m_custs = norm_mandatory_dict.get(p_name_plain, [])
                mandatory_for_plant = [m_custs] if isinstance(m_custs, str) else m_custs

            if mandatory_for_plant:
                # Buscamos clientes obligatorios en el dataframe original
                try:
                    m_names_plain = [self._normalize_text(m) for m in mandatory_for_plant]
                    
                    # Creamos una columna temporal normalizada para el filtro rápido
                    df_temp = df_temp.with_columns(
                        pl.col("name").map_elements(self._normalize_text, return_dtype=pl.String).alias("name_plain")
                    )
                    
                    df_mandatory = df_temp.filter(pl.col("name_plain").is_in(m_names_plain))
                    if not df_mandatory.is_empty():
                        df_candidates = pl.concat([df_candidates, df_mandatory.drop("name_plain")]).unique(subset=["lat", "lng"])
                except Exception as e:
                    logger.warning("Error filtrando obligatorios para %s: %s", plant['name'], e)
            
            pre_candidates = df_candidates.to_dicts()
            
            if not pre_candidates:
                logger.warning("Ningún cliente local a menos de %skm para %s", max_radius_km, plant['name'])
                plant["customers"] = []
                final_carton_plants.append(plant.copy())
                continue
                
            logger.info("Evaluando %d candidatos locales reales para %s...", len(pre_candidates), plant['name'])

            # --- FASE 2: Matriz Real de Carretera Vía GeoUtils ---
            # Construimos los Nodos: [0] = Planta, [1] = Mengíbar, [2..N+2] = Clientes locales
            local_nodes = [{'id': plant['id'], 'lat': p_lat, 'lng': p_lng}]
            local_nodes.append({'id': self.paper_plant.get('id', 'PAPER_MILL'), 'lat': m_lat, 'lng': m_lng})
            local_nodes.extend({'id': c['id'], 'lat': c['lat'], 'lng': c['lng']} for c in pre_candidates)
            
            matrix, _ = self.geo.calculate_distance_matrix(local_nodes)
            
            real_dist_PM = matrix[0][1] / 1000.0  # Planta -> Mengíbar
            
            qualified_customers = []
            
            # Validamos los clientes (índices en la matriz del 2 en adelante)
            for idx, cand in enumerate(pre_candidates, start=2):
                real_dist_PC = matrix[0][idx] / 1000.0  # Planta -> Cliente
                real_dist_CM = matrix[idx][1] / 1000.0  # Cliente -> Mengíbar
                detour = (real_dist_PC + real_dist_CM) - real_dist_PM
                
                is_mandatory = False
                if mandatory_for_plant:
                    c_name_plain = self._normalize_text(cand['name'])
                    m_names_plain = [self._normalize_text(m) for m in mandatory_for_plant]
                    is_mandatory = c_name_plain in m_names_plain
                
                # --- EXCEPCIÓN VIP: Si es obligatorio, se salta los filtros de Radio y Desvío ---
                if is_mandatory:
                    logger.info("  -> Cliente '%s' reconocido como OBLIGATORIO para %s", cand['name'], plant['name'])
                    cand['detour'] = detour
                    cand['real_dist_km'] = real_dist_PC
                    cand['obligatorio'] = True
                    cand['parent_cp'] = plant['id']  # ← necesario para que solver lo vincule
                    qualified_customers.append(cand)
                    continue

                # Check estricto para clientes normales
                if real_dist_PC > max_radius_km:
                    continue
                    
                if detour <= threshold_km:
                    cand['detour'] = detour
                    cand['real_dist_km'] = real_dist_PC
                    cand['obligatorio'] = False
                    cand['parent_cp'] = plant['id']  # ← consistencia con obligatorios
                    qualified_customers.append(cand)
                    
            # --- FASE 3: Selección Final ---
            # Aseguramos que los clientes obligatorios sí o sí entren en la lista.
            mandatories = [c for c in qualified_customers if c.get('obligatorio')]
            optionals = [c for c in qualified_customers if not c.get('obligatorio')]
            
            # Ordenamos los opcionales por menor desvío
            optionals.sort(key=lambda x: x['detour'])
            
            # Los obligatorios tienen prioridad absoluta y NO cuentan para el límite 
            # de "clientes opcionales" si el usuario quiere un máximo de N extras.
            # Sin embargo, para ser fieles al espíritu de 'max_customers_per_plant',
            # incluiremos todos los obligatorios y luego rellenaremos hasta el límite.
            # Si ya hay más obligatorios que el límite, se quedan todos los obligatorios y 0 opcionales.
            num_optionals_to_add = max(0, max_customers_per_plant - len(mandatories))
            eligible_customers = mandatories + optionals[:num_optionals_to_add]

            new_plant = plant.copy()
            new_plant["customers"] = eligible_customers
            final_carton_plants.append(new_plant)

        total_selected = sum(len(p['customers']) for p in final_carton_plants)
        logger.info("Selección final completada: %d clientes asigandos en total.", total_selected)

        return {
            "paper_plant": self.paper_plant,
            "carton_plants": final_carton_plants
        }