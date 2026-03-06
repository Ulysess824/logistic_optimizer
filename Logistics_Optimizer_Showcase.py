# ======================================================================
# 🔧 PARÁMETROS — Modifica estos valores para experimentar
# ======================================================================
N_CLIENTES = 4              # Máximo de clientes por ruta
VARIAS_PLANTAS = False      # True → multi-planta (MC-VRPB)
MAX_PLANTAS_RUTA = 2        # Plantas máximas por ruta (si varias_plantas=True)
MAX_CUSTOMERS_PER_PLANT = 4 # Pre-selección de clientes por planta (DataManager)
THRESHOLD_KM = 100          # Umbral de desvío para filtro de retorno (km)
# ======================================================================

import json
import sys
import numpy as np
from pathlib import Path

ROOT = Path('.').resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR, RESULTS_DIR
from src.utils.data_manager import DataManager
from src.utils.geo import GeoUtils

plants_file = DATA_DIR / 'locations_smurfit.json'
clients_file = DATA_DIR / 'cliente_ubi.json'

with open(plants_file, 'r', encoding='utf-8') as f:
    plants_data = json.load(f)

print(f"🏛️ Fábrica de Papel: {plants_data['paper_plant']['name']}")
print(f"   Ubicación: ({plants_data['paper_plant']['lat']}, {plants_data['paper_plant']['lng']})")
print(f"\n🏭 Plantas de Cartón: {len(plants_data['carton_plants'])}")
for p in plants_data['carton_plants']:
    print(f"   • {p['name']} ({p['id']})")

dm = DataManager(
    paper_plant=plants_data['paper_plant'],
    carton_plants=plants_data['carton_plants'],
    clients_file=clients_file
)

enriched_data = dm.get_optimized_locations(
    max_customers_per_plant=MAX_CUSTOMERS_PER_PLANT,
    threshold_km=THRESHOLD_KM
)

print("\n📊 Resultado del Filtro de Retorno:")
print("-" * 50)
total_customers = 0
for plant in enriched_data['carton_plants']:
    n_cust = len(plant.get('customers', []))
    total_customers += n_cust
    print(f"  {plant['name']}: {n_cust} clientes seleccionados")
    for c in plant.get('customers', []):
        print(f"    └─ {c['name']} (desvío: {c['detour']:.2f} km)")
print(f"\n  Total: {total_customers} clientes en {len(enriched_data['carton_plants'])} plantas")

from src.engine.solver import LogisticsSolver

solver = LogisticsSolver(enriched_data)

print(f"Motor de distancias: {'GPS Real' if solver.is_real_road else 'Haversine (línea recta)'}")
print(f"Nodos totales: {len(solver.nodes)}")
print(f"Tamaño de la matriz: {solver.distance_matrix.shape}")
print(f"\n📋 Parámetros del solver:")
print(f"   n_clientes={N_CLIENTES}  |  varias_plantas={VARIAS_PLANTAS}  |  max_plantas_ruta={MAX_PLANTAS_RUTA}")

# Ejecutar optimización con los parámetros configurados
routes = solver.solve(
    n_clientes=N_CLIENTES,
    varias_plantas=VARIAS_PLANTAS,
    max_plantas_ruta=MAX_PLANTAS_RUTA,
)

if routes:
    print(f"\n✅ Éxito: {len(routes)} rutas optimizadas encontradas.")
else:
    print("\n❌ No se encontró solución.")

if routes:
    total_km = 0
    results_table = []
    
    for i, route in enumerate(routes):
        dist_km = sum(
            solver.distance_matrix[n1['matrix_idx']][n2['matrix_idx']]
            for n1, n2 in zip(route, route[1:])
        ) / 1000
        total_km += dist_km
        
        plants = [n for n in route if n['type'] == 'carton_plant']
        customers = [n for n in route if n['type'] == 'customer']
        
        plants_str = ' + '.join(p['name'].replace('Smurfit Westrock ', '') for p in plants)
        
        print(f"\n{'='*60}")
        print(f"🚛 RUTA {i+1}: {plants_str}")
        if len(plants) > 1:
            print(f"   ⚡ Multi-planta: {len(plants)} plantas en esta ruta")
        print(f"{'='*60}")
        
        for j in range(len(route) - 1):
            n1, n2 = route[j], route[j+1]
            tramo_km = solver.distance_matrix[n1['matrix_idx']][n2['matrix_idx']] / 1000
            icon = {'depot': '📦', 'carton_plant': '🏭', 'customer': '🏪'}[n1['type']]
            print(f"  {icon} {n1['name']} → {n2['name']}  ({tramo_km:.1f} km)")
        
        print(f"  ▸ Plantas visitadas: {len(plants)}")
        print(f"  ▸ Clientes atendidos: {len(customers)}")
        print(f"  ▸ Distancia total: {dist_km:.2f} km")
        
        results_table.append({
            'route_id': i + 1,
            'plants': [p['name'] for p in plants],
            'plant_ids': [p['id'] for p in plants],
            'num_plants': len(plants),
            'num_customers': len(customers),
            'customers': [c['name'] for c in customers],
            'distance_km': round(dist_km, 2),
            'num_stops': len(route)
        })
    
    print(f"\n{'━'*60}")
    print(f"🏁 TOTAL: {total_km:.2f} km en {len(routes)} rutas")
    print(f"{'━'*60}")

if routes:
    routes_path = RESULTS_DIR / 'optimized_routes.json'
    with open(routes_path, 'w', encoding='utf-8') as f:
        json.dump(routes, f, indent=2, ensure_ascii=False)
    print(f"✅ Rutas detalladas: {routes_path}")
    
    summary = {
        'num_routes': len(routes),
        'total_km': round(total_km, 2),
        'distance_source': 'GPS Real' if solver.is_real_road else 'Haversine (estimación)',
        'parameters': {
            'n_clientes': N_CLIENTES,
            'varias_plantas': VARIAS_PLANTAS,
            'max_plantas_ruta': MAX_PLANTAS_RUTA,
        },
        'routes': results_table
    }
    
    summary_path = RESULTS_DIR / 'optimization_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"✅ Resumen KPIs: {summary_path}")
    
    print(f"\n📄 Preview del resumen:")
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:2000])

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

if routes:
    G = nx.DiGraph()
    unique_nodes = {}
    
    for route in routes:
        for node in route:
            unique_nodes[node['id']] = node
            G.add_node(node['id'], name=node['name'], type=node['type'])
    
    for route in routes:
        for j in range(len(route) - 1):
            start, end = route[j], route[j+1]
            dist_km = solver.distance_matrix[start['matrix_idx']][end['matrix_idx']] / 1000
            G.add_edge(start['id'], end['id'], weight=round(dist_km, 1))
    
    print(f"Grafo: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")

if routes:
    node_colors = []
    node_sizes = []
    labels = {}
    
    for node_id in G.nodes():
        n_data = unique_nodes[node_id]
        words = n_data['name'].replace('Smurfit Westrock ', '').split()
        short_name = '\n'.join(words[:2]) if len(words) > 1 else words[0] if words else ''
        labels[node_id] = short_name
        
        # Tamaños de nodos más pequeños
        if n_data['type'] == 'depot':
            node_colors.append('#ff7f0e'); node_sizes.append(800)
        elif n_data['type'] == 'carton_plant':
            node_colors.append('#1f77b4'); node_sizes.append(400)
        else:
            node_colors.append('#cccccc'); node_sizes.append(100)
    
    # Canvas más ajustado (menos espacio en blanco sobrante)
    fig, ax = plt.subplots(1, 1, figsize=(16, 12), facecolor='white')
    pos = {n: (unique_nodes[n]['lng'], unique_nodes[n]['lat']) for n in G.nodes()}
    
    # Manteniendo las curvas (connectionstyle='arc3,rad=0.1') que generan los círculos
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.5, width=1.5, edge_color='#666666',
        arrows=True, arrowsize=15, arrowstyle='->', connectionstyle='arc3,rad=0.1')
    
    edge_labels = {k: f'{v} km' for k, v in nx.get_edge_attributes(G, 'weight').items()}
    
    # Letras del kilometraje más grandes
    nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels,
        font_size=9, font_color='#444444', alpha=0.8)
    
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
        edgecolors='#333333', linewidths=1.5, alpha=1.0)
        
    # Etiquetas de los nombres más grandes
    nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=11,
        font_family='sans-serif', font_weight='bold', font_color='black', verticalalignment='center')
    
    legend_handles = [
        mpatches.Patch(facecolor='#ff7f0e', edgecolor='#333', label='Depósito (Mengíbar)'),
        mpatches.Patch(facecolor='#1f77b4', edgecolor='#333', label='Planta de Cartón'),
        mpatches.Patch(facecolor='#cccccc', edgecolor='#333', label='Cliente'),
    ]
    
    # Leyenda grande
    ax.legend(handles=legend_handles, loc='upper left', fontsize=16,
              framealpha=0.9, fancybox=True, shadow=True)
    
    mode_str = 'MC-VRPB (Multi-Planta)' if VARIAS_PLANTAS else 'VRPB (Clásico)'
    
    # Título enorme
    ax.set_title(f'Red Logística — {mode_str}\nn_clientes={N_CLIENTES} | max_plantas_ruta={MAX_PLANTAS_RUTA}',
                fontsize=22, fontweight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    
    graph_img_path = RESULTS_DIR / 'Logistics_Graph_NetworkX.png'
    fig.savefig(graph_img_path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f'📊 Grafo guardado en: {graph_img_path}')
    plt.show()


if routes:
    n_routes = len(routes)
    cols = min(3, n_routes)
    rows = (n_routes + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(10 * cols, 10 * rows), facecolor='white')
    if n_routes == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    route_colors_list = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                         '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for i, route in enumerate(routes):
        ax = axes[i]
        Gi = nx.DiGraph()
        
        for node in route:
            Gi.add_node(node['id'], name=node['name'], type=node['type'])
        for j in range(len(route) - 1):
            s, e = route[j], route[j+1]
            d = solver.distance_matrix[s['matrix_idx']][e['matrix_idx']] / 1000
            Gi.add_edge(s['id'], e['id'], weight=round(d, 1))
        
        pos_i = {n: (unique_nodes[n]['lng'], unique_nodes[n]['lat']) for n in Gi.nodes()}
        
        colors_i, sizes_i, labels_i = [], [], {}
        for nid in Gi.nodes():
            nd = unique_nodes[nid]
            w = nd['name'].replace('Smurfit Westrock ', '').split()
            labels_i[nid] = '\n'.join(w[:2]) if len(w) > 1 else w[0] if w else ''
            if nd['type'] == 'depot':
                colors_i.append('#ff7f0e'); sizes_i.append(800)
            elif nd['type'] == 'carton_plant':
                colors_i.append('#1f77b4'); sizes_i.append(500)
            else:
                colors_i.append('#cccccc'); sizes_i.append(200)
        
        nx.draw_networkx_edges(Gi, pos_i, ax=ax, alpha=0.6, width=1.5,
            edge_color=route_colors_list[i % len(route_colors_list)],
            arrows=True, arrowsize=12)
        nx.draw_networkx_nodes(Gi, pos_i, ax=ax, node_size=sizes_i,
            node_color=colors_i, edgecolors='#333', linewidths=1)
        nx.draw_networkx_labels(Gi, pos_i, ax=ax, labels=labels_i,
            font_size=7, font_weight='bold')
        edge_labels_i = {k: f'{v} km' for k, v in nx.get_edge_attributes(Gi, 'weight').items()}
        nx.draw_networkx_edge_labels(Gi, pos_i, ax=ax, edge_labels=edge_labels_i,
            font_size=5, font_color='#777')
        
        plants_i = [n for n in route if n['type'] == 'carton_plant']
        title_plants = ' + '.join(p['name'].replace('Smurfit Westrock ', '') for p in plants_i)
        dist_i = sum(solver.distance_matrix[a['matrix_idx']][b['matrix_idx']]
                     for a, b in zip(route, route[1:])) / 1000
        multi_tag = ' 🔄' if len(plants_i) > 1 else ''
        ax.set_title(f'Ruta {i+1}: {title_plants}{multi_tag}\n({dist_i:.1f} km)',
                     fontsize=11, fontweight='bold')
        ax.axis('off')
    
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    
    fig.suptitle('Desglose por Ruta — Red Logística', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    routes_img_path = RESULTS_DIR / 'Routes_Breakdown_NetworkX.png'
    fig.savefig(routes_img_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f'📊 Desglose por ruta: {routes_img_path}')
    plt.show()

if routes:
    mode_label = 'MC-VRPB (Multi-Planta)' if VARIAS_PLANTAS else 'VRPB (Clásico)'
    
    print('╔' + '═' * 58 + '╗')
    print('║' + f'  📊 KPIs — {mode_label}'.center(58) + '║')
    print('╠' + '═' * 58 + '╣')
    print(f'║  🚛 Rutas generadas:         {len(routes):>3}' + ' ' * 22 + '║')
    print(f'║  📍 Nodos optimizados:       {len(solver.nodes):>3}' + ' ' * 22 + '║')
    print(f'║  🏭 Plantas de cartón:       {sum(1 for n in solver.nodes if n["type"]=="carton_plant"):>3}' + ' ' * 22 + '║')
    print(f'║  🏪 Clientes atendidos:      {sum(1 for n in solver.nodes if n["type"]=="customer"):>3}' + ' ' * 22 + '║')
    print(f'║  🏁 Kilómetros totales:   {total_km:>8.2f} km' + ' ' * 14 + '║')
    print(f'║  📡 Fuente de distancias:    {"GPS Real" if solver.is_real_road else "Haversine":>12}' + ' ' * 12 + '║')
    print('╠' + '─' * 58 + '╣')
    print('║' + '  Parámetros:'.ljust(58) + '║')
    print(f'║    n_clientes={N_CLIENTES}  varias_plantas={VARIAS_PLANTAS}  max_plantas={MAX_PLANTAS_RUTA}'.ljust(59) + '║')
    print('╠' + '─' * 58 + '╣')
    print('║' + '  Detalle por ruta:'.ljust(58) + '║')
    print('╠' + '─' * 58 + '╣')
    
    for r in results_table:
        plants_short = ' + '.join(p.replace('Smurfit Westrock ', '') for p in r['plants'])
        multi = '🔄' if r['num_plants'] > 1 else '  '
        line = f"  R{r['route_id']}: {plants_short:<25} {r['num_customers']}c {r['distance_km']:>7.1f}km {multi}"
        print(f'║{line:<58}║')
    
    print('╚' + '═' * 58 + '╝')
    
    total_cust = sum(r['num_customers'] for r in results_table)
    if total_cust > 0:
        print(f'\n⚡ Eficiencia: {total_km / total_cust:.1f} km/cliente')
    print(f'📁 Archivos: {RESULTS_DIR}')
