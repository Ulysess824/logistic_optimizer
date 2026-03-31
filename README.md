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
> **Consistencia de Distancias**: Siempre que calcules un escenario "Base" frente a uno "Optimizado", asegúrate de usar distancias reales de ida y vuelta por separado (OSRM) para evitar errores por asimetría vial.

---

## 🚀 Lo que Llevamos Desarrollado

Actualmente, el proyecto cuenta con un sistema maduro, empaquetado y altamente visual que automatiza los procesos complejos de la cadena de suministro:

1. **Motor de VRP de Alta Resiliencia**: Usamos Google OR-Tools con una arquitectura de **Restricciones Blandas (Disjunctions)**.
2. **Sistema de GPS Real (OSRM Automático)**: Integración precisa para recuperar distancias terrestres. El sistema calcula rutas de ida y vuelta de forma independiente para evitar asimetrías viales.
3. **Métricas de Retorno de Inversión (Software ROI)**: Evaluación financiera que calcula el **ROI Anualizado** y el **Payback Period** de la inversión en software.
4. **Reducción Sistémica de CO2 (Absoluta)**: Cuantificación de la huella de carbono evitada al desplazar el transporte externo por el interno en el tramo *Linehaul* (Planta -> Clientes).
5. **Dashboard Interactivo Profesional**: Visualización modularizada (`Presentacion_Logistica.html`) con KPIs financieros, ambientales y operativos.
6. **Optimización Multi-Planta (Backhauling Avanzado)**: Soporte para múltiples recogidas en una misma ruta (`MC-VRPB`).
7. **Simulación Dinámica de Flotas (SOTA)**: Modelado con **SimPy**.
8. **Optimización Volumétrica 3D**: Validador de capacidad física real (13.6m / 34 pallets EPAL) con lógica de apilamiento dinámico.

---

## 🔄 ¿Cómo usar este modelo en OTROS CONTEXTOS?

Aunque originalmente se diseñó para la industria del cartón, esta herramienta es **totalmente adaptable a cualquier logística de distribución con backhauling**.

### 1. Prepara tus datos (.json)
El modelo espera archivos en la carpeta `data/`:
* **Plantas/Nodos Estratégicos:** Origen (`depot`) y paradas de carga (`carton_plants`).
* **Clientes Finales:** Base de datos de destinos con coordenadas.

### 2. Configura las Reglas en `main.py`
Ajusta las constantes en la parte superior:
- `N_CLIENTES`: Límite máximo de clientes por ruta.
- `MAX_PALLETS`: Límite de capacidad física total por camión.
- `THRESHOLD_KM`: Desvío máximo permitido para aceptar un cliente en la ruta de retorno.

### 3. Ejecución y Dualidad de Escenarios
* **Escenario de Producción (Optimizado)**: `python main.py`
  - Actualiza las pestañas de **"Resumen Ejecutivo"**, **"Detalle Operativo"** y **"Mapa"**.

### 4. Dashboard Modularizado
El punto de entrada principal es `outputs/Presentacion_Logistica.html`. 
Esta interfaz unificada consume piezas HTML independientes generadas por los scripts anteriores.

---

## 🍃 Sostenibilidad e Impacto Ambiental (GLEC v3.0)
El motor utiliza el modelo **FCR (Fuel Consumption Rate)** aliado con el marco **GLEC v3.0**:
- **Factores VECTO**: Calibrado para vehículos de 40t (Subgrupo 5-LH).
- **Consumo Realista**: Distingue entre tramos en vacío (0.652 kg/km) y cargado (1.085 kg/km).

## 🧠 Modelo de Selección Geográfica (Dual-Pass)

El sistema utiliza un filtrado de doble capa (Radio Haversine + Validación GPS) para elegir a los mejores clientes candidatos por cada planta antes de entrar al motor VRP.

---

## 📊 Guía de Estructura de Datos (Estándar GSIM)

Este proyecto alinea su estructura de datos con el **Modelo Genérico de Información Estadística (GSIM)** para asegurar trazabilidad e interoperabilidad en entornos corporativos.
