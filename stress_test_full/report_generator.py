import json
from pathlib import Path

def generate_stress_html(results_file, output_html):
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    # Preparar datos para gráficos
    labels = [r['scenario_name'] for r in results]
    times = [r['total_time_s'] for r in results]
    nodes = [r['total_nodes'] for r in results]
    memory = [r['memory_diff_mb'] for r in results]

    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stress Test Full Report - Logistics Optimizer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .glass {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans">
    <div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div class="mb-12 text-center text-gray-900">
            <h1 class="text-4xl font-extrabold tracking-tight sm:text-5xl mb-4">
                🚀 Stress Test Full Report
            </h1>
            <p class="text-xl text-gray-600">Evaluación del modelo en situaciones extremas</p>
        </div>

        <!-- Dashboard Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            <!-- Gráfico de Tiempos -->
            <div class="glass p-6 rounded-2xl shadow-xl">
                <h3 class="text-lg font-semibold mb-4">Tiempo Total de Ejecución (s)</h3>
                <canvas id="timeChart"></canvas>
            </div>
            <!-- Gráfico de Nodos -->
            <div class="glass p-6 rounded-2xl shadow-xl">
                <h3 class="text-lg font-semibold mb-4">Complejidad (Nodos Procesados)</h3>
                <canvas id="nodeChart"></canvas>
            </div>
        </div>

        <!-- Tabla de KPIs -->
        <div class="glass rounded-2xl shadow-xl overflow-hidden mb-12">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">Escenario</th>
                        <th class="px-6 py-4 text-center text-xs font-bold text-gray-600 uppercase tracking-wider">Nodos</th>
                        <th class="px-6 py-4 text-center text-xs font-bold text-gray-600 uppercase tracking-wider">Rutas</th>
                        <th class="px-6 py-4 text-center text-xs font-bold text-gray-600 uppercase tracking-wider">Tiempo (s)</th>
                        <th class="px-6 py-4 text-center text-xs font-bold text-gray-600 uppercase tracking-wider">Memoria (MB)</th>
                        <th class="px-6 py-4 text-center text-xs font-bold text-gray-600 uppercase tracking-wider">Solución</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                    {''.join([f'''
                    <tr class="hover:bg-gray-50 transition-colors">
                        <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{r['scenario_name']}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-center">{r['total_nodes']}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-center">{r['total_routes']}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-center font-bold text-indigo-600">{r['total_time_s']}s</td>
                        <td class="px-6 py-4 whitespace-nowrap text-center">{r['memory_diff_mb']} MB</td>
                        <td class="px-6 py-4 whitespace-nowrap text-center">
                            <span class="px-3 py-1 rounded-full text-xs font-bold {'bg-green-100 text-green-700' if r['solution_found'] else 'bg-red-100 text-red-700'}">
                                {'ÉXITO' if r['solution_found'] else 'FALLO'}
                            </span>
                        </td>
                    </tr>''' for r in results])}
                </tbody>
            </table>
        </div>

        <!-- Detalles por Escenario -->
        <div class="space-y-8">
            <h2 class="text-2xl font-bold border-b border-gray-200 pb-2">Detalle de Pruebas</h2>
            {''.join([f'''
            <div class="glass p-8 rounded-2xl shadow-lg border-l-8 border-indigo-500">
                <h3 class="text-xl font-bold mb-4">{r['scenario_name']}</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div class="space-y-2">
                        <p class="text-sm text-gray-500">Parámetros:</p>
                        <ul class="text-xs space-y-1 font-mono bg-gray-50 p-3 rounded-lg border border-gray-100">
                            { "".join([f"<li>- {k}: {v}</li>" for k, v in r['parameters'].items()]) }
                        </ul>
                    </div>
                    <div class="col-span-2 space-y-4">
                        <p class="text-gray-700 leading-relaxed">
                            Esta prueba evalúa la capacidad del modelo bajo condiciones de 
                            <strong>{r['scenario_name'].lower()}</strong>. 
                            Se procesaron {r['total_nodes']} nodos en {r['total_time_s']} segundos.
                        </p>
                        <div class="flex space-x-4">
                            <div class="text-center p-4 bg-indigo-50 rounded-xl flex-1">
                                <p class="text-xs text-indigo-600 font-bold uppercase mb-1">Carga Solver</p>
                                <p class="text-2xl font-black text-indigo-800">{r['solver_time_s']}s</p>
                            </div>
                            <div class="text-center p-4 bg-emerald-50 rounded-xl flex-1">
                                <p class="text-xs text-emerald-600 font-bold uppercase mb-1">Rutas</p>
                                <p class="text-2xl font-black text-emerald-800">{r['total_routes']}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>''' for r in results])}
        </div>
    </div>

    <script>
        const labels = {json.dumps(labels)};
        
        new Chart(document.getElementById('timeChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Tiempo Total (s)',
                    data: {json.dumps(times)},
                    backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    borderRadius: 8
                }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
        }});

        new Chart(document.getElementById('nodeChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Nodos Totales',
                    data: {json.dumps(nodes)},
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
        }});
    </script>
</body>
</html>
    """
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    results_path = Path(__file__).parent / "results" / "all_stress_results.json"
    output_path = Path(__file__).parent / "stress_report.html"
    generate_stress_html(results_path, output_path)
    print(f"Reporte generado en: {{output_path}}")
