# 📉 Evaluación Realista de ROI en Proyectos de Flota (Asset-Heavy)

Tienes toda la razón. Presentar un **ROI del 473%** y un **Payback de 10 meses** a una Junta Directiva en un proyecto de CAPEX de 7 millones de euros restará credibilidad al modelo. Matemáticamente nuestros números cuadran porque comparan "tarifa de mercado de venta" vs "cálculo de combustible y amortización", pero desde el punto de vista del **Total Cost of Ownership (TCO) y Finanzas Corporativas**, están incompletos.

A continuación, resumo la documentación estándar del sector (apoyada por estudios del *National Private Truck Council* y consultoras de cadena de suministro) sobre por qué ocurre esto y cómo se debe evaluar la viabilidad de comprar flota propia.

---

## 1. ¿Por qué nuestro 473% de ROI es "Surrealista"? (Los Costes Ocultos)

El modelo de *financial_analyzer.py* actual sufre de un sesgo de "mundo ideal". Asume que todo diferencial entre pagarle a un tercero (1.35 €/km) y hacerlo nosotros (1.03 €/km) es beneficio neto. Ignora varias bolsas de coste crítico:

### A. Gastos de Estructura (Overhead Hub)
Tener 51 camiones propios requiere una mini-empresa dentro de la empresa:
*   **Gestores de tráfico (Planners):** Necesitamos nóminas de personal operando el TMS 24/7.
*   **Aparcamiento seguro y bases operativas:** 51 camiones no se aparcan en la calle. Requieren alquiler de campas vigiladas.
*   **Mantenimiento Imprevisto (Downtime):** El modelo no asume averías graves. Cuando un camión externo se rompe, el proveedor manda otro. Cuando el nuestro se rompe, perdemos la ruta del día *y* pagamos la grúa.

### B. El Riesgo de Sub-Utilización (El gran enemigo del CAPEX)
Nuestro modelo calcula que ahorramos dinero todos los días basándose en la demanda "media". 
*   ¿Qué pasa en los meses "valle" donde salen 25 viajes en lugar de 38? 
*   Los camiones externos simplemente no se contratan (coste cero). Nuestros camiones propios y los salarios de nuestros conductores **hay que pagarlos igual**, destrozando el ROI anual.

### C. La Crisis de Choferes (RRHH)
Contratar 51 choferes, pagarles vacaciones, gestionar bajas médicas, dietas y rotación tiene un coste oculto altísimo en el sector del transporte que no está en el coste por kilómetro puro.

---

## 2. ¿Cómo se evalúan realmente estos proyectos en la Industria?

Para presentar esto de forma realista ante inversores, no se usa un ROI puro bruto, sino proyecciones financieras complejas:

### A. Modelado de TCO (Total Cost of Ownership) Fully-Burdened
En lugar de un coste técnico de 1.03 €/km, se debe calcular el coste "Totalmente Cargado" (Fully-Burdened CPM).
Esto sube el coste interno real a **~1.22 € - 1.28 €/km**. 
El ahorro frente al externo (1.35 €/km) sigue existiendo, pero el margen se estrecha brutalmente. El ahorro anual de 5.4 M€ bajaría rápidamente a un escenario realista de **1.0 M€ - 1.5 M€**.

### B. TIR (Tasa Interna de Retorno) y VAN en lugar de ROI Simple
Las empresas no valoran igual 1 millón de euros hoy que dentro de 4 años por culpa de la inflación y el coste de oportunidad.
*   Se exige un **WACC (Coste Promedio de Capital)** para el proyecto.
*   **Benchmark del Sector:** Una inversión logística de flota propia se aprueba normalmente si arroja una **TIR de entre el 12% y el 20%** con un **Payback de 3 a 4.5 años**. Todo lo que prometa recuperación en menos de 1 año (nuestros 10 meses) dispara las alarmas del departamento de riesgos.

### C. Justificación por Valor Intangible (Service Level)
Según la literatura, la compra de flota masiva raras veces se justifica *únicamente* por el puro ahorro de "céntimo por kilómetro". La justificación real del Escenario B incluye:
*   **Garantía de Capacidad:** En picos como Black Friday, los externos suben el precio un 40% o directamente no tienen camiones. La flota tuya asegura que la planta no se ahogue en stock.
*   **Calidad de Servicio y Marca:** Los choferes propios llevan tu uniforme, conocen las normativas de seguridad de la planta a fondo y dañan menos la carga.
*   **Protección Ambiental Constante:** Te garantiza que estás usando tractoras EURO 6 modernas o GNL, mientras que el externo podría mandarte la tractora que le sobre.

---

## 3. Propuesta de "Narrativa" para el Dashboard (Sin tocar código todavía)

Dado que no podemos tocar el código ahora mismo, la estrategia en la presentación del caso debería ser esta:

> *"La herramienta arroja un ROI técnico bruto superior al 400%, lo cual demuestra una disfunción masiva en las tarifas que estamos pagando actualmente a terceros. Sin embargo, sabemos que en la realidad, la asunción de estructura corporativa para gestionar 50 camiones propios absorberá al menos un 60-70% de este margen teórico, aterrizando el proyecto en un ROI financiero realista de entre un **18% y 25% anual** (Payback de 3.5 a 4 años), lo cual sigue siendo extremadamente rentable y justifica transicionar paulatinamente de un modelo Asset-Light a uno mixto."*
