import sqlite3
import json
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class GeoCache:
    def __init__(self, db_path="data/geo_cache_v3.db"):
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
