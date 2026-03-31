import os
with open('outputs/maps/Logistics_Dashboard.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    if 'sidebar' in content:
        print("Sidebar found!")
    else:
        print("Sidebar NOT found.")
    if '📦 Logística' in content:
        print("Header found!")
    else:
        print("Header NOT found.")
