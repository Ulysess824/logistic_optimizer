import zipfile
import os
from pathlib import Path

def zip_delivery(output_zip_name):
    base_dir = Path(__file__).resolve().parent.parent / "outputs"
    zip_path = base_dir / output_zip_name
    
    print(f"Creando paquete de entrega ZIP en: {zip_path}")
    
    # Directorios y archivos que queremos incluir (manteniendo estructura)
    items_to_include = [
        "Presentacion_Logistica.html",
        "HTML_Bodies",
        "maps",
        "results",
        "tables"
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in items_to_include:
            item_path = base_dir / item
            
            if not item_path.exists():
                print(f"  -> WARNING: No encontrado: {item}")
                continue
                
            if item_path.is_file():
                print(f"  -> Agregando archivo: {item}")
                zipf.write(item_path, item)
            else:
                print(f"  -> Agregando carpeta: {item}")
                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        full_path = Path(root) / file
                        # Guardar ruta relativa respecto a 'outputs'
                        rel_path = full_path.relative_to(base_dir)
                        zipf.write(full_path, rel_path)
    
    print(f"\nExito: Paquete ZIP generado ({os.path.getsize(zip_path)/(1024*1024):.2f} MB)")
    print("Instrucciones: Descomprimir el archivo y abrir 'Presentacion_Logistica.html'")

if __name__ == "__main__":
    zip_delivery("Entrega_TFM_Echandi.zip")
