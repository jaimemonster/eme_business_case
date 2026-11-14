"""Previsión de demanda por SKU (Reto 2).

Responsabilidad: estimar, a partir del histórico de ventas limpias, la demanda
semanal esperada de cada SKU para el horizonte que necesita la reposición
(lead time + cobertura objetivo). Incluye el tratamiento de SKUs sin histórico
suficiente y la medición del error del método elegido.
"""

from __future__ import annotations

from typing import Tuple

import pandas as pd


def serie_semanal_por_sku(ventas: pd.DataFrame) -> pd.DataFrame:
    """Construye la serie de unidades vendidas por SKU y semana ISO, rellenando
    con cero las semanas sin venta dentro del periodo de vida del SKU."""
    raise NotImplementedError


def prever_demanda_sku(
    serie: pd.DataFrame,
    horizonte_semanas: int,
) -> pd.DataFrame:
    """Devuelve la demanda semanal prevista por SKU para el horizonte indicado."""
    raise NotImplementedError


def evaluar_forecast(
    serie: pd.DataFrame,
    horizonte_semanas: int,
) -> pd.DataFrame:
    """Backtesting del método: error (MAE/MAPE/sesgo) frente a semanas conocidas."""
    raise NotImplementedError


def generar_forecast(ventas: pd.DataFrame, horizonte_semanas: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Orquesta la previsión y devuelve (previsión, métricas de error)."""
    raise NotImplementedError
