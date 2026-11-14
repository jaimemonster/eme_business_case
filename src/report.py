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


def bloque_decision_plegable(
    titulo: str,
    que_pasaba: str,
    ejemplo: pd.DataFrame,
    decision: str,
    impacto: str,
) -> str:
    """Renderiza una decisión como bloque plegable (`<details>`/`<summary>`).

    Cerrado se ve solo el titular; al desplegarlo aparecen el problema, un
    ejemplo con filas reales del dato original, la decisión con sus alternativas
    descartadas, y el impacto sobre las cifras del informe.

    Se usa HTML nativo a propósito: sin JavaScript, el informe sigue siendo un
    único fichero que funciona con doble clic.
    """
    raise NotImplementedError


def pagina_decisiones(reto: str, ejemplos: Dict[str, pd.DataFrame]) -> str:
    """Construye la página "Decisiones y calidad de datos" del informe.

    Lee las decisiones de docs/decisiones.md filtrando por reto, y las empareja
    con los ejemplos extraídos de los datos crudos durante el perfilado. Nunca se
    escribe a mano: la fuente de verdad es el log de decisiones.
    """
    raise NotImplementedError


def recopilar_ejemplos_decisiones(tablas_crudas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Extrae de las tablas CRUDAS las filas que ilustran cada decisión (las 25
    duplicadas, las 10 devoluciones, los SKUs en minúscula, EME999-BLA-M...).

    Se toman de `data/raw` a propósito: el ejemplo tiene que enseñar el problema
    tal como estaba, no ya corregido.
    """
    raise NotImplementedError


def construir_informe(metricas: Dict[str, pd.DataFrame], destino: Path) -> Path:
    """Ensambla el informe completo y lo escribe en `destino`. Devuelve la ruta."""
    raise NotImplementedError
