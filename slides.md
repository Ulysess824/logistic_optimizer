# Contexto del Proyecto: TFM — Logistics Optimizer v5.3

## Objetivo de la Presentación

Crear una presentación de TFM con Quarto y (Trabajo de Fin de Máster) que comunique de forma clara, rigurosa e impactante el desarrollo y resultados del sistema **Logistics Optimizer v5.3**, un optimizador logístico basado en inteligencia operacional y machine learning aplicado a redes de distribución multi-planta.

La presentación debe funcionar como **pitch técnico-ejecutivo**: convencer a un tribunal académico tanto de la solidez técnica como del valor de negocio real del proyecto.

---

## Audiencia

- **Tribunal de TFM** con perfil mixto: académico + profesional/empresarial.
- Se valora tanto el rigor metodológico como la aplicabilidad real.
- El tribunal espera ver: problema bien definido, solución técnica sólida, resultados cuantificables y visión de impacto.

---

## Estructura Narrativa de la Presentación

La historia a contar es: **Problema → Solución Técnica → Validación → Impacto**

### Bloque 1 — El Problema (2-3 slides)
- Ineficiencia estructural en logística de distribución multi-planta
- El coste real de los km en vacío en flotas de camiones pesados
- Limitaciones de los enfoques tradicionales (estimaciones lineales, optimización manual)
- **Gancho**: cuantificar el problema antes de mostrar la solución

### Bloque 2 — Arquitectura Técnica (4-5 slides)
- Visión general del sistema: diagrama de componentes
- **Motor de optimización**: Google OR-Tools con modelo MC-VRPB (Multi-Depot Vehicle Routing Problem with Backhauls)
  - Por qué MC-VRPB y no enfoques más simples
- **Lógica de Backhauling**: maximización de carga en trayectos de retorno
- **Integración OSRM**: distancias y tiempos reales por carretera vs. estimaciones euclidianas
- **Validación física**: restricción de 34 pallets EPAL por camión de 44t (modelo volumétrico real)

### Bloque 3 — Red Logística y Datos (2-3 slides)
- **11 plantas** de producción y distribución integradas en el modelo
- Generador de escenarios estocásticos: 250-261 días laborales con volatilidad controlada
- Sistema de filtrado dual de candidatos:
  - Radio Haversine para preselección geográfica
  - Validación GPS para confirmación de coordenadas reales
- Cómo se modela la demanda y la variabilidad operativa

### Bloque 4 — Business Case (3-4 slides) ⭐ *El más crítico*
- **ROI Anualizado**: ~1.318,8%
  - Contextualizar por qué es creíble (Capex/Opex alineado con estándares MITMA)
- **Ahorro sistémico anual**: ~354.699 € frente a baseline sin optimización
- **Payback Period**: inversión en software + transición de flota
- **Comparativa de adquisición**: Compra vs. Leasing vs. Renting (modelo dinámico)
- Mostrar el baseline claramente para que el delta sea tangible

### Bloque 5 — Impacto Ambiental (1-2 slides)
- **Ahorro proyectado**: ~1.923,8 toneladas de CO₂ al año
- Marco metodológico: **GLEC v3.0** (Global Logistics Emissions Council)
- Factores **VECTO**: específicos para camiones 40-44t (Subgrupo 5-LH)
- Posicionar la sostenibilidad como ventaja competitiva, no solo como cumplimiento normativo

### Bloque 6 — Dashboards y Demo (2-3 slides)
- Cuadro de mando modular:
  - Mapas interactivos de rutas
  - Grafos de red logística
  - Análisis de riesgos operativos
- **Slicer Temporal**: auditoría día a día de rutas generadas + consolidado anual
- Si es posible: vídeo corto o GIF animado del sistema en acción

### Bloque 7 — Conclusiones y Trabajo Futuro (1-2 slides)
- Síntesis de los 3 grandes logros: técnico, financiero, ambiental
- Limitaciones actuales y honestidad metodológica
- Líneas futuras: escalabilidad, integración con ERP, modelos predictivos de demanda

---

## KPIs y Métricas Clave a Destacar

| Métrica | Valor |
|---|---|
| ROI Anualizado | ~1.318,8% |
| Ahorro anual | ~354.699 € |
| CO₂ ahorrado/año | ~1.923,8 t |
| Plantas integradas | 11 |
| Días simulados | 250-261 días laborales |
| Capacidad por camión | 34 pallets EPAL / 44t |

---

## Stack Tecnológico del Proyecto

- **Optimización**: Google OR-Tools (MC-VRPB)
- **Geoespacial**: OSRM (Open Source Routing Machine)
- **Estándar financiero**: MITMA (vehículos pesados)
- **Estándar ambiental**: GLEC v3.0 + factores VECTO (Subgrupo 5-LH)
- **Visualización**: Dashboards modulares con mapas interactivos y slicer temporal

---

## Tono y Estilo de la Presentación

- **Ejecutivo pero riguroso**: datos precisos, sin inflar resultados
- **Visual sobre textual**: gráficas, diagramas y mapas en lugar de bullet points
- **Narración lineal**: cada slide debe responder a "¿y esto por qué importa?"
- **El Business Case es el clímax**: construir toda la presentación hacia ese momento
- Evitar jerga técnica sin contexto; cada concepto técnico va acompañado de su impacto práctico

---

## Instrucciones para el Agente

1. Usa esta estructura como guía narrativa, no como índice rígido — puedes ajustar el número de slides por bloque según el contenido disponible.
2. Prioriza **impacto visual**: gráficas de barras para ahorros, mapas para la red logística, diagramas de flujo para la arquitectura.
3. El **Bloque 4 (Business Case)** es el más importante — dedícale más espacio y claridad visual.
4. Cada slide debe tener **un mensaje principal** claro en el título (no un título genérico como "Resultados", sino "354.699 € de ahorro anual demostrable").
5. El slide de **ROI** debe incluir contexto comparativo para que el dato sea creíble, no solo el número.
6. Para el bloque de sostenibilidad, menciona explícitamente los estándares GLEC y VECTO como señal de rigor metodológico.
7. La demo de dashboards debe ir **antes** de las conclusiones, como prueba visual del sistema funcionando.