"""Limpieza de datos y aplicación de las reglas de negocio.

Responsabilidad: convertir las tablas crudas en tablas limpias y tipadas listas
para analizar, y ser el ÚNICO lugar donde se aplican las reglas de negocio del
caso:

1. Los pedidos con etiqueta `influencers` son regalos y se excluyen de toda venta.
2. Los pedidos con etiqueta `special` se marcan con el flag `is_special`.
3. La llegada de compras usa la fecha real si existe y, si no, la estimada
   (`fecha_llegada_efectiva`).
4. Modelo = producto + color; cada talla es un SKU distinto (`modelo_id`).

Toda corrección aplicada aquí debe quedar reflejada en docs/notas_calidad_datos.md.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Pasa los nombres de columna a snake_case y sin acentos."""
    raise NotImplementedError


def limpiar_producto(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia el catálogo y crea la clave `modelo_id` (regla 4)."""
    raise NotImplementedError


def limpiar_ventas(df: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Limpia las líneas de pedido, parsea etiquetas y aplica las reglas 1 y 2.

    Devuelve solo las ventas reales (sin regalos), con el flag `is_special` y las
    métricas de línea calculadas (facturación neta y margen).
    """
    raise NotImplementedError


def extraer_regalos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve las líneas etiquetadas como `influencers`, excluidas de la venta
    pero necesarias para entender el consumo de stock."""
    raise NotImplementedError


def limpiar_stock(df: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Limpia el stock a fecha de cierre y lo enriquece con `modelo_id`."""
    raise NotImplementedError


def limpiar_compras(df: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Limpia las compras y calcula `fecha_llegada_efectiva` (regla 3)."""
    raise NotImplementedError


def ejecutar_limpieza() -> Dict[str, pd.DataFrame]:
    """Orquesta la limpieza completa y persiste las tablas en data/interim."""
    raise NotImplementedError
