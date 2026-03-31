# Plan de Implementación: Dashboard Ejecutivo (Negocio, Finanzas y ESG)

El objetivo central es dotar al optimizador logístico de una capa de presentación y cálculo orientada a directivos, crucial para asegurar la máxima calificación en un entorno académico de *Business School* (IE).

Se proponen **4 partes independientes y secuenciales** para no alterar la lógica existente.

## Parte 1: Motor Auxiliar de Inteligencia Financiera (Backend)

**Objetivo:** Crear un módulo de cálculo financiero autónomo que tome los ahorros por ruta e infiera métricas anualizadas.

**Acciones:**
- [NEW] Crear `logistic_core/utils/financial_analyzer.py`.
- **Funciones a implementar:**
  1. `project_annual_savings(daily_savings, active_days=250)`: Extrapola el ahorro calculado en una ejecución a valores anuales, tanto económicos (€) como medioambientales (CO2).
  2. `calculate_roi(initial_investment, annual_savings, horizon_years=3)`: Calcula el Retorno de Inversión. Se establecerá un costo fijo parametrizable para la inversión inicial en software TMS y horas de consultoría.
  3. `calculate_payback_period(initial_investment, annual_savings)`: Determinación del tiempo de recuperación de la inversión (en meses).
  4. `sensitivity_analysis(base_fuel_price, variations=[-10, -5, 5, 10])`: Genera una tabla de estrés sobre cómo impacta la variación del combustible en el TCO y el ahorro.
- **Riesgo y Seguridad:** Ninguno. Es un script *standalone* que consumirá los outputs preexistentes sin tocar el solver central.

---

## Parte 2: Pestaña "Business Case & Finanzas" (Frontend)

**Objetivo:** Transformar los números del motor financiero en una vista visualmente premium dentro de la arquitectura modular actual.

**Acciones:**
- [MODIFY] `logistic_core/utils/report_generator.py`: Añadir el flujo para generar `tab_finanzas.html`.
- Este módulo leerá el resumen (por ejemplo, `optimization_summary.json`) y el motor financiero de la Parte 1.
- Renderizará utilizando TailwindCSS:
  - Tarjetas (KPI Cards) de Gran Formato con el Ahorro Anual Proyectado (en €), ROI y Payback (meses).
  - Una "Mini-Tabla" visual indicando el Análisis de Sensibilidad (escenarios pesimista, base y optimista).
- Generación del archivo en `outputs/HTML_Bodies/tab_finanzas.html`.

---

## Parte 3: Pestaña "Implantación y Matriz de Riesgos" (Frontend)

**Objetivo:** Abordar la crítica sobre "Gestión del Cambio" y "Business Case" proveyendo un camino claro hacia la ejecución.

**Acciones:**
- [MODIFY] `logistic_core/utils/report_generator.py`: Añadir la función `_generate_implementacion_tab()`.
- Contenidos HTML estáticos (pero con diseño espectacular Tailwind):
  - **Cronograma de Roll-out (Gantt HTML):** Piloto mes 1-2, Ajuste de capacidad, Expansión a todas las plantas, etc.
  - **Matriz de Riesgos y Mitigación:** Grid 2x2. (Riesgo: Rechazo de transportistas -> Mitigación: Gamificación y bonificación; Riesgo: Fallos API OSRM -> Mitigación: caché y fallback a Haversine, etc.).
- Generación de `outputs/HTML_Bodies/tab_implementacion.html`.

---

## Parte 4: Integración y Menú de Navegación

**Objetivo:** Integrar el acceso a las nuevas pestañas en el entorno global de visualización.

**Acciones:**
- [MODIFY] El *wrapper* (probablemente haya que ajustar la plantilla que une los "bodies" o las referencias de inyección en `report_generator.py` o directamente el archivo maestro de reporte de presentación si existe uno de ensamble global).
- Actualizar o crear los botones en el panel principal que apunten a los nuevos HTML creados, manteniendo el diseño responsivo.

## User Review Required

> [!IMPORTANT]
> **Definición de Inversión (CAPEX) Inicial**
> Para que el ROI sea realista, necesitamos fijar un valor de "inversión analítica inicial" en el código. Sugerimos basarnos en un proyecto tipo de implantación algorítmica:
> - Software/TMS: ~15,000 €
> - Consultoría/Gestión de la IA: ~10,000 €
> - Total asimilado: **25,000 €**. ¿Te parece realista para el caso práctico?
>
> **Factor de Proyección Anual**
> ¿Asumimos 250 días al año de operación para el cálculo anualizado?

> [!TIP]
> ¿Estás de acuerdo con arrancar primero con la **Parte 1 (Motor Financiero)** y mostrarte su salida por consola antes de maquetarla en HTML?
