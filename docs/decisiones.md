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
