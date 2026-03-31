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

### D. Ahorro Vacío %
Mide la eficiencia física lograda al "rellenar" el retorno vacío tradicional con entregas a clientes.
*   **Fórmula**: `(Km_Vacío_Base - Km_Vacío_Optimizado) / Km_Vacío_Base`
*   *Representa el porcentaje de "kilómetros muertos" que hemos logrado eliminar.*

### E. Ahorro Retornos Vacíos (€) - "Ahorro Físico"
Es el valor monetario de los kilómetros que hemos dejado de recorrer en vacío gracias al modelo MC-VRPB.
*   **Fórmula**: `(Km_Vacío_Base - Km_Vacío_Optimizado) * INTERNAL_OPERATIONAL_TCO_RATE`

### F. Ahorro Sistémico (€) - "Margen de Outsourcing"
Representa el dinero que la empresa captura al operar con flota propia el tramo de entrega (Linehaul), en lugar de pagar a un transportista externo.
*   **Segmento Linehaul**: Desde la salida de la Planta hasta el último Cliente de la ruta.
*   **Fórmula**: `Distancia_Linehaul * (Tarifa_Externa - Tarifa_Interna)`
    *   *Tarifa Externa*: 2.22 €/km (Mercado)
    *   *Tarifa Interna*: 1.31 €/km (Propia)
    *   *Margen Capturado*: **0.91 € por cada kilómetro de entrega.**

---

## 3. Emisiones de CO2 (GLEC / VECTO)

El cálculo de emisiones es dinámico y sensible a la carga del camión en cada tramo del viaje.

1.  **Tramo Depot -> Planta**: El motor asume carga máxima (Bobinas de papel). Consumo alto.
2.  **Tramo Planta -> Clientes**: La carga disminuye progresivamente tras cada entrega.
3.  **Tramo Último Cliente -> Depot**: Camión vacío. Consumo mínimo.

*   **Fórmula Base**: `Consumo = Emisión_Suelo_Vacío + (Intensidad_Incremental * Carga_Actual)`
*   **Reducción CO2 %**: Compara los kg de CO2 generados por la ruta optimizada frente a la suma de CO2 de los dos viajes tradicionales separados (Inbound + Outbound tradicional).

---

## 4. Resumen de Tarifas Usadas (config.py)

| Parámetro | Valor | Fuente |
| :--- | :--- | :--- |
| **Tarifa Mercado (Externo)** | 2.22 €/km | Histórico CUBO |
| **Tarifa Técnica (Interna/TCO)** | 1.31 €/km | Cálculo estructura de costes 2026 |
| **Inversión CAPEX Camión** | 145,000 € | Precio mercado Tractora + Semi |
