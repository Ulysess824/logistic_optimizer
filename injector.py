import re

with open('temp_html_utf8.html', 'r', encoding='utf-8') as f:
    html_old = f.read()

with open('outputs/Presentacion_Logistica.html', 'r', encoding='utf-8') as f:
    html_new = f.read()

match = re.search(r'(<tbody class="divide-y divide-gray-100">.*?</tbody>)', html_old, re.DOTALL)
if match:
    tbody_content = match.group(1)
    
    # We replace the empty tbody with the one we found
    new_html = re.sub(
        r'<tbody\s+id="km-table-tbody"\s+class="divide-y\s+divide-gray-100">\s*<!--.*?-->\s*</tbody>', 
        tbody_content, 
        html_new, 
        flags=re.DOTALL
    )
    
    with open('outputs/Presentacion_Logistica.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("Tbody inyectado con exito.")
else:
    print("No se encontro el tbody.")
