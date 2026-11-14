"""Generación del informe HTML del Reto 1.

Responsabilidad: convertir las tablas de métricas en un informe HTML
autocontenido (Plotly embebido + plantilla Jinja2) pensado para que la dirección
lo abra cada lunes. No calcula KPIs: solo los presenta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


def grafico_evolucion_semanal(df: pd.DataFrame):
    """Serie temporal de unidades, facturación neta y margen por semana."""
    raise NotImplementedError


def grafico_desglose(df: pd.DataFrame, dimension: str):
    """Reparto de la semana por mercado, sección o categoría."""
    raise NotImplementedError


def tabla_html(df: pd.DataFrame, titulo: str) -> str:
    """Renderiza un DataFrame como tabla HTML con el formato del informe."""
    raise NotImplementedError


def seccion_decisiones(reto: str) -> str:
    """Renderiza la sección "Decisiones y supuestos" del informe a partir de
    docs/decisiones.md, filtrando las entradas que afectan al reto indicado.

    Nunca se escribe a mano: la fuente de verdad es el log de decisiones.
    """
    raise NotImplementedError


def seccion_calidad_datos() -> str:
    """Renderiza el resumen de calidad de datos a partir de
    docs/notas_calidad_datos.md: qué se encontró, qué se corrigió y qué no."""
    raise NotImplementedError


def construir_informe(metricas: Dict[str, pd.DataFrame], destino: Path) -> Path:
    """Ensambla el informe completo y lo escribe en `destino`. Devuelve la ruta."""
    raise NotImplementedError
