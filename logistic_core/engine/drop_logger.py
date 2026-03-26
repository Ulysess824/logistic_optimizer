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
        
    def _normalize_plant_id(self, plant_id):
        """Asegura que el ID de planta sea consistente (ej. CP_VALENCIA)."""
        if not plant_id: return "CP_DESCONOCIDA"
        p_id = str(plant_id).upper()
        if not p_id.startswith("CP_"):
            # Mapeo: NAVARRA -> CP_NAVARRA
            p_id = f"CP_{p_id}"
        return p_id

    def track_nodes(self, nodes):
        """Registra en memoria todos los clientes iniciales enviados al VRP."""
        self._initial_customers.clear()
        for n in nodes:
            if n.get('type') == 'customer':
                # Normalizar siempre a formato CP_XXXX
                raw_plant = n.get('parent_cp', 'DESCONOCIDA')
                plant_name = self._normalize_plant_id(raw_plant)
                    
                self._initial_customers[n['id']] = {
                    "name": n.get('name', 'N/A'),
                    "plant": plant_name,
                    "pallets": n.get('demanda_pallets', 0),
                    "dist_to_plant": n.get('dist_to_plant', 0)
                }
                
    def log_dropped_nodes(self, active_routes, fleet_data=None, dimension_stats=None):
        """
        Calcula por qué se descartaron los clientes comparando con el estado de la flota.
        fleet_data: Información sobre vehículos disponibles vs usados.
        dimension_stats: Estadísticas de carga/distancia de las rutas activas.
        """
        # 1. Identificar clientes servidos
        servidos = set()
        for route in active_routes:
            for n in route:
                if n.get('type') == 'customer':
                    servidos.add(n['id'])
                    
        # 2. Identificar descartados y diagnosticar
        descartados_por_planta = {}
        for cid, info in self._initial_customers.items():
            if cid not in servidos:
                plant = info['plant']
                if plant not in descartados_por_planta:
                    descartados_por_planta[plant] = []
                
                # DIAGNÓSTICO LÓGICO
                motivo = "El algoritmo prioritizó otros nodos por eficiencia general."
                
                # Caso especial: Fuera de rango geográfico
                dist_to_base = info.get('dist_to_plant', 0)
                if dist_to_base > 500:
                    motivo = "FUERA DE RANGO: El cliente está a {:.1f}km de su planta base (Límite: 500km).".format(dist_to_base)
                
                elif dimension_stats and plant in dimension_stats:
                    stats = dimension_stats[plant]
                    # Si la carga media de las rutas de esa planta es > 90%
                    if stats.get('avg_load_pct', 0) > 90:
                        motivo = "SATURACIÓN DE CAPACIDAD: Los camiones asignados a esta planta van al >90% de su capacidad."
                    elif stats.get('max_stops_reached', False):
                        motivo = "LÍMITE DE PARADAS: Los vehículos alcanzaron el número máximo de paradas permitido por jornada."
                    elif stats.get('avg_dist_km', 0) > 500:
                        motivo = "DISTANCIA/TIEMPO: El cliente implicaba un desvío que excedía el tiempo legal de conducción."
                
                if fleet_data and plant in fleet_data:
                    f_info = fleet_data[plant]
                    if f_info['used'] >= f_info['total']:
                        motivo = "FLOTA INSUFICIENTE: Se han usado todos los camiones ({}/{}) disponibles para esta planta.".format(f_info['used'], f_info['total'])

                info['motivo'] = motivo
                descartados_por_planta[plant].append(info)
                
        # 3. Escribir el Log agrupado por Planta (solo las oficiales CP_)
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] REPORTE DEL MOTOR: AUDITORIA DE EXCLUSIONES\n")
            f.write("="*80 + "\n")
            
            if not descartados_por_planta and not active_routes:
                f.write("SOLVER FINALIZADO: No hay datos de rutas ni descartes.\n")
            else:
                # Filtrar y ordenar plantas (solo las que comienzan por CP)
                all_plants = set(list(descartados_por_planta.keys()) + (list(fleet_data.keys()) if fleet_data else []))
                sorted_plants = sorted([p for p in all_plants if str(p).startswith("CP_")])

                for plant in sorted_plants:
                    f.write(f"\nPLANTA: {plant.upper()}\n")
                    f.write("-" * 40 + "\n")
                    
                    # Mostrar estado de subrutas (camiones)
                    if fleet_data and plant in fleet_data:
                        f_info = fleet_data[plant]
                        f.write(f"ESTADO DE FLOTA: {f_info['used']} de {f_info['total']} camiones en uso\n")
                        if "subroutes" in f_info and f_info["subroutes"]:
                            f.write("DETALLE DE SUBRUTAS ACTIVAS:\n")
                            for sub in f_info["subroutes"]:
                                f.write(f"  - {sub}\n")
                            f.write("\n")
                    
                    # Clientes rechazados
                    items = descartados_por_planta.get(plant, [])
                    if items:
                        f.write("PEDIDOS RECHAZADOS EN ESTA PLANTA:\n")
                        for info in items:
                            f.write(f"  RECHAZADO: {info['name']}\n")
                            f.write(f"     - Carga: {info['pallets']} pallets\n")
                            f.write(f"     - Diagnostico: {info['motivo']}\n\n")
                    else:
                        f.write("  EXITO: Todos los pedidos de esta planta han sido enrutados.\n\n")

            f.write("="*80 + "\n")
            
        logger.info(f"DropLogger ha generado el reporte avanzado (sin emojis) en: {self.log_path}")
        return str(self.log_path)
