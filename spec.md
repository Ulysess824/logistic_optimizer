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
├── main.py                          # Punto de entrada y orquestador. Define parámetros (ej. N_CLIENTES)
├── src/                             # Código fuente principal
│   ├── config.py                    # Variables de entorno y rutas (RESULTS_DIR, DATA_DIR, etc.)
│   ├── engine/
│   │   └── solver.py                # Contiene LogisticsSolver. Usa Google OR-Tools para el cálculo.
│   └── utils/
│       ├── data_manager.py          # DataManager: Pre-filtra qué clientes son viables mediante umbrales (Haversine).
│       ├── geo.py                   # Lógica de cálculo de distancias (API de Google Maps real o Haversine).
│       ├── visualizer.py            # Generación de mapas interactivos con Folium y grafos con Plotly.
│       └── report_generator.py      # Plantillas Jinja/HTML para empaquetar resultados en un Dashboard final.
│
├── data/                            # Directorio de entradas (JSON).
└── outputs/                         # Rutas exportadas (JSON, Dashboards HTML).
```

## 3. Guía para Expandir Funcionalidades (Para IA)

Si recibes la orden de agregar nuevas funciones, sigue estas pautas:

- **Cambio de Lógica o Restricciones del VRP:** Las reglas de ruteo y penalizaciones van en `src/engine/solver.py`.
- **Preprocesamiento o Filtros de Datos:** Las modificaciones previas al paso del solver van en `src/utils/data_manager.py`.
- **Nuevas Métricas o APIs Geoespaciales:** Se deben agregar en `src/utils/geo.py` o dentro del método `_build_summary` en `main.py`.
- **Nuevos Gráficos:** Agrega los métodos en `src/utils/visualizer.py` y asegúrate de renderizarlos en `report_generator.py`.
- **Reglas del Usuario (IMPORTANTE):** 
  - *No modifiques archivos sin autorización explícita* (excepto run_command o si te fue pedido concretamente).
  - *IMPORTANTE:* Cada vez que se modifique una **clase o método**, debes entregar un script de ejemplo o explicación clara de cómo usarlo al usuario. 
  - Si el usuario te pregunta por qué no funciona el código o te hace una pregunta del código, NO modifiques nada, solo explica.
  - Si en el desarrollo de una nueva funcionalidad ocurre un bug(s) debes darle en una tabla resumen al usuario que pasó, por qué y como se solucionó.
## 4. Dependencias Principales
- `ortools` (Google OR-Tools para optimización combinatorial).
- `folium` (Mapas interactivos).
- `plotly` (Grafos y reportes visuales).
- `pandas` y `numpy` (Tratamiento de datos).

## 5. Estado Actual (Marzo 2026)
El modelo cuenta con la capacidad de usar tiempos y distancias reales (Google Maps API) con fallback a Haversine. Además, el pipeline genera automáticamente un archivo HTML (`outputs/Presentacion_Logistica.html`) interactivo, altamente visual y con una sección metodológica que muestra el rigor matemático.
