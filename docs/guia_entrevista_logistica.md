# Guía de Alineación con el Responsable de Expediciones

Este documento sirve como guía para la entrevista con el responsable de expediciones de la planta. El objetivo es asegurar que los datos del "mundo real" se estructuren correctamente para alimentar el optimizador de rutas (VRPTW).

## 1. Objetivo de la reunión
Establecer un flujo para la **planificación diaria dinámica**. Dado que los clientes y pedidos cambian constantemente, el objetivo es que el modelo procese el "listado de pedidos del día" y genere las rutas óptimas de forma automatizada, eliminando la dependencia de rutas fijas o memoria histórica.

## 2. Estándares del Mundo Real (Logística 4.0)
Para que el responsable de expediciones entienda el nivel del proyecto, menciónale estas **mejores prácticas** que el modelo puede soportar:

*   **Ciclo de Planificación (Cut-Off)**: Determinar la hora exacta en que se "cierran" los pedidos para que el algoritmo tenga 5-10 minutos de cálculo antes de cargar los camiones.
*   **Integración OMS/ERP**: El modelo está preparado para conectarse vía API o importar archivos CSV/Excel exportados directamente del sistema de ventas, sin intervención manual.
*   **Ajuste de Tiempos de Servicio (Datos Históricos)**: El optimizador no solo usa tráfico de Google, sino que permite meter el "tiempo real de muelle" de cada cliente (ej. si un cliente grande siempre tarda 40 min en descargar, se parametriza así).
*   **Re-optimización Interdiaria**: Posibilidad de re-calcular la ruta a mitad de jornada si entra un pedido de emergencia o hay una avería, re-enviando la nueva secuencia al conductor.

## 3. Definición de la "Foto Diaria" de Pedidos
El modelo no trabaja con clientes fijos, sino con un **volcado dinámico**. Debes preguntar: **"¿A qué hora sois capaces de exportar la lista de pedidos confirmados para mañana?"**

Para cada lista diaria, necesitamos:

| Campo | Importancia en Modelo Dinámico |
| :--- | :--- |
| **Punto de Entrega** | Clave para que la API de Google geolocalice el punto exacto hoy. |
| **Peso/Volumen del Pedido** | Varía cada día; determina cuántos camiones necesitaremos hoy. |
| **Ventanas Horarias** | Pueden cambiar según el día de la semana o el tipo de pedido. |
| **Service Time** | Tiempo que el camión estará ocupado en ese punto antes de ir al siguiente. |

## 4. Preguntas Clave para el Entorno Dinámico
Para que el algoritmo se adapte a la variabilidad diaria:

1.  **Cierre de Pedidos**: "¿Cuál es el 'cut-off' (hora límite) tras el cual ya no entran más pedidos para el reparto del día siguiente?".
2.  **Nuevos Clientes**: "Si entra un pedido de un cliente nuevo hoy, ¿el sistema tiene su dirección grabada para que el optimizador lo encuentre?".
3.  **Gestión de Errores**: "¿Cómo gestionáis hoy los pedidos que no caben en el camión por peso o volumen?".

## 5. Conexión Dinámica con el Modelo
Explica al responsable que el sistema es un **motor de decisión rápida**:

*   **Paso A**: Se carga el Excel de pedidos recién salido del horno (con clientes distintos cada día).
*   **Paso B**: El optimizador cruza esos puntos con el tráfico de Google previsto para mañana.
*   **Paso C**: En menos de 2 minutos, tiene las rutas que mejor encajan para *esa combinación específica* de pedidos.
