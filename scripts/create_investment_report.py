import sys
import os

# Asegurar que el path alcance logistic_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logistic_core.utils.investment_analyzer import InvestmentAnalyzer

def print_separator():
    print("-" * 75)

def main():
    print("===========================================================================")
    print(" 🚛📊 REPORTE DE INVERSIÓN: TCO 44T (A 5 AÑOS) ")
    print("===========================================================================")

    # Escenario: Transporte Intensivo para 44t (~130,000 kms/año)
    kms = 130_000
    analyzer = InvestmentAnalyzer(kms_anuales=kms)
    
    print(f"Parámetros Base:")
    print(f" - Distancia Anual Mínima: {kms:,.0f} km".replace(',', '.'))
    print(f" - Horizonte: 5 Años ({kms * 5:,.0f} km totales)".replace(',', '.'))
    print(f" - Inflación Esperada Anual: {analyzer.inflacion * 100}%")
    print(f" - Tasa de Descuento (WACC): {analyzer.wacc * 100}%\n")
    
    print_separator()
    print(f"{'TECNOLOGÍA & MODO':<35} | {'TCO (VAN acumulado) €':<20} | {'€ / KM (Neto)':<15}")
    print_separator()

    tecnologias = ["diesel", "electrico"]
    
    for tec in tecnologias:
        res_compra = analyzer.evaluar_compra(tec)
        res_leasing = analyzer.evaluar_leasing(tec)
        res_renting = analyzer.evaluar_renting(tec)
        
        fmt_tec = "DIESEL" if tec == "diesel" else "ELÉCTRICO (E-Truck)"
        
        print(f"🔹 {fmt_tec}")
        
        rows = [
            ("Propiedad (Compra direct./crédito)", res_compra),
            ("Leasing Financiero", res_leasing),
            ("Renting Operativo Todo Incluido", res_renting),
        ]
        
        for name, data in rows:
            van_eur = f"{-data['tco_van_acumulado']:,.0f} €".replace(',', '.')
            km_eur = f"{data['coste_neto_por_km']:.3f} €"
            print(f"   {name:<32} | {van_eur:>20} | {km_eur:>15}")
            
        print_separator()

    print("\n🔍 NOTA DE DIAGNÓSTICO:")
    print("El análisis 'TCO VAN Acumulado' representa la salida de caja neta (coste real), ")
    print("descontada al presente e incluyendo pago de impuestos/deducciones (Tax Shield 25%).")
    print("El Valor Residual se recupera en el Año 5 en las modalidades de Compra y Leasing.")

if __name__ == "__main__":
    main()
