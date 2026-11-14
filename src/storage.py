"""Entrada/salida de datos.

Responsabilidad: leer el Excel original de `data/raw` (nunca escribirlo) y
persistir/recuperar las tablas intermedias y procesadas en parquet. Ningún otro
módulo debe abrir ficheros directamente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from . import config


def cargar_excel_crudo() -> Dict[str, pd.DataFrame]:
    """Carga las cuatro pestañas de datos del Excel original sin transformarlas.

    Devuelve un diccionario {nombre_pestaña: DataFrame} con los datos tal cual.
    Se lee con `dtype=object` a propósito: así pandas no unifica el tipo de cada
    columna y podemos ver la mezcla real de tipos celda a celda (números
    guardados como texto, fechas como cadena, etc.), que es justo lo que el
    perfilado necesita detectar.
    """
    if not config.FICHERO_EXCEL.exists():
        raise FileNotFoundError(
            f"No se encuentra el Excel original en {config.FICHERO_EXCEL}. "
            "Colócalo en data/raw/ antes de ejecutar los pipelines."
        )
    return {
        pestana: pd.read_excel(config.FICHERO_EXCEL, sheet_name=pestana, dtype=object)
        for pestana in config.PESTANAS
    }


def guardar_tabla(df: pd.DataFrame, nombre: str, carpeta: Path) -> Path:
    """Guarda un DataFrame en parquet dentro de `carpeta` y devuelve la ruta."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.parquet"
    df.to_parquet(ruta, index=False)
    return ruta


def cargar_tabla(nombre: str, carpeta: Path) -> pd.DataFrame:
    """Lee de parquet una tabla previamente guardada."""
    ruta = carpeta / f"{nombre}.parquet"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecuta antes el paso del pipeline que la genera."
        )
    return pd.read_parquet(ruta)
