# Guía Técnica de Cálculos: Dashboard Logístico

Este documento explica de forma detallada la procedencia y lógica matemática de las métricas presentadas en la tabla de **Impacto de la Optimización** del dashboard.

---

## 1. Escenario de Referencia (Escenario Base Inbound)

Para medir el ahorro, el sistema genera automáticamente una "Línea de Base" que representa la operativa tradicional antes de la optimización.

*   **Definición**: Un camión sale del **Depósito (Mengíbar)**, viaja directamente a la **Planta de Cartón**, carga, y regresa al Depósito.
*   **Fórmula Distancia Base**: `Distancia_Total = (Depósito -> Planta) + (Planta -> Depósito)`.
*   **Km Vacíos (Base)**: Se asume que el retorno de la planta al depósito (`Planta -> Depósito`) es el tramo ineficiente que el modelo intenta eliminar.

---

## 2. Métricas de la Ruta Optimizada (MC-VRPB)

### A. Distancia Total (km)
Es la suma de todos los tramos de la ruta optimizada calculados nodo a nodo (Depósito -> Planta -> Cliente 1 -> ... -> Cliente N -> Depósito). Sincronizada con la distancia real del Mapa Interactivo.

### B. Km Vacíos
Corresponde estrictamente al tramo final de retorno: `Último Cliente -> Depósito`. 
> **Objetivo**: La optimización busca que los clientes visitados estén lo más cerca posible del Depósito final para minimizar este valor.

### C. Coste Total (€)
Se calcula multiplicando la distancia total de la ruta por la **Tarifa Técnica Interna (TCO)**.
*   **Fórmula**: `Distancia_Total * INTERNAL_OPERATIONAL_TCO_RATE (Default: 1.31 €/km)`
> *Nota: Este coste incluye combustible, mantenimiento, personal y amortización de flota propia.*

### E. Rentabilidad de Retornos (Evitado) - "Recuperación de Ganancia"
Representa la transformación de un **costo hundido** (el viaje de retorno vacío obligatorio del escenario base) en una **ganancia neta operativa**. Al eludir estos kilómetros mediante la integración de clientes (Backhauling), la empresa deja de incurrir en un gasto inevitable, recuperando ese capital para la operación.
*   **Concepto**: Cuantificación del dinero que antes se "perdía" por diseño logístico ineficiente y que ahora se captura como rentabilidad.
*   **Fórmula**: `(Km_Vacío_Base - Km_Vacío_Optimizado) * INTERNAL_OPERATIONAL_TCO_RATE`

### F. Ahorro Sistémico (€) - "Margen de Outsourcing"
Representa el dinero que la empresa captura al operar con flota propia el tramo de entrega (Linehaul), en lugar de pagar a un transportista externo.
*   **Segmento Linehaul**: Desde la salida de la Planta hasta el último Cliente de la ruta.
*   **Fórmula**: `Distancia_Linehaul * (Tarifa_Externa - Tarifa_Interna)`
    *   *Tarifa Externa*: 1.70 €/km (Mercado)
    *   *Tarifa Interna*: 1.50 €/km (TCO Propio)
    *   *Margen Capturado*: **0.20 € por cada kilómetro de entrega.**

---

## 3. Emisiones de CO2 (GLEC / VECTO)

El cálculo de emisiones es dinámico y sensible a la carga del camión en cada tramo del viaje.

1.  **Tramo Depot -> Planta**: El motor asume carga máxima (Bobinas de papel). Consumo alto.
2.  **Tramo Planta -> Clientes**: La carga disminuye progresivamente tras cada entrega.
3.  **Tramo Último Cliente -> Depot**: Camión vacío. Consumo mínimo.

*   **Fórmula GLEC (FCR Model)**:
    $$E_{ruta} = \sum_{seg=1}^{n} \left[ d_{seg} \times \left( e_{base} + (i \times m_{seg}) \right) \right] \times f_{CO2}$$

*   **Parámetros de Calibración**:
    *   $e_{base}$: Emisión base en vacío ($0.652 \text{ kg CO}_2/\text{km}$).
    *   $i$: Intensidad por tonelada transportada ($17.32 \text{ g CO}_2/\text{tkm}$).
    *   $f_{CO2}$: Factor de conversión del combustible ($2.68 \text{ kg CO}_2/\text{L}$).

*   **Reducción CO2 %**:
    $$\Delta CO_2\% = \left( 1 - \frac{\sum E_{opt}}{\sum E_{trad}} \right) \times 100$$

---

## 4. Resumen de Tarifas Usadas (config.py)

| Parámetro | Valor | Fuente |
| :--- | :--- | :--- |
| **Tarifa Mercado (Externo)** | 1.70 €/km | Ref: Observatorio MITMA 2026 |
| **Tarifa Técnica (Interna/TCO)** | 1.50 €/km | Ref: Estructura de costes TFM |
| **Inversión CAPEX Camión** | 145,000 € | Precio mercado Tractora + Semi |

---

## 5. Resumen Ejecutivo (KPIs de Alto Nivel)

Esta sección describe las métricas agregadas que aparecen en el Resumen Ejecutivo del Dashboard.

### A. Ahorro de Kilómetros Vacíos (%)
Mide la eficiencia del algoritmo en la eliminación de trayectos sin carga en comparación con el escenario base.
*   **Lógica**: Se compara la suma de los tramos de retorno de todas las rutas optimizadas frente al total de retornos obligatorios del baseline.
*   **Fórmula**: 
    $$\text{Ahorro Vacío \%} = \frac{\sum \text{Km\_Vacíos\_Base}_i - \sum \text{Km\_Vacíos\_Opt}_j}{\sum \text{Km\_Vacíos\_Base}_i}$$

### B. Ahorro Sistémico Total (€)
Es el ahorro neto acumulado al evitar el margen del transportista externo en el segmento de entrega (Linehaul).
*   **Fórmula**: 
    $$\text{Ahorro Sistémico Total} = \sum_{r=1}^{n} (\text{Distancia\_Linehaul}_r \times (1.70 - 1.50))$$

### C. Reducción CO2 Sistémico (kg)
Cuantifica el impacto ambiental positivo del proyecto como un todo.
*   **Fórmula**: 
    $$\text{Reducción CO2 Total} = \text{CO2\_Total\_Baseline} - \text{CO2\_Total\_Proyecto}$$

---

## 6. Métricas de Retorno de Inversión (Software)

Basado en una inversión en tecnología de **25,000 € (CAPEX)**.

### A. ROI Anualizado (%)
Proyecta la rentabilidad del software asumiendo un ciclo operativo de 300 días.
*   **Fórmula**:
    $$\text{ROI} = \frac{(\text{Ahorro Sistémico Diario} \times 300) - \text{CAPEX\_Software}}{\text{CAPEX\_Software}} \times 100$$
    *Nota: En el panel actual, el ROI se calcula sobre el Margen de Outsourcing (Ahorro Sistémico) capturado por la flota propia.*

### B. Periodo de Recuperación (Payback)
Tiempo necesario para que los ahorros operativos amorticen el coste del software.
*   **Fórmula**:
    $$\text{Payback (Días)} = \frac{\text{CAPEX\_Software}}{\text{Ahorro Sistémico Diario}}$$

---

## 7. Glosario de Términos
*   **Linehaul**: Segmento de la ruta desde que el camión sale cargado de la planta hasta que realiza la última entrega al cliente.
*   **Backhauling**: Estrategia de aprovechar el retorno del camión para realizar recogidas o entregas adicionales, eliminando el "kilómetro muerto".
*   **Coste Hundido (Sunk Cost)**: En este modelo, nos referimos al gasto de retorno vacío que la empresa *ya estaba obligada a pagar* en el modelo tradicional y que el software "rescata".

---

## 8. Modelo de Flota Descarbonizada (EV)

El sistema soporta la asignación de status **100% Eléctrico (EV)** a plantas específicas para modelar la transición energética.

### A. Emisiones Directas (Tank-to-Wheel)
Bajo los estándares GLEC v3.0, un camión eléctrico de batería (BEV) operando con energía renovable reporta **0 kg CO2** de emisiones directas en el alcance logístico operativo.
*   En el Dashboard, las rutas que parten de un Hub Eléctrico marcarán la métrica `(EV) 0 kg/km`.

### B. Modelo Energético Dinámico (Sensible a la Masa)
A diferencia del modelo diésel, el consumo eléctrico en vehículos BEV de 44t es altamente sensible a la inercia y carga útil. Aplicamos un modelo de interpolación lineal por tramos de ruta para mayor rigor académico.

*   **Fórmula de Consumo por Tramo**:
    $$kWh_{seg} = d \times \left( C_{empty} + (C_{full} - C_{empty}) \times \frac{Load}{Payload_{max}} \right)$$

*   **Parámetros de Calibración (44t BEV)**:
    *   $C_{empty} = 1.05 \text{ kWh/km}$ (Suelo vacío)
    *   $C_{full} = 1.70 \text{ kWh/km}$ (Carga nominal de 25t)

Este nivel de granularidad permite al tribunal validar la eficiencia real del backhauling, ya que el camion consume menos energia al regresar con pallets de carton que al salir con bobinas de papel pesado.

---

## 9. Modelo de Inversion Mixta (Compra / Leasing / Renting)

El modelo financiero evalua el **TCO (Total Cost of Ownership)** de la flota a un horizonte de 5 anos bajo tres modalidades de adquisicion, considerando una composicion mixta de 7 camiones diesel y 4 electricos.

### A. TCO en Modalidad de Compra

El coste total de propiedad incluye el CAPEX inicial, el OPEX anualizado con inflacion, el escudo fiscal (Tax Shield) por deducciones y la recuperacion del valor residual al final del periodo.

$$TCO_{compra} = -CAPEX + \sum_{t=1}^{5} \frac{-OPEX_t + (OPEX_t + Amort_t) \times \tau}{(1+WACC)^t} + \frac{VR \times (1-\tau)}{(1+WACC)^5}$$

Donde:
*   $OPEX_t = (E_t + M_t + S_t) \times (1 + \pi)^t$ (Energia + Mantenimiento + Seguro con inflacion)
*   $Amort_t = \frac{CAPEX}{5}$ (Amortizacion lineal a 5 anos, 20% anual)
*   $\tau = 0.25$ (Tipo impositivo IS)
*   $VR = CAPEX \times r_{residual}$ (Valor residual al ano 5)
*   *Nota: Escenario sin ayudas estatales directas (MOVES elidido).*

### B. TCO en Modalidad de Leasing Financiero

El arrendamiento financiero difiere de la compra en que no hay desembolso inicial del CAPEX, pero si cuotas mensuales deducibles fiscalmente.

$$TCO_{leasing} = \sum_{t=1}^{5} \frac{-OPEX_t - C_{lease,t} + (OPEX_t + C_{lease,t}) \times \tau}{(1+WACC)^t}$$

Donde:
*   $C_{lease,t} = Cuota_{mensual} \times 12$ (Cuota anual del leasing)
*   Al ejercer la opcion de compra en $t=5$, el pago del VR se compensa con la propiedad del activo (efecto neto = 0).

### C. TCO en Modalidad de Renting Operativo (Full-Service)

El renting incluye mantenimiento y seguro en la cuota, por lo que el unico OPEX variable es la energia.

$$TCO_{renting} = \sum_{t=1}^{5} \frac{-E_t - C_{rent,t} + (E_t + C_{rent,t}) \times \tau}{(1+WACC)^t}$$

Donde:
*   $C_{rent,t} = Cuota_{mensual,FS} \times 12$ (Cuota Full-Service anual)
*   $E_t$ = Coste energetico anual (combustible o electricidad), con inflacion.
*   No hay valor residual. Al finalizar el contrato, se devuelve el vehiculo.

### D. TCO Consolidado de Flota Mixta

El coste total de la flota se obtiene escalando el TCO unitario por el numero de vehiculos de cada tecnologia:

$$TCO_{flota}^{mod} = N_{diesel} \times TCO_{diesel}^{mod} + N_{ev} \times TCO_{ev}^{mod}$$

*   **Configuracion actual**: $N_{diesel} = 7$, $N_{ev} = 4$, Total = 11 camiones.
*   **Recomendacion**: La modalidad con menor $|TCO_{flota}^{mod}|$ es la optima desde el punto de vista financiero.

### E. Parametros de Mercado

| Parametro | Diesel | Electrico | Fuente |
|:---|:---|:---|:---|
| CAPEX | 140,000 EUR | 340,000 EUR | ACEA 2024 |
| Valor Residual (5a) | 30% | 25% | Mercado secundario |
| Renting Mensual | 2,800 EUR/mes | 5,600 EUR/mes | Ofertas mercado 2025 |
| Leasing Mensual | 2,600 EUR/mes | 5,200 EUR/mes | TAE ~6.5% |
| Subvencion MOVES | - | 90,000 EUR | MOVES III (parametrizable) |
|   |   |   |   |

---

## 10. Indicadores de Eficiencia y Unit Economics (TFM)

Esta sección detalla los indicadores de rendimiento (KPIs) de segundo nivel utilizados para la auditoría operativa del algoritmo en el marco del TFM.

### A. Fill Rate (%) - Saturación de Flota
Mide el aprovechamiento de la capacidad de carga del vehículo en el conjunto de rutas optimizadas.
*   **Fórmula**:
    $$\text{Fill Rate \%} = \frac{\text{Total Pallets Movidos}}{\text{Num Rutas} \times \text{Capacidad Máxima (34)}} \times 100$$
*   *Interpretación*: Un valor cercano al 100% indica una consolidación de carga óptima, minimizando el número de camiones necesarios.

*   *Nota*: En este modelo, el tramo vacío es el trayecto desde el último cliente hasta el Depósito (Mengíbar).

