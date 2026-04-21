import os
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

def parse_html_table(soup, tbody_id):
    """Parsea una tabla HTML específica por su ID de tbody."""
    tbody = soup.find('tbody', id=tbody_id)
    if not tbody:
        return None, None

    thead = tbody.parent.find('thead')
    headers = [th.get_text(strip=True) for th in thead.find_all('th')]
    
    rows_data = []
    current_planta_meta = ""
    current_energia_meta = ""
    
    for tr in tbody.find_all('tr'):
        # Caso de fila agrupada (colspan) - común en la tabla de comparación
        parent_td = tr.find('td', colspan=True)
        if parent_td:
            span = parent_td.find('span')
            div = parent_td.find('div')
            if span:
                current_planta_meta = span.get_text(strip=True).replace("PLANTA:", "").strip().upper()
            if div:
                energy_t = div.get_text(strip=True).upper()
                current_energia_meta = "Eléctrico" if "ELÉCTRICO" in energy_t or "ZERO" in energy_t else "Diésel"
            
            # Solo añadimos metadatos si no estamos en la tabla de outsourcing (que es más plana)
            if tbody_id == 'comparison-tbody':
                rows_data.append([current_planta_meta, current_energia_meta] + [parent_td.get_text(strip=True)] + [""] * (len(headers)-1))
            continue
            
        tds = tr.find_all('td')
        if not tds: continue
        
        row_values = []
        # Añadir metadatos solo a la tabla de impacto
        if tbody_id == 'comparison-tbody':
            row_values = [current_planta_meta, current_energia_meta]
        
        for td in tds:
            text = td.get_text(strip=True)
            # Limpieza para que Excel reconozca números
            clean_text = text.replace('€', '').replace('kg', '').replace('%', '').replace(',', '').replace('kWh', '').replace('~', '').replace('km', '').strip()
            try:
                # Si empieza por + o -, intentamos limpiar y convertir
                val_to_check = clean_text.replace('+', '').replace('-', '')
                if val_to_check and all(c in '0123456789.' for c in val_to_check):
                    row_values.append(float(clean_text))
                else:
                    row_values.append(text)
            except:
                row_values.append(text)
                
        rows_data.append(row_values)

    all_headers = headers
    if tbody_id == 'comparison-tbody':
        all_headers = ["TAB PLANTA", "TAB ENERGÍA"] + headers
        
    df_result = pd.DataFrame(rows_data, columns=all_headers)
    return df_result, all_headers

def parse_kpi_grid(soup):
    """Extrae las métricas de alta jerarquía de eficiencia y unit economics."""
    h2 = soup.find('h2', text=lambda t: t and 'Auditoría Operativa' in t)
    if not h2:
        return None
    parent_card = h2.parent
    nested_grid = parent_card.find('div', class_=lambda c: c and 'grid' in c)
    if not nested_grid:
        return None
    
    data = []
    for item in nested_grid.find_all('div', recursive=False):
        ps = item.find_all('p')
        if len(ps) >= 2:
            label = ps[0].get_text(strip=True)
            value = ps[1].get_text(strip=True)
            # Limpiamos el valor para ser numérico si es posible
            clean_v = value.replace('€', '').replace('%', '').replace('kg', '').strip()
            num_val = value
            try:
                num_val = float(clean_v)
            except:
                pass
            data.append({"Métrica": label, "Valor Absoluto": num_val, "Formato Original": value})
            
    return pd.DataFrame(data)

def export_complete_tfm_report(html_source_path, output_excel_path):
    print(f"Exportando reporte multi-hoja desde: {html_source_path}")
    
    if not os.path.exists(html_source_path):
        print(f"Error: No se encuentra {html_source_path}")
        return

    with open(html_source_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    # Hoja 1: Impacto de la Optimización
    df_impacto, _ = parse_html_table(soup, 'comparison-tbody')
    
    # Hoja 2: Comparativa de Outsourcing
    df_outsourcing, _ = parse_html_table(soup, 'outsourcing-tbody')

    # Hoja 3: Auditoría Operativa y Unit Economics
    df_kpis = parse_kpi_grid(soup)

    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        if df_impacto is not None:
            df_impacto.to_excel(writer, sheet_name='Impacto Optimización', index=False)
            ws1 = writer.sheets['Impacto Optimización']
            for column_cells in ws1.columns:
                valid_v = [c.value for c in column_cells if c.value is not None]
                if valid_v:
                    length = max(len(str(v)) for v in valid_v)
                    ws1.column_dimensions[column_cells[0].column_letter].width = min(length + 3, 50)

        if df_outsourcing is not None:
            df_outsourcing.to_excel(writer, sheet_name='Comparativa Outsourcing', index=False)
            ws2 = writer.sheets['Comparativa Outsourcing']
            for column_cells in ws2.columns:
                valid_v = [c.value for c in column_cells if c.value is not None]
                if valid_v:
                    length = max(len(str(v)) for v in valid_v)
                    ws2.column_dimensions[column_cells[0].column_letter].width = min(length + 3, 50)
                    
        if df_kpis is not None:
            df_kpis.to_excel(writer, sheet_name='Indicadores Eficiencia (TFM)', index=False)
            ws3 = writer.sheets['Indicadores Eficiencia (TFM)']
            for column_cells in ws3.columns:
                valid_v = [c.value for c in column_cells if c.value is not None]
                if valid_v:
                    length = max(len(str(v)) for v in valid_v)
                    ws3.column_dimensions[column_cells[0].column_letter].width = min(length + 3, 50)

    print(f"Éxito: Reporte Ejecutivo sincronizado con KPIs generado en {output_excel_path}")

if __name__ == "__main__":
    base_out = Path(__file__).resolve().parent.parent / "outputs"
    html_file = base_out / "HTML_Bodies" / "tab_resumen.html"
    excel_file = base_out / "results" / "Reporte_Ejecutivo_Logistico.xlsx"
    
    export_complete_tfm_report(html_file, excel_file)
