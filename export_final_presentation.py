import os
import shutil
from pathlib import Path

def export_submission():
    print("Iniciando empaquetado final de la Presentación TFM...")
    
    # 1. Configurar rutas origen y destino
    root_dir = Path(".")
    outputs_dir = root_dir / "outputs"
    export_dir = root_dir / "FINAL_SUBMISSION_TFM"
    
    # Crear carpeta de entrega limpia
    if export_dir.exists():
        shutil.rmtree(export_dir)
    os.makedirs(export_dir, exist_ok=True)
    
    # 2. Archivos a copiar a la RAÍZ
    files_to_copy = [
        ("outputs/Presentacion_Logistica.html", "Presentacion_Logistica.html"),
        ("custom.css", "custom.css"),
        ("Anexo_Tecnico_Metodologia_TFM.docx", "Anexo_Tecnico_Metodologia_TFM.docx")
    ]
    
    # 2.1. Copiar automáticamente cualquier GIF o PNG de la raíz de outputs a la raíz de entrega
    # Esto es crítico para la animación de simulación
    outputs_path = root_dir / "outputs"
    if outputs_path.exists():
        for ext in ["*.gif", "*.png"]:
            for asset_file in outputs_path.glob(ext):
                shutil.copy2(asset_file, export_dir / asset_file.name)
                print(f"OK (Asset): {asset_file.name} -> Entrega")

    # 3. Directorios a copiar (Ecosistema completo)
    dirs_to_copy = [
        ("outputs/HTML_Bodies", "HTML_Bodies"),
        ("results_analysis", "results_analysis"), # Excel Reports
        ("outputs/maps", "maps"),                 # Folium Maps
        ("outputs/results", "results"),           # Pyvis Graphs
        ("outputs/tables", "tables"),             # COMPARATIVAS Baseline (CRÍTICO)
        ("outputs/assets", "assets")              # Simulation GIFs/Images
    ]
    
    print("-" * 30)
    
    # Copiar archivos individuales
    for src_rel, dest_rel in files_to_copy:
        src = root_dir / src_rel
        dest = export_dir / dest_rel
        if src.exists():
            shutil.copy2(src, dest)
            print(f"OK: {src_rel} -> {dest_rel}")
            
    # Copiar directorios
    for src_rel, dest_rel in dirs_to_copy:
        src = root_dir / src_rel
        dest = export_dir / dest_rel
        if src.exists():
            shutil.copytree(src, dest, dirs_exist_ok=True)
            print(f"OK: Directorio {src_rel} -> {dest_rel}")

    # 4. REPARACIÓN DE ENLACES (PORTABILIDAD TOTAL - VERSIÓN MAESTRA)
    # Corregimos todas las subcarpetas de la entrega
    bodies_path = export_dir / "HTML_Bodies"
    if bodies_path.exists():
        print("Realizando barrido de portabilidad maestro en todos los módulos...")
        for html_file in bodies_path.glob("*.html"):
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # REPARACIÓN DE RUTAS DINÁMICA
            # Convertimos cualquier ruta de desarrollo (que sube 2 niveles) a ruta de entrega (que sube 1 nivel)
            new_content = content.replace("../../results_analysis/", "../results_analysis/")
            new_content = new_content.replace("../../results/", "../results/")
            new_content = new_content.replace("../../assets/", "../assets/")
            new_content = new_content.replace("../../maps/", "../maps/")
            
            # También arreglamos enlaces que suban solo 1 nivel si el archivo está en la raíz en la entrega
            # (Ej: tab_grafo.html apuntando a ../results/ sigue siendo ../results/ en la entrega)
            # El reemplazo de ../../ por ../ es el más crítico.
            new_content = new_content.replace("../../", "../")
            
            if new_content != content:
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"   Refactorizado: {html_file.name}")

    print("-" * 30)
    print(f"EMPAQUETADO COMPLETADO EXITOSAMENTE.")
    print(f"Ruta de entrega: {export_dir.absolute()}")
    print("REQUISITO: La persona que lo reciba necesita INTERNET para cargar mapas y estilos.")

if __name__ == "__main__":
    export_submission()
