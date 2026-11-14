# CLAUDE.md · Caso práctico AI Specialist · EME STUDIOS

Guía de trabajo para este repositorio. Todo el código, los nombres de columnas y la
documentación siguen las convenciones descritas aquí.

---

## Contexto

- Marca de moda. Datos **ficticios** de actividad del **2024-01-01 al 2025-11-09**.
- Fuente única: `data/raw/EME_Caso_Practico_Datos.xlsx`, con una pestaña `LEEME`
  (documentación del propio caso) y cuatro pestañas de datos:

  | Pestaña    | Contenido                                                                      |
  |------------|--------------------------------------------------------------------------------|
  | `VENTAS`   | Líneas de pedido: fecha, pedido, SKU, mercado, unidades, precio, descuento, etiquetas |
  | `PRODUCTO` | Catálogo: SKU, producto, color, talla, sección, categoría, **subcategoría**, drop, coste, PVP |
  | `STOCK`    | Stock disponible por SKU en almacén a fecha de cierre                            |
  | `COMPRAS`  | Pedidos a proveedor: SKU, unidades, proveedor, fecha estimada y fecha real de llegada |

- **Los datos contienen errores a propósito** (duplicados, nulos, tipos mezclados,
  valores imposibles, SKUs huérfanos…). Cualquier problema detectado y su tratamiento
  se documenta en [`docs/notas_calidad_datos.md`](docs/notas_calidad_datos.md).
- El enunciado original está en [`docs/enunciado/`](docs/enunciado/).

### Los tres retos

| Reto | Peso | Entregable |
|------|------|------------|
| 1 · Informe semanal de ventas y stock | 40 % | Informe HTML autocontenido en `output/reto1/` |
| 2 · Automatizar la propuesta de reposición | 30 % | Propuesta revisable (Excel/online) en `output/reto2/` + esquema de producción |
| 3 · Hoja de ruta de IA a 6 meses | 30 % | `docs/reto3_roadmap_ia.md` + material en `output/reto3/` |

---

## Reglas de negocio (OBLIGATORIAS)

> Se aplican **exclusivamente en `src/clean.py`** y nunca en otro módulo.
> El resto del código consume las tablas ya limpias de `data/interim/` y asume que
> estas reglas ya están aplicadas. Si un módulo necesita reaplicarlas, es señal de
> que la limpieza está incompleta: se corrige en `clean.py`.

1. **`influencers` = regalos.** Los pedidos con la etiqueta `influencers` son regalos,
   no ventas. Se **excluyen de TODO análisis de venta** (unidades, facturación, margen,
   sell-through, demanda prevista…). Se conservan marcados en una tabla aparte por si
   hacen falta para consumo de stock.
2. **`special` = precio especial.** Los pedidos con la etiqueta `special` se vendieron
   a precio rebajado. La etiqueta aparece en **variantes** (`special`, `SPECIAL XX`…),
   así que se normaliza antes de comparar. Se marcan con el flag booleano
   **`is_special`** y se analizan
   **aparte** del precio completo (nunca se mezclan en los KPIs de precio/margen sin
   decir explícitamente que están incluidos).
3. **Llegada de compras.** Se usa la **fecha real si existe** y, si no, la **estimada**
   (fecha real vacía = pendiente de llegar o sin confirmar).
   El resultado se materializa en la columna **`fecha_llegada_efectiva`**, junto con
   `origen_fecha_llegada` (`real` | `estimada`) para poder medir la fiabilidad del proveedor.
4. **Modelo = producto + color.** Cada talla es un SKU distinto. Se crea la clave
   **`modelo_id`** en `PRODUCTO` y se propaga a ventas, stock y compras.

---

## Parámetros del caso

Viven en [`src/config.py`](src/config.py); aquí quedan documentados para referencia.

| Parámetro | Valor |
|-----------|-------|
| Semana de análisis (W0) | **2025-11-03 → 2025-11-09** (lunes a domingo, ISO 2025-W45) |
| Semana anterior (W-1) | **2025-10-27 → 2025-11-02** (ISO 2025-W44) |
| Misma semana del año anterior (LY) | **2024-11-04 → 2024-11-10** (misma semana ISO: 2024-W45) |
| Lead time de proveedor | **6 semanas** |
| Cobertura objetivo | **8 semanas** |
| Fecha de cierre del stock | **2025-11-09** |

Las semanas son **ISO (lunes a domingo)**. La comparación interanual se hace por
**número de semana ISO**, no por fecha calendario, para que ambas semanas tengan los
mismos días de la semana.

---

## Definiciones de KPIs

> **SUPUESTOS PENDIENTES DE VALIDAR tras el perfilado** (`src/profiling.py`).
> Si los datos contradicen alguno de estos supuestos, **avisar antes de cambiarlo**
> y registrar la decisión en `docs/decisiones.md`.

- **Facturación neta** = `unidades × pvp_unitario − descuento`.
  **Confirmado por la pestaña `LEEME`**: el importe bruto es `unidades × PVP` y el
  descuento viene **en euros** (importe por línea, no porcentaje ni por unidad).
  Sigue **pendiente** saber si los precios llevan **IVA**; se asume que **no** hasta
  que se diga lo contrario.
  Ojo: `VENTAS` trae su propio `PVP unitario (€)` y `PRODUCTO` trae otro `PVP (€)`.
  Manda el de la línea de venta (precio al que se vendió de verdad); la discrepancia
  entre ambos se mide y se reporta en las notas de calidad.
- **Margen** = `facturación neta − unidades × coste`.
  **Margen %** = `margen / facturación neta`.
- **Sell-through** = `unidades vendidas / (unidades vendidas + stock actual)`,
  sobre el periodo que se defina y se documente explícitamente en el informe.
- **Rotura en 4 semanas**: `stock actual + compras con fecha_llegada_efectiva ≤ 4 semanas
  < demanda prevista de 4 semanas`.
- **Exceso de stock**: semanas de cobertura por encima de un umbral **a definir y
  documentar** (candidato inicial: cobertura > 2 × cobertura objetivo).

---

## Convenciones de trabajo

- **Stack**: Python + pandas. Informe del Reto 1 en **HTML autocontenido con Plotly**
  (un solo fichero, sin dependencias externas al abrirlo).
- **`data/raw` nunca se modifica.** Es de solo lectura.
- Flujo de datos: `data/raw` → `clean.py` → `data/interim/*.parquet` →
  `metrics.py` / `forecast.py` / `replenishment.py` → `data/processed/*.parquet` →
  `report.py` / exports de `output/`.
- Toda decisión o supuesto nuevo se registra **con fecha** en
  [`docs/decisiones.md`](docs/decisiones.md).
- **Antes de implementar lógica nueva, proponer el enfoque y esperar confirmación.**
- Código y **nombres de columnas en `snake_case`**. Comentarios y documentación **en español**.
- Las salidas (`output/`, `data/interim`, `data/processed`) son **reproducibles**: se
  regeneran ejecutando los pipelines, no se editan a mano.

## Trazabilidad en los entregables (OBLIGATORIO)

**Cada entregable incluye una sección final de "Decisiones y supuestos"** con las
decisiones tomadas en ese reto: qué se decidió, por qué, y qué impacto tiene en las
cifras que el lector acaba de ver. El objetivo es que nadie tenga que fiarse de un
número sin saber cómo se ha construido.

- El informe HTML del Reto 1 lleva una sección **"Decisiones y supuestos"** y otra de
  **"Calidad de los datos"** (resumen de lo que se arregló y lo que no).
- La propuesta de reposición del Reto 2 lleva una **hoja/pestaña de decisiones** con
  los parámetros usados y la lógica del cálculo.
- La hoja de ruta del Reto 3 cierra con los **supuestos** sobre los que se ha priorizado.

La fuente de verdad es `docs/decisiones.md`: las secciones de los entregables se
construyen **a partir de ese fichero**, filtrando por reto, no escribiéndolas a mano.
Por eso cada entrada de `decisiones.md` debe indicar a qué reto afecta.

## Cómo ejecutar

```bash
source .venv/bin/activate
python pipelines/run_reto1.py   # limpieza → métricas → informe HTML
python pipelines/run_reto2.py   # limpieza → forecast → reposición → export
```
