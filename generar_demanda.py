import json
import random
from pathlib import Path

def main():
    # Rutas de archivos
    input_file = Path("data/cliente_ubi.json")
    output_file = Path("data/demanda_simulada.json")

    print(f"Leyendo clientes desde {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        clientes_data = json.load(f)

    # Fijar semilla para reproducibilidad
    random.seed(42)

    total_clientes = 0
    # Inyectar demanda a cada cliente
    for cp, destinos in clientes_data.items():
        for destino in destinos:
            # Generar una demanda aleatoria entre 1 y 12 pallets
            destino["demanda_pallets"] = random.randint(10, 33)
            total_clientes += 1

    print(f"Demanda inyectada a {total_clientes} clientes.")

    print(f"Guardando nuevo archivo en {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clientes_data, f, indent=2, ensure_ascii=False)
        
    print("¡Proceso completado con éxito!")

if __name__ == "__main__":
    main()
