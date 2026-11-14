"""Entrada/salida de datos.

Responsabilidad: leer el Excel original de `data/raw` (nunca escribirlo) y
persistir/recuperar las tablas intermedias y procesadas en parquet. Ningún otro
módulo debe abrir ficheros directamente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


def cargar_excel_crudo() -> Dict[str, pd.DataFrame]:
    """Carga las cuatro pestañas del Excel original sin transformarlas.

    Devuelve un diccionario {nombre_pestaña: DataFrame} con los datos tal cual,
    sin castear tipos ni renombrar columnas.
    """
    raise NotImplementedError


def guardar_tabla(df: pd.DataFrame, nombre: str, carpeta: Path) -> Path:
    """Guarda un DataFrame en parquet dentro de `carpeta` y devuelve la ruta."""
    raise NotImplementedError


def cargar_tabla(nombre: str, carpeta: Path) -> pd.DataFrame:
    """Lee de parquet una tabla previamente guardada."""
    raise NotImplementedError
