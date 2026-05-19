import logging
import folium
from folium import plugins
import plotly.graph_objects as go
import polyline
import networkx as nx
from logistic_core.config import MAPS_DIR, RESULTS_DIR
from logistic_core.utils.geo import GeoUtils

logger = logging.getLogger(__name__)


class Visualizer:
    def __init__(self, routes, distance_matrix=None, geo_utils=None):
        self.routes = routes
        self.distance_matrix = distance_matrix
        self.geo = geo_utils or GeoUtils()
        # Colores optimizados (Alta visibilidad)
        self.route_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]

    def _generate_sidebar_html(self):
        """Genera el código HTML para la tabla lateral interactiva de rutas."""
        table_rows = ""
        total_km = 0
        total_empty_km = 0

        for i, route in enumerate(self.routes):
            color = self.route_colors[i % len(self.route_colors)]
            route_dist = 0
            empty_dist = 0
            detail_html = "<ul style='padding-left: 5px; font-size: 11px; margin: 5px 0; color: #444; list-style-type: none;'>"
            
            # --- CÁLCULO DE CARGA (KGs) Y ESTADO POR TRAMO ---
            from logistic_core.config import PAPER_LOAD_KG, PALLET_WEIGHT_KG
            load_change = [0] * len(route)
            paper_dropped = False
            for idx, node in enumerate(route):
                if node['type'] == 'depot' and idx == 0:
                    load_change[idx] = PAPER_LOAD_KG
                elif node['type'] == 'carton_plant':
                    delta = 0
                    if not paper_dropped:
                        delta -= PAPER_LOAD_KG
                        paper_dropped = True
                    # Calcular pallets que se cargan en esta planta
                    plant_id = str(node.get('id', ''))
                    base_plant_id = plant_id.split('_clone')[0]
                    
                    matched_pallets = sum(c.get('demanda_pallets', 0) for c in route if c['type'] == 'customer' and base_plant_id in str(c.get('parent_cp','')))
                    # Failsafe: Si no encuentra asociaciones de ID por renombramientos, la primera planta asume todo
                    if matched_pallets == 0 and sum(load_change[:idx+1]) <= 0:
                        matched_pallets = sum(c.get('demanda_pallets', 0) for c in route if c['type'] == 'customer')
                    
                    delta += matched_pallets * PALLET_WEIGHT_KG
                    load_change[idx] += delta
                elif node['type'] == 'customer':
                    pallets = node.get('demanda_pallets', 0)
                    load_change[idx] -= pallets * PALLET_WEIGHT_KG

            loads_leaving = []
            curr_l = 0
            for chg in load_change:
                curr_l += chg
                loads_leaving.append(curr_l)

            for j in range(len(route) - 1):
                start, end = route[j], route[j+1]
                dist_m = self.distance_matrix[start['matrix_idx']][end['matrix_idx']]
                dist_km = dist_m / 1000
                route_dist += dist_km
                
                # Estado de la carga en este tramo
                weight_in_segment = max(0, loads_leaving[j])
                estado_badge = ""
                if weight_in_segment > 20000:
                    estado_badge = f"<span style='background:#1f77b4; color:white; padding:1px 4px; border-radius:3px; font-size:9px;'>CARG. ({weight_in_segment:,.0f} kg)</span>"
                elif weight_in_segment > 0:
                    estado_badge = f"<span style='background:#f39c12; color:white; padding:1px 4px; border-radius:3px; font-size:9px;'>PARCIAL ({weight_in_segment:,.0f} kg)</span>"
                else:
                    estado_badge = f"<span style='background:#e74c3c; color:white; padding:1px 4px; border-radius:3px; font-size:9px;'>VACÍO (0 kg)</span>"
                
                # Check if returning to depot at the end of the route
                if end['type'] == 'depot' and j == len(route) - 2:
                    empty_dist += dist_km
                    # Forzar estado vacío al retornar por seguridad
                    estado_badge = f"<span style='background:#e74c3c; color:white; padding:1px 4px; border-radius:3px; font-size:9px;'>VACÍO SAFARI</span>" # Debug just in case, wait no Safari
                    estado_badge = f"<span style='background:#e74c3c; color:white; padding:1px 4px; border-radius:3px; font-size:9px;'>VACÍO (0 kg)</span>"

                s_icon = "🏢" if start['type'] == 'depot' else "🏭" if start['type'] == 'carton_plant' else "🏪"
                e_icon = "🏢" if end['type'] == 'depot' else "🏭" if end['type'] == 'carton_plant' else "🏪"

                detail_html += (
                    f"<li style='margin-bottom:6px; background:#fff; padding:4px; border:1px solid #eee; border-radius:4px;'>"
                    f"  <div style='display:flex; justify-content:space-between; margin-bottom:2px;'>"
                    f"    <span style='white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 75%;' title='{start['name']} → {end['name']}'>{s_icon} {start['name'].split()[0]} <span style='color:{color}'>→</span> {e_icon} {end['name'].split()[0]}</span>"
                    f"    <b style='min-width: 40px; text-align:right;'>{dist_km:.1f} km</b>"
                    f"  </div>"
                    f"  <div style='text-align:right;'>{estado_badge}</div>"
                    f"</li>"
                )

            detail_html += "</ul>"
            total_km += route_dist
            total_empty_km += empty_dist

            table_rows += f"""
            <tr onclick="toggleRoute({i})" style="cursor: pointer; border-bottom: 1px solid #ddd; background-color: {color}11;">
                <td style="padding: 10px; font-weight: bold; color: {color};">#{i+1}</td>
                <td style="padding: 10px;">{route[1]['name']}</td>
                <td style="padding: 10px; text-align: right;">{route_dist:.1f} km<br><span style="font-size: 0.85em; color: #7f8c8d;">({empty_dist:.1f} km en vacío)</span></td>
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
                <p style="margin: 5px 0;"><strong>🚚 Kilómetros en Vacío:</strong> <span style="font-size: 1.1em; color: #e74c3c;">{total_empty_km:.2f}</span> km</p>
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

    def create_map(self, filename="Logistics_Dashboard.html", show_sidebar=True):
        m = folium.Map(location=[40.4167, -3.7037], zoom_start=6, tiles="cartodbpositron")
        
        if show_sidebar:
            sidebar_html = self._generate_sidebar_html()
            m.get_root().html.add_child(folium.Element(sidebar_html))

        for i, route in enumerate(self.routes):
            color = self.route_colors[i % len(self.route_colors)]

            for j in range(len(route) - 1):
                start, end = route[j], route[j+1]
                encoded_poly = self.geo.get_route_polyline((start['lat'], start['lng']), (end['lat'], end['lng']))

                if encoded_poly and encoded_poly != "BILLING_ERROR":
                    decoded_points = polyline.decode(encoded_poly)
                    
                    # --- OPTIMIZACIÓN: Simplificación inteligente para reducir peso HTML ---
                    points_count = len(decoded_points)
                    if points_count > 500:
                        # Sub-muestreo: Mantener extremos y tomar 1 de cada N puntos
                        # Para 4000 puntos, un factor de 5 deja 800 puntos (fino para 800km)
                        step = max(1, points_count // 800) 
                        if step > 1:
                           simplified = decoded_points[::step]
                           # Asegurar que el último punto original se incluye
                           if simplified[-1] != decoded_points[-1]:
                               simplified.append(decoded_points[-1])
                           decoded_points = simplified
                    
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
        logger.info("Mapa guardado en: %s", output_path)
        return output_path

    def create_plotly_graph(self, filename="Logistics_Graph.html"):
        """Crea una vista de grafo avanzada usando NetworkX para el layout y Plotly para la visualización."""
        G = nx.DiGraph()

        unique_nodes = {}
        for route in self.routes:
            for node in route:
                unique_nodes[node['id']] = node
                G.add_node(node['id'], name=node['name'], type=node['type'])

        for route in self.routes:
            for j in range(len(route) - 1):
                start, end = route[j], route[j+1]
                
                # Fallback si no hay matriz de distancias
                if self.distance_matrix is not None:
                    dist_km = self.distance_matrix[start['matrix_idx']][end['matrix_idx']] / 1000
                else:
                    dist_km = self.geo.get_route_distance(
                        (start['lat'], start['lng']), 
                        (end['lat'], end['lng'])
                    ) / 1000.0
                
                G.add_edge(start['id'], end['id'], weight=dist_km)

        pos = {n: (unique_nodes[n]['lng'], unique_nodes[n]['lat']) for n in G.nodes()}

        edge_lon = []
        edge_lat = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_lon.extend([x0, x1, None])
            edge_lat.extend([y0, y1, None])

        edge_trace = go.Scattergeo(
            lon=edge_lon, lat=edge_lat,
            mode='lines',
            line=dict(width=2, color='#3b82f6'), # Azul intenso para rutas optimizadas
            opacity=0.8,
            hoverinfo='none',
            showlegend=False
        )

        n_types_config = {
            'depot': {'name': 'Depot', 'color': '#ef4444', 'size': 12},
            'carton_plant': {'name': 'Carton Plant', 'color': '#10b981', 'size': 9},
            'customer': {'name': 'Customer', 'color': '#6b7280', 'size': 5}
        }

        node_traces = []

        for t_key, t_config in n_types_config.items():
            t_lon, t_lat, t_hover = [], [], []

            for node_id in G.nodes():
                n_data = unique_nodes[node_id]
                if n_data['type'] == t_key:
                    lon, lat = pos[node_id]
                    t_lon.append(lon)
                    t_lat.append(lat)
                    t_hover.append(f"<b>{n_data['name']}</b><br>Tipo: {n_data['type']}")

            if len(t_lon) > 0:
                trace = go.Scattergeo(
                    lon=t_lon, lat=t_lat,
                    mode='markers',
                    name=t_config['name'],
                    hoverinfo='text',
                    hovertext=t_hover,
                    marker=dict(
                        color=t_config['color'],
                        size=t_config['size'],
                        opacity=1.0,
                        line=dict(width=1, color='white')
                    )
                )
                node_traces.append(trace)

        fig = go.Figure(data=[edge_trace] + node_traces)

        fig.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                scope='europe',
                resolution=50,
                showcoastlines=True, coastlinecolor="LightBlue",
                showland=True, landcolor="#f8fafc",
                showcountries=True, countrycolor="#e2e8f0",
                lonaxis_range=[-10, 4],
                lataxis_range=[35, 44],
                projection_type='mercator'
            )
        )

        output_path = RESULTS_DIR / filename
        fig.write_html(str(output_path))
        logger.info("Grafo Plotly guardado en: %s", output_path)
        return output_path

    def create_global_complexity_graph(self, paper_plant, carton_plants, all_clients, filename="Logistics_Global_Complexity.html"):
        """Crea un grafo que muestra la complejidad total (todas las conexiones posibles) sin optimizar."""
        fig = go.Figure()

        # Nodos
        nodes_x = []
        nodes_y = []
        node_colors = []
        node_sizes = []
        node_hovers = []

        # 1. Depot
        nodes_x.append(paper_plant['lng'])
        nodes_y.append(paper_plant['lat'])
        node_colors.append('#ff7f0e') # Naranja (Original)
        node_sizes.append(15)
        node_hovers.append(f"Depósito: {paper_plant['name']}")

        # 2. Plantas
        for p in carton_plants:
            nodes_x.append(p['lng'])
            nodes_y.append(p['lat'])
            node_colors.append('#1f77b4') # Azul (Original)
            node_sizes.append(10)
            node_hovers.append(f"Planta: {p['name']}")

        # 3. Clientes (Todos)
        for c in all_clients:
            nodes_x.append(c['lng'])
            nodes_y.append(c['lat'])
            node_colors.append('#cccccc') # Gris
            node_sizes.append(4)
            node_hovers.append(f"Cliente: {c['name']}")

        edge_x = []
        edge_y = []
        for p in carton_plants:
            for c in all_clients[:200]: 
                edge_x.extend([p['lng'], c['lng'], None])
                edge_y.extend([p['lat'], c['lat'], None])

        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.4, color='rgba(150,150,150,0.2)'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        ))

        fig.add_trace(go.Scatter(
            x=nodes_x, y=nodes_y,
            mode='markers',
            hoverinfo='text',
            hovertext=node_hovers,
            marker=dict(
                color=node_colors,
                size=node_sizes,
                line=dict(width=0.5, color='#333333')
            ),
            showlegend=False
        ))

        fig.update_layout(
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0,l=0,r=0,t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template="plotly_white",
            paper_bgcolor='white',
            plot_bgcolor='white'
        )

        output_path = RESULTS_DIR / filename
        fig.write_html(str(output_path))
        logger.info("Grafo de Complejidad guardado en: %s", output_path)
        return output_path
