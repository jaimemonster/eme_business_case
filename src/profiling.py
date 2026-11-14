"""Perfilado de calidad de datos.

Responsabilidad: describir el estado de las tablas crudas (tipos, nulos,
duplicados, cardinalidades, rangos, valores imposibles, claves huérfanas) para
poder decidir cómo limpiarlas. No transforma nada: solo observa y reporta.

Su salida alimenta docs/notas_calidad_datos.md.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd


def perfilar_tabla(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    """Devuelve un resumen por columna: tipo, % nulos, nº únicos, min/max y ejemplos."""
    raise NotImplementedError


def detectar_duplicados(df: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Devuelve las filas duplicadas según el conjunto de claves indicado."""
    raise NotImplementedError


def detectar_claves_huerfanas(
    tablas: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Busca SKUs de VENTAS/STOCK/COMPRAS que no existen en PRODUCTO (y viceversa)."""
    raise NotImplementedError


def detectar_valores_imposibles(tablas: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Marca valores fuera de rango: unidades/precios negativos, fechas fuera del periodo,
    descuentos superiores al importe, costes mayores que el PVP, etc."""
    raise NotImplementedError


def generar_informe_perfilado(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Ejecuta todos los perfilados y devuelve las tablas de hallazgos."""
    raise NotImplementedError
