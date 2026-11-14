# Notas de calidad de datos

> Plantilla. Se rellena tras ejecutar el perfilado (`src/profiling.py`) y la
> limpieza (`src/clean.py`). Un problema solo se considera tratado cuando aparece
> aquí con su impacto y su decisión.

## Resumen ejecutivo

_Pendiente._ (3–5 líneas: qué estado tienen los datos y qué hay que saber antes
de leer el informe.)

## Inventario de tablas

| Tabla | Filas | Columnas | Periodo | Observaciones |
|-------|-------|----------|---------|---------------|
| VENTAS |  |  |  |  |
| PRODUCTO |  |  |  |  |
| STOCK |  |  |  |  |
| COMPRAS |  |  |  |  |

## Problemas detectados y tratamiento

| # | Tabla | Problema | Cómo se detecta | Volumen afectado | Impacto en el análisis | Tratamiento aplicado |
|---|-------|----------|-----------------|------------------|------------------------|----------------------|
| 1 |  |  |  |  |  |  |

### Por categoría

#### Valores ausentes

_Pendiente._

#### Duplicados

_Pendiente._

#### Tipos y formatos (fechas, números como texto, mayúsculas/acentos)

_Pendiente._

#### Valores imposibles o fuera de rango

_Pendiente._

#### Integridad referencial (SKUs huérfanos entre tablas)

_Pendiente._

#### Aplicación de las reglas de negocio

_Pendiente._ (Cuántas líneas se excluyen por `influencers`, cuántas se marcan
como `special`, cuántas compras usan fecha estimada en vez de real.)

## Problemas conocidos no resueltos

_Pendiente._ (Qué queda sin arreglar, por qué, y cómo afecta a la lectura del informe.)
