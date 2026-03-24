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
| 🔵 **Potencial** | **Ventanas Horarias (Time Windows - VRPTW)** | Migración de la función objetivo principal de Distancia a Tiempo. Integra franjas de recepción de clientes, tiempos de carga y flujos de tránsito. | Alta | Muy Alto | **4/5** |
| 🔵 **Potencial** | **Flota Heterogénea y Costes Variables** | Asignación de perfiles dinámicos de vehículos (LTL, FTL) con métricas de capacidad (pallets) y *pricing* asimétricos. | Media-Alta | Alto | **3/5** |

---

## 📈 Evaluación de Progreso y Estimación AI (Meta: Abril)

### Estado Actual: **75% del Motor Core Completado**
El motor ya resuelve el problema base con restricciones geográficas, de carga (pallets) y de flota dedicada de forma estable. El dashboard visualiza el ahorro real de kilómetros en vacío.

### Estimación para Entrega Final (IA-Driven)
Asumiendo la fecha límite de **finales de Abril**, este es el tiempo estimado para que una IA complete las dimensiones restantes:

1.  **Ventanas Horarias (VRPTW)**: 2-3 sesiones de trabajo. Requiere reconstruir las matrices de coste para que se basen en segundos y no solo metros.
2.  **Flota Heterogénea**: 1 sesión. Modificando el array `capacities` para admitir valores variables por vehículo.
3.  **Pulido de UI y Storytelling**: 1 sesión. Ajustes finales en el Dashboard para que sea auto-explicativo para el tribunal.

**Conclusión**: En **1 semana de trabajo intensivo (aprox. 5-7 sesiones)**, el modelo puede estar en nivel de "Investigación Avanzada" para el TFM.
