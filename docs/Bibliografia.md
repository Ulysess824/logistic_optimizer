# Bibliografía Verificada para TFM: Optimización Logística MC-VRPB

Este documento contiene una selección de referencias académicas verificadas para sustentar el Trabajo de Fin de Máster (TFM). Los artículos han sido validados para asegurar su existencia y relevancia técnica en el campo de la investigación operativa y logística.

##  Resumen por Capítulo del TFM

| Capítulo TFM | Temática Principal | Referencias Clave |
| :--- | :--- | :--- |
| **Introducción / Motivación** | Justificación del Backhauling y ahorro de costes. | [11], [12], [13] |
| **Revisión de Literatura** | Estado del arte del VRP con Backhauls (VRPB). | [1], [2], [5], [6] |
| **Formulación Matemática** | Modelos Multi-Centro / Multi-Depósito y MC-VRPB. | [3], [4], [7], [9] |
| **Metodología** | Búsqueda Local Guiada (GLS) y uso de OR-Tools. | [16], [17], [18], [19] |
| **Caso de Estudio y Resultados** | Aplicación industrial y validación empírica. | [14], [15], [20] |

## Detalle de Referencias (Verificadas)

### Bloque 1: Modelos Matemáticos del VRPB
- **[1] Koç, Ç. & Laporte, G. (2018).** *"Vehicle routing with backhauls: Review and research perspectives"*. Computers & Operations Research, 91, 79–91. (Survey exhaustivo sobre VRPB).
- **[2] Queiroga, E., et al. (2020).** *"On the exact solution of vehicle routing problems with backhauls"*. European Journal of Operational Research, 287(1), 76–89. (Algoritmos BCP para soluciones óptimas).
- **[3] Toth, P. & Vigo, D. (Eds.) (2002/2014).** *"The Vehicle Routing Problem"* y *"Vehicle Routing: Problems, Methods, and Applications"*. (Las referencias canónicas del campo).
- **[4] Santos, M.J., et al. (2020).** *"The vehicle routing problem with backhauls towards a sustainability perspective: a review"*. TOP Journal. (Enfoque en reducción de CO2 y km en vacío).
- **[5] Ropke, S. & Pisinger, D. (2006).** *"A unified heuristic for a large class of vehicle routing problems with backhauls"*. EJOR. (Base para metaheurísticas generalistas).

### Bloque 2: Multi-Depot VRP (MD-VRP)
- **[6] Montoya-Torres, J.R., et al. (2015)**. *"A literature review on the vehicle routing problem with multiple depots"*. Computers and Industrial Engineering. (Justificación de la componente Multi-Planta).
- **[7] Jayarathna, D.G.N.D., et al. (2021)**. *"Survey on Ten Years of Multi-Depot Vehicle Routing Problems"*. JSDTL. (Tendencias recientes en MDVRP).
- **[8] Ramos, T.R.P., et al. (2020)**. *"Multi-depot vehicle routing problem: a comparative study of alternative formulations"*. IJLRA. (Modelado matemático avanzado).

### Bloque 3: Consolidación y Kilómetros en Vacío (Deadhead)
- **[9] Dong, Z., et al. (2025)**. *"Practical and Effective Heuristics for the Backhaul Profit Maximization Problem"*. Networks and Spatial Economics. (Estrategias de maximización de utilidad en el retorno).
- **[10] MIT CTL Master's Thesis (2022)**. *"Empty Miles Reduction in the Downstream Network for a Consumer Goods Manufacturer"*. MIT Sloan/CTL. (Caso de estudio análogo al problema papelero).

### Bloque 4: Casos de Estudio y Metaheurísticas
- **[11] Goetschalckx, M. & Jacobs-Blecha, C. (1989/1992)**. *"The vehicle routing problem with backhauls: Properties and solution algorithms"*. (Paper seminal del campo).
- **[12] Brandão, J. (2006)**. *"A new tabu search algorithm for the vehicle routing problem with backhauls"*. EJOR. (Escalabilidad a +1000 nodos).
- **[13] Ubeda, S., et al. (2011)**. *"Green logistics at Eroski: A case study"*. IJPE. (Caso real en flota española multi-depósito).

### Bloque 5: Guided Local Search (GLS) y OR-Tools
- **[14] Voudouris, C. & Tsang, E.P.K. (1999)**. *"Guided local search and its application to the travelling salesman problem"*. EJOR. (Referencia fundacional del algoritmo GLS usado en el proyecto).
- **[15] Cuvelier, T., et al. (2023)**. *"OR-Tools' Vehicle Routing Solver: A Generic Constraint-Programming Solver with Heuristic Search"*. ROADEF/Google Research. (Referencia técnica oficial de OR-Tools).
- **[16] Zhong, Y. & Cole, M.H. (2005)**. *"A vehicle routing problem with backhauls and time windows: a guided local search solution"*. Transportation Research Part E. (Unión de VRPB y GLS, clave para la Fase 2).

### Bloque 6: Software y Librerías de Desarrollo (Citas Técnicas)
Para la implementación técnica se han utilizado herramientas de código abierto que deben citarse de la siguiente manera:

- **[17] Perron, L. & Furnon, V. (2024).** *"OR-Tools"*. Google Optimization Tools. https://developers.google.com/optimization.
- **[18] McKinney, W. (2010).** *"Data structures for statistical computing in Python"*. Proc. of the 9th Python in Science Conference. (Referencia para `Pandas`).
- **[19] Harris, C.R., et al. (2020).** *"Array programming with NumPy"*. Nature, 585(7825), 357–362.
- **[20] Hunter, J.D. (2007).** *"Matplotlib: A 2D graphics environment"*. Computing in Science & Engineering, 9(3), 90–95.
- **[21] Vink, R. (2024).** *"Polars: A lightning-fast DataFrame library"*. GitHub Repository. https://github.com/pola-rs/polars.
- **[22] Luxen, D. & Vetter, C. (2011).** *"Real-time routing with OpenStreetMap data"*. Proc. of the 19th ACM SIGSPATIAL. (Referencia para `OSRM`).
- **[23] Plotly Technologies Inc. (2015).** *"Collaborative data science"*. Montréal, QC. https://plot.ly.
- **[24] Team SimPy. (2020).** *"SimPy: Discrete event simulation for Python"*. https://simpy.readthedocs.io.
- **[25] python-visualization. (2020).** *"Folium"*. https://python-visualization.github.io/folium/.
