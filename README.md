# 🚚 SOTA Logistics Optimizer: Multi-Vehicle VRP with Backhauling

[![License](https://img.shields.io/badge/Status-Optimized-blue?style=for-the-badge)](https://github.com/Ulysess824/logistic_optimizer)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)

Este proyecto representa una solución avanzada para la optimización logística de la cadena de suministro de papel y cartón. El modelo integra un flujo circular complejo: desde la planta de papel de **Mengíbar**, pasando por plantas de cartón estratégicas, hasta la entrega a clientes finales optimizada por proximidad en la ruta de retorno.

---

## 🧠 Concepto del Modelo

El modelo adopta un enfoque de **Optimización de Retorno (Backhauling Optimization)**. 

### El Ciclo Operativo:
1. **Salida (Depósito):** Camión sale de la fábrica de papel (Mengíbar) cargado de bobinas de papel.
2. **Entregas/Recogidas (Plantas):** Entrega el papel en una planta de cartón y recoge el producto terminado (cajas de cartón).
3. **Distribución (Clientes):** Entrega el cartón a clientes seleccionados inteligentemente.
4. **Retorno:** El camión vuelve a Mengíbar vacío para reiniciar el ciclo, minimizando los kilómetros "muertos".

---

## ➗ Fundamentos Matemáticos

El optimizador utiliza el motor de **Google OR-Tools** resolviendo una variante compleja del VRP:

### 1. Función Objetivo
Minimizar el coste total (distancia) sujeto a:
$$\min \sum_{i,j \in V} d_{ij} x_{ij}$$

### 2. Restricciones de Precedencia
Para cada ruta $r$, se asegura que la visita a la Planta de Cartón $P$ preceda a cualquier Cliente $C$ asignado:
$$T_{visit}(P) < T_{visit}(C)$$

### 3. Filtro de Proximidad de Retorno
Seleccionamos clientes $C$ tales que el desvío respecto a la ruta directa de vuelta ($P \to M$) sea inferior a un umbral $\tau$:
$$(dist(P, C) + dist(C, M)) - dist(P, M) < \tau$$

---

## 🛠️ Arquitectura del Código

El sistema está modularizado siguiendo estándares de ingeniería de software profesionales:

- **`DataManager`**: Implementa el filtro de retorno utilizando **Polars** y **NumPy** para procesamiento vectorizado de alta velocidad.
- **`LogisticsSolver`**: El motor de decisión. Utiliza metaheurísticas de búsqueda local (Guided Local Search) para escapar de óptimos locales.
- **`Visualizer`**: Genera un Dashboard interactivo en HTML utilizando **Folium**, con tablas laterales de KPI y diferenciación de rutas por colores.

---

## 🚀 Instalación y Uso

1. **Requisitos:**
   ```bash
   pip install ortools folium polars numpy googlemaps python-dotenv
   ```

2. **Ejecución:**
   ```bash
   python main.py
   ```

3. **Resultado:** 
   Se generará un archivo `Logistics_Dashboard.html` en la carpeta `outputs/maps/`.

---

## 📊 Dashboard de Visualización

El dashboard generado no es solo un mapa; es una interfaz de toma de decisiones que incluye:
- **Resumen Estadístico:** Kilómetros totales y número de rutas.
- **Tabla Lateral:** Detalles por ruta con nombres de plantas y distancias.
- **Iconografía Unificada:** Iconos diferenciados para Fábrica, Plantas de Cartón y Clientes.

---

*Desarrollado con estándares de excelencia operativa para Smurfit Westrock.*
