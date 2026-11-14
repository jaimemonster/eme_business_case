"""KPIs del Reto 1 (informe semanal de ventas y stock).

Responsabilidad: calcular, sobre las tablas limpias, los indicadores que responde
el informe semanal. No lee ficheros ni dibuja gráficos: recibe DataFrames y
devuelve DataFrames.
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, Tuple

import pandas as pd


def resumen_semanal(
    ventas: pd.DataFrame,
    semana: Tuple[dt.date, dt.date],
) -> pd.DataFrame:
    """Unidades, facturación neta y margen de una semana, separando precio especial."""
    raise NotImplementedError


def comparativa_semanas(
    ventas: pd.DataFrame,
    semana_actual: Tuple[dt.date, dt.date],
    semana_anterior: Tuple[dt.date, dt.date],
    semana_ano_anterior: Tuple[dt.date, dt.date],
) -> pd.DataFrame:
    """Compara la semana de análisis contra la anterior y contra la misma semana ISO
    del año pasado, con variaciones absolutas y en porcentaje."""
    raise NotImplementedError


def desglose_por_dimension(
    ventas: pd.DataFrame,
    semana: Tuple[dt.date, dt.date],
    dimension: str,
) -> pd.DataFrame:
    """Reparto de la semana por mercado, sección o categoría, con el peso del
    precio especial sobre el total."""
    raise NotImplementedError


def ranking_modelos(
    ventas: pd.DataFrame,
    stock: pd.DataFrame,
    periodo: Tuple[dt.date, dt.date],
    top_n: int = 10,
) -> Dict[str, pd.DataFrame]:
    """Top y bottom de modelos por ventas, con su sell-through."""
    raise NotImplementedError


def sell_through(
    ventas: pd.DataFrame,
    stock: pd.DataFrame,
    periodo: Tuple[dt.date, dt.date],
    nivel: str = "modelo_id",
) -> pd.DataFrame:
    """Sell-through = unidades vendidas / (unidades vendidas + stock actual)."""
    raise NotImplementedError


def alertas_stock(
    ventas: pd.DataFrame,
    stock: pd.DataFrame,
    compras: pd.DataFrame,
    horizonte_semanas: int,
) -> Dict[str, pd.DataFrame]:
    """Modelos en riesgo de rotura en el horizonte indicado y modelos con exceso
    de stock, según las definiciones documentadas en CLAUDE.md."""
    raise NotImplementedError


def calcular_todas_las_metricas(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Orquesta el cálculo de todos los KPIs del informe y los persiste en
    data/processed."""
    raise NotImplementedError
