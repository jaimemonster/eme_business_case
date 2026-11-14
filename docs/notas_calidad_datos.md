# Notas de calidad de datos

Estado tras el perfilado (`src/profiling.py`) y la limpieza (`src/clean.py`).
Las decisiones completas, con sus alternativas descartadas, están en
[`decisiones.md`](decisiones.md).

## Resumen ejecutivo

Los datos están **en mejor estado de lo habitual**: no hay números guardados como
texto, ni fechas rotas, ni stock negativo, ni costes por encima del PVP. Las
ventas son **continuas: 95 semanas sin un solo hueco**, del 15/01/2024 al
09/11/2025.

Los problemas encontrados son **de formato y de reglas**, no de integridad, y
afectan en conjunto a menos del 1 % de las líneas. Ninguna cifra del informe
cambia de forma material por ellos.

La excepción es un **hallazgo de negocio, no de datos**: el **77 % de las entregas
de proveedor llega tarde** y hay **37 pedidos vencidos sin confirmar**. Eso sí
condiciona el Reto 2.

## Inventario de tablas

| Tabla | Filas crudas | Filas limpias | Periodo | Observaciones |
|-------|--------------|---------------|---------|---------------|
| VENTAS | 18.292 | **17.708** | 2024-01-15 → 2025-11-09 | −25 duplicadas, −559 regalos |
| PRODUCTO | 579 | 579 | — | 119 modelos, 2 secciones, 6 categorías, 12 drops |
| STOCK | 580 | **579** | corte 2025-11-09 | −1 SKU sin catálogo |
| COMPRAS | 723 | 723 | 2024-01-05 → 2025-12-28 | 168 sin fecha real de llegada |

Cuadre de VENTAS: `18.292 − 25 duplicadas − 559 regalos = 17.708`.

## Problemas detectados y tratamiento

| # | Tabla | Problema | Volumen | Impacto | Tratamiento |
|---|-------|----------|---------|---------|-------------|
| 1 | VENTAS | Etiqueta `WELCOME10` no documentada en el enunciado | 999 líneas (5,5 %) | Reparto precio completo vs. especial | Venta a precio completo con flag `es_promocion` |
| 2 | VENTAS | Variantes `special` / `SPECIAL ES` / `US` / `NL` | 1.684 líneas | Filtrado de precio especial | Unificadas en `is_special`; sufijo a `mercado_etiqueta` |
| 3 | VENTAS | Unidades negativas (devoluciones) | 10 líneas (0,05 %) | Despreciable | Se conservan, marcadas con `es_devolucion` |
| 4 | VENTAS | Descuento positivo en líneas de unidades negativas | 10 líneas (1 tras excluir regalos) | 11,20 € | Se revierte el signo del descuento |
| 5 | VENTAS | Filas exactamente duplicadas | 25 pares | −25 unidades sobre 19.727 | Se elimina una de cada par |
| 6 | VENTAS | SKU en minúsculas | 15 líneas | 15 ventas perdidas si no se trata | Normalizado a mayúsculas |
| 7 | VENTAS | Mercado con variantes de escritura | 26 líneas | Reparto por mercado | `Spain`/`ESP`/`es` → `ES` |
| 8 | VENTAS | Mercado sin informar | 14 líneas (0,08 %) | Despreciable | → `DESCONOCIDO`, sin imputar |
| 9 | STOCK | `EME999-BLA-M` con stock pero sin catálogo | 1 SKU, 14 uds | 14 uds fuera del análisis | Excluido y reportado |
| 10 | COMPRAS | Entregas más tarde de lo estimado | 427 de 555 (77 %) | **Alto, Reto 2** | Marcado `dias_retraso`; se decide en Reto 2 |
| 11 | COMPRAS | Pedidos vencidos sin fecha real | 37 | **Alto, Reto 2** | Marcado `esta_vencida` |

### Por categoría

#### Valores ausentes

Solo tres columnas tienen nulos, y los tres son significativos, no errores:

- `VENTAS.Etiquetas` (15.048) → la mayoría de ventas no lleva etiqueta. Es lo normal.
- `VENTAS.Mercado` (14) → sin informar. Pasan a `DESCONOCIDO`.
- `COMPRAS.Fecha llegada real` (168) → pendiente de llegar o sin confirmar, tal
  como avisa la pestaña `LEEME`. Es lo que activa la regla 3.

#### Duplicados

25 pares de filas idénticas en VENTAS. `PRODUCTO`, `STOCK` y `COMPRAS` no tienen
duplicados por clave ni filas repetidas.

#### Tipos y formatos

Ningún problema de tipos: las fechas vienen como fecha y los números como número.
Los problemas de formato son de **contenido textual**: SKUs en minúsculas y
variantes de escritura del mercado.

#### Valores imposibles o fuera de rango

Solo las 10 líneas de unidades negativas, que resultaron ser devoluciones
legítimas. Sin precios ni costes negativos, sin stock negativo y sin ningún
producto con coste por encima del PVP.

#### Integridad referencial

- 15 "huérfanos" de VENTAS eran **falsos**: solo diferían en mayúsculas.
- 1 huérfano real: `EME999-BLA-M` en STOCK.
- COMPRAS no tiene huérfanos.
- 17 SKUs del catálogo no se han vendido nunca. No es un error: son producto sin
  rotación, y es justo lo que el informe tiene que señalar.

#### Aplicación de las reglas de negocio

| Regla | Efecto medido |
|-------|---------------|
| 1 · `influencers` = regalo | **559 líneas excluidas** de todo análisis de venta (561 crudas, 2 eran duplicadas). Descuentan el 100 %: son regalos de verdad. |
| 2 · `special` = precio especial | **1.679 líneas** marcadas `is_special`, con ~40 % de descuento medio. |
| 3 · Llegada efectiva | **555 compras** usan fecha real; **168** caen a la estimada. |
| 4 · Modelo = producto + color | **119 modelos** sobre 579 SKUs (4,9 tallas por modelo de media). |

## Hallazgos de negocio

Cosas que no son errores de datos pero que dirección debería ver:

1. **El proveedor llega tarde de forma sistemática.** 427 de 555 entregas (77 %)
   llegaron después de la estimada; solo 102 llegaron antes. La fecha estimada no
   es fiable como base de planificación.
2. **37 pedidos están perdidos**: su fecha estimada venció y no hay confirmación
   de llegada.
3. **El precio especial es estacional**, no continuo: se concentra en rebajas de
   enero, verano (julio–agosto) y noviembre de 2024 (Black Friday). La semana
   analizada no tiene ni una venta a precio especial.
4. **14 unidades en almacén de un SKU que el catálogo no conoce** (`EME999-BLA-M`).
5. **17 SKUs del catálogo nunca se han vendido.**

## Problemas conocidos no resueltos

- **Si los precios llevan IVA o no.** Se asume que **no**. Nada en los datos ni en
  la pestaña `LEEME` lo aclara. Si lo llevasen, facturación y margen estarían
  sobrevalorados de forma proporcional, pero **ninguna comparativa cambiaría**:
  todas las cifras se verían afectadas igual.
- **El lead time real del proveedor no es medible.** `COMPRAS` no trae fecha de
  pedido, solo de llegada. Las 6 semanas del enunciado se toman como dadas, sin
  poder contrastarlas con los datos.
- **Los 14 mercados `DESCONOCIDO` no se pueden recuperar.** Aparecerán como
  categoría propia en los desgloses por mercado.
