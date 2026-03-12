# 🚚 Logistics Optimizer

Bienvenido a **Logistics Optimizer**, un sistema avanzado en Python diseñado para optimizar el enrutamiento de transporte y la logística de distribución, minimizando específicamente los "kilómetros en vacío" durante las rutas de retorno a la base de operaciones (backhauling).

---

## 🚀 Lo que Llevamos Desarrollado

Actualmente, el proyecto cuenta con un sistema maduro, empaquetado y altamente visual que automatiza los procesos complejos de la cadena de suministro. Esto es lo que se ha logrado construir:

1. **Motor de VRP Avanzado**: Usamos Google OR-Tools para calcular las mejores combinaciones posibles en escenarios complejos que involucran un origen principal (Ej. papelera central), nodos productivos (Ej. fábricas de procesado del cartón) y nodos finales (clientes). Incluye la capacidad de previsualizar los resultados numéricos rápidamente con el método `.summary()` (estilo `statsmodels`).
2. **Sistema de GPS Real (Compatible con Camiones)**: Integración precisa para recuperar distancias terrestres a través de la moderna **Google Routes API**, permitiendo perfiles de enrutamiento pesado (emisiones, altura, peso máximo). Posee un sistema de respaldo automático que hace estimaciones geográficas si no hay API disponible.
3. **Smart Data Filtering (Filtros Inteligentes)**: El sistema automáticamente descarta ramificaciones inviables por distancia antes de saturar el motor matemático, asegurando mucha mayor rapidez computacional al descartar clientes que se alejan excesivamente en la ruta de retorno natural.
4. **Dashboard Interactivo Profesional**: En lugar de simples planillas de texto, el proyecto emite un archivo HTML interactivo (`Presentacion_Logistica.html`) combinando Mapas satelitales (Folium), Grafos relacionales (Plotly), y tablas de KPIs matemáticos. Incluye un logo corporativo y una estética premium optimizada para presentaciones ejecutivas.
5. **Simulación Dinámica de Flotas (SOTA)**: Módulo especializado (`src/simulation/`) que utiliza **SimPy** para modelar la operación real. A diferencia de modelos estáticos, esta simulación:
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
- `N_CLIENTES`: Capacidad del camión (clientes por ruta).
- `THRESHOLD_KM`: Desvío máximo permitido para aceptar un cliente en la ruta de retorno.
- `MANDATORY_CUSTOMERS`: (Opcional) Fuerza visitas a clientes específicos para plantas seleccionadas, ignorando filtros de distancia si es necesario.
- `TRUCK_SPECS`: Define peso, altura y emisiones para que el cálculo de Google sea apto para vehículos pesados.

### 3. Ejecuta el Motor
Lanza el orquestador para generar los resultados y el reporte inicial:
```bash
python main.py
```

### 4. Sincroniza el Dashboard o la Simulación
Si solo deseas actualizar el diseño del HTML o volver a simular la flota con los resultados ya existentes (sin gastar créditos de API de nuevo):
* **Actualizar Dashboard:** `python refresh_dashboard.py`
* **Nueva Simulación:** `python ejemplo_simulacion.py` (Genera el GIF `outputs/simulacion_rutas_optimizadas.gif`).

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
