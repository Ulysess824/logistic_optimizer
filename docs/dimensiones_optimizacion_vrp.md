# Análisis Dimensional del Optimizador VRP: Estado Actual y Evolución

Este documento presenta una evaluación técnica y de negocio sobre las dimensiones matemáticas gestionadas por el motor de optimización **MC-VRPB** (*Multi-Plant Carton - Vehicle Routing Problem with Backhauling*). 

Se detallan las dimensiones actualmente integradas en el pipeline logístico y se priorizan estratégicamente (del 1 al 5) aquellas que aportarían mayor valor en futuras iteraciones iteraciones del producto, formulando una hoja de ruta ideal para la defensa del Trabajo de Fin de Máster (TFM).

## Matriz de Dimensiones Logísticas

| Estado | Dimensión Logística | Descripción Técnica (Implementación en OR-Tools) | Complejidad de Implementación | Impacto en Negocio | Prioridad TFM (1 a 5) |
| :---: | :--- | :--- | :---: | :---: | :---: |
| 🟢 **Aplicada** | **Distancia (Distance)** | Minimización de kilómetros reales (vía API). Estructura el *Backhauling* forzando matemáticamente la precedencia (Planta → Cliente) mediante variables cumulativas (`CumulVar`). | Alta | Crítico | **5/5** |
| 🟢 **Aplicada** | **Nº de Plantas (PlantCount)** | Restricción estructural que limita dinámicamente cuántas ubicaciones de carga (carton plants) puede consolidar un mismo vehículo en la ruta de bajada. | Baja | Crítico | **5/5** |
| 🟢 **Aplicada** | **Capacidad Estática (CustomerCount)** | Límite máximo de entregas por vehículo. Actúa como una "capacidad discreta" para aproximar la saturación de los tráilers propios. | Baja | Alto | **4/5** |
| 🟢 **Aplicada** | **Capacidad Física Acumulada (Volumen/Pallets)** | Transición de "nº paradas" a demanda real física (ej. 35 pallets max). Implementación mediante `AddDimensionWithVehicleCapacity` acoplado matemáticamente a condicionales `ActiveVar` para un bin-packing a prueba de fallos. | Media | Crítico | **5/5** |
| 🟢 **Aplicada** | **Flota Específica y Muelles** | Definición de número de camiones dedicados por planta y gestión de "muelles virtuales" (clonación de nodos) para permitir múltiples salidas de una misma ubicación. | Media | Crítico | **5/5** |
| 🟢 **Aplicada** | **Sostenibilidad (CO2)** | Cálculo de emisiones basado en factor de carga (FCR) y kilometraje. Permite visualizar el impacto ambiental del backhauling frente al modelo tradicional. | Baja-Media | Muy Alto | **5/5** |
| 🟢 **Aplicada** | **Estimación Económica (Costes)** | Integración de KPis financieros (1.14 €/km) para comparar ROI. Permite justificar la optimización frente a gastos operativos reales. | Baja | Crítico | **5/5** |
| 🔵 **Potencial** | **Ventanas Horarias (Time Windows - VRPTW)** | Migración de la función objetivo principal de Distancia a Tiempo. Integra franjas de recepción de clientes, tiempos de carga y flujos de tránsito. | Alta | Muy Alto | **4/5** |
| 🔵 **Potencial** | **Flota Heterogénea y Costes Variables** | Asignación de perfiles dinámicos de vehículos (LTL, FTL) con métricas de capacidad (pallets) y *pricing* asimétricos. | Media-Alta | Alto | **3/5** |

## Matriz de Impacto Económico (Rentabilidad)

| Dimensión Económica | Indicador / Fórmula | Beneficio AS-IS vs TO-BE | Impacto Estratégico |
| :--- | :--- | :--- | :---: |
| **ROI (3-5 años)** | `(Beneficio Total - Coste) / Coste` | Reducción del 20% en km totales proyecta ROI >45%. | **Crítico** |
| **Payback Period** | `Inversión / Ahorro Anual Neto` | Retorno estimado en **< 1.5 años** por ahorro de combustible. | **Alto** |
| **Coste por Ton-Km** | `Total Cost / (Total Tons · Total Km)` | Dilución de costes fijos al eliminar el 100% de vacío en retorno. | **Muy Alto** |
| **Break-even** | `CF / (Tarifa Backhaul - CV)` | Determina el volumen crítico de recogidas para rentabilidad. | **Medio-Alto** |
| **Ingresos Extra** | `Tarifa Flete Retorno` | Conversión de **coste muerto** en ingreso neto real. | **Crítico** |

---

## 📈 Evaluación de Progreso y Estimación AI (Meta: Abril)

### Estado Actual: **85% del Motor Core Completado** (Nivel Avanzado)
El motor ya resuelve el problema completo con restricciones geográficas, físicas (pallets) y **financieras/ambientales** de forma integrada. El dashboard comparativo "Cara a Cara" por ruta es el cierre funcional de la lógica de negocio.

### Estimación para Entrega Final (IA-Driven)
Asumiendo la fecha límite de **finales de Abril**, este es el tiempo estimado para que una IA complete las dimensiones restantes:

1.  **Ventanas Horarias (VRPTW)**: 2 sesiones de trabajo. Requiere pasar de la "Distancia" al "Tiempo de Tránsito" como dimensión principal (usando matrices de segundos).
2.  **Flota Heterogénea**: 1 sesión. Implementar perfiles de camión (Rígido vs Tráiler) con capacidades asimétricas.
3.  **Análisis de Sensibilidad Final**: 1 sesión. Uso del Laboratorio de Experimentos para extraer las conclusiones definitivas del TFM.

**Conclusión**: En **menos de 4 sesiones de trabajo focalizado**, el proyecto alcanzará el nivel de **Excelencia Técnica** para la defensa del TFM.
