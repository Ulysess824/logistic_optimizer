import unittest
from logistic_core.utils.investment_analyst import LeasingInversionAnalyst

class TestLeasingInversionAnalyst(unittest.TestCase):
    def test_analysis_output(self):
        analyst = LeasingInversionAnalyst()
        results = analyst.analyze_investment()
        
        # Verificar que tenemos las claves necesarias
        self.assertIn("npv_buy", results)
        self.assertIn("npv_lease", results)
        self.assertIn("recommendation", results)
        
        # Verificar tipos de datos
        self.assertIsInstance(results["npv_buy"], float)
        self.assertIsInstance(results["npv_lease"], float)
        
        # Comprobar recomendación lógica (si el leasing es más caro en NPV, compra gana)
        # Nota: en nuestro modelo financiero, el VPN es negativo (coste), por lo que 
        # el mayor (menos negativo) es el mejor.
        if results["npv_lease"] > results["npv_buy"]:
            self.assertEqual(results["recommendation"], "LEASING")
        else:
            self.assertEqual(results["recommendation"], "COMPRA")

    def test_specialized_surcharge(self):
        analyst = LeasingInversionAnalyst()
        # El mantenimiento de compra debe ser mayor que el base debido al recargo de bobinas
        # Este valor depende de las constantes en config.py
        self.assertGreater(analyst.annual_maint_buy, 10000)

if __name__ == "__main__":
    print("\n--- Ejecutando Prueba de Analista de Inversión ---\n")
    analyst = LeasingInversionAnalyst()
    analyst.print_investor_report()
    
    print("\n--- Ejecutando Tests Automáticos ---\n")
    unittest.main()
