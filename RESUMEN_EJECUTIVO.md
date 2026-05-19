# Explicación Matemática y Narrativa de los Outputs del Resumen Ejecutivo

Este documento proporciona una guía técnica, detallada y rigurosa sobre los indicadores clave de rendimiento (KPIs) y las tablas operativas presentadas en la pestaña de **Resumen Ejecutivo** del optimizador logístico.

---

## 1. Indicadores Clave de Rendimiento (KPIs Principales)

Esta sección describe las tarjetas métricas superiores que muestran los agregados consolidados de la red optimizada.

### 1.1 Rutas Totales
*   **Narrativa:** Representa el número de vehículos físicos independientes (viajes de ida y vuelta) despachados desde el depósito central en Mengíbar hacia las plantas de cartón y sus correspondientes clientes durante el periodo de análisis.
*   **Fórmula Matemática:**
    $$N_{\text{rutas}} = \sum_{r \in R} 1$$
    Donde $R$ es el conjunto de rutas activas e independientes generadas por el solucionador VRPB.

### 1.2 Clientes
*   **Narrativa:** Indica el número total de clientes únicos que han sido programados y atendidos con éxito en las rutas del sistema en este periodo.
*   **Fórmula Matemática:**
    $$N_{\text{clientes}} = |C_{\text{atendidos}}|$$
    Donde $C_{\text{atendidos}} = \bigcup_{r \in R} C_r$, siendo $C_r$ el conjunto de nodos de tipo cliente en la ruta $r$.

### 1.3 Distancia Total
*   **Narrativa:** Refleja la suma de las distancias geográficas reales (calculadas mediante OSRM) recorridas por todos los camiones optimizados, desde que salen de Mengíbar, pasan por las plantas y clientes, hasta que retornan al depósito.
*   **Fórmula Matemática:**
    $$D_{\text{total}} = \sum_{r \in R} d_r$$
    Donde $d_r$ es la distancia total en kilómetros de la ruta $r$.

### 1.4 Ahorro de Coste (Coste Total Optimizado)
*   **Narrativa:** Aunque en la interfaz está etiquetada como "Ahorro de Coste", esta métrica muestra el coste total de explotación interna (TCO Interno) de toda la flota de transporte propio optimizada por el modelo. Se basa en una tarifa por kilómetro que varía según el tipo de motorización (diésel o eléctrico).
*   **Fórmula Matemática:**
    $$Coste_{\text{TCO, total}} = \sum_{r \in R} \left( d_r \times T_r \right)$$
    Donde:
    *   $d_r$ es la distancia de la ruta $r$ en kilómetros.
    *   $T_r$ es la tarifa de transferencia interna en euros por kilómetro ($Tarifa_r$), que depende de la tecnología del vehículo:
        *   Si la planta origen utiliza diésel: $T_r = 1.50$ euros/km.
        *   Si la planta origen utiliza camión eléctrico (EV): $T_r = 1.60$ euros/km.

### 1.5 CO2 Total
*   **Narrativa:** Estima el volumen total de emisiones de gases de efecto invernadero expresado en kilogramos de dióxido de carbono equivalente ($kg\ CO_2e$) generado por la flota propia diésel optimizada. Los camiones eléctricos asignados a las plantas piloto se consideran de cero emisiones directas.
*   **Fórmula Matemática:**
    $$E_{\text{CO2, total}} = \sum_{r \in R} E_{\text{CO2}, r}$$
    Donde para cada ruta $r$, las emisiones $E_{\text{CO2}, r}$ se calculan tramo por tramo mediante el modelo de interpolación lineal basado en actividad (GLEC Framework v3.0 / ISO 14_083):
    *   Si es camión eléctrico: $E_{\text{CO2}, r} = 0.0$
    *   Si es camión diésel, para cada tramo (leg) $j$ de distancia $d_j$ y peso de carga actual $w_j$ (en toneladas):
        $$E_{\text{CO2}, j} = d_j \times \left( FE_{\text{vacío}} + \left( FE_{\text{cargado}} - FE_{\text{vacío}} \right) \times \frac{w_j}{w_{\text{máx}}} \right)$$
        Donde:
        *   $FE_{\text{vacío}} = 0.652\ kg\ CO_2\text{/km}$
        *   $FE_{\text{cargado}} = 1.085\ kg\ CO_2\text{/km}$ (a 25 toneladas)
        *   $w_{\text{máx}} = 25.0\text{ toneladas}$
        *   $w_j$ es la carga transportada en el tramo $j$ (calculada secuencialmente deduciendo la demanda de los clientes entregados).

### 1.6 Milla Vacía (%)
*   **Narrativa:** Métrica de eficiencia logística que calcula el porcentaje de la distancia total recorrida que los camiones viajan sin carga de regreso al depósito central (Mengíbar) una vez finalizadas todas las entregas a clientes.
*   **Fórmula Matemática:**
    $$\% Milla\_Vacía_{\text{sistema}} = \frac{\sum_{r \in R} d_{\text{retorno}, r}}{D_{\text{total}}} \times 100$$
    Donde $d_{\text{retorno}, r}$ es la distancia en kilómetros del último nodo cliente de la ruta $r$ de vuelta a Mengíbar.

---

## 2. Sostenibilidad

Esta sección detalla el impacto ambiental comparativo y los consumos energéticos de la flota propia.

### 2.1 CO2 Evitado Absoluto
*   **Narrativa:** Es la cantidad total de emisiones de dióxido de carbono que se han evitado a nivel sistémico al operar con nuestra flota propia optimizada en lugar de recurrir al escenario tradicional o a transportistas externos diésel estándar en los tramos de entrega.
*   **Fórmula Matemática:**
    $$E_{\text{evitado, total}} = \sum_{r \in R} E_{\text{evitado}, r}$$
    Donde para cada ruta $r$, el CO2 evitado representa la diferencia entre la emisión de referencia si el segmento Linehaul (de planta a clientes) se subcontratara externamente (asumiendo camión diésel externo convencional) y las emisiones reales de nuestra flota propia optimizada (que pueden ser cero si el vehículo de la ruta es eléctrico).
    $$E_{\text{evitado}, r} = E_{\text{externo, diésel}} - E_{\text{real}, r}$$
    *   $E_{\text{externo, diésel}}$ se calcula mediante la fórmula de actividad GLEC para la distancia del tramo Linehaul ($d_{\text{Linehaul}, r}$):
        $$E_{\text{externo, diésel}} = d_{\text{Linehaul}, r} \times \left( FE_{\text{vacío}} + \left( FE_{\text{cargado}} - FE_{\text{vacío}} \right) \times \frac{w_{\text{carga}}}{25.0} \right)$$
    *   $E_{\text{real}, r}$ es $0.0$ si la ruta es eléctrica, o es el valor real calculado en el tramo diésel propio.

### 2.2 Reducción Relativa
*   **Narrativa:** Porcentaje de reducción en la intensidad de carbono media por kilómetro de la red optimizada frente a una red de transporte de referencia no optimizada (sin consolidación de retornos ni planificación VRPB).
*   **Fórmula Matemática:**
    $$\% Reducción\_CO2_{\text{relativa}} = \left( 1 - \frac{I_{\text{CO2, optimizada}}}{I_{\text{CO2, tradicional}}} \right) \times 100$$
    Donde:
    *   $I_{\text{CO2, optimizada}} = \frac{E_{\text{CO2, total}}}{D_{\text{total}}}$ (intensidad de emisiones del sistema actual en $kg\ CO_2\text{/km}$).
    *   $I_{\text{CO2, tradicional}} = \frac{E_{\text{CO2, tradicional}}}{D_{\text{tradicional}}}$ (intensidad de emisiones proyectada bajo la operativa base).

### 2.3 Energía BEV (Total)
*   **Narrativa:** Muestra el consumo total de electricidad medido en kilovatios-hora (kWh) por los camiones eléctricos de batería (BEV) asignados a las plantas de Huelva, Almería y Córdoba.
*   **Fórmula Matemática:**
    $$\text{Energía BEV}_{\text{total}} = \sum_{r \in R_{\text{EV}}} \sum_{j \in L_r} \left( d_j \times C_{\text{EV}, j} \right)$$
    Donde para cada tramo (leg) $j$ de la ruta eléctrica:
    *   $d_j$ es la distancia del tramo en kilómetros.
    *   $C_{\text{EV}, j}$ es el consumo de energía instantáneo por kilómetro ($kWh/km$), determinado mediante el modelo dinámico basado en la carga:
        $$C_{\text{EV}, j} = C_{\text{vacío}} + (C_{\text{lleno}} - C_{\text{vacío}}) \times \frac{w_j}{w_{\text{máx}}}$$
        Con los siguientes parámetros operativos:
        *   Consumo en vacío ($C_{\text{vacío}}$) = $1.05\ kWh/km$.
        *   Consumo a plena carga ($C_{\text{lleno}}$) = $1.70\ kWh/km$.
        *   $w_{\text{máx}} = 25_000\ kg$ (peso de carga correspondiente a 34 pallets).
        *   $w_j$ es la carga en kg sobre el tramo $j$ ($Pallets_j \times 500\ kg$ por pallet).

---

## 3. Detalle Operativo por Planta (Backhauling)

Esta tabla analiza la eficiencia de llenado, la reducción de millas vacías y la facturación correspondiente a cada centro logístico (planta de cartón).

### 3.1 Escenario Base Inbound (Sin Clientes)
*   **Narrativa:** Fila de referencia que describe el trayecto inbound tradicional e independiente: un camión sale de Mengíbar con bobinas de papel, viaja hasta la planta correspondiente para entregarlas y regresa vacío a Mengíbar, sin realizar entregas secundarias a clientes.
*   **Distancia Base:**
    $$d_{\text{Base}} = d_{\text{Depot} \rightarrow \text{Planta}} + d_{\text{Planta} \rightarrow \text{Depot}}$$
*   **Milla Vacía Base:**
    $$\% Milla\_Vacía_{\text{Base}} = 50.0\%$$
    (Ya que el trayecto de vuelta representa exactamente la mitad de la distancia total recorrida y se realiza 100% en vacío).
*   **Coste Base:**
    $$Coste_{\text{Base}} = d_{\text{Base}} \times T_r$$

### 3.2 Línea Base Total Planta
*   **Narrativa:** Proyección de la línea base anterior multiplicada por la cantidad de rutas optimizadas reales asignadas a dicha planta en la simulación. Permite realizar una comparación agregada en volumen de la misma escala.
*   **Distancia:** $N_{\text{rutas, planta}} \times d_{\text{Base}}$
*   **Coste:** $N_{\text{rutas, planta}} \times Coste_{\text{Base}}$
*   **CO2 / Energía:** $N_{\text{rutas, planta}} \times E_{\text{Base}}$

### 3.3 Métricas por Ruta (Filas Detalladas)
*   **Clientes:** Cantidad de clientes atendidos en la ruta.
*   **Pallets:** Cantidad de pallets totales despachados en el camión.
*   **Llenado %:** Fracción de ocupación volumétrica/física de los pallets transportados frente a la capacidad útil del remolque (34 pallets).
    $$\% Llenado = \frac{P_{\text{ruta}}}{34} \times 100$$
    *(Nota: Si la ruta es encadenada (ej. Vigo-Alcalá), es el promedio simple de ocupación por planta).*
*   **Milla Vacía %:** Porcentaje de distancia en vacío recorrida en el retorno de la ruta.
    $$\% Milla\_Vacía_{\text{ruta}} = \frac{d_{\text{retorno}, r}}{d_{\text{VRPB}, r}} \times 100$$
    Donde $d_{\text{retorno}, r}$ es el último tramo desde el último cliente hasta Mengíbar.
*   **Facturación:** El ingreso teórico asignado a la división logística interna por realizar el transporte de esa ruta:
    $$Facturación_{\text{ruta}} = d_{\text{VRPB}, r} \times Tarifa_{\text{interna}}$$
*   **CO2 / Energía:** Emisión de CO2 (diésel, kg) o energía consumida (eléctrico, kWh) calculada según las ecuaciones dinámicas detalladas en la sección anterior.
*   **Evitado:** Emisiones de CO2 evitadas comparadas con subcontratar el tramo de entrega.
*   **Ahorro:** Beneficio económico sistémico obtenido de la ruta.

### 3.4 Total Planta (Optimizado Real)
*   **Narrativa:** Fila de resumen que agrega los resultados reales de todas las rutas optimizadas que sirvieron a esa planta.
*   **Fórmulas de Agregación:**
    *   **Distancia Total Planta:** $D_{\text{planta}} = \sum_{r \in R_{\text{planta}}} d_r$
    *   **Milla Vacía Agregada Planta:**
        $$\% Milla\_Vacía_{\text{planta}} = \frac{\sum_{r \in R_{\text{planta}}} d_{\text{retorno}, r}}{D_{\text{planta}}} \times 100$$
    *   **Llenado Medio Planta:** Promedio de los porcentajes de llenado de sus rutas asociadas.

---

## 4. Ahorro Sistémico (Linehaul)

Esta tabla evalúa la viabilidad económica de realizar el transporte de entrega secundaria (desde la planta hasta los clientes) utilizando la flota propia, en comparación con la contratación de un operador logístico externo cobrado a tarifa de mercado por kilómetro de entrega punto a punto (Linehaul).

### 4.1 Distancia
*   **Narrativa:** Representa la distancia de entrega del segmento Linehaul ($d_{\text{Linehaul}}$). Esto corresponde a la distancia acumulada recorrida por el vehículo propio desde que sale de la planta de cartón, visita a todos los clientes programados en esa ruta específica, hasta llegar al último cliente (justo antes de iniciar el retorno en vacío).
*   **Fórmula Matemática:**
    $$d_{\text{Linehaul}} = \sum_{j \in \text{Legs de entrega}} d_j$$

### 4.2 TCO Interno
*   **Narrativa:** El coste imputado por realizar ese tramo de entrega con la flota interna propia, utilizando la tarifa de transferencia establecida para la tecnología correspondiente de la planta.
*   **Fórmula Matemática:**
    $$Coste_{\text{interno}} = d_{\text{Linehaul}} \times Tarifa_{\text{interna}}$$
    Donde $Tarifa_{\text{interna}}$ es $1.50$ euros/km para camiones diésel y $1.60$ euros/km para eléctricos.

### 4.3 Tarifa Mercado
*   **Narrativa:** Coste estimado de subcontratar a un proveedor logístico externo para realizar el mismo tramo de entrega (Linehaul).
*   **Fórmula Matemática:**
    $$Coste_{\text{mercado}} = d_{\text{Linehaul}} \times Tarifa_{\text{mercado}}$$
    Donde $Tarifa_{\text{mercado}} = 1.70$ euros/km (definido por el parámetro `EXTERNAL_PROVIDER_RATE_PER_KM`).

### 4.4 Ahorro Neto
*   **Narrativa:** El beneficio económico neto y directo que se retiene en el grupo empresarial al optar por realizar la distribución capilar con el vehículo propio que ha consolidado el retorno de bobinas, en lugar de comprar el transporte al mercado externo.
*   **Fórmula Matemática:**
    $$Ahorro_{\text{neto}} = Coste_{\text{mercado}} - Coste_{\text{interno}} = d_{\text{Linehaul}} \times \left( Tarifa_{\text{mercado}} - Tarifa_{\text{interna}} \right)$$
    Dado que las tarifas internas propias son inferiores al coste de mercado externo, el ahorro neto unitario es de:
    *   **Rutas Diésel:** $0.20$ euros/km ($1.70 - 1.50$).
    *   **Rutas Eléctricas:** $0.10$ euros/km ($1.70 - 1.60$).

### 4.5 CO2 Evitado
*   **Narrativa:** Estimación del volumen de gases contaminantes evitados en el tramo de entrega, asumiendo que el proveedor externo opera exclusivamente camiones diésel tradicionales, mientras que nosotros optimizamos con mejores tasas de carga o mediante el uso de camiones eléctricos de cero emisiones.
*   **Fórmula Matemática:**
    *   Si nuestra ruta es eléctrica: $CO2_{\text{evitado}} = E_{\text{externo, diésel}}$ (se evita el 100% de la emisión por combustión).
    *   Si nuestra ruta es diésel: $CO2_{\text{evitado}} = E_{\text{externo, diésel}} - E_{\text{interno, diésel}}$ (ahorro marginal por diferencias de eficiencia de carga).
