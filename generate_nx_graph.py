import json
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
DATA_FILE = Path("outputs/results/optimized_routes.json")
OUTPUT_FILE = Path("outputs/results/Logistics_Graph_Static.png")

def generate_static_graph():
    if not DATA_FILE.exists():
        print(f"❌ Error: No se encontró {DATA_FILE}. Ejecuta main.py primero.")
        return

    print("Cargando rutas optimizadas...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        routes = json.load(f)

    G = nx.DiGraph()

    # Recopilar todos los nodos y sus atributos
    unique_nodes = {}
    for route in routes:
        for node in route:
            unique_nodes[node['id']] = node
            G.add_node(node['id'], name=node['name'], type=node['type'])

    # Añadir aristas
    for route in routes:
        for j in range(len(route) - 1):
            G.add_edge(route[j]['id'], route[j+1]['id'])

    # Generar layout compacto
    pos = nx.spring_layout(G, k=0.15, iterations=150, seed=42)

    # Preparar listas de estilos
    node_colors = []
    node_sizes = []
    labels = {}

    for node_id in G.nodes():
        n_data = unique_nodes[node_id]
        
        # Limpieza de textos (Romper en dos lineas si es necesario)
        words = n_data['name'].replace('Smurfit Westrock ', '').split()
        short_name = "\n".join(words[:2]) if len(words) > 1 else words[0] if words else ""
        labels[node_id] = short_name

        # Asignación de colores fieles a la imagen de referencia
        if n_data['type'] == 'depot':
            node_colors.append('#ff7f0e')   # Naranja (Origen)
            node_sizes.append(5000)
        elif n_data['type'] == 'carton_plant':
            node_colors.append('#1f77b4')   # Azul (Plantas)
            node_sizes.append(2800)
        else:
            node_colors.append('#cccccc')   # Gris Claro (Clientes)
            node_sizes.append(1000)

    # Inicializar el lienzo de Matplotlib
    plt.figure(figsize=(14, 14), facecolor='white')
    plt.axis('off') # Quitar cuadrícula y ejes
    
    # 1. Trazar líneas grises en el fondo
    nx.draw_networkx_edges(
        G, pos, 
        alpha=0.6, width=1.0, edge_color='#666666', arrows=False
    )

    # 2. Trazar esferas (nodos) con bordes grises/negros
    nx.draw_networkx_nodes(
        G, pos, 
        node_size=node_sizes, node_color=node_colors, 
        edgecolors='#333333', linewidths=1.5, alpha=1.0
    )

    # 3. Trazar etiquetas de texto justo en el centro
    nx.draw_networkx_labels(
        G, pos, 
        labels=labels, font_size=9, font_family='sans-serif', font_weight='bold', font_color='black'
    )

    # Exportar el resultado a imagen pura
    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✅ Grafo estático generado 100% con NetworkX de forma exitosa.")
    print(f"📊 La imagen la puedes encontrar en: {OUTPUT_FILE.absolute()}")

if __name__ == "__main__":
    generate_static_graph()
