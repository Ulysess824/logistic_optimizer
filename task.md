# Tareas: Dashboard Ejecutivo y Finanzas (Prioridad 2)

## Tareas Principales
- [x] Parte 1: Motor Auxiliar de Inteligencia Financiera
  - [x] Crear el script `logistic_core/utils/financial_analyzer.py`
  - [x] Programar lógica de escenarios Asset-Light vs Asset-Heavy
  - [x] Programar proyecciones anuales (250 días) y cálculo de ROI/Payback
  - [x] Implementar la función de sensibilidad al combustible
  - [x] Crear test sencillo integrado (sin tocar simulación)
- [x] Parte 2: Pestaña Business Case & Finanzas (Frontend)
  - [x] Actualizar `report_generator.py` para invocar `financial_analyzer.py`
  - [x] Diseñar el HTML de la pestaña `tab_finanzas.html` usando TailwindCSS
  - [x] Incluir selector o métricas comparativas "Subcontratar vs Comprar Flota"
- [x] Parte 3: Pestaña Implantación y Matriz de Riesgos (Frontend)
  - [x] Añadir función de generación en `report_generator.py`
  - [x] Construir layout de Gantt de 6 meses
  - [x] Construir la matriz de riesgos (Prioridades IE)
- [x] Parte 4: Integración y Sistema de Navegación
  - [x] Modificar el layout global (`Presentacion_Logistica.html`) para las nuevas *tabs*
  - [x] Validar visualización y responsiveness
