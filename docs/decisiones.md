# Log de decisiones y supuestos

> Toda decisión o supuesto que no sea evidente a partir de los datos se registra
> aquí, con fecha. Formato: una entrada por decisión.

## Formato

```
### [AAAA-MM-DD] Título corto de la decisión
- **Contexto:** qué problema o ambigüedad lo motiva.
- **Opciones consideradas:** alternativas descartadas y por qué.
- **Decisión:** qué se hace.
- **Reto:** 1 | 2 | 3 | transversal  (se usa para filtrar al construir los entregables).
- **Impacto:** a qué KPIs o entregables afecta.
- **Estado:** supuesto pendiente de validar | validado con los datos | confirmado con negocio.
```

---

## Decisiones

### [2026-11-14] Estructura inicial del repositorio y supuestos de partida
- **Contexto:** arranque del caso, antes de mirar los datos.
- **Decisión:** se fija la estructura del repositorio, los parámetros del caso
  (semanas de análisis, lead time 6 semanas, cobertura objetivo 8 semanas) y las
  definiciones preliminares de KPIs recogidas en `CLAUDE.md`.
- **Reto:** transversal.
- **Impacto:** transversal a los tres retos.
- **Estado:** supuestos pendientes de validar tras el perfilado.

<!-- Nuevas entradas al final -->

### [2026-11-14] `src/io.py` pasa a llamarse `src/storage.py`
- **Contexto:** `io` colisiona con el módulo `io` de la librería estándar de Python.
  Aunque dentro del paquete `src` los imports son absolutos y no rompe nada, ejecutar
  código desde dentro de `src/` podría sombrear la stdlib.
- **Decisión:** renombrar el módulo a `storage.py`. Responsabilidad sin cambios:
  leer el Excel de `data/raw` y persistir/recuperar tablas en parquet.
- **Reto:** transversal.
- **Impacto:** imports del proyecto y árbol de carpetas en README.
- **Estado:** confirmado.

### [2026-11-14] Supuestos resueltos por la pestaña `LEEME` del Excel
- **Contexto:** el Excel trae una quinta pestaña, `LEEME`, con documentación del caso
  que no estaba descrita en el enunciado PDF.
- **Decisión:** se dan por confirmados dos supuestos que estaban pendientes:
  (a) el **descuento viene en euros**, como importe por línea, y el importe bruto es
  `unidades × PVP`; (b) la etiqueta de precio especial aparece en **variantes**
  (`special`, `SPECIAL XX`), por lo que hay que normalizarla antes de filtrar.
  Sigue pendiente si los precios llevan IVA: se asume que **no**.
- **Reto:** 1 y 2.
- **Impacto:** definición de facturación neta y margen (Reto 1), y filtrado de
  etiquetas en `clean.py`.
- **Estado:** validado con los datos (origen: pestaña `LEEME`).

### [2026-11-14] El PVP de la línea de venta manda sobre el del catálogo
- **Contexto:** `VENTAS` tiene `PVP unitario (€)` y `PRODUCTO` tiene `PVP (€)`.
  Pueden no coincidir.
- **Decisión:** para facturación y margen se usa el **PVP de la línea de venta**, que
  es el precio al que se vendió de verdad. El PVP de catálogo se usa solo como
  referencia para medir el descuento efectivo sobre tarifa.
- **Reto:** 1.
- **Impacto:** facturación neta, margen, análisis de precio especial.
- **Estado:** supuesto pendiente de validar con el volumen real de discrepancias.

### [2026-11-14] CORRECCIÓN: el PVP de venta y el de catálogo coinciden siempre
- **Contexto:** se registró una decisión sobre cuál de los dos PVP usar. El
  perfilado la deja sin objeto: coinciden en las **18.292 líneas** (0 discrepancias).
- **Reto:** 1 y 2.
- **Decisión:** se usa el de la línea de venta, pero deja de ser un supuesto con
  riesgo. No hay que medir ninguna discrepancia.
- **Estado:** validado con los datos.

### [2026-11-14] `WELCOME10` es venta a precio completo, no precio especial
- **Contexto:** aparece una etiqueta que el enunciado no menciona, en 999 líneas
  (5,5 %). Descuenta exactamente el 10 %, frente al ~40 % de `special` y el 100 %
  de `influencers`.
- **Opciones consideradas:** tratarla como `special`. Descartada: mezclaría un
  cupón del 10 % con liquidaciones del 40 % y distorsionaría el margen del canal
  de precio completo.
- **Decisión:** es una venta a tarifa con un cupón promocional encima. Entra en
  precio completo, con flag propio `es_promocion` para poder medirla aparte.
- **Reto:** 1.
- **Impacto:** reparto precio completo vs. especial; margen por canal.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Las variantes `SPECIAL XX` se unifican en `is_special`
- **Contexto:** `special` (851), `SPECIAL ES` (717), `SPECIAL US` (61),
  `SPECIAL NL` (55). Todas descuentan ~40 %, luego son lo mismo.
- **Decisión:** cualquier etiqueta que empiece por `SPECIAL` marca `is_special`.
  El sufijo se guarda en `mercado_etiqueta` como dato de control, para contrastarlo
  con el mercado de la línea, no para analizar con él.
- **Reto:** 1 y 2.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Las unidades negativas son devoluciones y se conservan
- **Contexto:** 10 líneas con `unidades = -1` (0,05 % del total).
- **Opciones consideradas:** excluirlas. Descartada: inventaría 10 ventas que se
  devolvieron. Es lo que haría un ERP: restan de la venta neta.
- **Decisión:** se mantienen, marcadas con `es_devolucion`.
- **Reto:** 1 y 2.
- **Impacto:** despreciable en las cifras; relevante para la honestidad del dato.
- **Estado:** confirmado con el usuario.

### [2026-11-14] En una devolución, el descuento se revierte con las unidades
- **Contexto:** consecuencia mecánica de la decisión anterior. Las 10 devoluciones
  traen las unidades en negativo pero el descuento en positivo, así que
  `bruto − descuento` restaría de más. Es el origen de las 10 filas que el
  perfilado marcó como "descuento > importe bruto".
- **Decisión:** en las líneas con `es_devolucion`, el descuento se multiplica por
  −1 para que lleve el mismo signo que las unidades.
- **Reto:** 1 y 2.
- **Impacto:** **1 sola línea** tras excluir los regalos (una devolución
  `SPECIAL ES` con 11,20 € de descuento). El resto tenía descuento 0.
- **Estado:** decidido durante la limpieza; no estaba en la lista original de 8.

### [2026-11-14] Las 25 líneas de venta duplicadas se eliminan
- **Contexto:** 25 pares de filas idénticas en todas sus columnas (mismo pedido,
  mismo SKU, misma fecha, mismo precio, 1 unidad cada una).
- **Opciones consideradas:** conservarlas, por si el sistema crease una línea por
  unidad. Descartada: un ERP agruparía 2 unidades en una línea con `unidades = 2`,
  y el enunciado avisa de que hay errores introducidos a propósito.
- **Decisión:** se elimina una de cada par.
- **Reto:** 1 y 2.
- **Impacto:** −25 líneas sobre 18.292 (0,1 %). De ellas, 2 eran regalos y 5 eran
  de precio especial.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Normalizaciones de formato: SKU y mercado
- **Contexto:** 15 líneas traen el SKU en minúsculas (`eme010-bro-m`), y 26 traen
  el mercado escrito de otra forma (`Spain` 10, `ESP` 9, `es` 7). Además hay 14
  líneas sin mercado.
- **Decisión:** SKU siempre a mayúsculas sin espacios; las 26 variantes se
  normalizan a `ES`; los 14 nulos pasan a `DESCONOCIDO`, **sin imputar**.
- **Reto:** 1 y 2.
- **Impacto:** sin la normalización de SKU se perderían 15 ventas en silencio al
  cruzar con el catálogo. Imputar los 14 mercados sería inventar dato por el 0,08 %.
- **Estado:** confirmado con el usuario.

### [2026-11-14] El SKU `EME999-BLA-M` se excluye del análisis
- **Contexto:** tiene 14 unidades de stock pero no existe en el catálogo y nunca
  se ha vendido.
- **Decisión:** se excluye (cruce `inner` con PRODUCTO) y se reporta con nombre y
  apellidos en las notas de calidad. Sin producto, color ni talla no se puede
  agregar por modelo ni calcular margen.
- **Reto:** 1 y 2.
- **Impacto:** 14 unidades de stock fuera del análisis. Es un aviso para almacén.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Las compras vencidas se marcan, no se descartan
- **Contexto:** 37 pedidos sin fecha real de llegada cuya fecha estimada ya pasó
  a la fecha de corte. Además, 427 de 555 entregas (77 %) llegaron tarde.
- **Decisión:** `clean.py` las marca con `esta_vencida` contra `FECHA_CORTE_DATOS`
  (no contra la semana de análisis, que es exclusiva del Reto 1). Qué hacer con
  ellas se decide en el Reto 2.
- **Reto:** 1 (se reporta) y 2 (se decide).
- **Impacto:** en el Reto 2, contarlas como stock en camino llevaría a reponer de
  menos para unidades que probablemente no lleguen.
- **Estado:** marcado; tratamiento pendiente de decidir en el Reto 2.
