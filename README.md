# 🚚 Logistics Optimizer ⚙️

Bienvenido a **Logistics Optimizer**. un sistema en Python diseñado para optimizar el enrutamiento de transporte y la logística de distribución.

---

## 🤖 Guía para Desarrolladores IA (Assistant Instructions)

Si eres una IA trabajando en este repositorio, **DEBES leer los siguientes archivos esenciales** para entender la lógica de negocio antes de realizar cambios estructurales:

1. `logistic_core/config.py`: **El cerebro de los parámetros.** Contiene las tarifas, costos y factores de CO2.
2. `logistic_core/utils/report_generator.py`: **La lógica del Dashboard.** Aquí reside el cálculo del ROI, el Ahorro Sistémico y la inyección de KPIs en el HTML.
3. `logistic_core/utils/geo.py`: **El motor geográfico.** Controla cómo se piden las distancias a OSRM y cómo se gestiona la caché.
4. `logistic_core/engine/solver.py`: **El corazón de la optimización.** Implementación de OR-Tools.

> [!IMPORTANT]
> **Estructura Organizada**: A partir del 10/04/2026, el proyecto sigue una jerarquía estricta: `logistic_core` (lógica), `scripts` (utilidades), `docs` (especificaciones) y `outputs` (resultados). Evita colocar archivos sueltos en la raíz.

---

## 🚀 Lo que Llevamos Desarrollado

Actualmente, el proyecto cuenta con un sistema maduro, empaquetado y altamente visual que automatiza los procesos complejos de la cadena de suministro:

1. **Motor de VRP de Alta Resiliencia**: Usamos Google OR-Tools con una arquitectura de **Restricciones Blandas (Disjunctions)**.
2. **Sistema de GPS Real (OSRM Automático)**: Integración precisa para recuperar distancias terrestres. El sistema calcula rutas de ida y vuelta de forma independiente.
3. **Métricas de Retorno de Inversión (Software ROI)**: Evaluación financiera que calcula el **ROI Anualizado** y el **Payback Period** de la inversión en software.
4. **Reducción Sistémica de CO2 (Absoluta)**: Cuantificación de la huella de carbono evitada en el tramo *Linehaul*.
5. **Simulación Anual (250 Días Laborales)**: Capacidad de proyectar el ahorro y la eficiencia operativa a lo largo de un año completo (Novedad).
6. **Dashboard Interactivo con Slicer Temporal**: Un nuevo visor (`Presentacion_Anual.html`) que permite filtrar resultados por fecha específica y ver métricas acumuladas anuales (ROI, Ahorro TCO, Toneladas CO2).
7. **Optimización Volumétrica 3D**: Validador de capacidad física real (34 pallets EPAL).
8. **KPI "Clientes Totales"**: Nueva métrica que contabiliza el éxito real del ruteo consolidado frente al pool de candidatos.

---

## 📂 Estructura del Proyecto

```text
/logistics_optimizer
├── data/               # Bases de datos de clientes, plantas y demanda (.json, .xlsx)
├── docs/               # Especificaciones técnicas, contexto y guías del proyecto
├── logistic_core/      # El motor central (Engine, Utils, Config, Simulation)
├── scripts/            # Utilidades de mantenimiento, tests y ejecutores de simulación
├── outputs/            # Resultados finales (HTML, Maps, Results JSON, Logs)
├── main.py             # Entrada principal para optimización diaria
└── README.md           # Esta guía de uso
```

---

## 🔄 Simulación Anual de 250 Días

Para evaluar el impacto estratégico a largo plazo, el sistema permite correr una simulación batch:

1. **Generar Escenario**: `python scripts/generate_yearly_data.py` (Crea 250 días de demanda sintética con volatilidad).
2. **Ejecutar Ciclo**: `python scripts/run_yearly_simulation.py` (Corre el optimizador para cada día y consolida estadísticas).
3. **Visualizar**: `python logistic_core/utils/yearly_report_generator.py` (Genera el dashboard interactivo con slicer).

---

## 🍃 Sostenibilidad e Impacto Ambiental (GLEC v3.0)

El motor utiliza el modelo **FCR (Fuel Consumption Rate)** aliado con el marco **GLEC v3.0**:
- **Factores VECTO**: Calibrado para vehículos de 40t (Subgrupo 5-LH).
- **Consumo Realista**: Distingue entre tramos en vacío (0.652 kg/km) y cargado (1.085 kg/km).

---

## 🧠 Modelo de Selección Geográfica (Dual-Pass)

El sistema utiliza un filtrado de doble capa (Radio Haversine + Validación GPS) para elegir a los mejores clientes candidatos por cada planta antes de entrar al motor VRP.

---

## 📊 Guía de Estructura de Datos (Estándar GSIM)

Este proyecto alinea su estructura de datos con el **Modelo Genérico de Información Estadística (GSIM)** para asegurar trazabilidad e interoperabilidad en entornos corporativos.
