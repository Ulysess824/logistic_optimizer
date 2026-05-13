import json
import math
import logging
import numpy as np
import unicodedata
import polars as pl
from pathlib import Path
from logistic_core.utils.geo import GeoUtils
from logistic_core.config import DEFAULT_MAX_CUSTOMERS, DEFAULT_THRESHOLD_KM

logger = logging.getLogger(__name__)


class DataManager:
    _cached_raw_data = None  # Caché de clase para evitar re-lectura de disco

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

        # Lógica de Remontar y agrupación
        n_pallets = int(dest.get('n_pallets', dest.get('demanda_pallets', 0)))
        remontar = int(dest.get('remontar', 0))
        if remontar == 1:
            # Si se puede remontar, cada 2 pallets ocupan 1 hueco de suelo.
            # math.ceil asegura que un número impar (ej. 3) redondee a 2 huecos, no 1.
            eff_pallets = math.ceil(n_pallets / 2)
        else:
            eff_pallets = n_pallets
            
        return {
            "id": f"C_{zip_code}_{dest['municipio_destino'][:3]}".upper(),
            "name": dest['municipio_destino'],
            "lat": lat,
            "lng": lng,
            "demanda_pallets": eff_pallets,
            "n_pallets_original": n_pallets,
            "remontar": remontar,
            "year": int(dest.get('year', 0)),
            "month": int(dest.get('month', 0))
        }

    # ------------------------------------------------------------------
    # Selección inteligente de clientes (Filtro de Retorno)
    # ------------------------------------------------------------------
    def get_optimized_locations(self, max_customers_per_plant=None, threshold_km=None, max_radius_km=None, mandatory_customers=None, sorting_strategy="detour", default_limit=None, max_pallets=None, target_year=None, target_month=None):
        """
        Selecciona clientes mediante doble filtro:
        1. Filtro local (Haversine): Clientes dentro de max_radius_km.
        2. Filtro de desvío (API Real): Quedarse con los que supongan el menor desvío
           hacia Mengíbar usando distancias por carretera de la Google Routes API.
        
        Args:
            max_pallets: Capacidad máxima del camión. Si un envío excede este valor,
                         se particiona automáticamente en envíos parciales.
        """
        fallback = default_limit or DEFAULT_MAX_CUSTOMERS
        max_customers_per_plant = max_customers_per_plant if max_customers_per_plant is not None else fallback
        threshold_km = threshold_km or DEFAULT_THRESHOLD_KM
        max_radius_km = max_radius_km or 1000  # Default grande si no se especifica
        mandatory_customers = mandatory_customers or {}
        self._max_pallets = max_pallets  # Guardar para validación pre-solver

        logger.info("Procesando clientes de %s (Radio Max: %skm)...", self.clients_file.name, max_radius_km)

        if DataManager._cached_raw_data is None:
            with open(self.clients_file, 'r', encoding='utf-8') as f:
                DataManager._cached_raw_data = json.load(f)
        
        raw_data = DataManager._cached_raw_data

        flattened_clients = []
        for zip_code, destinations in raw_data.items():
            for dest in destinations:
                validated = self._validate_client(dest, zip_code)
                if validated:
                    # Aplicar filtro temporal si se especifica
                    match_year = (target_year is None) or (validated['year'] == target_year)
                    match_month = (target_month is None) or (validated['month'] == target_month)
                    
                    if match_year and match_month:
                        flattened_clients.append(validated)

        if not flattened_clients:
            logger.error("No se encontraron clientes válidos.")
            return {"paper_plant": self.paper_plant, "carton_plants": []}

        # --- VALIDACIÓN PRE-SOLVER: Partición de envíos sobredimensionados ---
        from logistic_core.config import ALLOW_ROUTE_SPLITTING
        if max_pallets and max_pallets > 0 and ALLOW_ROUTE_SPLITTING:
            partitioned = []
            for client in flattened_clients:
                dem = client['demanda_pallets']
                if dem > max_pallets:
                    # Partir en envíos que quepan en un solo camión
                    part_num = 1
                    remaining = dem
                    while remaining > 0:
                        chunk = min(remaining, max_pallets)
                        part = dict(client)
                        part['id'] = f"{client['id']}_P{part_num}"
                        part['demanda_pallets'] = chunk
                        part['envio_parcial'] = True
                        part['envio_original_pallets'] = dem
                        partitioned.append(part)
                        remaining -= chunk
                        part_num += 1
                    logger.info(
                        "ALLOW_ROUTE_SPLITTING=True: Envio '%s' (%d pallets) particionado en %d envios.",
                        client['name'], dem, part_num - 1
                    )
                else:
                    partitioned.append(client)
            flattened_clients = partitioned
        else:
            if max_pallets and not ALLOW_ROUTE_SPLITTING:
                logger.info("ALLOW_ROUTE_SPLITTING=False: Los envíos se tratarán como unidades atómicas.")

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
                    cand['real_dist_CM'] = real_dist_CM
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
                    cand['real_dist_CM'] = real_dist_CM
                    cand['obligatorio'] = False
                    cand['parent_cp'] = plant['id']  # ← consistencia con obligatorios
                    qualified_customers.append(cand)
                    
            # --- FASE 3: Selección Final ---
            # Determinamos el límite para esta planta específica
            current_limit = fallback
            if isinstance(max_customers_per_plant, dict):
                # Usamos el nombre normalizado para la búsqueda en el dict
                # Buscamos coincidencias con nombres cortos (sin "Smurfit Westrock")
                plant_key = self._normalize_text(plant['name'].replace("Smurfit Westrock ", ""))
                # También permitimos la búsqueda por el nombre completo
                full_plant_key = self._normalize_text(plant['name'])
                
                # Prioridad: nombre corto -> nombre completo -> global default
                dict_norm = {self._normalize_text(k): v for k, v in max_customers_per_plant.items()}
                current_limit = dict_norm.get(plant_key, dict_norm.get(full_plant_key, fallback))
            elif isinstance(max_customers_per_plant, int):
                current_limit = max_customers_per_plant

            # Aseguramos que los clientes obligatorios sí o sí entren en la lista.
            mandatories = [c for c in qualified_customers if c.get('obligatorio')]
            optionals = [c for c in qualified_customers if not c.get('obligatorio')]
            
            # Evaluamos el criterio de optimización escogido para los opcionales
            if sorting_strategy == "far_plant_close_depot":
                # Priorizar los más lejanos a la planta pero cercanos al depot
                optionals.sort(key=lambda x: x.get('real_dist_CM', 0) - x.get('real_dist_km', 0))
            else:
                # Comportamiento por defecto ("detour"): menor desvío global
                optionals.sort(key=lambda x: x.get('detour', float('inf')))
            
            # Los obligatorios tienen prioridad absoluta. 
            # El límite se aplica al total de la ruta para esta planta.
            num_optionals_to_add = max(0, current_limit - len(mandatories))
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
