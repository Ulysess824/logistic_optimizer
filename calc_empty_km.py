import json
from src.utils.geo import GeoUtils

def main():
    with open('outputs/results/optimized_routes.json', 'r', encoding='utf-8') as f:
        routes = json.load(f)
    
    geo = GeoUtils()
    
    print("<!-- Tabla de impacto de Km Vacíos -->")
    print('<table class="min-w-full bg-white text-sm border mt-4">')
    print('<thead class="bg-gray-100">')
    print('<tr>')
    print('<th class="py-2 px-4 border-b text-left font-semibold text-gray-700">Ruta / Origen</th>')
    print('<th class="py-2 px-4 border-b text-center font-semibold text-gray-700">Km Vacíos (Tradicional)</th>')
    print('<th class="py-2 px-4 border-b text-center font-semibold text-gray-700">Km Vacíos (Optimizado)</th>')
    print('<th class="py-2 px-4 border-b text-center font-semibold text-gray-700">Ahorro Neto (Km)</th>')
    print('<th class="py-2 px-4 border-b text-center font-semibold text-gray-700">Mejora (%)</th>')
    print('</tr>')
    print('</thead>')
    print('<tbody class="text-gray-700">')

    total_empty_before = 0
    total_empty_after = 0

    for i, route in enumerate(routes, 1):
        depot = route[0]
        plant = route[1]
        last_customer = route[-2]
        
        # Km vacío antes (Planta -> Depot)
        empty_before = geo.haversine_km(plant['lat'], plant['lng'], depot['lat'], depot['lng'])
        
        # Km vacío después (Último Cliente -> Depot)
        empty_after = geo.haversine_km(last_customer['lat'], last_customer['lng'], depot['lat'], depot['lng'])
        
        savings_km = empty_before - empty_after
        improvement_pct = (savings_km / empty_before) * 100 if empty_before > 0 else 0
        
        total_empty_before += empty_before
        total_empty_after += empty_after

        plant_name = plant['name'].replace('Smurfit Westrock ', '')
        
        print('<tr class="border-b">')
        print(f'<td class="py-2 px-4 font-semibold">{i} - {plant_name}</td>')
        print(f'<td class="py-2 px-4 text-center text-red-500 font-mono">{empty_before:.2f} km</td>')
        print(f'<td class="py-2 px-4 text-center text-green-600 font-mono">{empty_after:.2f} km</td>')
        print(f'<td class="py-2 px-4 text-center font-bold text-blue-600">{savings_km:.2f} km</td>')
        print(f'<td class="py-2 px-4 text-center font-bold text-blue-600">{improvement_pct:.1f}%</td>')
        print('</tr>')
        
    total_savings = total_empty_before - total_empty_after
    total_pct = (total_savings / total_empty_before) * 100 if total_empty_before > 0 else 0
    
    print('<tr class="bg-gray-50 border-t-2 border-gray-300">')
    print('<td class="py-3 px-4 font-bold text-right uppercase">TOTAL FLOTA</td>')
    print(f'<td class="py-3 px-4 text-center font-bold text-red-600">{total_empty_before:.2f} km</td>')
    print(f'<td class="py-3 px-4 text-center font-bold text-green-600">{total_empty_after:.2f} km</td>')
    print(f'<td class="py-3 px-4 text-center font-extrabold text-blue-700">{total_savings:.2f} km</td>')
    print(f'<td class="py-3 px-4 text-center font-extrabold text-blue-700">{total_pct:.1f}%</td>')
    print('</tr>')

    print('</tbody>')
    print('</table>')

if __name__ == "__main__":
    main()
