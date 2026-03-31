# Bibliografía Técnica y Científica

Este documento recopila las fuentes, normativas y estudios científicos que respaldan los cálculos de optimización, emisiones y costes del proyecto Logistics Optimizer.

## Gestión de Emisiones y Huella de Carbono

### [DOI: 10.1016/j.trd.2019.08.002](https://doi.org/10.1016/j.trd.2019.08.002)
*   **Referencia**: Grigoratos, T., et al. (2019). *Real world emissions performance of heavy-duty Euro VI diesel vehicles*. Transportation Research Part D: Transport and Environment.
*   **Aplicación**: Proporciona los factores de emisión reales (kg CO2/km) para camiones de 40t (Subgrupo VECTO 5-LH) utilizados en el dashboard ejecutivo.
*   **Valores adoptados**: Vacío (0.652 kg/km), Cargado (1.085 kg/km).

### Marco GLEC (Global Logistics Emissions Council)
*   **Referencia**: SFC (2023). [GLEC Framework for Logistics Emissions Methodologies v3.0](https://www.smartfreightcentre.org/en/projects/glec-framework-v3/).
*   **Aplicación**: Estándar para el cálculo de la intensidad de emisiones (g CO2e/tkm) y alineación con la norma **ISO 14083**.

### Herramienta VECTO (Comisión Europea)
*   **Referencia**: [Reglamento (UE) 2017/2400](https://climate.ec.europa.eu/eu-action/transport/road-transport-reducing-co2-emissions-heavy-duty-vehicles_en) relativo a la determinación de las emisiones de CO2 y el consumo de combustible de los vehículos pesados.
*   **Aplicación**: Motor de simulación base para los KPIs de certificación de flota Euro VI.

---

## Optimización y Algoritmia

### [DOI: 10.1016/j.cor.2012.04.017](https://doi.org/10.1016/j.cor.2012.04.017)
*   **Referencia**: Demir, E., et al. (2014). *The fuel-only version of the pollution-routing problem*. Computers & Operations Research.
*   **Aplicación**: Fundamento para la integración de costes de combustible en el problema de ruteo (PRP).

### [DOI: 10.1016/j.cor.2011.08.010](https://doi.org/10.1016/j.cor.2011.08.010)
*   **Referencia**: Xiao, Y., et al. (2012). *Development of a fuel consumption optimization model for the capacitated vehicle routing problem*. Computers & Operations Research.
*   **Aplicación**: Ecuación de interpolación lineal de consumo según carga (Capa-VRP).

---

## Estructura de Costes de Explotación y TCO

### Herramienta ACOTRAM / ACOTRAN (MITMA)
*   **Referencia**: [Simulador de costes de transporte de mercancías por carretera](https://apps.fomento.gob.es/ACOTRAM/). Ministerio de Transportes y Movilidad Sostenible.
*   **Aplicación**: Metodología oficial para el cálculo del coste por kilómetro ($€/km$) desglosado en costes fijos (personal, amortización, seguros) y variables (combustible, mantenimiento).
*   **Fórmula Base**: $C_{total} = \frac{\sum FC_{anuales}}{KM_{anuales}} + VC_{km}$.

### Observatorio de Costes (MITMA)
*   **Referencia**: [Observatorio de Costes del Transporte de Mercancías por Carretera](https://www.transportes.gob.es/transporte-terrestre/servicios-al-transportista/observatorios-del-transporte/observatorio-de-costes-del-transporte-de-mercancias-por-carretera).
*   **Aplicación**: Proporciona los porcentajes de distribución de costes estándar para el mercado español (ej. Camión de 40t: Combustible ~33%, Personal ~40%).
*   **Actualización 2026**: Inclusión de la categoría de **Articulado de 44 toneladas de carga general**.
*   **Impacto Normativo**: Basado en la [Orden TMA/215/2024](https://www.boe.es/eli/es/o/2024/03/15/tma215) y reportes de **FENADISMER** sobre el incremento de costes de mantenimiento y neumáticos (+12%) derivado de la masa máxima autorizada de 44t.
*   **Valores 2026**: Coste anual de explotación para vehículo de 44t fijado en **168.543,75 €** (Referencia Q1 2026).

---

## Dimensionamiento de Flota (Fleet Sizing)

### The Fleet Sizing and Mix Problem (FSMP)
*   **Referencia**: Golden, B. L., et al. (1984). [The fleet size and mix vehicle routing problem](https://doi.org/10.1016/0305-0548(84)90007-8). Computers & Operations Research.
*   **Aplicación**: Teoría matemática para determinar el número óptimo de vehículos necesarios para cubrir una demanda conocida considerando tiempos de ciclo.
*   **Fórmula Aplicada**: $N = \sum \frac{Demanda_i \times T_{ciclo, i}}{H_{disponibles} \times Disponibilidad}$.
*   **Cálculo de Ciclo**: $T_{ciclo} = 2 \times \frac{Distancia}{Vel\_Media} + T_{operativo}$.
