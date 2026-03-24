# 🚚 Logistics Optimizer

Bienvenido a **Logistics Optimizer**, un sistema avanzado en Python diseñado para optimizar el enrutamiento de transporte y la logística de distribución, minimizando específicamente los "kilómetros en vacío" durante las rutas de retorno a la base de operaciones (backhauling).

---

## 🚀 Lo que Llevamos Desarrollado

Actualmente, el proyecto cuenta con un sistema maduro, empaquetado y altamente visual que automatiza los procesos complejos de la cadena de suministro. Esto es lo que se ha logrado construir:

1. **Motor de VRP de Alta Resiliencia**: Usamos Google OR-Tools con una arquitectura de **Restricciones Blandas (Disjunctions)**. Esto permite que el sistema maneje clientes obligatorios en escenarios geográficamente extremos sin fallar ni detenerse, priorizando siempre la viabilidad del negocio y la convergencia global de la flota.
2. **Sistema de GPS Real (Compatible con Camiones)**: Integración precisa para recuperar distancias terrestres a través de la moderna **Google Routes API**, permitiendo perfiles de enrutamiento pesado (emisiones, altura, peso máximo). Posee un sistema de respaldo automático que hace estimaciones geográficas si no hay API disponible.
3. **Smart Data Filtering y Capacidad Física**: El sistema descarta ramificaciones inviables por distancia antes de saturar el motor y aplica **Restricciones Duras de BIN-PACKING (Pallets)**. Un camión descarta inteligentemente clientes si su demanda supera la capacidad paramétrica del tráiler (ej. 35 Pallets).
4. **Dashboard Interactivo Profesional**: En lugar de simples planillas de texto, el proyecto emite un archivo HTML interactivo (`Presentacion_Logistica.html`) combinando Mapas satelitales (Folium), Grafos relacionales (Plotly), y tablas de KPIs matemáticos. **Incluye una sección de metodología con visualización interactiva de la lógica de filtros y elipse de desvío.**
5. **Optimización Multi-Planta (Backhauling Avanzado)**: El solver ahora permite que un mismo vehículo visite múltiples plantas en su ruta de regreso, maximizando la consolidación de carga y reduciendo drásticamente la flota necesaria cuando se activa el modo `VARIAS_PLANTAS`.
6. **Simulación Dinámica de Flotas (SOTA)**: Módulo especializado (`src/simulation/`) que utiliza **SimPy** para modelar la operación real. A diferencia de modelos estáticos, esta simulación:
    - Considera **tiempos de viaje reales** y **polilíneas de carretera** (vía caché de Google).
    - Modela cuellos de botella en **muelles de carga** y **disponibilidad de conductores**.
    - Incluye un parámetro de `desfase_hora` para simular la llegada aleatoria de camiones, evitando sincronizaciones artificiales.
    - Genera animaciones GIF que muestran el flujo logístico sobre el mapa real.

---

## 🔄 ¿Cómo usar este modelo en OTROS CONTEXTOS?

Aunque originalmente se diseñó para la industria del cartón, esta herramienta es **totalmente adaptable a cualquier logística de distribución con backhauling** (entrega de mercancía y recogida en puntos estratégicos de regreso).

### 1. Prepara tus datos (.json)
El modelo espera archivos en la carpeta `data/`:
* **Plantas/Nodos Estratégicos:** Origen (`depot`) y paradas de carga (`carton_plants`).
* **Clientes Finales:** Base de datos de destinos con coordenadas.

### 2. Configura las Reglas en `main.py`
Ajusta las constantes en la parte superior:
- `N_CLIENTES`: Límite máximo de clientes por ruta.
- `MAX_PALLETS`: Límite de capacidad física total (suma de demanda_pallets) por camión.
- `THRESHOLD_KM`: Desvío máximo permitido para aceptar un cliente en la ruta de retorno.
- `MANDATORY_CUSTOMERS`: (Opcional) Fuerza visitas a clientes específicos para plantas seleccionadas, ignorando filtros de distancia si es necesario.
- `TRUCK_SPECS`: Define peso, altura y emisiones para que el cálculo de Google sea apto para vehículos pesados.

### 3. Ejecución y Dualidad de Escenarios (Módulos)
El sistema ahora opera en dos modos independientes para garantizar la integridad de los resultados:
* **Escenario de Referencia (Baseline)**: `python main_baseline.py`
  - Actualiza la pestaña **"Condiciones Normales"** del dashboard.
  - Útil para comparativas de impacto directo.
* **Escenario de Producción (Optimizado)**: `python main.py`
  - Actualiza las pestañas de **"Resumen Ejecutivo"**, **"Detalle Operativo"** y **"Mapa"**.
  - Incluye el cálculo dinámico de **emisiones de CO2** basado en carga (25t papel / pallets).

### 4. Dashboard Modularizado
El punto de entrada principal es `outputs/Presentacion_Logistica.html`. 
Esta interfaz unificada consume piezas HTML independientes generadas por los scripts anteriores, permitiendo actualizaciones parciales sin pérdida de datos en otras secciones.

### 5. Sincronización de Componentes
Si solo deseas actualizar el diseño visual o la simulación sin re-ejecutar el optimizador:
* **Generar Reporte:** `python src/utils/report_generator.py` (Ensambla los .html).
* **Nueva Simulación (GIF):** `python ejecutar_simulacion.py` (Genera la animación con los datos de producción).

---

## 🍃 Sostenibilidad e Impacto Ambiental
El motor ahora integra una estimación de huella de carbono basada en el modelo **FCR (Fuel Consumption Rate)**:
- **Carga de Vacío**: Calculada sobre el peso del tráiler.
- **Carga Dinámica**: 25,000 kg para el tramo de papel y peso variable según número de pallets para el tramo de cartón.
- **KPIs**: Las emisiones totales y por ruta se visualizan en el **Detalle Operativo**.

## 🧠 Modelo de Selección Geográfica (Dual-Pass)

Para garantizar la eficiencia y no saturar las llamadas a la API de Google, el sistema utiliza un filtrado de doble capa para elegir a los mejores clientes candidatos por cada planta:

```mermaid
graph TD
    A[Universo de Clientes (Base Completa)] --> B{Filtro 1: Radio Haversine}
    B -- "<= MAX_RADIUS_KM (Estimado)" --> C[Shortlist de Candidatos Proximidad]
    C --> D{Fase 2: Validación Google Routes API}
    D -- "Distancia REAL <= MAX_RADIUS_KM" --> E[Candidatos GPS Confirmados]
    E --> F[Cálculo de Desvío Marginal (Backhauling)]
    F -- "Fórmula: (P→C + C→M) - P→M" --> G[Ranking de Eficiencia de Retorno]
    G --> H[Selección Top N por Planta]
    H --> I[Motor VRP (Google OR-Tools)]
    I --> J[Resultados: Rutas Consolidadas Multi-Planta]
```

### Visualización de la Lógica (Elipse de Desvío)
Puedes ver una explicación visual e interactiva de cómo funcionan estos filtros ejecutando:
```bash
python visualizacion_filtros.py
```
Esto generará un mapa en `outputs/maps/visualizacion_logica_datamanager.html` mostrando el **círculo de radio** y la **elipse de desvío** (eficiencia de retorno).

### Explicación de los Filtros
1. **Filtro de Última Milla (Radio Local):** Limita geográficamente la zona de actuación. Un camión que carga en una planta solo puede entregar a clientes en un radio de acción controlado (asfalto real), evitando que el motor sugiera cruzar el país para una entrega simple si no es estrictamente eficiente.
2. **Cálculo de Desvío (Backhauling):** Una vez dentro del radio, el sistema prioriza a aquellos clientes que se encuentren "más de camino" hacia el destino final (Jaén). Si un cliente está a 30km de la planta pero en dirección opuesta al regreso, tendrá peor puntuación que uno que esté a 40km pero en la misma autovía de bajada.

---

## 🛠 Notas Técnicas sobre la API y "Fallback a Haversine"

Si al ejecutar el optimizador observas que la procedencia de las distancias menciona **"Haversine (estimación)"** en los reportes, significa que el sistema no ha podido recuperar el asfalto real por alguna de estas tres razones:

1. Faltan tus credenciales (`GOOGLE_MAPS_API_KEY`) en el entorno de ejecución (`.env`).
2. Tienes un problema de *Billing* (facturación inactiva) en la consola de Google Cloud, que bloquea el uso de la *Routes API*.
3. La configuración masiva matricial de la ruta (`computeRouteMatrix`) ha sido rechazada porque contiene atributos locales no procesables por los servidores de Google. (Para evitar detenciones el código actual *sanitiza* los atributos de vehículos como peso y altura hacia características aceptadas como tipo de emisión `emissionType: DIESEL`, enviando solo parámetros estables).

**Diseño de Alta Disponibilidad:** Hemos programado el código (`src/utils/geo.py`) asumiendo que las APIs pueden caerse. Si cualquiera de estos problemas asalta el cálculo de ruta, **el modelo no tirará un error que detenga el programa**. Instantáneamente tomará nota, bajará a su núcleo offline alternativo (`Haversine distance`), y te trazará las rutas matemáticamente en línea recta sin detener la ejecución de optimización.

---

## 📊 Guía de Estructura de Datos (Estándar GSIM)

Para garantizar la interoperabilidad, trazabilidad y correcta interpretación de la información logística en un entorno empresarial, los datos de entrada de este proyecto se han documentado alineándose con el **Modelo Genérico de Información Estadística (GSIM)**.

### 1. Grupo de Conceptos (Concept Group)
Define el significado y la unidad funcional de la información manejada por el algoritmo:
- **Punto de Origen (Depot - Mengíbar)**: Base central donde inician y terminan todas las rutas (Paper Plant).
- **Planta de Carga (Cartonera)**: Hub intermedio inter-conectado donde el camión se abastece de producto para cliente final antes de iniciar la distribución de retorno (Backhauling).
- **Demanda Física (Pallets)**: Unidad de medida estándar de capacidad volumétrica/peso. 
- **Apilamiento (`remontar`)**: Característica física del producto que permite duplicar la eficiencia espacial del camión si el valor es positivo.

### 2. Grupo de Estructuras (Structure Group)
Define cómo se organizan sintácticamente los conjuntos de datos (Datasets):
* **`locations_smurfit.json` (Dataset Estructural)**:
  Contiene diccionarios estáticos que definen la infraestructura operativa total.
  *Variables Identificadoras*: `id` (Código único GSIM), `name` (Etiqueta descriptiva).
  *Variables de Medida*: `lat` / `lng` (Coordenadas geodésicas absolutas WGS84).
* **`demanda_simulada.json` (Dataset Transaccional)**:
  Estructura relacional de llave-valor agrupada por micro-territorios (Código Postal).
  *Variables de Medida Central*: `demanda_pallets` / `n_pallets` (Carga), `municipio_destino`.

### 3. Grupo de Intercambio (Exchange Group)
Define el flujo técnico de entrada y salida de información:
- **Ingesta de Datos (Input)**: Lectura pasiva de JSON y diccionarios inyectados (`FLOTA_POR_PLANTA`).
- **Canal de Intercambio Externo**: Solicitudes API HTTP asíncronas hacia servidores topológicos (OSRM / Google Routes) transmutando las coordenadas puras en matrices de distancia terrestre.
- **Provisión de Información (Outputs)**: Consolidación de un log transaccional de desvíos técnicos (`logs/descartados_motivos.log`) y cuadros de mando analíticos (`.html`).

### 4. Grupo de Negocio (Business Group)
La gobernanza general orientada al objetivo logístico del modelo:
- **Regla Estricta (Hard Constraint)**: Bin-packing restrictivo aplicado sobre la suma marginal de la variable `demanda_pallets` respecto a `MAX_PALLETS` del tráiler.
- **Regla Blanda (Soft Constraint)**: Minimización de métrica monetaria penalizando el exceso de kilómetros totales en rutas de transporte.
