# Implementación de Clientes Obligatorios (Plant-to-Client Mapping)

Este documento explica los cambios realizados en el `logistics_optimizer` para soportar la asignación obligatoria de clientes a plantas de cartón, garantizando que estos nunca sean filtrados ni recortados.

## 1. El Problema Detectado

Originalmente, el sistema intentaba manejar clientes obligatorios, pero sufría dos fallos críticos:
1. **Filtro de Radio:** Si un cliente obligatorio estaba fuera del `MAX_RADIUS_KM` (ej. Ciudad Real a >150km de Alcalá), el pre-filtro de Haversine lo descartaba antes de llegar al motor de optimización.
2. **Truncamiento por Límite:** La lógica final utilizaba un simple recorte de lista: `combined[:max_customers_per_plant]`. Si tenías 3 clientes obligatorios y el límite era 2, el sistema borraba al tercero sin avisar.

## 2. La Solución Técnica

Se ha rediseñado la fase de **Selección Inteligente** en `src/utils/data_manager.py` siguiendo tres pilares:

### A. Bypass de Filtros Geográficos
En la **Fase 2 (Validación de Matrix)**, ahora identificamos explícitamente si un candidato es obligatorio comparando con el diccionario proporcionado. Si lo es:
- Se le asigna `obligatorio = True`.
- Se registra su `detour` y `real_dist_km` solo a efectos informativos.
- Se añade a la lista de "cualificados" **saltando todas las comprobaciones** de `detour <= threshold_km` y `real_dist_km <= max_radius_km`.

### B. Lógica de Selección Prioritaria (Anti-Truncamiento)
Se cambió la forma en que se construye la lista final de clientes por planta.

**Código Anterior (Fallido):**
```python
combined = mandatories + optionals
eligible_customers = combined[:max_customers_per_plant] # <--- ¡Aquí se perdían datos!
```

**Código Nuevo (Corregido):**
```python
# Los obligatorios NO cuentan para el límite de "opcionales"
num_optionals_to_add = max(0, max_customers_per_plant - len(mandatories))
eligible_customers = mandatories + optionals[:num_optionals_to_add]
```
Ahora, si el límite es 2 y hay 3 obligatorios, el sistema incluirá los 3 obligatorios y 0 opcionales. El límite actúa como un "relleno" de clientes extra, no como una guillotina para los obligatorios.

## 3. Resumen de Archivos Modificados

| Archivo | Cambio Principal |
| :--- | :--- |
| `src/utils/data_manager.py` | Implementación de la lógica de prioridad absoluta y bypass de filtros. |
| `main.py` | (Verificado) Listo para procesar el dict `MANDATORY_CUSTOMERS`. |

### C. Restricción de Acoplamiento (Solver)
Para que los clientes obligatorios funcionen físicamente, se ha reforzado el motor en `src/engine/solver.py` con la **Regla de Oro**:
- `routing.solver().Add(routing.VehicleVar(c_node) == routing.VehicleVar(p_node))`
Esto garantiza que el cliente obligatorio sea visitado **exactamente por el mismo vehículo** que realizó la carga en su planta, respetando la cadena de custodia de la mercancía.

## 4. Cómo Usarlo en `main.py`

Ahora puedes pasar clientes obligatorios de forma flexible:

```python
# En main.py
MANDATORY_CUSTOMERS = {
    "Alcalá": ["Ciudad Real", "Puertollano"], # Lista de clientes
    "Valencia": "Gandia"                      # O un solo cliente (string)
}
```

## 5. Verificación de Éxito
Se han realizado pruebas con datos reales donde:
- Se forzó a **Ciudad Real** como obligatorio para **Alcalá**.
- Se bajó el límite a **1 cliente por planta**.
- **Resultado:** El sistema conservó a Ciudad Real satisfactoriamente a pesar de estar a más de 160km y superar el límite de 1.

---
*Documentación generada para Logistics Optimizer SOTA v2.0*
