import os
import re
import base64
from pathlib import Path

def process_html_recursively(file_path, base_dir):
    """
    Lee un archivo HTML, busca iframes y embebe su contenido de forma recursiva.
    """
    if not os.path.exists(file_path):
        print(f"  -> ERROR: No encontrado: {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex para capturar <iframe src="...">
    # Capturamos el src y nos aseguramos de no procesar data URIs ya procesados
    iframe_pattern = re.compile(r'<iframe\s+[^>]*src=["\']((?!data:)[^"\']+)["\'][^>]*>', re.IGNORECASE)
    
    # Directorio actual para resolver rutas relativas
    current_dir = Path(file_path).parent

    def replace_iframe(match):
        src_attr = match.group(1)
        full_tag = match.group(0)
        
        # Limpiar query params (ej: ?v=1.2)
        clean_src = src_attr.split('?')[0]
        
        if clean_src.startswith('http'):
            return full_tag  # No procesar externos
            
        # Resolver ruta absoluta respecto al archivo actual
        target_path = (current_dir / clean_src).resolve()
        
        print(f"  -> Procesando nivel: {clean_src}")
        
        # Llamada recursiva para procesar iframes dentro del sub-archivo
        sub_content = process_html_recursively(target_path, base_dir)
        
        if sub_content:
            # Codificar a Base64
            encoded = base64.b64encode(sub_content.encode('utf-8')).decode('utf-8')
            data_uri = f"data:text/html;charset=utf-8;base64,{encoded}"
            return full_tag.replace(src_attr, data_uri)
        
        return full_tag

    # Reemplazar todos los hallazgos en este nivel
    new_content = iframe_pattern.sub(replace_iframe, content)
    return new_content

def create_standalone_dashboard(input_path, output_path):
    print(f"Iniciando empaquetado RECURSIVO de: {input_path}")
    base_dir = Path(input_path).parent
    
    final_html = process_html_recursively(input_path, base_dir)
    
    if final_html:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"\nExito: Dashboard 100% standalone generado en: {output_path}")
        print(f"Tamano final: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
    else:
        print("Error en el procesamiento.")

if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent / "outputs"
    input_file = base / "Presentacion_Logistica.html"
    output_file = base / "presentación TFM_echandi.html"
    
    create_standalone_dashboard(input_file, output_file)
