import json

path = "data/cliente_ubi.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Ciudad Real es CP 13001
new_entry = {
    "municipio_destino": "Ciudad Real",
    "pais_destino": "España",
    "latitude": 38.9836,
    "longitude": -3.9288,
    "n_pallets": 28,
    "remontar": 0,
    "year": 2025,
    "month": 4
}

if "13001" in data:
    data["13001"].append(new_entry)
else:
    data["13001"] = [new_entry]

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("¡Pedido de Ciudad Real (Abril 2025) inyectado con éxito!")
