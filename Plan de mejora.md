# Plan de Mejora: Logistics Optimizer & Modelo Financiero

Este documento detalla las propuestas de evolución técnica para el proyecto de optimización logística, categorizadas por área funcional, prioridad y tiempo estimado de ejecución para una IA.

---

## 1. Grupo: Optimizador (Engine)

El optimizador actual utiliza OR-Tools con una configuración sólida de MC-VRPB, pero puede ganar competitividad mediante el refinamiento de su función de coste y restricciones operativas.

| Mejora Propuesta | Descripción | Prioridad | Tiempo Ejecución (IA) |
| :--- | :--- | :--- | :--- |
| **Optimización Dinámica de Costes (Cost Function)** | Sustituir la penalización fija de retorno (`*2.5`) por una función que integre el coste real por km según el TCO, diferenciando entre km cargado y km en vacío. | **Alta** | 1 hora |
| **Restricción de Ventanas Temporales (TW)** | Implementar `TimeWindows` para asegurar que las entregas en clientes se realicen en horarios comerciales, evitando rutas teóricas no ejecutables. | **Media** | 3 horas |
| **Balanceo de Carga Estocástico** | Incorporar un factor de seguridad en la demanda (`demanda_pallets`) frente a la variabilidad real, optimizando rutas que no vayan al 100% del límite físico para evitar fallos en carga real. | **Media** | 1.5 horas |
| **Integración de Tráfico Real** | Conectar con el motor de OSRM/Google para obtener `travel_times` dinámicos según la hora de salida, no solo distancias estáticas. | **Baja** | 4 horas |
| **Refactorización de "Muelles Virtuales"** | Limpiar la lógica de clonación de nodos en `solver.py` para que sea más escalable y permita flotas heterogéneas (camiones de distinto tamaño). | **Baja** | 2 horas |

---

## 2. Grupo: Modelo Financiero

El modelo financiero es robusto en parámetros (WACC, CAPEX), pero actúa de forma estática. La mejora debe enfocarse en la granularidad y la integración con la simulación.

| Mejora Propuesta | Descripción | Prioridad | Tiempo Ejecución (IA) |
| :--- | :--- | :--- | :--- |
| **Modelo de Coste Granular (Variable vs Fijo)** | Desglosar el `INTERNAL_OPERATIONAL_TCO_RATE` en: Combustible (variable por carga), Conductor (fijo/por hora), Neumáticos y Mantenimiento. | **Alta** | 1.5 horas |
| **Dashboard de Sensibilidad ROI/PAYBACK** | Crear un script que tome los resultados de la simulación anual y genere una tabla de sensibilidad frente a cambios en el precio del diesel o tipos de interés. | **Alta** | 2.5 horas |
| **Cálculo de Inactividad (Idling/Standing)** | Integrar el coste de oportunidad del camión parado. Si una ruta es muy corta, el modelo financiero debe penalizar la infrautilización del activo. | **Media** | 2 horas |
| **Automatización de Auditoría GLEC v3.0** | Refinar el cálculo de CO2 basado en los consumos reales derivados de la carga de cada tramo, superando la estimación lineal actual. | **Media** | 2 horas |
| **Vinculación con Incertidumbre (Monte Carlo)** | Ejecutar el modelo financiero sobre 100 variaciones de demanda diaria para obtener un intervalo de confianza del ahorro esperado. | **Baja** | 3 horas |

---

## Diagnóstico Técnico Preliminar

### Optimizador
*   **Estado:** Funcional y robusto para rutas punto a punto con retorno (VRPB).
*   **Debilidad:** La función de arco (`arc cost`) es puramente técnica/geométrica. No "entiende" de rentabilidad directa ni de restricciones humanas (tiempos de conducción).
*   **Oportunidad:** Convertir el solver en un motor de "Margen de Contribución" en lugar de "Mínima Distancia".

### Modelo Financiero
*   **Estado:** Excelente base de datos de costes (CAPEX/OPEX) alineada con estándares del MITMA.
*   **Debilidad:** Desconexión relativa en el flujo automático. Los resultados de la simulación diaria reportan un "coste total" basado en un ratio plano, lo que puede ocultar ineficiencias en rutas de montaña o con mucha carga.
*   **Oportunidad:** Integrar el modelo financiero como la verdadera "función objetivo" del optimizador.
