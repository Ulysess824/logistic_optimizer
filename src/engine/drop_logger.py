import logging
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class DropLogger:
    """
    Clase del motor (Engine) especializada en registrar los clientes que el 
    LogisticsSolver decide descartar debido a restricciones de capacidad, distancia o flota.
    """
    
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "descartados_motivos.log"
        self._initial_customers = {}  # Diccionario para O(1) lookups
        
    def track_nodes(self, nodes):
        """Registra en memoria todos los clientes iniciales enviados al VRP."""
        self._initial_customers.clear()
        for n in nodes:
            if n.get('type') == 'customer':
                plant_name = n.get('parent_cp', 'Desconocida')
                # Normalizar IDs: CP_ALCALA -> Alcala, carton_alcala -> Alcala
                if plant_name.startswith('CP_'):
                    plant_name = plant_name.replace('CP_', '').capitalize()
                elif plant_name.startswith('carton_'):
                    plant_name = plant_name.replace('carton_', '').capitalize()
                    
                self._initial_customers[n['id']] = {
                    "name": n.get('name', 'N/A'),
                    "plant": plant_name,
                    "pallets": n.get('demanda_pallets', 0)
                }
                
    def log_dropped_nodes(self, active_routes, max_pallets=None):
        """
        Calcula la diferencia geométrica entre los clientes pedidos y los servidos
        en las rutas finales. Exporta el delta a un archivo log de texto plano.
        """
        # 1. Identificar a los afortunados (clientes que entraron en un camión)
        servidos = set()
        for route in active_routes:
            for n in route:
                if n.get('type') == 'customer':
                    servidos.add(n['id'])
                    
        # 2. Identificar a los descartados (Dropped Nodes en jerga OR-Tools)
        descartados = []
        for cid, info in self._initial_customers.items():
            if cid not in servidos:
                descartados.append(info)
                
        # 3. Escribir el Log puro (Sobreescribimos 'w' en cada ejecución del modelo)
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] REPORTE DEL MOTOR: EXCLUSIONES DEL SOLVER\n")
            f.write("="*80 + "\n")
            
            if not descartados:
                f.write("✅ ÉXITO ABSOLUTO: El Solver consiguió enrutar el 100% de la demanda.\n")
                f.write("   Ningún cliente fue descartado por el modelo matemático.\n")
            else:
                limite_str = f" límite de {max_pallets} pallets" if max_pallets else " límite de capacidad o flota"
                for info in descartados:
                    motivo = f"El algoritmo priorizó otros nodos para maximizar la eficiencia o no cabía por el {limite_str}."
                    f.write(f" ❌ RECHAZADO: {info['name']}  [Planta: {info['plant']}]\n")
                    f.write(f"    - Pérdida de Carga: {info['pallets']} pallets\n")
                    f.write(f"    - Diagnóstico OR-Tools: {motivo}\n\n")
            f.write("="*80 + "\n")
            
        logger.info(f"DropLogger ha generado el reporte oficial de rechazos en: {self.log_path}")
        return str(self.log_path)
