# 🚚 Logistics Optimizer

Bienvenido a **Logistics Optimizer**, un sistema avanzado en Python diseñado para optimizar el enrutamiento de transporte y la logística de distribución, minimizando específicamente los "kilómetros en vacío" durante las rutas de retorno a la base de operaciones (backhauling).

---

## 🚀 Lo que Llevamos Desarrollado

Actualmente, el proyecto cuenta con un sistema maduro, empaquetado y altamente visual que automatiza los procesos complejos de la cadena de suministro. Esto es lo que se ha logrado construir:

1. **Motor de VRP Avanzado**: Usamos Google OR-Tools para calcular las mejores combinaciones posibles en escenarios complejos que involucran un origen principal (Ej. papelera central), nodos productivos (Ej. fábricas de procesado del cartón) y nodos finales (clientes). Incluye la capacidad de previsualizar los resultados numéricos rápidamente con el método `.summary()` (estilo `statsmodels`).
2. **Sistema de GPS Real (Compatible con Camiones)**: Integración precisa para recuperar distancias terrestres a través de la moderna **Google Routes API**, permitiendo perfiles de enrutamiento pesado (emisiones, altura, peso máximo). Posee un sistema de respaldo automático que hace estimaciones geográficas si no hay API disponible.
3. **Smart Data Filtering (Filtros Inteligentes)**: El sistema automáticamente descarta ramificaciones inviables por distancia antes de saturar el motor matemático, asegurando mucha mayor rapidez computacional al descartar clientes que se alejan excesivamente en la ruta de retorno natural.
4. **Dashboard Interactivo Profesional**: En lugar de simples planillas de texto, el proyecto emite un archivo HTML interactivo (`Presentacion_Logistica.html`) combinando Mapas satelitales (Folium), Grafos relacionales (Plotly), y tablas de KPIs matemáticos que cualquier ejecutivo o supervisor puede entender de un vistazo.
5. **Simulación Dinámica de Flotas (SimPy)**: Módulo especializado (`src/simulation/`) para prever cuellos de botella reales en los muelles de carga y disponibilidad de conductores. Incorpora la generación de animaciones GIF para previsualizar el comportamiento logístico a lo largo del tiempo.

---

## 🔄 ¿Cómo usar este modelo en OTROS CONTEXTOS?

Aunque originalmente se diseñó para transportar bobinas de papel y cajas de cartón, esta herramienta es **totalmente adaptable a cualquier otro modelo de negocio logístico** en el que se entregue mercancía y se requiera optimizar la ruta de regreso. 

Por ejemplo: Transporte de alimentos, logística inversa de pallets, transporte de materiales de construcción con visitas a otras canteras operativas intermedias, etc.

Para adaptarlo a tu propio caso de uso, la forma más sencilla es seguir estos tres pasos:

### 1. Prepara tus datos (.json)
El modelo espera dos archivos en la carpeta `data/`:
* **Plantas/Nodos Estratégicos:** Define tu origen principal (`depot`) y tus paradas intermedias (`carton_plants`). Deben contener el parámetro `lat` (Latitud), `lon` (Longitud) y `name` (Nombre del almacén).
* **Clientes Finales:** Define a quiénes vas a entregar los productos, también con su latitud y longitud.

*No importa si vendes zapatos, muebles, o carne, el motor matemático lee coordenadas geográficas, no mercancías.*

### 2. Configura los parámetros en `main.py`
Abre el archivo principal `main.py` y ajusta las siguientes reglas básicas de negocio en la parte superior del archivo:
- `N_CLIENTES`: Máximo número de clientes que el camión puede visitar en una sola ruta (por volumen, tiempo, etc).
- `MAX_PLANTAS_RUTA`: En cuántos almacenes intermedios el camión puede recoger o dejar mercancía antes de ir a los clientes.
- `THRESHOLD_KM`: Es el "límite elástico" de kilómetros de desvío. Le dices al sistema: *"Solo visita a clientes que en el camino de regreso al origen como mucho me desvíen un máximo de X kilómetros sobre la ruta directa."*
- `MAX_RADIUS_KM`: Radio de cobertura local (km por carretera). El sistema solo considerará clientes situados dentro de este radio de acción desde la planta donde se carga la mercancía.

### 3. Ejecuta el Motor
Simplemente abre tu consola en esta carpeta y lanza el orquestador:

```bash
python main.py
```

### Resultados que obtendrás
Al instante, en la consola observarás un **Resumen Analítico (Summary)** que detalla los kilómetros, tiempos estimados por vehículo y especificaciones del camión. Además, en la carpeta `outputs/` se generarán reportes automáticos y un `Presentacion_Logistica.html` que podrás abrir en cualquier navegador web. Te mostrará el esquema de cómo deberían moverse tus camiones, la lista de qué clientes ha juntado en qué rutas de entrega y cuántos **kilómetros de más (o en vacío)** lograste reducir con esta decisión.

También puedes revisar `example_usage.py` para un código minimalista sobre cómo inicializar el motor directamente con parámetros de camiones (Routes API).

### 4. Simulación de Flotas
Si deseas simular temporalmente las salidas y llegadas de la flota de camiones teniendo en cuenta las limitaciones operativas (muelles y conductores), puedes ejecutar:

```bash
python ejemplo_simulacion.py
```
Esto generará un GIF animado (`outputs/simulacion_logistica_demo.gif`) que muestra los horarios de salida y las posiciones en ruta de los camiones.

---

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
```

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
