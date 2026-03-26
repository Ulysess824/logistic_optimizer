# Bibliografía Técnica y Científica

Este documento recopila las fuentes, normativas y estudios científicos que respaldan los cálculos de optimización, emisiones y costes del proyecto Logistics Optimizer.

## Gestión de Emisiones y Huella de Carbono

### [DOI: 10.1016/j.trd.2019.08.002]
*   **Referencia**: Grigoratos, T., et al. (2019). *Real world emissions performance of heavy-duty Euro VI diesel vehicles*. Transportation Research Part D: Transport and Environment.
*   **Aplicación**: Proporciona los factores de emisión reales (kg CO2/km) para camiones de 40t (Subgrupo VECTO 5-LH) utilizados en el dashboard ejecutivo.
*   **Valores adoptados**: Vacío (0.652 kg/km), Cargado (1.085 kg/km).

### Marco GLEC (Global Logistics Emissions Council)
*   **Referencia**: SFC (2023). *GLEC Framework for Logistics Emissions Methodologies v3.0*.
*   **Aplicación**: Estándar para el cálculo de la intensidad de emisiones (g CO2e/tkm) y alineación con la norma **ISO 14083**.

### Herramienta VECTO (Comisión Europea)
*   **Referencia**: Reglamento (UE) 2017/2400 relativo a la determinación de las emisiones de CO2 y el consumo de combustible de los vehículos pesados.
*   **Aplicación**: Motor de simulación base para los KPIs de certificación de flota Euro VI.

---

## Optimización y Algoritmia

### [DOI: 10.1016/j.cor.2012.04.017]
*   **Referencia**: Demir, E., et al. (2014). *The fuel-only version of the pollution-routing problem*. Computers & Operations Research.
*   **Aplicación**: Fundamento para la integración de costes de combustible en el problema de ruteo (PRP).

### [DOI: 10.1016/j.cor.2011.08.010]
*   **Referencia**: Xiao, Y., et al. (2012). *Development of a fuel consumption optimization model for the capacitated vehicle routing problem*. Computers & Operations Research.
*   **Aplicación**: Ecuación de interpolación lineal de consumo según carga (Capa-VRP).
