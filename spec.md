# Especificaciones del Proyecto para IA (AI_SPEC.md)

Este documento sirve como contexto y guía para cualquier agente de Inteligencia Artificial que vaya a interactuar, modificar o expandir el repositorio `logistics_optimizer`.

## 1. Contexto del Proyecto

**Logistics Optimizer** es un sistema de optimización de rutas logísticas. Se desarrolló originalmente para la cadena de suministro de papel y cartón (ej., con origen en una planta papelera en Mengíbar, pasando por plantas de cartón ondulado y terminando en los clientes) minimizando los "kilómetros en vacío" (empty miles) en el retorno. 

El modelo resuelve variantes del **Vehicle Routing Problem (VRP)** como el **MC-VRPB** (Multi-Commodity VRP with Backhauls).

### Flujo Principal:
1. **Carga Inicial:** Sale del depósito central (papelera, ej. Mengíbar).
2. **Pickup (Plantas Intermedias):** Visita 1 o varias plantas para descargar materia prima y cargar producto final.
3. **Distribución (Clientes):** Entrega el producto a clientes ubicados cerca de la ruta de vuelta.
4. **Retorno:** El camión vuelve al depósito central.

## 2. Arquitectura del Código

El código sigue una arquitectura modular en Python 3.12:

```text
logistics_optimizer/
│
├── main.py                          # Punto de entrada y orquestador. Define parámetros (ej. MANDATORY_CUSTOMERS)
├── refresh_dashboard.py               # Utilidad para actualizar el HTML sin re-ejecutar el solver.
├── ejemplo_simulacion.py              # Script para ejecutar la simulación de flota y generar el GIF.
├── src/                             # Código fuente principal
│   ├── config.py                    # Variables de entorno y rutas.
│   ├── engine/
│   │   └── solver.py                # Contiene LogisticsSolver (OR-Tools) con lógica de Disjunctions (Soft Constraints).
│   ├── simulation/
│   │   ├── camion.py                # Clase TruckSimulated (SimPy). Usa duraciones reales de la caché.
│   │   ├── animador.py              # Clase AnimadorLogistico (GIFs). Soporta polilíneas de carretera.
│   │   └── __init__.py
│   └── utils/
│       ├── data_manager.py          # DataManager: Soporta 'Mandatory Customers'.
│       ├── geo.py                   # Google Routes API v2 + GeoCache (SQLite).
│       ├── visualizer.py            # Mapas (Folium) y Grafos (Plotly).
│       └── report_generator.py      # Generación dinámica del Dashboard interactivo.
│
├── data/                            # Directorio de entradas (JSON, Excel, DB Cache).
└── outputs/                         # Resultados, Mapas, y GIFs.
```

## 3. Guía para Expandir Funcionalidades (Para IA)

Si recibes la orden de agregar nuevas funciones, sigue estas pautas:

- **Cambio de Lógica o Restricciones del VRP:** Las reglas de ruteo y penalizaciones van en `src/engine/solver.py`.
- **Preprocesamiento o Filtros de Datos:** `src/utils/data_manager.py`. Aquí se gestiona el filtrado Haversine inicial y la lógica de clientes obligatorios.
- **Geolocalización y Caché:** `src/utils/geo.py` maneja las peticiones a Google. La persistencia de rutas (distancia, duración, polilíneas) está en `data/geo_cache.db` vía `geo_cache.py`.
- **Dashboard:** Se actualiza mediante `report_generator.py`. Las rutas para las tablas provienen de `outputs/results/optimized_routes.json`.
- **Reglas del Usuario (IMPORTANTE):** 
  - *No modifiques archivos sin autorización explícita* (excepto run_command o si te fue pedido concretamente).
  - *IMPORTANTE:* Cada vez que se modifique una **clase o método**, debes entregar un script de ejemplo o explicación clara de cómo usarlo al usuario. 
  - Si el usuario te pregunta por qué no funciona el código o te hace una pregunta del código, NO modifiques nada, solo explica.
  - Si en el desarrollo de una nueva funcionalidad ocurre un bug(s) debes darle en una tabla resumen al usuario que pasó, por qué y como se solucionó.

## 4. Dependencias Principales
- `ortools` (Optimización combinatorial).
- `folium` (Mapas interactivos).
- `simpy` (Simulación de eventos discretos).
- `googlemaps` (Geocoding y Routing clásico).
- `polars` (Procesamiento de datos de alto rendimiento en DataManager).

## 5. Estado Actual (Marzo 2027): El sistema es SOTA (State of the Art) en logística de backhauling. Utiliza **Google Routes API v2** con perfiles de camión pesados y una caché persistente en SQLite. La lógica de optimización se basa en **Disjunctions (Soft Constraints)** con penalizaciones diferenciadas para plantas y obligatorios, garantizando siempre una solución válida y permitiendo ejecuciones de orquestación única (Optimización + Simulación + Dashboard).
