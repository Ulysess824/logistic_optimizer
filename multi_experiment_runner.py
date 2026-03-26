import os
import json
import folium
import polyline
from pathlib import Path
from main import run_optimization, PLANTS_FILE, RESULTS_DIR
from logistic_core.utils.cost_estimator import CostEstimator
import base64

# Configuración de salida
OUTPUT_DIR = Path("outputs/experiments")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FINAL_HTML = "Multiples_pruebas.html"

def generate_experiment_map(routes, solver, test_id):
    """Genera un mapa folium rápido (líneas rectas) para experimentos masivos."""
    with open(PLANTS_FILE, 'r', encoding='utf-8') as f:
        plants_data = json.load(f)
    
    m_lat, m_lng = plants_data['paper_plant']['lat'], plants_data['paper_plant']['lng']
    mapa = folium.Map(location=[m_lat, m_lng], zoom_start=6, tiles="CartoDB positron")
    colores_ruta = ['blue', 'green', 'red', 'purple', 'orange', 'darkred', 'cadetblue']

    for i, route in enumerate(routes):
        color_actual = colores_ruta[i % len(colores_ruta)]
        for n in route:
            icon = 'home' if n['type'] == 'depot' else ('industry' if n['type'] == 'carton_plant' else 'info-sign')
            folium.Marker([n['lat'], n['lng']], icon=folium.Icon(color=color_actual, icon=icon)).add_to(mapa)

        # Líneas rectas para velocidad máxima en el lab
        coords = [[n['lat'], n['lng']] for n in route]
        folium.PolyLine(coords, color=color_actual, weight=3, opacity=0.7).add_to(mapa)

    map_path = OUTPUT_DIR / f"map_test_{test_id}.html"
    mapa.save(str(map_path))
    return map_path.as_posix()

def run_suite():
    # Definición de las 20 pruebas
    experiments = []
    
    variations = [
        (35, 50, 30), (35, 20, 30), (35, 80, 30), 
        (28, 50, 30), (32, 50, 30), (38, 50, 30), 
        (35, 50, 10), (35, 50, 20), (45, 50, 45), 
        (30, 30, 20), (30, 60, 25), (40, 40, 35), 
        (35, 15, 15), (35, 100, 50),              
        (33, 40, 30), (33, 60, 30),               
        (25, 50, 30), (45, 50, 30),               
        (35, 45, 40), (35, 55, 15)                
    ]

    results = []
    print(f"Iniciando Suite de {len(variations)} Experimentos (MODO FAST)...")

    for i, (pals, thres, cands) in enumerate(variations):
        test_id = i + 1
        # USAMOS api_type="haversine" para que sea instantáneo
        routes, summary, solver = run_optimization(
            max_pallets=pals,
            threshold_km=thres,
            n_candidatos=cands,
            max_search_time=5, 
            api_type="haversine",
            silent=True
        )

        if routes:
            map_rel_path = generate_experiment_map(routes, solver, test_id)
            results.append({
                "id": test_id,
                "params": {"pallets": pals, "threshold": thres, "candidates": cands},
                "stats": summary,
                "cost_eur": round(summary['total_km'] * 1.14, 2),
                "map_url": map_rel_path
            })
            print(f"  [Test {test_id}/20] OK: {summary['total_km']}km, {summary['num_routes']} rutas.")
        else:
            print(f"  [Test {test_id}/20] Error en optimización.")

    # Generar el HTML final consolidad
    generate_consolidated_html(results)

def generate_consolidated_html(results):
    """Ensambla el dashboard premium Multiples_pruebas.html."""
    
    # Generar filas del Leaderboard
    leaderboard_rows = ""
    # Ordenar por eficiencia (Ahorro relativo si lo tuviéramos, pero usemos km totales por ahora)
    sorted_results = sorted(results, key=lambda x: x['stats']['total_km'])
    
    for r in sorted_results:
        leaderboard_rows += f"""
        <tr onclick="showTest({r['id']})" style="cursor:pointer;" class="hover:bg-blue-50 transition-colors">
            <td class="px-4 py-2 font-bold text-blue-600">#{r['id']}</td>
            <td class="px-4 py-2">{r['params']['pallets']} P</td>
            <td class="px-4 py-2">{r['params']['threshold']} km</td>
            <td class="px-4 py-2">{r['params']['candidates']}</td>
            <td class="px-4 py-2 font-mono">{r['stats']['total_km']:,} km</td>
            <td class="px-4 py-2 font-mono text-purple-600">{r['stats']['total_co2_kg']:,} kg</td>
            <td class="px-4 py-2 font-mono text-blue-700 font-bold">{r['cost_eur']:,} €</td>
            <td class="px-4 py-2 text-center"><span class="bg-gray-100 px-2 py-1 rounded text-xs">{r['stats']['num_routes']} rutas</span></td>
        </tr>
        """

    # Generar JS para cambiar de test
    js_data = {r['id']: r for r in results}
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>Laboratorio de Optimización Logística - 20 Pruebas</title>
        <style>
            .glass {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }}
            .sidebar-item.active {{ background-color: #2563eb; color: white; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 10px; }}
        </style>
    </head>
    <body class="bg-slate-900 text-slate-800 font-sans h-screen flex overflow-hidden">
        
        <!-- Sidebar -->
        <div class="w-64 bg-slate-800 text-slate-300 flex flex-col shadow-xl">
            <div class="p-6 border-b border-slate-700">
                <h1 class="text-xl font-bold text-white tracking-tight">LOGI-LAB <span class="text-blue-400">VRP</span></h1>
                <p class="text-[10px] uppercase tracking-widest text-slate-500 mt-1">20 Escenarios de Prueba</p>
            </div>
            <div class="flex-1 overflow-y-auto p-4 space-y-2" id="sidebar-list">
                <!-- Se poblará por JS -->
            </div>
        </div>

        <!-- Main Content -->
        <div class="flex-1 flex flex-col overflow-y-auto bg-slate-50">
            
            <!-- Header / Leaderboard -->
            <div class="p-8">
                <div class="flex justify-between items-end mb-6">
                    <div>
                        <h2 class="text-3xl font-black text-slate-900">Métricas Comparativas</h2>
                        <p class="text-slate-500">Ranking de eficiencia basado en distancia total recorrida.</p>
                    </div>
                </div>

                <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-8">
                    <table class="w-full text-left">
                        <thead class="bg-slate-50 text-slate-400 text-[10px] uppercase tracking-wider font-bold">
                            <tr>
                                <th class="px-4 py-4">Test ID</th>
                                <th class="px-4 py-4">Capacidad</th>
                                <th class="px-4 py-4">Desvío</th>
                                <th class="px-4 py-4">Candidatos</th>
                                <th class="px-4 py-4">Distancia Total</th>
                                <th class="px-4 py-4">CO2 Estimado</th>
                                <th class="px-4 py-4 text-blue-800">Coste (1.14€/km)</th>
                                <th class="px-4 py-4 text-center">Flota</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 text-sm">
                            {leaderboard_rows}
                        </tbody>
                    </table>
                </div>

                <!-- Experiment Viewer -->
                <div id="viewer" class="grid grid-cols-1 lg:grid-cols-3 gap-8 pb-12">
                    
                    <!-- KPIs Section -->
                    <div class="lg:col-span-1 space-y-6">
                        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 shadow-blue-100/50">
                            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4" id="test-title">Detalle del Test</h3>
                            <div class="grid grid-cols-2 gap-4">
                                <div class="bg-slate-50 p-4 rounded-xl">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase">Distancia</p>
                                    <p class="text-xl font-black text-blue-600" id="stat-dist">-</p>
                                </div>
                                <div class="bg-slate-50 p-4 rounded-xl">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase">CO2 (kg)</p>
                                    <p class="text-xl font-black text-purple-600" id="stat-co2">-</p>
                                </div>
                                <div class="bg-slate-50 p-4 rounded-xl">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase">Coste Estimado</p>
                                    <p class="text-xl font-black text-blue-800" id="stat-cost">-</p>
                                </div>
                                <div class="bg-slate-50 p-4 rounded-xl">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase">Rutas</p>
                                    <p class="text-xl font-black text-slate-800" id="stat-routes">-</p>
                                </div>
                                <div class="bg-slate-50 p-4 rounded-xl">
                                    <p class="text-[10px] font-bold text-slate-400 uppercase">Promedio Km</p>
                                    <p class="text-xl font-black text-slate-800" id="stat-avg">-</p>
                                </div>
                            </div>
                            
                            <div class="mt-6 pt-6 border-t border-slate-100">
                                <p class="text-[11px] font-bold text-slate-800 mb-2">Parámetros de Entrada:</p>
                                <ul class="text-xs space-y-1 text-slate-500" id="param-list">
                                    <!-- JS -->
                                </ul>
                            </div>
                        </div>
                    </div>

                    <!-- Map Section -->
                    <div class="lg:col-span-2">
                        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-2 h-[500px] overflow-hidden relative">
                            <iframe id="map-iframe" src="" class="w-full h-full rounded-xl bg-slate-100 border-0"></iframe>
                            <div class="absolute top-4 right-4 bg-white/80 backdrop-blur px-3 py-1 rounded-full text-[10px] font-bold shadow-sm border border-slate-200">MAPA INTERACTIVO</div>
                        </div>
                    </div>

                </div>

                <!-- Technical Section: GLS -->
                <div class="mt-12 bg-slate-900 rounded-3xl p-8 border border-slate-800 shadow-2xl">
                    <div class="flex items-center gap-4 mb-6 border-b border-slate-800 pb-4">
                        <div class="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                            <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                        </div>
                        <div>
                            <h3 class="text-white font-bold text-lg">Análisis Técnico: Algoritmo GLS (Guided Local Search)</h3>
                            <p class="text-slate-500 text-[10px] uppercase tracking-widest uppercase">Basado en: Voudouris & Tsang (1999)</p>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div class="space-y-4">
                            <h4 class="text-blue-400 text-xs font-bold uppercase tracking-wider">1. Función de Objetivo Aumentada (h)</h4>
                            <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 text-center shadow-inner">
                                <code class="text-xl text-white font-mono italic">h(s) = g(s) + &lambda; &middot; &sum; (p<sub>i</sub> &middot; I<sub>i</sub>(s))</code>
                            </div>
                            <ul class="text-[11px] space-y-2 text-slate-400 list-disc list-inside">
                                <li><span class="text-slate-200">g(s):</span> Coste base (Distancia real en km).</li>
                                <li><span class="text-slate-200">&lambda;:</span> Hiper-parámetro de regularización de penalización.</li>
                                <li><span class="text-slate-200">p<sub>i</sub>:</span> Penalización acumulada por el arco (i).</li>
                                <li><span class="text-slate-200">I<sub>i</sub>(s):</span> Binario (1 si el arco está presente en la solución).</li>
                            </ul>
                        </div>

                        <div class="space-y-4">
                            <h4 class="text-amber-400 text-xs font-bold uppercase tracking-wider">2. Criterio de Perturbación (Utilidad)</h4>
                            <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 text-center shadow-inner">
                                <code class="text-xl text-white font-mono italic">Util(s, i) = c<sub>i</sub>(s) / (1 + p<sub>i</sub>)</code>
                            </div>
                            <p class="text-[11px] text-slate-400 leading-relaxed">
                                Tras alcanzar un óptimo local, el algoritmo penaliza los arcos con mayor <span class="text-slate-200 italic font-medium">coste de transporte (c<sub>i</sub>)</span> 
                                que tienen bajas penalizaciones previas. Esto genera un gradiente sintético que "expulsa" al 
                                solver de cuencas de atracción sub-óptimas, facilitando la búsqueda de mejores consolidaciones de flota.
                            </p>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <script>
            const data = {json.dumps(js_data)};
            
            function initSidebar() {{
                const list = document.getElementById('sidebar-list');
                Object.values(data).forEach(t => {{
                    const btn = document.createElement('button');
                    btn.className = `sidebar-item w-full text-left p-3 rounded-lg text-sm font-medium transition-all hover:bg-slate-700/50 flex justify-between items-center`;
                    btn.id = 'side-' + t.id;
                    btn.onclick = () => showTest(t.id);
                    btn.innerHTML = "<span>Test Case #" + t.id + "</span><span class='text-[10px] opacity-50 font-mono'>" + t.stats.total_km + " km</span>";
                    list.appendChild(btn);
                }});
            }}

            function showTest(id) {{
                const t = data[id];
                if (!t) return;

                // UI Updates
                document.getElementById('test-title').innerText = "Detalle del Test #" + id;
                document.getElementById('stat-dist').innerText = t.stats.total_km + ' km';
                document.getElementById('stat-co2').innerText = t.stats.total_co2_kg + ' kg';
                document.getElementById('stat-cost').innerText = t.cost_eur + ' €';
                document.getElementById('stat-routes').innerText = t.stats.num_routes;
                document.getElementById('stat-avg').innerText = (t.stats.total_km / t.stats.num_routes).toFixed(1) + ' km';

                document.getElementById('param-list').innerHTML = 
                    "<li>• Capacidad: <b>" + t.params.pallets + " pallets</b></li>" +
                    "<li>• Desvío Max: <b>" + t.params.threshold + " km</b></li>" +
                    "<li>• Candidatos: <b>" + t.params.candidates + " por planta</b></li>";

                document.getElementById('map-iframe').src = t.map_url;

                // Active Sidebar effect
                document.querySelectorAll('.sidebar-item').forEach(b => b.classList.remove('active'));
                document.getElementById('side-' + id).classList.add('active');
                
                // Scroll to viewer if mobile
                if (window.innerWidth < 1024) {{
                    document.getElementById('viewer').scrollIntoView({{behavior: 'smooth'}});
                }}
            }}

            initSidebar();
            // Mostrar el primero por defecto
            showTest(Object.keys(data)[0]);
        </script>
    </body>
    </html>
    """
    
    with open(FINAL_HTML, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"\nFinalizado: Dashboard consolidado en '{FINAL_HTML}'")

if __name__ == "__main__":
    run_suite()
