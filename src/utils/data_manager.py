import json
import numpy as np
import polars as pl
from pathlib import Path

class DataManager:
    def __init__(self, paper_plant, carton_plants, clients_file):
        self.paper_plant = paper_plant
        self.carton_plants = carton_plants
        self.clients_file = Path(clients_file)

    def haversine(self, lat1, lon1, lat2, lon2):
        """Calcula la distancia Haversine simplificada en km."""
        R = 6371  # Radio de la Tierra en km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    def get_optimized_locations(self, max_customers_per_plant=3, threshold_km=80):
        """
        Selecciona clientes que están 'de camino' entre la planta de cartón y Mengíbar.
        Filtro de Retorno: Minimiza el desvío (P->C + C->M) - P->M
        """
        print(f"Data Loader: Procesando clientes de {self.clients_file.name}...")
        
        with open(self.clients_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        flattened_clients = []
        for zip_code, destinations in raw_data.items():
            for dest in destinations:
                flattened_clients.append({
                    "id": f"C_{zip_code}_{dest['municipio_destino'][:3]}".upper(),
                    "name": dest['municipio_destino'],
                    "lat": float(dest['latitude']),
                    "lng": float(dest['longitude'])
                })
        
        df_clients = pl.DataFrame(flattened_clients).unique(subset=["lat", "lng"])
        
        m_lat, m_lng = self.paper_plant['lat'], self.paper_plant['lng']
        final_carton_plants = []
        
        for plant in self.carton_plants:
            p_lat, p_lng = plant['lat'], plant['lng']
            dist_pm = self.haversine(p_lat, p_lng, m_lat, m_lng)
            
            # Vectorizar cálculo de desvío
            c_lats = df_clients["lat"].to_numpy()
            c_lngs = df_clients["lng"].to_numpy()
            
            dist_pc = self.haversine(p_lat, p_lng, c_lats, c_lngs)
            dist_cm = self.haversine(c_lats, c_lngs, m_lat, m_lng)
            detours = (dist_pc + dist_cm) - dist_pm
            
            df_temp = df_clients.with_columns(pl.Series("detour", detours))
            
            # Seleccionar los mejores clientes en el pasillo de retorno
            # Usamos un umbral mayor para asegurar que hayamos cubierto la mayoría de España
            eligible_customers = (
                df_temp.filter(pl.col("detour") < threshold_km)
                .sort("detour")
                .head(max_customers_per_plant)
                .to_dicts()
            )
            
            new_plant = plant.copy()
            new_plant["customers"] = eligible_customers
            final_carton_plants.append(new_plant)
            
        print(f"✅ Selección completada: {sum(len(p['customers']) for p in final_carton_plants)} clientes seleccionados.")
        return {
            "paper_plant": self.paper_plant,
            "carton_plants": final_carton_plants
        }
