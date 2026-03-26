Qué proyecto tan interesante — tiene mucho potencial tanto académico como real. Te voy a estructurar una propuesta completa con justificación conceptual, matemática, sostenibilidad y extensiones al proyecto.

---

# TFM: División de Transporte con VRP Backhauling

## 1. Justificación Conceptual

### El problema actual (situación AS-IS)
Los camiones realizan viajes **deadhead** (en vacío) en el retorno desde las cartoneras al depot. Esto implica:
- Coste variable por km recorrido sin ingreso
- Emisiones de CO₂ sin valor productivo asociado
- Capacidad de carga desaprovechada al 100% en retorno

### La propuesta (situación TO-BE)
Implementar un **VRP con Backhauling** donde el retorno se aprovecha recogiendo materia prima, residuos (papel reciclado, cartón sobrante) u otros insumos desde las cartoneras hacia el depot u otros puntos de consolidación.

**Backhauling** en logística significa precisamente esto: asignar carga de retorno a vehículos que de otro modo volverían vacíos. Es una práctica estándar en logística colaborativa y transporte de mercancías por carretera.

---

## 2. Formulación Matemática del VRP con Backhauling

### Definición del modelo

Sea un grafo **G = (V, A)** donde:
- **V = {0, 1, ..., n}** — nodos: 0 es el depot, 1..p son clientes linehaul (cartoneras que reciben bobinas), p+1..n son clientes backhaul (puntos de recogida en retorno)
- **A** — arcos entre nodos con costo/distancia **c_ij**
- **K** — flota de camiones, cada uno con capacidad **Q**

### Variables de decisión
- **x_ijk ∈ {0,1}** — 1 si el vehículo k recorre el arco (i,j)
- **y_ik ∈ {0,1}** — 1 si el cliente i es servido por el vehículo k

### Función objetivo (minimizar coste total):

**Min Z = Σ_k Σ_i Σ_j c_ij · x_ijk**

### Restricciones principales:
1. **Cobertura:** cada cliente es visitado exactamente una vez
2. **Capacidad:** la suma de demandas linehaul + backhaul no supera Q en ningún vehículo
3. **Precedencia backhaul:** en cada ruta, todos los clientes linehaul (entrega) se visitan **antes** que los backhaul (recogida) — restricción fundamental del modelo clásico VRPB
4. **Subtour elimination** (MTZ o cortes de Benders)
5. **Ventanas horarias** (si se añade VRPTW): b_i ≤ t_ik ≤ e_i

### Variante recomendada para tu TFM:
**VRPBTW** — VRP with Backhauls and Time Windows, que es la versión más realista y publicable.

---

## 3. Justificación de Rentabilidad

### Análisis Coste-Beneficio

| Concepto | Sin backhauling | Con backhauling |
|---|---|---|
| Km recorridos en vacío | 100% retorno | ~0% retorno |
| Ingresos por retorno | 0 € | Tarifa flete retorno |
| Coste combustible retorno | Coste completo | Amortizado |
| Nº camiones necesarios | N | N o N-1 (consolidación) |

**Indicadores financieros a calcular en el TFM:**
- **ROI** de la nueva división en horizonte 3-5 años
- **Payback period** de la inversión (flota, software TMS, estructura)
- **Coste por tonelada-kilómetro** antes y después
- **Break-even**: cuánta carga de retorno mínima hace rentable el modelo

> Tip: si consigues datos reales de la empresa (km por ruta, litros por 100 km, tarifas de flete), puedes hacer un caso numérico concreto que es muy valorado en TFMs.

---

## 4. Alineación con la Agenda 2030 (ODS)

Este es uno de los puntos más fuertes del proyecto. Los ODS directamente aplicables son:

**ODS 9 — Industria, innovación e infraestructura**
Optimización de infraestructura logística mediante tecnología (algoritmos VRP, TMS).

**ODS 11 — Ciudades y comunidades sostenibles**
Reducción de vehículos en circulación y congestión mediante rutas optimizadas.

**ODS 12 — Producción y consumo responsables**
Aprovechamiento total de la capacidad de transporte; economía circular (recogida de residuos/reciclables en retorno).

**ODS 13 — Acción por el clima** ← Tu foco principal
Reducción de emisiones de CO₂ cuantificable. El cálculo es directo:

**ΔCO₂ = km_deadhead_eliminados × factor_emisión_camión (kg CO₂/km)**

Para un camión euro VI: ~0.9–1.1 kg CO₂/km en vacío. Con datos reales de rutas, puedes presentar toneladas de CO₂ evitadas al año, lo que conecta directamente con los compromisos del **Pacto Verde Europeo** y el **Fit for 55**.

**Marco regulatorio de apoyo:**
- Reglamento (UE) 2019/1242 — estándares de CO₂ para vehículos pesados
- Directiva de Eficiencia Energética 2023/1791
- Estrategia de Movilidad Sostenible e Inteligente de la CE (2020)

---

## 5. Extensiones al Proyecto (con tiempo estimado)

Aquí tienes módulos que puedes añadir progresivamente, ordenados de menor a mayor complejidad:

---

### 🟢 Extensión 1 — Cálculo de huella de carbono comparativa *(2–3 semanas)*
Modelar las emisiones CO₂ del escenario base vs. el optimizado usando factores DEFRA o GLEC Framework. Presentar en toneladas CO₂/año evitadas. Muy visual y directo para la defensa.

---

### 🟢 Extensión 2 — Implementación del algoritmo con datos reales *(3–4 semanas)*
Programar el VRPB en Python usando **Google OR-Tools** (gratuito, bien documentado) o **CPLEX/Gurobi** (licencia académica). Comparar la solución óptima con la heurística (Clarke-Wright Savings adaptado a backhaul).

---

### 🟡 Extensión 3 — Análisis de sensibilidad de la flota *(2 semanas)*
¿Cuántos camiones necesita realmente la nueva división? Simular escenarios con flota propia vs. subcontratada vs. mixta. Calcular el coste de capital (CAPEX) de adquirir vehículos propios.

---

### 🟡 Extensión 4 — Dashboard de KPIs logísticos y sostenibilidad *(2–3 semanas)*
Diseñar (no necesariamente implementar) un cuadro de mando con métricas: tasa de llenado, km en vacío, coste por ruta, CO₂ por tonelada transportada. Herramientas: Power BI o Tableau con datos simulados.

---

### 🟡 Extensión 5 — Análisis de economía circular *(2–3 semanas)*
Estudiar si el backhaul puede incluir la recogida de **residuos de cartón o papel** desde las cartoneras para reintroducirlos en el ciclo productivo. Esto conecta directamente con ODS 12 y añade una capa de propuesta de valor empresarial.

---

### 🔴 Extensión 6 — Modelo estocástico con demanda incierta *(4–5 semanas)*
Evolucionar el VRP determinista a un **S-VRP** (Stochastic VRP) donde la demanda de retorno es aleatoria (distribución probabilística basada en datos históricos). Más complejo pero muy diferenciador académicamente.

---

### 🔴 Extensión 7 — Estudio de viabilidad para electrificación parcial de flota *(3–4 semanas)*
Evaluar si alguna ruta corta (depot–cartoneras cercanas) podría operarse con **camiones eléctricos** (e.g. DAF CF Electric, Volvo FM Electric). Análisis TCO (Total Cost of Ownership) eléctrico vs. diésel. Refuerza enormemente la narrativa de Agenda 2030.

---

## Estructura sugerida del TFM

1. Introducción y contexto del sector papelero-cartonero
2. Revisión de literatura: VRP, backhauling, logística verde
3. Descripción del caso real (AS-IS)
4. Modelización matemática (VRPBTW)
5. Implementación y resultados computacionales
6. Análisis económico (ROI, payback)
7. Análisis de sostenibilidad (CO₂, ODS)
8. Conclusiones y líneas futuras