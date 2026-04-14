# Contexto del Proyecto: Logistics Optimizer

## Propósito
**Logistics Optimizer** es una solución avanzada de optimización y simulación logística desarrollada en Python. Su objetivo principal es la reducción de "kilómetros en vacío" (empty miles) mediante estrategias de **backhauling** (aprovechamiento del viaje de retorno). Originalmente diseñado para la industria del papel y cartón, el sistema permite optimizar rutas que parten de un depósito central, visitan plantas de producción y entregan a clientes finales antes de regresar a la base.

## Arquitectura y Estructura
El proyecto sigue una estructura modular y profesional:

### 1. Núcleo Lógico (`logistic_core/`)
*   **`engine/solver.py`**: Utiliza **Google OR-Tools** para resolver el VRP. Implementa "Soft Constraints" (Disjunctions) para garantizar que el modelo siempre converja, incluso en escenarios extremos.
*   **`simulation/`**: Módulo basado en **SimPy** para simular la operación real de la flota, incluyendo tiempos de carga/descarga y tránsito.
*   **`utils/`**:
    *   `data_manager.py`: Preprocesamiento de datos y filtrado geográfico (Haversine + Elipse de desvío).
    *   `geo.py`: Integración con **Google Routes API v2** y sistema de caché en SQLite.
    *   `financial_analyzer.py`: Motor de inteligencia financiera para comparar escenarios *Asset-Light* vs *Asset-Heavy* y calcular ROI/Payback.
    *   `fcr_estimator.py`: Cálculo de huella de carbono bajo el estándar científico **GLEC v3.0**.
    *   `capacity_estimator.py`: Optimización volumétrica 3D para la carga de pallets en tráilers de 13.6m.

### 2. Datos y Configuración
*   **`data/`**: Contiene los archivos JSON de clientes, plantas y demanda, así como la base de datos de caché geográfica.
*   **`logistic_core/config.py`**: Centraliza parámetros críticos como factores de emisión, costes operativos (TCO), y especificaciones técnicas de los vehículos.

### 3. Salidas y Visualización (`outputs/`)
*   **`Presentacion_Logistica.html`**: Dashboard interactivo premium que integra mapas de **Folium**, grafos de **Plotly** y tablas de KPIs financieros y operativos.
*   **`results/`**: Almacena los resultados de las optimizaciones en formato JSON para su posterior análisis.

## Tecnologías Principales
*   **Optimización**: OR-Tools (VRP, Bin Packing).
*   **Simulación**: SimPy.
*   **Geospatial**: Google Routes API, Folium, Polyline.
*   **Datos**: Polars, Pandas.
*   **Frontend**: HTML5/TailwindCSS (para el Dashboard).

## Estado del Proyecto
El sistema es **SOTA (State of the Art)** en logística de retorno, integrando perfiles de vehículos pesados (emisiones, altura, peso) y una metodología de cálculo de CO2 auditada. Permite actualizaciones modulares del dashboard y simulaciones dinámicas con generación de GIFs.
