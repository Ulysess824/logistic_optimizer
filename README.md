# 🚚 SOTA Logistics Optimizer: Multi-Vehicle VRP with Backhauling

[![SOTA](https://img.shields.io/badge/Algorithm-SOTA-blue.svg)](https://developers.google.com/optimization)
[![Python](https://img.shields.io/badge/Python-3.12-green.svg)](https://www.python.org/)
[![Google OR-Tools](https://img.shields.io/badge/Engine-Google%20OR--Tools-orange.svg)](https://developers.google.com/optimization/routing)

Sistema profesional de optimización logística de vanguardia (State-of-the-Art) diseñado para resolver problemas complejos de **ruteo de vehículos (VRP) con retroceso (Backhauling)**. El sistema coordina una flota para suministrar papel a plantas industriales y gestionar la distribución de productos terminados (cartón) a clientes finales en una única ruta optimizada.

## 🧠 Arquitectura del Sistema
El sistema ha sido reestructurado siguiendo patrones de diseño SOTA para escalabilidad y mantenimiento:

```text
logistic_optimizer/
├── src/                # Código fuente del núcleo
│   ├── engine/         # Motor de optimización (Google OR-Tools)
│   ├── utils/          # Utilidades de Geometría y Visualización
│   └── config.py       # Configuración centralizada
├── data/               # Base de datos de localizaciones (JSON)
├── outputs/            # Resultados de ejecución
│   ├── maps/           # Mapas interactivos (Folium)
│   └── results/        # Rutas calculadas (JSON)
├── logs/               # Registros de ejecución
└── main.py             # Punto de entrada principal
```

## 🔬 Algoritmo de Optimización
El núcleo utiliza una combinación de **Constraint Programming (CP)** y **Metaheurísticas** sobre el motor **Google OR-Tools**:

1.  **Guided Local Search (GLS):** Nuestra metaheurística principal que permite al algoritmo escapar de óptimos locales mediante penalizaciones dinámicas.
2.  **Backhauling Logic:** Restricciones estrictas de precedencia que aseguran que el suministro de la planta (Pickup) siempre ocurra antes de la entrega al cliente (Delivery).
3.  **Cluster-based Assignment:** Cada vehículo se asigna estratégicamente a una planta industrial para maximizar la cobertura regional.

## 🚀 Instalación y Uso

### 1. Clonar y Preparar
```bash
# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar API (Google Maps)
Crea un archivo `.env` en la raíz del proyecto:
```env
GOOGLE_MAPS_API_KEY=tu_api_key_aqui
```
*Nota: El sistema funcionará con distancias Haversine (línea recta) si la API no está configurada.*

### 3. Ejecutar Optimización
```bash
python main.py
```

## 📊 Visualización de Resultados
Tras la ejecución, el sistema genera automáticamente:
*   **Mapa SOTA:** En `outputs/maps/optimized_multiple_routes.html` con rutas diferenciadas por colores e íconos inteligentes.
*   **JSON de Rutas:** En `outputs/results/routes.json` para integración con otros sistemas.

## 🛠️ Tecnologías Principales
*   **Google OR-Tools**: El estándar de oro en optimización combinatoria.
*   **Google Maps Platform**: Para distancias reales por carretera e infraestructura vial.
*   **Folium**: Generación de capas geoespaciales dinámicas.
*   **Numpy**: Procesamiento de matrices de alta velocidad.

---
*Optimizado para operaciones logísticas de alta complejidad.*
