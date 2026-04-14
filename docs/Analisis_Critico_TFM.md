# Auditoría Crítica y Puntos de Ataque (TFM)

Este documento detalla las debilidades intrínsecas del modelo **GABM-EPF** (Logistics Optimizer). Está diseñado para preparar al autor ante una defensa académica rigurosa, identificando qué partes del modelo son simplificaciones y dónde residen los riesgos de implementación.

---

## 🛑 Debilidades del Modelo Logístico

### 1. Determinismo y Rigidez Temporal
*   **El Problema:** El simulador no incluye **Ventanas Horarias (Time Windows)**. Asume que el cliente puede recibir la mercancía en cualquier momento tras la salida del camión.
*   **Riesgo de Defensa:** El tribunal puede argumentar que los ahorros son ficticios si las rutas óptimas obligan a entregas a las 03:00 AM en clientes que abren a las 09:00 AM.
*   **Contramedida:** Definir el modelo como una "Evaluación de Capacidad Sistémica" y no como un secuenciador de última milla.

### 2. Heurística de Penalización de Retorno
*   **El Problema:** El uso de un factor multiplicador fijo ($ \times 2.5 $) para forzar el backhauling es una solución técnica ad-hoc, no derivada de un estudio de costes marginales real.
*   **Riesgo de Defensa:** Cuestionamiento sobre la sensibilidad del modelo ante variaciones de este parámetro "mágico".

### 3. Homogeneidad de Activos
*   **El Problema:** Se asume una flota única de 44 toneladas (Euro VI).
*   **Riesgo de Defensa:** Ignora restricciones urbanas de acceso (ZBE), limitaciones de muelle en clientes pequeños y la necesidad de flota capilar (furgonetas/camiones rígidos).

---

## 💰 Debilidades del Modelo Financiero

### 1. Estática de Costes (TCO)
*   **El Problema:** El TCO de 1.50 €/km es un promedio ponderado basado en datos de 2026, pero no contempla la **volatilidad del diesel** ni el incremento del coste salarial por escasez de choferes.
*   **Riesgo de Defensa:** El tribunal preguntará por el análisis de sensibilidad ante un escenario inflacionista agresivo.

### 2. Olvido del Coste de Oportunidad
*   **El Problema:** Proponer un CAPEX de >7M€ en camiones asume que el transporte es el mejor lugar para poner el capital de la empresa.
*   **Riesgo de Defensa:** ¿Por qué invertir en camiones y no en una nueva línea de producción de cartón con mayor margen? (Asset-Heavy vs Asset-Light).

### 3. Gastos Indirectos (Estructura)
*   **El Problema:** El modelo no detalla el incremento de **Estructura de Personal**: jefes de tráfico, mecánicos, gestores de flota y administrativos necesarios para gestionar 51 camiones propios.

---

## 🛡️ "Ataques" Probables del Tribunal y Respuestas

| Pregunta del Tribunal | Debilidad del Proyecto | Respuesta Recomendada (Defensa) |
| :--- | :--- | :--- |
| **¿Y si un conductor causa baja?** | Resiliencia operativa. | El buffer del 10% ($\rho = 1.10$) cubre redundancia de activos y personal según convenio. |
| **¿Cómo escala a 1000 nodos?** | Rendimiento computacional. | OR-Tools (GLS) es un meta-heurístico con convergencia polinomial; se usaría zonificación en escalas mayores. |
| **¿Ha validado la limpieza de carga?** | Compatibilidad Inbound/Outbound. | Se considera el transporte de papel (materia prima) compatible con cajas de cartón; no requiere lavado químico. |
| **¿Por qué ser dueño de la flota?** | Riesgo de Activo. | No es solo un ahorro de €, es un seguro de capacidad de servicio ante la crisis logística actual. |

---

## ⚠️ Conclusión de Riesgo
El modelo es **SOTA (State of the Art)** en cuanto a visualización y lógica de optimización matemática, pero es **frágil** en la integración de restricciones de la vida real (tráfico dinámico, huelgas, cierres de muelles). Debe presentarse como una **herramienta estratégica de toma de decisiones**, no como un sistema de despacho automático sin supervisión humana.
