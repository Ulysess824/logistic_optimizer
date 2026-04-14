import json
from pathlib import Path

# Configuraciones
BASE_DIR = Path(__file__).resolve().parent.parent.parent
YEARLY_STATS_FILE = BASE_DIR / "outputs" / "results" / "yearly_stats.json"
HTML_OUTPUT_PATH = BASE_DIR / "outputs" / "Presentacion_Anual.html"

def generate_yearly_dashboard():
    """
    Genera un HTML interactivo que contiene un Slicer por fecha y agrega los totales anuales.
    El HTML usa un script en JS para actualizar el DOM cuando cambia la fecha seleccionada.
    """
    if not YEARLY_STATS_FILE.exists():
        print(f"Error: {YEARLY_STATS_FILE} no encontrado. Ejecuta run_yearly_simulation primero.")
        return

    with open(YEARLY_STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)

    # Calculamos agregados anuales (ignorando fechas con error)
    valid_days = [d for d in stats.values() if "error" not in d]
    
    total_days = len(valid_days)
    if total_days == 0:
        print("No hay días válidos en los stats para generar el reporte.")
        return
        
    y_routes = sum(d["routes_generated"] for d in valid_days)
    y_customers = sum(d.get("total_customers", 0) for d in valid_days)
    y_km = sum(d["total_km"] for d in valid_days)
    y_empty_km = sum(d["empty_km"] for d in valid_days)
    y_co2 = sum(d["total_co2_kg"] for d in valid_days)
    y_cost = sum(d["total_cost_eur"] for d in valid_days)
    
    # Inyectamos el JSON como variable JS para que el navegador resuelva
    stats_js = json.dumps(stats)

    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard TFM - Multi-Fecha y Anual</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f3f4f6; }}
        .card {{ background-color: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 20px; }}
        .kpi-val {{ font-size: 2rem; font-weight: bold; color: #1d4ed8; }}
        .kpi-lbl {{ font-size: 0.8rem; color: #6b7280; text-transform: uppercase; }}
        .tab-btn {{ padding: 10px 20px; cursor: pointer; transition: 0.3s; }}
        .tab-btn.active {{ border-bottom: 3px solid #1d4ed8; font-weight: bold; color: #1d4ed8; }}
    </style>
</head>
<body class="p-6">

    <div class="max-w-7xl mx-auto">
        <h1 class="text-3xl font-bold text-gray-800 border-b pb-2 mb-6">Panel de Control: Optimización Logística (Multi-Fecha)</h1>
        
        <!-- Pestañas -->
        <div class="flex space-x-4 border-b border-gray-300 mb-6">
            <div id="btn-tab-day" class="tab-btn active" onclick="switchTab('day')">📊 Vista por Día (Slicer)</div>
            <div id="btn-tab-year" class="tab-btn" onclick="switchTab('year')">📈 Vista Agregada Anual ({total_days} días)</div>
        </div>

        <!-- TAB: VISTA POR DÍA -->
        <div id="tab-day" class="block">
            <div class="card mb-6 flex items-center justify-between bg-white border-l-4 border-blue-600">
                <div>
                    <h2 class="text-lg font-bold text-gray-700">Selector de Fecha (Slicer Temporal)</h2>
                    <p class="text-sm text-gray-500">Selecciona un día laboral de la simulación para visualizar su impacto específico.</p>
                </div>
                <select id="date-slicer" class="p-2 border border-gray-300 rounded text-lg font-semibold text-gray-700" onchange="updateDailyView()">
                    <!-- Opciones inyectadas por JS -->
                </select>
            </div>

            <!-- KPIs Dinámicos -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div class="card text-center border-t-4 border-blue-500">
                    <p class="kpi-lbl">Rutas Activas</p>
                    <p id="dy-routes" class="kpi-val">-</p>
                </div>
                <div class="card text-center border-t-4 border-cyan-500">
                    <p class="kpi-lbl">Clientes Servidos</p>
                    <p id="dy-cust" class="kpi-val text-cyan-600">-</p>
                </div>
                <div class="card text-center border-t-4 border-green-500">
                    <p class="kpi-lbl">Distancia (km)</p>
                    <p id="dy-km" class="kpi-val">-</p>
                </div>
                <div class="card text-center border-t-4 border-amber-500">
                    <p class="kpi-lbl">Coste Operativo</p>
                    <p id="dy-cost" class="kpi-val text-amber-600">-</p>
                </div>
                <div class="card text-center border-t-4 border-fuchsia-600">
                    <p class="kpi-lbl">Emisiones CO2 (kg)</p>
                    <p id="dy-co2" class="kpi-val text-fuchsia-700">-</p>
                </div>
                <div class="card text-center border-t-4 border-red-500">
                    <p class="kpi-lbl">Km en Vacío</p>
                    <p id="dy-empty" class="kpi-val text-red-500">-</p>
                </div>
            </div>

            <!-- Visor de Mapa Dinámico -->
            <div class="card p-0 overflow-hidden mb-6" style="height: 600px;">
                <div class="bg-gray-100 px-4 py-2 border-b flex justify-between items-center">
                    <span class="text-sm font-bold text-gray-600">Visor Geográfico de Rutas (Día Seleccionado)</span>
                    <span id="map-status" class="text-xs text-blue-600 font-mono">Cargando visor...</span>
                </div>
                <iframe id="map-frame" src="" class="w-full h-full border-none"></iframe>
            </div>

            
            <div id="error-msg" class="hidden bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                <strong>Error: </strong> Esta fecha no generó rutas u ocurrió un problema en el solver.
            </div>
        </div>

        <!-- TAB: VISTA ANUAL Y MÉTRICAS DE LA IMAGEN (ROI, CAPEX) -->
        <div id="tab-year" class="hidden">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Consolidado Anual ({total_days} operaciones)</h2>
            
            <div class="grid grid-cols-2 md:grid-cols-3 gap-6 mb-6">
                <div class="card hover:shadow-lg transition">
                    <p class="kpi-lbl">Total Rutas ({total_days} días)</p>
                    <p class="text-4xl font-black text-gray-800 mt-2">{y_routes:,}</p>
                </div>
                <div class="card hover:shadow-lg transition bg-blue-50 border border-blue-100">
                    <p class="kpi-lbl text-blue-700">Total KM Recorridos</p>
                    <p class="text-4xl font-black text-blue-900 mt-2">{y_km:,.0f} <span class="text-lg">km</span></p>
                </div>
                <div class="card hover:shadow-lg transition bg-fuchsia-50 border border-fuchsia-100">
                    <p class="kpi-lbl text-fuchsia-700">Huella de Carbono Total</p>
                    <p class="text-4xl font-black text-fuchsia-900 mt-2">{(y_co2/1000):,.1f} <span class="text-lg">Tons</span></p>
                </div>
            </div>

            <!-- KPIs Financieros Estilo ROI (Proyectados) -->
            <h3 class="text-xl font-bold text-gray-700 border-l-4 border-indigo-500 pl-3 mb-4 mt-8">Impacto Financiero del Algoritmo a Nivel Anual</h3>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="card bg-indigo-50 border-indigo-100 border text-center">
                    <p class="kpi-lbl text-indigo-700">Inversión (CAPEX Software)</p>
                    <p class="text-3xl font-bold text-indigo-900 mt-2">25,000 €</p>
                </div>
                <div class="card bg-green-50 border-green-100 border text-center">
                    <p class="kpi-lbl text-green-700">Ahorro Anual Estimado (Sistémico)</p>
                    <p class="text-3xl font-bold text-green-900 mt-2">{(1359 * total_days):,.0f} €</p>
                    <p class="text-xs text-green-600 mt-1">*Proyección basada en {total_days} días vs línea base</p>
                </div>
                <div class="card bg-amber-50 border-amber-100 border text-center">
                    <p class="kpi-lbl text-amber-700">ROI Anualizado</p>
                    <p class="text-3xl font-bold text-amber-900 mt-2">{(((1359 * total_days)-25000)/25000)*100:,.1f}%</p>
                </div>
                <div class="card bg-teal-50 border-teal-100 border text-center shadow-md">
                    <p class="kpi-lbl text-teal-700">Ahorro CO2 Sistémico (Toneladas)</p>
                    <p class="text-3xl font-bold text-teal-900 mt-2">{((7371 * total_days) / 1000):,.1f} t</p>
                </div>
            </div>
        </div>

    </div>

    <!-- SCRIPT DE INTERACTIVIDAD -->
    <script>
        const statsData = {stats_js};
        const slicer = document.getElementById("date-slicer");
        
        // Pestañas
        function switchTab(tabId) {{
            document.getElementById("tab-day").classList.add("hidden");
            document.getElementById("tab-year").classList.add("hidden");
            document.getElementById("btn-tab-day").classList.remove("active");
            document.getElementById("btn-tab-year").classList.remove("active");
            
            document.getElementById("tab-" + tabId).classList.remove("hidden");
            document.getElementById("btn-tab-" + tabId).classList.add("active");
        }}

        // Inicializar Slicer
        function initSlicer() {{
            const dates = Object.keys(statsData).sort();
            dates.forEach(date => {{
                let opt = document.createElement("option");
                opt.value = date;
                opt.textContent = date;
                slicer.appendChild(opt);
            }});
            updateDailyView();
        }}

        // Formatear numeros
        function fmt(n) {{ return new Intl.NumberFormat('es-ES', {{maximumFractionDigits: 1}}).format(n); }}

        // Actualizar vista diaria
        function updateDailyView() {{
            const date = slicer.value;
            const data = statsData[date];
            
            if(data.error) {{
                document.getElementById("error-msg").classList.remove("hidden");
                document.getElementById("map-frame").classList.add("hidden");
                ["routes", "cust", "km", "cost", "co2", "empty"].forEach(id => document.getElementById("dy-" + id).textContent = "-");
            }} else {{
                document.getElementById("error-msg").classList.add("hidden");
                document.getElementById("map-frame").classList.remove("hidden");
                document.getElementById("dy-routes").textContent = data.routes_generated || 0;
                document.getElementById("dy-cust").textContent = data.total_customers || 0;
                document.getElementById("dy-km").textContent = fmt(data.total_km) + " km";
                document.getElementById("dy-cost").textContent = fmt(data.total_cost_eur) + " €";
                document.getElementById("dy-co2").textContent = fmt(data.total_co2_kg);
                document.getElementById("dy-empty").textContent = fmt(data.empty_km) + " km";
                
                // Actualizar el mapa
                const mapPath = `./rutas_diarias/Rutas_${{date}}.html`;
                document.getElementById("map-frame").src = mapPath;
                document.getElementById("map-status").textContent = `Archivo: Rutas_${{date}}.html`;
            }}
        }}

        // Arranque
        initSlicer();
    </script>
</body>
</html>
    """

    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Dashboard anual interactivo generado exitosamente en: {HTML_OUTPUT_PATH}")

if __name__ == "__main__":
    generate_yearly_dashboard()
