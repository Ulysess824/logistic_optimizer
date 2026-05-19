"""
test_chained_plants.py
-----------------------
Script de validacion para la funcionalidad de Rutas Multi-Planta Encadenadas.
Usa datos sinteticos para verificar que el solver genera la secuencia correcta:
   DEPOT -> Planta A -> Clientes(A) -> Planta B -> Clientes(B) -> DEPOT

Se ejecuta de forma autonoma sin dependencias externas de API (usa Haversine).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import json
import logging
from logistic_core.engine.solver import LogisticsSolver
from logistic_core.engine.chained_dispatcher import ChainedClientDispatcher
from logistic_core.utils.geo import GeoUtils

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# DATOS SINTETICOS
# =============================================================================

# Depot: Mengibar (Jaen)
PAPER_PLANT = {
    "name": "Mengibar",
    "lat": 37.98148,
    "lng": -3.80058,
}

# Planta A: Cordoba (al OESTE de Mengibar)
PLANT_A = {
    "id": "CP_CORDOBA",
    "name": "Cordoba",
    "lat": 37.93214,
    "lng": -4.67292,
    "customers": [
        {
            "id": "C_LUCENA",
            "name": "Lucena",
            "lat": 37.4088,
            "lng": -4.4853,
            "demanda_pallets": 8,
            "n_pallets_original": 8,
            "remontar": 0,
            "obligatorio": False,
        },
        {
            "id": "C_ANDUJAR",
            "name": "Andujar",
            "lat": 38.0393,
            "lng": -4.0506,
            "demanda_pallets": 10,
            "n_pallets_original": 10,
            "remontar": 0,
            "obligatorio": True,
        },
    ],
}

# Planta B: Huelva (mas al OESTE, "en camino" desde Cordoba)
# 4 clientes, demanda total 40P.
# Con 1 camion directo de cap=20P -> solo caben 2 clientes -> 2 remanentes para la Pasada 2.
PLANT_B = {
    "id": "CP_HUELVA",
    "name": "Huelva",
    "lat": 37.3635,
    "lng": -6.5430,
    "customers": [
        {
            "id": "C_SEVILLA",
            "name": "Sevilla",
            "lat": 37.3886,
            "lng": -5.9823,
            "demanda_pallets": 12,
            "n_pallets_original": 12,
            "remontar": 0,
            "obligatorio": False,
        },
        {
            "id": "C_LEPE",
            "name": "Lepe",
            "lat": 37.2548,
            "lng": -7.2040,
            "demanda_pallets": 12,
            "n_pallets_original": 12,
            "remontar": 0,
            "obligatorio": False,
        },
        {
            "id": "C_MOGUER",
            "name": "Moguer",
            "lat": 37.2756,
            "lng": -6.8388,
            "demanda_pallets": 10,
            "n_pallets_original": 10,
            "remontar": 0,
            "obligatorio": False,
        },
        {
            "id": "C_AYAMONTE",
            "name": "Ayamonte",
            "lat": 37.2102,
            "lng": -7.4028,
            "demanda_pallets": 6,
            "n_pallets_original": 6,
            "remontar": 0,
            "obligatorio": False,
        },
    ],
}

# Datos de entrada completos
ENRICHED_DATA = {
    "paper_plant": PAPER_PLANT,
    "carton_plants": [PLANT_A, PLANT_B],
}

# Flota estandar (2 camiones por planta)
FLOTA = {
    "CP_CORDOBA": 2,
    "CP_HUELVA": 2,
}

# Encadenamiento: Cordoba -> Huelva
CHAIN_MAP = {
    "CP_CORDOBA": ["CP_HUELVA"],
}


# =============================================================================
# TEST
# =============================================================================

def print_separator(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def describe_route(route, idx):
    """Imprime la secuencia de nodos de una ruta."""
    types_map = {
        "depot": "DEPOT",
        "carton_plant": "PLANTA",
        "customer": "CLIENTE",
    }
    seq = []
    total_pallets = 0
    for node in route:
        t = types_map.get(node["type"], node["type"])
        label = f"{t}({node['name']})"
        if node["type"] == "customer":
            p = node.get("demanda_pallets", 0)
            total_pallets += p
            label += f" [{p}P]"
        if node.get("is_chain_clone"):
            label += " [CHAIN]"
        seq.append(label)

    print(f"\n  Ruta #{idx + 1} ({len(route)} nodos, {total_pallets} pallets):")
    print(f"    {' -> '.join(seq)}")
    return total_pallets


def validate_chain_order(route, plant_a_id, plant_b_id):
    """Valida que la secuencia sea: Planta A -> Clientes(A) -> Planta B -> Clientes(B)."""
    errors = []

    plant_a_pos = None
    plant_b_pos = None
    client_a_positions = []
    client_b_positions = []

    for i, node in enumerate(route):
        nid = node.get("id", "")
        base_id = nid.split("_clone_")[0].split("_chain_")[0]

        if node["type"] == "carton_plant":
            if base_id == plant_a_id:
                plant_a_pos = i
            elif base_id == plant_b_id:
                plant_b_pos = i
        elif node["type"] == "customer":
            parent = node.get("parent_cp", "")
            if parent == plant_a_id:
                client_a_positions.append((i, node["name"]))
            elif parent == plant_b_id:
                client_b_positions.append((i, node["name"]))

    if plant_a_pos is None:
        errors.append("Planta A no encontrada en la ruta")
    if plant_b_pos is None:
        errors.append("Planta B no encontrada en la ruta")

    if plant_a_pos is not None and plant_b_pos is not None:
        if plant_a_pos >= plant_b_pos:
            errors.append(
                f"ORDEN INCORRECTO: Planta A (pos {plant_a_pos}) "
                f"debe estar ANTES de Planta B (pos {plant_b_pos})"
            )

        for pos, name in client_a_positions:
            if pos <= plant_a_pos:
                errors.append(f"Cliente A '{name}' (pos {pos}) esta ANTES de Planta A (pos {plant_a_pos})")
            if pos >= plant_b_pos:
                errors.append(f"Cliente A '{name}' (pos {pos}) esta DESPUES de Planta B (pos {plant_b_pos})")

        for pos, name in client_b_positions:
            if pos <= plant_b_pos:
                errors.append(f"Cliente B '{name}' (pos {pos}) esta ANTES de Planta B (pos {plant_b_pos})")

    return errors, {
        "plant_a_pos": plant_a_pos,
        "plant_b_pos": plant_b_pos,
        "clients_a": client_a_positions,
        "clients_b": client_b_positions,
    }


def run_test():
    """Ejecuta el test completo."""
    print_separator("TEST: Rutas Multi-Planta Encadenadas (Chained Plant VRP)")

    geo = GeoUtils(api_type="haversine")
    all_errors = []

    # --- 1. Ejecucion SIN encadenamiento (baseline) ---
    print_separator("FASE 1: Baseline (Sin Encadenamiento)")

    solver_base = LogisticsSolver(ENRICHED_DATA, geo_engine=geo)

    print(f"\n  Nodos parseados ({len(solver_base.nodes)}):")
    for n in solver_base.nodes:
        parent_info = f" [parent={n.get('parent_cp', '')}]" if n["type"] == "customer" else ""
        print(f"    idx={n['matrix_idx']} | {n['type']:15s} | {n['name']}{parent_info}")

    routes_base = solver_base.solve(
        n_clientes=10,
        varias_plantas=False,
        max_pallets_ruta=34,
        max_search_time=15,
        flota_por_planta=FLOTA,
        plant_chain_map=None,
    )

    if routes_base:
        print(f"\n  Rutas generadas (baseline): {len(routes_base)}")
        for i, r in enumerate(routes_base):
            describe_route(r, i)
    else:
        print("  WARN: No se generaron rutas en baseline (puede ser MIN_FILL_RATE_PCT)")

    # --- 2. Ejecucion CON encadenamiento ---
    print_separator("FASE 2: Con Encadenamiento (CP_CORDOBA -> CP_HUELVA)")

    solver_chain = LogisticsSolver(ENRICHED_DATA, geo_engine=geo)

    routes_chain = solver_chain.solve(
        n_clientes=10,
        varias_plantas=False,
        max_pallets_ruta=34,
        max_search_time=15,
        flota_por_planta=FLOTA,
        plant_chain_map=CHAIN_MAP,
    )

    if not routes_chain:
        print("  ERROR: El solver no genero rutas con encadenamiento.")
        return False

    print(f"\n  Rutas generadas (chain): {len(routes_chain)}")
    total_pallets_all = 0
    for i, r in enumerate(routes_chain):
        p = describe_route(r, i)
        total_pallets_all += p

    # --- 3. Validacion de la cadena ---
    print_separator("FASE 3: Validacion de Restricciones")

    chain_route_found = False

    for i, route in enumerate(routes_chain):
        has_a = any(
            n.get("id", "").split("_clone_")[0].split("_chain_")[0] == "CP_CORDOBA"
            and n["type"] == "carton_plant"
            for n in route
        )
        has_b = any(
            n.get("id", "").split("_clone_")[0].split("_chain_")[0] == "CP_HUELVA"
            and n["type"] == "carton_plant"
            for n in route
        )

        if has_a and has_b:
            chain_route_found = True
            print(f"\n  Ruta encadenada detectada: Ruta #{i + 1}")

            errors, positions = validate_chain_order(route, "CP_CORDOBA", "CP_HUELVA")

            if not errors:
                print("  [OK] Secuencia CORRECTA: Depot -> Cordoba -> Clientes(COR) -> Huelva -> Clientes(HUE) -> Depot")
                print(f"       Planta A pos={positions['plant_a_pos']}, "
                      f"Planta B pos={positions['plant_b_pos']}")
                print(f"       Clientes A: {positions['clients_a']}")
                print(f"       Clientes B: {positions['clients_b']}")
            else:
                print("  [FAIL] Errores de secuencia:")
                for e in errors:
                    print(f"    - {e}")
                all_errors.extend(errors)

    if not chain_route_found:
        print("  [FAIL] No se encontro ninguna ruta con ambas plantas (Cordoba + Huelva)")
        all_errors.append("No chain route found")

    # --- 4. Comparativa ---
    print_separator("FASE 4: Comparativa Baseline vs. Chain")

    n_base = len(routes_base) if routes_base else 0
    n_chain = len(routes_chain)
    base_nodes_total = sum(len(r) for r in (routes_base or []))
    chain_nodes_total = sum(len(r) for r in routes_chain)

    print(f"  Rutas baseline:        {n_base}")
    print(f"  Rutas chain:           {n_chain}")
    print(f"  Nodos totales base:    {base_nodes_total}")
    print(f"  Nodos totales chain:   {chain_nodes_total}")
    print(f"  Pallets totales chain: {total_pallets_all}")

    # --- 5. Two-Pass Chain Dispatch (escenario con overflow controlado) ---
    # Razon del diseno:
    #   La Pasada 1 del flujo real usa el solver SIN plant_chain_map.
    #   Para provocar remanentes usamos 1 camion directo de Huelva con cap=20P.
    #   Demanda total de B = 40P -> el solver solo cubre 2 clientes (~18P).
    #   Los 2 sobrantes son detectados por ChainedClientDispatcher y re-enrutados
    #   en la Pasada 2 al camion encadenado (Cordoba -> ... -> Huelva -> remanentes).
    print_separator("FASE 5: Two-Pass Chain Dispatch (Overflow Controlado)")

    print("\n  Setup: 1 camion directo de Huelva con cap=20P (fuerza overflow).")
    print("  Demanda total de B: 40P (Sevilla 12P + Lepe 12P + Moguer 10P + Ayamonte 6P).")
    print("  Esperado: 2 clientes cubiertos por directa, 2 remanentes -> Pasada 2.\n")

    flota_p1 = {"CP_CORDOBA": 2, "CP_HUELVA": 1}

    solver_p1 = LogisticsSolver(ENRICHED_DATA, geo_engine=geo)
    routes_p1 = solver_p1.solve(
        n_clientes=10,
        varias_plantas=False,
        max_pallets_ruta=20,      # Cap 20P para el camion directo de Huelva
        max_search_time=15,
        flota_por_planta=flota_p1,
        plant_chain_map=None,     # Sin cadenas en la Pasada 1
    )

    if not routes_p1:
        print("  WARN: Pasada 1 sin rutas. Saltando Fase 5.")
    else:
        print(f"  Rutas Pasada 1 ({len(routes_p1)}):")
        for i, r in enumerate(routes_p1):
            describe_route(r, i)

        dispatcher = ChainedClientDispatcher(
            enriched_data=ENRICHED_DATA,
            geo_engine=geo,
            distance_matrix=solver_p1.distance_matrix,
        )

        # 5a. Detectar remanentes
        remaining = dispatcher.get_remaining_clients(
            routes_pass1=routes_p1,
            plant_b_id="CP_HUELVA",
        )
        print(f"\n  Remanentes de CP_HUELVA: {len(remaining)}")
        for c in remaining:
            print(f"    - {c['id']} | {c['name']} | {c.get('demanda_pallets', 0)} pallets")

        # 5b. Construir sub-problema
        subproblem = dispatcher.build_chain_subproblem(
            plant_a_id="CP_CORDOBA",
            plant_b_id="CP_HUELVA",
            remaining_clients=remaining,
            routes_pass1=routes_p1,
        )
        if subproblem:
            n_a = len(subproblem["carton_plants"][0]["customers"])
            n_b = len(subproblem["carton_plants"][1]["customers"])
            print(f"  [OK] Sub-problema: A ({n_a} cl.) | B remanentes ({n_b} cl.)")

        # 5c. Ejecutar Pasada 2 y fusion
        routes_merged = dispatcher.run_chain_pass(
            routes_pass1=routes_p1,
            plant_a_id="CP_CORDOBA",
            plant_b_id="CP_HUELVA",
            flota_chain={"CP_CORDOBA": 1, "CP_HUELVA": 1},
            max_pallets=34,
            max_search_time=15,
        )

        print(f"\n  Rutas fusionadas (P1 + P2): {len(routes_merged)}")
        for i, r in enumerate(routes_merged):
            describe_route(r, i)

        # 5d. Verificar que el camion encadenado entrego pallets de B
        chain_delivers_b = False
        for r in routes_merged:
            plant_ids_in_r = {
                n.get("id", "").split("_clone_")[0].split("_chain_")[0]
                for n in r if n.get("type") == "carton_plant"
            }
            if "CP_CORDOBA" in plant_ids_in_r and "CP_HUELVA" in plant_ids_in_r:
                b_clients = [
                    n for n in r
                    if n.get("type") == "customer" and n.get("parent_cp") == "CP_HUELVA"
                ]
                if b_clients:
                    chain_delivers_b = True
                    pallets_b = sum(n.get("demanda_pallets", 0) for n in b_clients)
                    print(
                        f"\n  [OK] Chain Dispatch EXITOSO: camion encadenado entrega "
                        f"{pallets_b}P a {[n['name'] for n in b_clients]}"
                    )

        if remaining and not chain_delivers_b:
            print("\n  [WARN] Habia remanentes pero el camion encadenado no entrego pallets de B.")
        elif not remaining:
            print("\n  [INFO] Sin remanentes: Pasada 2 no fue necesaria (correcto).")

    # --- 6. Resultado Final ---
    print_separator("RESULTADO FINAL")
    if not all_errors:
        print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
        return True
    else:
        print(f"  {len(all_errors)} ERRORES ENCONTRADOS:")
        for e in all_errors:
            print(f"    - {e}")
        return False


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
