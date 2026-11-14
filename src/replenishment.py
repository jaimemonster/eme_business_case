"""Propuesta de reposición por SKU (Reto 2).

Responsabilidad: a partir de la demanda prevista, el stock disponible y las
compras pendientes de llegar, calcular qué reponer y cuántas unidades, con un
lead time de proveedor de 6 semanas y una cobertura objetivo de 8 semanas.

Lógica de referencia (a validar y documentar):
    necesidad = demanda(lead_time + cobertura_objetivo)
                - stock_disponible
                - compras que llegan dentro del lead time
"""

from __future__ import annotations

from typing import Dict

import pandas as pd


def stock_en_transito(compras: pd.DataFrame, horizonte_semanas: int) -> pd.DataFrame:
    """Unidades por SKU que llegarán al almacén dentro del horizonte, usando
    `fecha_llegada_efectiva`."""
    raise NotImplementedError


def calcular_necesidad(
    forecast: pd.DataFrame,
    stock: pd.DataFrame,
    compras: pd.DataFrame,
    lead_time_semanas: int,
    cobertura_objetivo_semanas: int,
) -> pd.DataFrame:
    """Calcula la necesidad neta de reposición por SKU."""
    raise NotImplementedError


def construir_propuesta(necesidad: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Convierte la necesidad en una propuesta revisable por Compras: una fila por
    SKU con modelo, color, talla, proveedor, unidades propuestas, prioridad y el
    porqué de la cifra."""
    raise NotImplementedError


def exportar_propuesta(propuesta: pd.DataFrame) -> Dict[str, str]:
    """Exporta la propuesta al formato de revisión de Compras y devuelve las rutas
    generadas."""
    raise NotImplementedError
