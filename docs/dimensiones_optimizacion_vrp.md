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
| 🔵 **Potencial** | **Ventanas Horarias (Time Windows - VRPTW)** | Migración de la función objetivo principal de Distancia a Tiempo. Integra franjas de recepción de clientes, tiempos de carga y flujos de tránsito. | Alta | Muy Alto | **4/5** |
| 🔵 **Potencial** | **Flota Heterogénea y Costes Variables** | Asignación de perfiles dinámicos de vehículos (LTL, FTL, furgonetas ligeras) con métricas de capacidad y *pricing* por kilómetro asimétricas. | Media-Alta | Alto | **3/5** |
| 🔵 **Potencial** | **Reasignación Multi-Viaje (Multi-Trip/Loop)** | Habilidad algorítmica para reutilizar un vehículo que termina temprano y asignarle una segunda ruta corta, optimizando el tamaño total del *pool* de camiones. | Alta | Medio | **2/5** |
| 🔵 **Potencial** | **Normativa Laboral (Tacógrafo Europeo)** | Restricciones duras de descansos obligatorios (ej. 45 min por cada 4.5h conducidas) inyectadas en el árbol de búsqueda de factibilidad del solver. | Muy Alta | Medio-Bajo | **1/5** |

---

## Análisis Estratégico y Justificación para el Tribunal

Las dimensiones potenciales han sido evaluadas y priorizadas ponderando el **Esfuerzo Técnico Algorítmico** frente al **Valor Percibido por un Tribunal de Negocios e Ingeniería**:

### 🎯 Prioridad Máxima (5/5 y 4/5) - Quick Wins de Alto Impacto
*   **Capacidad Física (5/5):** Es el salto cualitativo más evidente y defendible. Un tribunal experto identificará rápidamente que limitar por "paradas" es un cuello de botella analítico. Incorporar restricciones de "Pallets" o "Metros Cúbicos" ratifica el dominio sobre KPIs clave como el *Fill-Rate* y la consolidación volumétrica real.
*   **Ventanas Horarias (4/5):** Acercan el modelo a la fricción operativa del mundo real (B2B). Demuestra capacidad para manejar matrices de restricciones temporales complejas, aunque aumenta considerablemente la carga computacional para encontrar soluciones factibles de forma rápida.

### ⚖️ Prioridad Media (3/5) - Integraciones Transversales
*   **Flota Heterogénea:** Su mayor valor reside en la sinergia con otros apartados del TFM. Permitiría conectar los resultados del **Modelo Hedónico de Tarifas** directamente con el Optimizador, demostrando que el algoritmo selecciona la herramienta de carga óptima basándose en su curva de elasticidad precio-distancia.

### 🔻 Prioridad Baja (1/5 y 2/5) - Sobrecarga Técnica Innecesaria
*   **Normativa de Conducción y Multi-viaje:** Aunque aportan un grado de completitud algorítmica extremo (Nivel de Investigación Operativa Avanzada), la complejidad computacional que añaden puede comprometer los tiempos de ejecución (*solves* que demoran horas en lugar de segundos). Para una defensa de TFM centrada en impacto de negocio, agilidad operativa y viabilidad técnica, el esfuerzo marginal de programar estas restricciones estocásticas excede con creces el retorno académico.
