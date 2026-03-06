import json
from src.utils.geo import GeoUtils

with open('outputs/results/optimized_routes.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

geo = GeoUtils()

lines = []
lines.append('<!-- Tabla de impacto de Km Vacíos -->')
lines.append('<div class="overflow-x-auto mb-6">')
lines.append('<table class="min-w-full bg-white text-sm border mt-4 rounded-lg shadow">')
lines.append('<thead class="bg-red-50">')
lines.append('<tr>')
lines.append('<th class="py-3 px-4 border-b text-left font-semibold text-red-900 rounded-tl-lg">Ruta / Planta Origen</th>')
lines.append('<th class="py-3 px-4 border-b text-center font-semibold text-red-900">Km Vacíos (Tradicional)</th>')
lines.append('<th class="py-3 px-4 border-b text-center font-semibold text-green-900 bg-green-50">Km Vacíos (MC-VRPB)</th>')
lines.append('<th class="py-3 px-4 border-b text-center font-bold text-blue-900 bg-blue-50">Ahorro Neto (Km)</th>')
lines.append('<th class="py-3 px-4 border-b text-center font-bold text-blue-900 bg-blue-50 rounded-tr-lg">Mejora (%)</th>')
lines.append('</tr>')
lines.append('</thead>')
lines.append('<tbody class="text-gray-700">')

total_empty_before = 0
total_empty_after = 0

for i, route in enumerate(routes, 1):
    depot = route[0]
    plant = route[1]
    last_customer = route[-2]
    
    empty_before = geo.haversine_km(plant['lat'], plant['lng'], depot['lat'], depot['lng'])
    empty_after = geo.haversine_km(last_customer['lat'], last_customer['lng'], depot['lat'], depot['lng'])
    
    savings_km = empty_before - empty_after
    improvement_pct = (savings_km / empty_before) * 100 if empty_before > 0 else 0
    total_empty_before += empty_before
    total_empty_after += empty_after
    
    plant_name = plant['name'].replace('Smurfit Westrock ', '')
    lines.append('<tr class="border-b hover:bg-gray-50">')
    lines.append(f'<td class="py-2 px-4 font-semibold border-r">Ruta {i} - {plant_name}</td>')
    lines.append(f'<td class="py-2 px-4 text-center text-red-500 font-mono">{empty_before:.2f} km</td>')
    lines.append(f'<td class="py-2 px-4 text-center text-green-600 font-mono bg-green-50/30">{empty_after:.2f} km</td>')
    lines.append(f'<td class="py-2 px-4 text-center font-bold text-blue-600 bg-blue-50/30">{savings_km:.2f} km</td>')
    lines.append(f'<td class="py-2 px-4 text-center font-bold text-blue-600 bg-blue-50/30">{improvement_pct:.1f}%</td>')
    lines.append('</tr>')

total_savings = total_empty_before - total_empty_after
total_pct = (total_savings / total_empty_before) * 100 if total_empty_before > 0 else 0

lines.append('<tr class="bg-gray-100 border-t-2 border-gray-400">')
lines.append('<td class="py-3 px-4 font-bold text-right uppercase border-r text-gray-800">Total Flota</td>')
lines.append(f'<td class="py-3 px-4 text-center font-bold text-red-600">{total_empty_before:.2f} km</td>')
lines.append(f'<td class="py-3 px-4 text-center font-bold text-green-600">{total_empty_after:.2f} km</td>')
lines.append(f'<td class="py-3 px-4 text-center font-extrabold text-blue-700">{total_savings:.2f} km</td>')
lines.append(f'<td class="py-3 px-4 text-center font-extrabold text-blue-700">{total_pct:.1f}%</td>')
lines.append('</tr>')
lines.append('</tbody>')
lines.append('</table>')
lines.append('</div>')

with open('table_rendered.html', 'w', encoding='utf-8') as f:
    f.write(chr(10).join(lines))
