import re
from pathlib import Path

def generate_html_rejections(log_path="logs/descartados_motivos.log", output_path="outputs/reports/reporte_descartes.html"):
    log_path = Path(log_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not log_path.exists():
        return "Log no encontrado."

    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Estructura: rejections_by_plant[plant] = { "fleet_state": "", "subroutes": [], "rejects": [] }
    data_by_plant = {}
    current_plant = "GLOBAL"
    total_pallets = 0
    total_count = 0

    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # El buscador debe ser exacto al inicio para no confundirse con el diagnostico
        if line.startswith("PLANTA:"):
            current_plant = line.split(":")[-1].strip()
            if current_plant not in data_by_plant:
                data_by_plant[current_plant] = {"fleet_state": "Sin datos", "subroutes": [], "rejects": []}
        
        elif line.startswith("ESTADO DE FLOTA:"):
            data_by_plant[current_plant]["fleet_state"] = line.split(":")[-1].strip()
            
        elif line.startswith("- Camion"):
            data_by_plant[current_plant]["subroutes"].append(line.lstrip("- ").strip())

        elif line.startswith("RECHAZADO:"):
            customer = line.split(":")[-1].strip()
            total_count += 1
            data_by_plant[current_plant]["rejects"].append({
                "customer": customer,
                "pallets": 0,
                "reason": "Priorización por eficiencia"
            })
            
        elif line.startswith("- Carga:"):
            try:
                pallets = float(re.search(r"(\d+\.?\d*)", line).group(1))
                total_pallets += pallets
                if data_by_plant[current_plant]["rejects"]:
                    data_by_plant[current_plant]["rejects"][-1]["pallets"] = pallets
            except: pass
            
        elif line.startswith("- Diagnostico:"):
            reason = line.split(":")[-1].strip()
            if data_by_plant[current_plant]["rejects"]:
                data_by_plant[current_plant]["rejects"][-1]["reason"] = reason

    # Estilos CSS Premium inline para maxima compatibilidad
    css_styles = """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f8fafc; color: #1e293b; letter-spacing: -0.011em; }
        .glass-header { background: rgba(30, 41, 59, 0.98); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,0.1); }
        .plant-card { background: white; border-radius: 20px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
        .camion-header { background-color: #f1f5f9; border-left: 5px solid #3b82f6; padding: 0.75rem 1.25rem; font-weight: 800; color: #334155; font-size: 0.9rem; }
        .customer-row { transition: background 0.2s; border-bottom: 1px solid #f1f5f9; }
        .customer-row:hover { background-color: #f8fafc; }
        .reason-tag { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 6px; background: #fee2e2; color: #991b1b; }
        .success-tag { background: #dcfce7; color: #166534; }
    </style>
    """

    # Construir HTML Premium
    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auditoria Logistica Premium</title>
    <script src="https://cdn.tailwindcss.com"></script>
    {css_styles}
</head>
<body class="pb-24">
    <header class="glass-header text-white p-10 mb-12 sticky top-0 z-50 shadow-xl">
        <div class="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
            <div>
                <h1 class="text-4xl font-black tracking-tighter mb-2">Auditoria de Exclusiones</h1>
                <p class="text-slate-400 font-medium">Análisis detallado de carga y rechazos por Planta</p>
            </div>
            <div class="flex gap-8 text-center bg-slate-800/50 p-6 rounded-2xl border border-white/5">
                <div>
                    <div class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Total Pedidos</div>
                    <div class="text-3xl font-black">{total_count}</div>
                </div>
                <div class="w-px h-10 bg-slate-700 my-auto"></div>
                <div>
                    <div class="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Pallets Excluidos</div>
                    <div class="text-3xl font-black">{total_pallets:.1f}</div>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-5xl mx-auto px-6 space-y-12">
"""

    for plant, info in data_by_plant.items():
        if not info["rejects"] and not info["subroutes"]: continue
        
        html_template += f"""
        <section class="plant-card">
            <!-- Planta Header -->
            <div class="p-8 border-b border-slate-100 bg-white">
                <div class="flex justify-between items-end">
                    <div>
                        <span class="text-[10px] font-black text-blue-500 uppercase tracking-widest">Unidad Operativa</span>
                        <h2 class="text-3xl font-black text-slate-800 tracking-tighter">Planta: {plant.upper()}</h2>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Utilización de Flota</span>
                        <div class="px-4 py-1.5 bg-slate-100 text-slate-700 rounded-full text-xs font-bold border border-slate-200">
                            {info['fleet_state']}
                        </div>
                    </div>
                </div>
            </div>

            <div class="p-8 space-y-10">
                <!-- Seccion Camiones -->
                <div>
                    <div class="flex items-center gap-2 mb-4 text-slate-400">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"/></svg>
                        <h3 class="text-[10px] uppercase tracking-widest font-black">Subrutas Activas</h3>
                    </div>
                    <div class="grid grid-cols-1 gap-3">
                        {"".join([f'<div class="camion-header">{sub}</div>' for sub in info['subroutes']]) if info['subroutes'] else '<div class="text-slate-400 italic text-sm p-4 border border-dashed rounded-xl">Sin flota activa asignada en esta jornada.</div>'}
                    </div>
                </div>

                <!-- Seccion Descartes -->
                <div>
                    <div class="flex items-center gap-2 mb-4 text-red-500">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                        <h3 class="text-[10px] uppercase tracking-widest font-black">Pedidos Fuera de Ruta</h3>
                    </div>
                    
                    <div class="bg-white rounded-xl border border-slate-100 overflow-hidden">
        """

        if info["rejects"]:
            for rej in info["rejects"]:
                html_template += f"""
                <div class="customer-row p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div class="flex items-center gap-4">
                        <div class="w-1.5 h-1.5 rounded-full bg-red-400"></div>
                        <div>
                            <div class="font-bold text-slate-800 text-sm">{rej['customer']}</div>
                            <div class="text-[10px] text-slate-400 font-bold uppercase">{rej['pallets']} pallets</div>
                        </div>
                    </div>
                    <div class="reason-tag">
                        {rej['reason']}
                    </div>
                </div>
                """
        else:
            html_template += """
            <div class="p-8 text-center">
                <div class="text-green-500 font-black text-xs uppercase tracking-widest mb-1">Operación Exitosa</div>
                <div class="text-slate-400 text-sm">Todos los clientes han sido asignados eficientemente.</div>
            </div>
            """

        html_template += """
                    </div>
                </div>
            </div>
        </section>
        """

    html_template += """
    </main>
    <footer class="mt-24 pb-12 text-center">
        <div class="text-slate-300 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Sistema de Auditoria Logistica</div>
        <div class="w-8 h-1 bg-slate-200 mx-auto rounded-full"></div>
    </footer>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"Reporte generado con {total_count} descartes en {output_path}")

if __name__ == "__main__":
    generate_html_rejections()
