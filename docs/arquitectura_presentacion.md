# 🗺️ Mapa de Arquitectura del Optimizador GABM-Project

Este documento explica cómo se interrelacionan los archivos del proyecto, desde el motor de cálculo hasta el Dashboard de presentación final.

```mermaid
graph TD
    subgraph "Capas de Entrada y Configuración"
        A[config.py] -->|Constantes Ley Little, TCO, GLEC| B
        C[data/locations_smurfit.json] -->|Ubicaciones Planta y Depósito| B
        D[data/demanda_simulada.json] -->|Demanda de Clientes| B
    end

    subgraph "Núcleo de Optimización (Back-End)"
        B[main.py] -->|Ejecuta flujo principal| E[solver.py]
        B -->|Manejo de Datos| F[data_manager.py]
        E -->|Cálculo Rutas| G[GeoUtils / OSRM]
    end

    subgraph "Módulos de Inteligencia Analítica"
        H[cost_estimator.py] -->|OPEX - TCO| B
        I[fcr_estimator.py] -->|CO2 - GLEC v3| B
        J[fleet_estimator.py] -->|CAPEX - Ley de Little| B
        K[financial_analyzer.py] -->|Business Case - ROI/Payback| L[report_generator.py]
    end

    subgraph "Visualización y Presentación (Front-End)"
        B -->|Genera Datos de Resultados| L
        L -->|Actualiza Componentes| M[HTML_Bodies / tab_finanzas, tab_resumen...]
        M -->|Inyecta en Iframe| N[outputs/Presentacion_Logistica.html]
        B -->|Genera Mapa de Rutas| O[outputs/maps/Logistics_Dashboard.html]
    end

    style N fill:#1e3a8a,color:#fff,stroke:#333,stroke-width:4px
    style J fill:#f97316,color:#fff
    style K fill:#22c55e,color:#fff
```

---

## 📂 ¿Qué hace cada archivo clave?

| Archivo | Responsabilidad Principal | Impacto en la Presentación |
| :--- | :--- | :--- |
| **`config.py`** | El "Cerebro" de las constantes. Contiene los precios del diésel, costes de camiones, y los 1.2 días de ciclo. | Cambia los números de todas las pestañas. |
| **`main.py`** | La Orquesta. Coordina todas las llamadas, desde leer los datos hasta escribir los resultados finales. | Gestiona la ejecución de todo el proceso. |
| **`fleet_estimator.py`** | El Especialista en Inversión. Traduce la demanda operativa (λ) en número de camiones físicos usando la Ley de Little. | Define los **7.4M €** de inversión que ves. |
| **`financial_analyzer.py`** | El Financiero. Toma la inversión y los ahorros operativos para escupir el ROI y el tiempo de recuperación (Payback). | Alimenta la pestaña de **"Business Case"**. |
| **`report_generator.py`** | El "Maquetador". Es el encargado de coger los JSON de resultados y "dibujarlos" en los archivos HTML individuales. | Sin esto, la presentación no se actualizaría. |
| **`HTML_Bodies/`** | Son los fragmentos HTML de cada pestaña (Finanzas, Resultados, Mapa...). | Son las piezas de código que se cargan dentro del panel principal. |
| **`Presentacion_Logistica.html`** | El Marco Global. Es el archivo que abres en el navegador para ver todo el proyecto unificado. | Es tu cara al cliente/junta directiva. |

> [!NOTE]
> **Flujo de una actualización**: Cambias algo en `config.py` → Corres `main.py` → `report_generator.py` detecta el cambio → Actualiza `tab_finanzas.html` → Refrescas `Presentacion_Logistica.html` y ves el nuevo ROI.
