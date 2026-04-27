# Metodología de Cálculo: TCO a 5 Años (VAN)

Este documento detalla el modelo financiero utilizado por el sistema **Logistics Optimizer** para la evaluación estratégica de flotas. El modelo se basa en el **Valor Actual Neto (VAN)** de los flujos de caja operativos y de inversión.

## 1. Estructura del Modelo

El TCO se calcula sobre un horizonte temporal de **5 años (60 meses)** y se desglosa en dos componentes principales para permitir un análisis de sensibilidad limpio:

### 1.1. TCO de Activos (Hardware)
Representa los costes asociados directamente con el vehículo y su infraestructura:
*   **CAPEX Inicial**: Inversión neta (Precio Camión + Cargadores - Ayudas MOVES).
*   **OPEX Energía**: Consumo de combustible diésel o electricidad.
*   **Mantenimiento y Neumáticos**: Costes técnicos de operación.
*   **Seguros**: Primas anuales.
*   **Escudo Fiscal**: Ahorro impositivo (25%) sobre gastos operativos y amortización.
*   **Valor Residual**: Ingreso por venta del activo al final del periodo (Año 5).

### 1.2. TCO de Personal (Operación)
Representa el factor humano necesario para la actividad:
*   **Salario Conductor**: Coste total empresa (42.000 €/año base).
*   **Deducción Fiscal**: Ahorro del 25% por gastos de personal en el Impuesto de Sociedades.

---

## 2. Dinámica Temporal: Inflación y Descuento

A diferencia de modelos estáticos, este sistema aplica variaciones anuales:

### 2.1. Vector de Inflación ($\pi$)
Se aplica a todos los costes variables (Energía, Mantenimiento, Salarios).
- **Fórmula**: $Coste_{t} = Coste_{0} \times \prod_{i=1}^{t} (1 + \pi_i)$
- **Valores**: [2.0%, 3.0%, 5.0%, 3.0%, 2.0%]

### 2.2. Tasa de Descuento (WACC)
Representa el coste de oportunidad del capital. Se usa para traer los flujos futuros al presente.
- **Factor de Descuento**: $DF_t = \frac{1}{\prod_{i=1}^{t} (1 + WACC_i)}$
- **Valores**: [7.0%, 7.5%, 8.0%, 8.5%, 9.0%]

---

## 3. Cálculo de Rentabilidad (ROI y TIR)

Para evaluar la viabilidad de la inversión en la flota propia frente a la subcontratación, se utilizan métricas estándar de análisis de inversiones:

### 3.1. ROI (Retorno de la Inversión)
Se aplica la fórmula estándar internacional para medir el rendimiento acumulado en el horizonte de 5 años:

**ROI = [(Ganancia de la Inversión - Coste de la Inversión) / Coste de la Inversión] x 100**

Donde:
*   **Ganancia de la Inversión**: Sumatorio de los Flujos de Caja Libres (FCL) de los años 1 a 5, más el Valor Residual neto de impuestos.
*   **Coste de la Inversión**: Desembolso inicial (CAPEX Neto) realizado en el Año 0.

### 3.2. TIR (Tasa Interna de Retorno)
Representa la tasa de descuento que hace que el Valor Actual Neto (VAN) de la inversión sea igual a cero. Es la rentabilidad anualizada compuesta de la operación.

---

## 4. Supuestos Críticos para el TFM
- **Deducibilidad**: Se asume que la empresa tiene beneficios suficientes para aprovechar el 100% del escudo fiscal (25%).
- **Utilización**: Se asume un uso intensivo de 130.000 km/año por unidad.
- **Financiación**: Las cuotas de Renting/Leasing se mantienen fijas nominalmente (sin inflación) durante el contrato.
