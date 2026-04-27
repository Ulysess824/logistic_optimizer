import json
from docx import Document
import os

# 1. Cargar métricas dinámicas
metrics_path = "results_analysis/investment_metrics.json"
with open(metrics_path, "r", encoding="utf-8") as f:
    metrics = json.load(f)

d_res = metrics["diesel"]
e_res = metrics["electrico"]

# 2. Cargar documentos
files = ["Anexo_Tecnico_Metodologia_TFM.docx", "FINAL_SUBMISSION_TFM/Anexo_Tecnico_Metodologia_TFM.docx"]

for doc_path in files:
    if os.path.exists(doc_path):
        doc = Document(doc_path)
        print(f"Actualizando {doc_path} con ingresos indexados...")

        # Actualizar sección de resultados
        for p in doc.paragraphs:
            if "Resultados Simulados (Modelo Dinámico DCF con Conductor):" in p.text:
                p.text = "Resultados Simulados (Modelo Dinámico DCF con Conductor):"
                p.text += f"\n- Diésel Euro VI: {d_res['anos']:.1f} años ({d_res['km']:_.0f} km)"
                p.text += f"\n- Eléctrico BEV: {e_res['anos']:.1f} años ({e_res['km']:_.0f} km)"
            
            if "ROI Proyectado (5a Dinámico):" in p.text:
                p.text = f"ROI Proyectado (5a Dinámico): Diésel {d_res['roi']:.1f}% | Eléctrico {e_res['roi']:.1f}%"
            
            if "TIR (Tasa Interna de Retorno - DCF):" in p.text:
                p.text = f"TIR (Tasa Interna de Retorno - DCF): Diésel {d_res['tir']:.1f}% | Eléctrico {e_res['tir']:.1f}%"

        doc.save(doc_path)
        print(f"Sincronización completada para {doc_path}")
