import sqlite3
import json
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class GeoCache:
    def __init__(self, db_path="data/geo_cache_v4_osrm.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS route_cache (
                    key TEXT PRIMARY KEY,
                    distance_meters INTEGER,
                    duration_seconds INTEGER,
                    polyline TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _generate_key(self, origin, destination, travel_mode="DRIVE", truck_specs=None):
        """Genera un hash único basado en los parámetros de la ruta."""
        data = {
            "o": origin,
            "d": destination,
            "m": travel_mode,
            "s": truck_specs or {}
        }
        dump = json.dumps(data, sort_keys=True)
        return hashlib.sha256(dump.encode()).hexdigest()

    def get_route(self, origin, destination, travel_mode="DRIVE", truck_specs=None):
        key = self._generate_key(origin, destination, travel_mode, truck_specs)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT distance_meters, duration_seconds, polyline FROM route_cache WHERE key = ?", 
                (key,)
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                logger.debug("Cache HIT for route %s -> %s", origin, destination)
                return {
                    "distance_meters": row[0],
                    "duration_seconds": row[1],
                    "polyline": row[2]
                }
        return None

    def store_route(self, origin, destination, distance, duration, polyline=None, travel_mode="DRIVE", truck_specs=None):
        key = self._generate_key(origin, destination, travel_mode, truck_specs)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO route_cache (key, distance_meters, duration_seconds, polyline)
                VALUES (?, ?, ?, ?)
            """, (key, distance, duration, polyline))
            conn.commit()
            logger.debug("Cache STORE for route %s -> %s", origin, destination)

    def store_batch(self, entries):
        """Almacena múltiples rutas en una sola transacción para eficiencia.
        
        'entries' debe ser una lista de tuplas/dicts con origin, destination, distance, duration, polyline.
        """
        if not entries: return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for e in entries:
                key = self._generate_key(
                    e['origin'], e['destination'], 
                    e.get('travel_mode', 'DRIVE'), 
                    e.get('truck_specs', {})
                )
                cursor.execute("""
                    INSERT OR REPLACE INTO route_cache (key, distance_meters, duration_seconds, polyline)
                    VALUES (?, ?, ?, ?)
                """, (key, e['distance'], e['duration'], e.get('polyline')))
            conn.commit()
            logger.info("Cache BATCH_STORE: %d rutas persistidas en una transacción.", len(entries))

    def get_polyline(self, origin, destination, travel_mode="DRIVE", truck_specs=None):
        res = self.get_route(origin, destination, travel_mode, truck_specs)
        return res["polyline"] if res else None

    def store_polyline(self, origin, destination, polyline, travel_mode="DRIVE", truck_specs=None):
        # Si ya existe registro de distancia, actualizamos polyline. 
        # Si no, creamos uno nuevo con distancias nulas.
        key = self._generate_key(origin, destination, travel_mode, truck_specs)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO route_cache (key, polyline) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET polyline=excluded.polyline
            """, (key, polyline))
            conn.commit()
