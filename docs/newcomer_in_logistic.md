# Google OR-Tools para Perfiles Financieros y Económicos (VRP)

Pensando en tu formación en finanzas y economía, la mejor forma de entender **Google OR-Tools** es compararlo con herramientas y conceptos que ya dominas.

Piensa en Google OR-Tools como un **"Solver de Excel con esteroides"** diseñado específicamente para resolver problemas matemáticos de altísima complejidad. En economía y finanzas, constantemente buscas **maximizar ganancias** o **minimizar costos/riesgos** sujeto a ciertas **restricciones** (tu presupuesto, regulaciones de la SEC, nivel de liquidez, etc.). Eso es exactamente lo que hace OR-Tools, pero aplicado a la logística.

El problema específico que este proyecto resuelve se conoce como el **VRP (Vehicle Routing Problem)**. 

A continuación, un desglose de cómo se construyó el archivo `src/engine/solver.py` usando analogías de tu área para que seas 100% independiente en el futuro.

---

### 1. La Configuración Inicial: Tus "Activos" y "Costos de Transacción"

Antes de optimizar, el código prepara el tablero de juego (inicializando la clase `LogisticsSolver`).

*   **Los Nodos (`self.nodes`)**: Son tus "activos" financieros. Tienes 3 tipos de activos en este portafolio logístico:
    *   `Depot` (El banco central / Origen principal).
    *   `Carton Plants` (Plantas de producción / Fuentes de capital).
    *   `Customers` (Clientes / Inversiones que requieren ese capital o mercancía).
*   **La Matriz de Distancias (`self.distance_matrix`)**: Piensa en esto como tu **tabla de costos de transacción o comisiones**. Moverte del Activo A al Activo B cuesta *X*. El objetivo de OR-Tools será estructurar los viajes de manera que la suma de todos estos "costos de transacción" (distancia recorrida) sea la más baja posible.

### 2. El "Fondo de Inversión": Index Manager y Routing Model

```python
manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_idx)
routing = pywrapcp.RoutingModel(manager)
```
*   **`RoutingIndexManager`**: Es como el analista cuantitativo o contador del fondo. Traduce los nombres reales de tus nodos a índices matemáticos puros (0, 1, 2...) que el algoritmo en C++ pueda procesar extremadamente rápido.
*   **`RoutingModel` (routing)**: Es la estructura u hoja de cálculo del portafolio en sí. Aquí es donde iremos agregando todas las reglas del juego.
*   **Vehículos (`num_vehicles`)**: Son tus "gestores de cartera" o "fondos independientes". Cada camión buscará armar su propia ruta (su propio mini-portafolio de clientes a visitar).

### 3. Las Dimensiones: Tus Limitantes de Capital (Presupuestos)

En finanzas, no puedes invertir capital infinito; tienes un límite de apalancamiento o crédito. En programación estructurada de logística, esto se modela con las "Dimensiones".

```python
# Dimensión: Distancia
routing.AddDimension(transit_callback_index, 0, DIST_LIMIT, True, 'Distance')
```
*   **La Dimensión `Distance`**: Lleva la cuenta de cuánta distancia (costo acumulado) va consumiendo el camión. Se configura un `DIST_LIMIT` que es básicamente tu **presupuesto máximo operativo diario por vehículo**. Ningún gestor (vehículo) puede gastar más "capital" (distancia en km) que ese límite.

```python
# Dimensión: Plantas
routing.AddDimension(plant_cb_idx, 0, 1, True, 'PlantCount')
```
*   **La Dimensión `PlantCount`**: Es una contabilidad paralela para asegurar que un camión no visite demasiadas plantas productoras. Su presupuesto máximo acumulado estricto es `1`.

### 4. Las "Hard Constraints": Compliance y Regulación

Estas reglas lógicas son como el departamento de Compliance en finanzas (por ejemplo, "Un fondo de bajo riesgo no puede invertir más del 5% en una sola startup"). Si el programa intenta una solución que rompe una de estas reglas, se declara **completamente inválida**. 

Así es como le modelamos las reglas de negocio a OR-Tools:

1.  **Cada camión va a una sola planta (Regla Anti-Monopolio):**
    ```python
    routing.solver().Add(plant_dim.CumulVar(routing.End(v)) == 1)
    ```
    *Significado:* Al terminar su turno (`routing.End`), la suma de plantas que visitó cada vehículo `v` tiene que ser exactamente `1`. No pueden ir a cero plantas, ni a dos.

2.  **No hay clientes abandonados (Default Penalty / Multas):**
    ```python
    routing.AddDisjunction([c_node], 1_000_000)
    ```
    *Significado:* Esto es una **penalización por "Default"**. Le dices a OR-Tools: *"Tienes la opción de no visitar a un nodo (cliente), pero si lo dejas fuera de la cartera final, te cobraré una multa artificial de sanción de $1,000,000"*. Como el algoritmo busca minimizar la suma de costos, será matemáticamente empujado a visitar a todos para evitar la quiebra virtual de la solución.

3.  **Vinculación Planta-Cliente y Precedencia (Flujo de Caja Lógico):**
    ```python
    # Mismo vehículo
    routing.solver().Add(routing.ActiveVar(c_node) * (routing.VehicleVar(c_node) - routing.VehicleVar(p_node)) == 0)
    
    # Precedencia
    routing.solver().Add(dist_dim.CumulVar(p_node) < dist_dim.CumulVar(c_node))
    ```
    *Significado:* Si el Cliente A pertenece a la Planta A, el **mismo gestor (vehículo)** debe ser quien visite tanto a la Planta como al Cliente (para asegurar que de ahí salió el cartón que se entrega).
    Además, la cláusula de **Precedencia** asegura que el camión tiene que llegar a la Planta A **ANTES** (`<`) de llegar al Cliente A. 
    *Analogía Económica:* No puedes vender una acción en corto (entregarle el cartón al cliente) sin antes haberla pedido prestada a tu broker (ir a recoger el cartón a la planta). OR-Tools respeta ese flujo lógico obligatorio de recoger antes de entregar.

### 5. Las Estrategias de Búsqueda: Ejecución Algorítmica de Trading (HFT)

Una vez que definiste de cuánto presupuesto dispones y cuáles son tus regulaciones (compliance), sueltas a tus "traders algorítmicos" para encontrar la ruta más barata. Le configuraste dos etapas de búsqueda que trabajan en equipo:

```python
search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
```

*   **1. `First Solution Strategy`:** Piensa en esto como una **estimación inicial estructurada o una Oferta Pública Inicial (IPO) rápida**. El algoritmo `PARALLEL_CHEAPEST_INSERTION` simplemente busca armar una ruta legal lo más rápido posible, metiendo al cliente más barato o cercano disponible en ese momento a la ruta, sin pensar demasiado en el impacto a largo plazo de esa asignación. Produce un portafolio logístico "decente y legal" rápidamente para tener algo con qué empezar.
*   **2. `Local Search Metaheuristic`**: Este es verdaderamente tu operario de **Arbitraje Cuantitativo de Alta Frecuencia**. Una vez que tiene esa primera solución inicial, USA `GUIDED_LOCAL_SEARCH` por el tiempo máximo que le diste (ej. 90 segundos). Se dedica a hacer miles de millones de comprobaciones y permutaciones en memoria (intercambiar el cliente A de la ruta de Luis con el cliente B de la ruta de Carlos, voltear una ruta al revés, etc.) buscando rascar fracciones de centavo de ahorro en distancia global. 
La magia está en que al ser "Guided" (Guiado), el algoritmo se da cuenta si se estancó en un mínimo local (costo sub-óptimo del cual no puede salir haciendo cambios pequeños) y se auto-penaliza zonas saturadas temporalmente para reestructurar drásticamente la cartera de visitas y explorar nuevos enfoques buscando un menor costo global.

### 6. La Implementación en Código (Paso a Paso)

Para llevar esta teoría a la práctica en Python, usamos la librería de Google (escrita en C++ pero con "envolturas" para Python por temas de velocidad y facilidad). Fíjate cómo se divide la implementación exactamente en tu archivo `src/engine/solver.py`:

**A. Importación de las herramientas base:**
```python
from ortools.constraint_solver import routing_enums_pb2  # Herramientas para configurar tácticas (como GLS)
from ortools.constraint_solver import pywrapcp           # Motor principal (C++ Constraint Programming wrapper)
```
*   `pywrapcp` es el "cerebro" matemático en C++ que ensambla y resuelve ecuaciones, matrices y dimensiones.
*   `routing_enums_pb2` es un catálogo que contiene opciones y tácticas predefinidas.

**B. Inicialización (Crear los cimientos):**
```python
manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot_idx)
routing = pywrapcp.RoutingModel(manager)
```
Aquí le declaras a OR-Tools la escala del problema (`len(dist_matrix)`), cuántos operarios o activos fijos manejas (`num_vehicles`) y dónde está tu centro de operaciones o punto Cero (`depot_idx`).

**C. Función de Costos (Callbacks):**
OR-Tools es ciego a tus datos reales a menos que le enseñes a leerlos. Necesita saber constantemente "cuánto cobra" la vida real por viajar del nodo A al nodo B. Para eso usamos "Callbacks":
```python
def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return int(dist_matrix[from_node][to_node])

# Se registra la tarifa de transacción en el sistema central:
transit_callback_index = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
```
La función `distance_callback` será llamada internamente por Google OR-Tools millones de veces durante el cálculo. Sirve meramente de puente entre la lógica matemática del gestor (`from_index`) y la realidad de tus datos de cliente (`from_node`).

**D. La Implementación Real de GLS (Guided Local Search):**
A pesar de su complejidad matemática, implementar tu operario de arbitraje y alta frecuencia (GLS) solo requiere configurar en parámetros de búsqueda antes de arrancar.

```python
search_params = pywrapcp.DefaultRoutingSearchParameters()

# 1. Estrategia Inicial (IPO)
search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION

# 2. La Metaheurística (El "Operario" cuantitativo: GLS)
search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH

# 3. Time Limit (Tu presupuesto de riesgo temporal)
search_params.time_limit.seconds = 90
```

*   **¿Qué hace exactamente el parámetro `GUIDED_LOCAL_SEARCH` por detrás?**
    Una vez que OR-Tools armó una primera solución válida, GLS empieza a buscar "mejoras locales" (ej. "Intercambiar Cliente x con Cliente Y, ¿sale más barato?"). 
    Cuando la máquina se estanca en lo que llamamos un *mínimo local* (donde cualquier cambio diminuto hace la ruta más cara), GLS añade al vuelo "penalizaciones artificiales de costo" a los caminos que está usando muy seguido o que son naturalmente largos. Al volverlos artificialmente caros en la mente del algoritmo, obliga ciegamente al sistema a buscar y explorar nuevos caminos en el mapa que había ignorado durante los primeros segundos. Cuando acaba el tiempo, te da la ruta más barata original que alguna vez comprobó.

**E. Arranque del Motor:**
```python
solution = routing.SolveWithParameters(search_params)
```
Esta es la línea que detiene tu terminal por 90 segundos. Aquí, todo el motor de C++ empieza a permutar buscando optimizar costos hasta que el cronómetro se acabe. Te devolverá un objeto `solution` conteniendo las asignaciones óptimas, si es que logró estructurar alguna bajo las regulaciones.

---

### Resumen Visual de la Arquitectura de un Proyecto de OR-Tools

1.  **Inputs**: Tus Nodos Reales y la Matriz de Costos Exacta (Tu panorama de mercado).
2.  **Modelo (`Manager`/`Routing`)**: La hoja de cálculo maestra.
3.  **Dimensiones**: Tus limitantes de capacidad (Presupuestos max/min).
4.  **Lógica del Negocio (Constraints)**: Las reglas matemáticas que obligan a acciones lógicas (ej. recoger antes de entregar).
5.  **Ejecución de Búsqueda**: Crea una solución inicial viable, e invierte el resto del tiempo explorando arbitrajes hasta minimizar al máximo el "costo" devuelto.

### Cómo Escalarlo a Futuro
Si en el futuro alguien de la empresa te dice: *"Oye, ahora quiero que los camiones obligatoriamente descansen una hora a las 2 de la tarde"*, ya sabrás que eso significa añadir una nueva **Dimensión de Tiempo** y una **Restricción (Constraint)** asociada a pausas. 
O si te dicen *"Tenemos un camión viejo que gasta el doble de gasolina e incurre en mayores viáticos"*, eso simplemente significa alterar tu **matriz de costos o las dimensiones** para multiplicar por `x2` el consumo de ese gestor específico (`vehicle_id`).
