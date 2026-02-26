import folium
from folium import plugins
import plotly.graph_objects as go
import pandas as pd
import polyline
import networkx as nx
from src.config import MAPS_DIR, RESULTS_DIR
from src.utils.geo import GeoUtils
import os
import json

class Visualizer:
    def __init__(self, routes, distance_matrix):
        self.routes = routes
        self.distance_matrix = distance_matrix
        self.geo = GeoUtils()
        # Colores optimizados (Alta visibilidad)
        self.route_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]

    def _generate_sidebar_html(self):
        """Genera el código HTML para la tabla lateral interactiva de rutas."""
        table_rows = ""
        total_km = 0
        
        for i, route in enumerate(self.routes):
            color = self.route_colors[i % len(self.route_colors)]
            route_dist = 0
            detail_html = "<ul style='padding-left: 15px; font-size: 11px; margin: 5px 0; color: #444; list-style-type: none;'>"
            
            for j in range(len(route) - 1):
                start, end = route[j], route[j+1]
                dist_m = self.distance_matrix[start['matrix_idx']][end['matrix_idx']]
                dist_km = dist_m / 1000
                route_dist += dist_km
                
                # Definir iconos según tipo
                s_icon = "🏢" if start['type'] == 'depot' else "🏭" if start['type'] == 'carton_plant' else "🏪"
                e_icon = "🏢" if end['type'] == 'depot' else "🏭" if end['type'] == 'carton_plant' else "🏪"
                
                detail_html += f"<li>{s_icon} {start['name']} <span style='color:{color}'>→</span> {e_icon} {end['name']} <b style='float:right'>{dist_km:.1f} km</b></li>"
            
            detail_html += "</ul>"
            total_km += route_dist
            
            table_rows += f"""
            <tr onclick="toggleRoute({i})" style="cursor: pointer; border-bottom: 1px solid #ddd; background-color: {color}11;">
                <td style="padding: 10px; font-weight: bold; color: {color};">#{i+1}</td>
                <td style="padding: 10px;">{route[1]['name']}</td>
                <td style="padding: 10px; text-align: right;">{route_dist:.1f} km</td>
            </tr>
            <tr id="detail-{i}" style="display: none; background-color: #f9f9f9;">
                <td colspan="3" style="padding: 0 10px 10px 10px;">
                    {detail_html}
                </td>
            </tr>
            """

        html = f"""
        <div id="sidebar" style="
            position: fixed; top: 10px; right: 10px; width: 380px; height: 95%;
            background-color: rgba(255, 255, 255, 0.98); z-index: 1000;
            border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            padding: 20px; overflow-y: auto; font-family: 'Segoe UI', Roboto, sans-serif;
            border: 1px solid #e0e0e0;">
            
            <h2 style="color: #2c3e50; text-align: center; margin-top: 0; padding-bottom: 15px; border-bottom: 3px solid #3498db;">
                📦 Logística Estratégica
            </h2>
            
            <div id="stats-summary" style="margin: 20px 0; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 15px; border-radius: 10px; border-left: 5px solid #3498db;">
                <p style="margin: 5px 0;"><strong>🗺️ Rutas Activas:</strong> {len(self.routes)}</p>
                <p style="margin: 5px 0;"><strong>🏁 Kilómetros Totales:</strong> <span style="font-size: 1.2em; color: #2c3e50;">{total_km:.2f}</span> km</p>
                <p style="margin: 5px 0; font-size: 0.9em; color: #666;">📍 Base: Mengíbar (Papel)</p>
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #34495e; color: white; text-align: left;">
                        <th style="padding: 12px 10px;">#</th>
                        <th style="padding: 12px 10px;">Destino Principal</th>
                        <th style="padding: 12px 10px; text-align: right;">Distancia</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            
            <script>
                function toggleRoute(id) {{
                    var el = document.getElementById('detail-' + id);
                    if (el.style.display === 'none') {{
                        el.style.display = 'table-row';
                    }} else {{
                        el.style.display = 'none';
                    }}
                }}
            </script>
            
            <div style="margin-top: 30px; font-size: 11px; color: #95a5a6; text-align: center; font-style: italic;">
                Haz clic en una ruta para ver el desglose punto a punto.
            </div>
        </div>
        """
        return html

    def create_map(self, filename="Logistics_Dashboard.html"):
        m = folium.Map(location=[40.4167, -3.7037], zoom_start=6, tiles="cartodbpositron")
        sidebar_html = self._generate_sidebar_html()
        m.get_root().html.add_child(folium.Element(sidebar_html))

        for i, route in enumerate(self.routes):
            color = self.route_colors[i % len(self.route_colors)]
            
            for j in range(len(route) - 1):
                start, end = route[j], route[j+1]
                encoded_poly = self.geo.get_route_polyline((start['lat'], start['lng']), (end['lat'], end['lng']))
                
                if encoded_poly and encoded_poly != "BILLING_ERROR":
                    decoded_points = polyline.decode(encoded_poly)
                    folium.PolyLine(decoded_points, color=color, weight=4, opacity=0.8, 
                                   tooltip=f"{start['name']} → {end['name']}").add_to(m)
                else:
                    folium.PolyLine([[start['lat'], start['lng']], [end['lat'], end['lng']]], 
                                   color=color, weight=4, opacity=0.8, dash_array='5, 10',
                                   tooltip=f"{start['name']} → {end['name']} (Directo)").add_to(m)

            for step, node in enumerate(route):
                icon_type = "info-sign"
                icon_color = "blue"
                popup_text = f"<b>{node['name']}</b>"
                
                if node['type'] == 'depot':
                    icon_type = "home"; icon_color = "red"
                    popup_text = f"🏛️ <b>DEPÓSITO PAPEL:</b> {node['name']}"
                elif node['type'] == 'carton_plant':
                    icon_type = "industry"; icon_color = "green"
                    popup_text = f"🏭 <b>PLANTA CARTÓN:</b> {node['name']}"
                elif node['type'] == 'customer':
                    icon_type = "shopping-cart"; icon_color = "orange"
                    popup_text = f"🏪 <b>CLIENTE:</b> {node['name']}"

                folium.Marker(
                    location=[node['lat'], node['lng']],
                    popup=popup_text,
                    icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa' if node['type'] == 'carton_plant' else 'glyphicon')
                ).add_to(m)

        output_path = MAPS_DIR / filename
        m.save(output_path)
        return output_path

    def create_plotly_graph(self, filename="Logistics_Graph.html"):
        """Crea una vista de grafo avanzada usando NetworkX para el layout y Plotly para la visualización."""
        G = nx.DiGraph()
        
        # Recopilar todos los nodos y sus atributos
        unique_nodes = {}
        for route in self.routes:
            for node in route:
                unique_nodes[node['id']] = node
                G.add_node(node['id'], name=node['name'], type=node['type'])

        # Añadir aristas con peso (distancia)
        for route in self.routes:
            for j in range(len(route) - 1):
                start, end = route[j], route[j+1]
                dist_km = self.distance_matrix[start['matrix_idx']][end['matrix_idx']] / 1000
                G.add_edge(start['id'], end['id'], weight=dist_km)

        # Generar layout con NetworkX (spring_layout agrupado, k pequeño para emular vista compacta)
        pos = nx.spring_layout(G, k=0.15, iterations=150, seed=42)
        
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        # 1. Trazado de conexiones (Líneas finas grises oscuras)
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.8, color='#666666'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        )

        n_types_config = {
            'depot': {'name': 'Depot', 'color': '#ff7f0e', 'size': 65, 'f_size': 11},       # Naranja
            'carton_plant': {'name': 'Carton Plant', 'color': '#1f77b4', 'size': 50, 'f_size': 10}, # Azul
            'customer': {'name': 'Customer', 'color': '#cccccc', 'size': 25, 'f_size': 8}           # Gris claro
        }

        # 2. Trazado de nodos agrupados por tipo
        node_traces = []
        
        for t_key, t_config in n_types_config.items():
            t_x, t_y, t_hover, t_text = [], [], [], []
            
            for node_id in G.nodes():
                n_data = unique_nodes[node_id]
                if n_data['type'] == t_key:
                    x, y = pos[node_id]
                    t_x.append(x)
                    t_y.append(y)
                    
                    # Dividir nombres largos en dos lineas cortas para que quepan en la bola
                    words = n_data['name'].replace('Smurfit Westrock ', '').split()
                    short_name = "<br>".join(words[:2]) if len(words) > 1 else words[0] if words else ""
                    
                    t_text.append(short_name)
                    t_hover.append(f"<b>{n_data['name']}</b><br>Tipo: {n_data['type']}")
                    
            if len(t_x) > 0:
                trace = go.Scatter(
                    x=t_x, y=t_y,
                    mode='markers+text',
                    text=t_text,
                    textposition='middle center',
                    textfont=dict(size=t_config['f_size'], color='black', family='Arial'),
                    name=t_config['name'], 
                    hoverinfo='text',
                    hovertext=t_hover,
                    marker=dict(
                        showscale=False,
                        color=t_config['color'],
                        size=t_config['size'],
                        opacity=1.0,
                        line=dict(width=1, color='#333333') # Borde gris oscuro como en la foto
                    )
                )
                node_traces.append(trace)

        # 3. Ensamblar e imprimir
        fig = go.Figure(data=[edge_trace] + node_traces)
        
        fig.update_layout(
            title='', 
            showlegend=False, # La imagen no destaca una leyenda
            hovermode='closest',
            margin=dict(b=0,l=0,r=0,t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template="plotly_white",
            paper_bgcolor='rgba(255,255,255,1)',
            plot_bgcolor='rgba(255,255,255,1)'
        )

        output_path = RESULTS_DIR / filename
        fig.write_html(str(output_path))
        return output_path
