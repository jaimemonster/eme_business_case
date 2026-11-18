"""Configuración central del proyecto.

Responsabilidad: ser la única fuente de verdad para rutas, fechas de corte y
parámetros de negocio (lead time, cobertura objetivo, umbrales). Ningún otro
módulo debe contener constantes de negocio escritas a mano.

Nota: los valores aquí definidos están documentados en CLAUDE.md. Cualquier
cambio debe registrarse en docs/decisiones.md.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

# --- Rutas -----------------------------------------------------------------
RAIZ_PROYECTO: Path = Path(__file__).resolve().parents[1]
DIR_DATOS: Path = RAIZ_PROYECTO / "data"
DIR_RAW: Path = DIR_DATOS / "raw"
DIR_INTERIM: Path = DIR_DATOS / "interim"
DIR_PROCESSED: Path = DIR_DATOS / "processed"
DIR_OUTPUT: Path = RAIZ_PROYECTO / "output"
DIR_DOCS: Path = RAIZ_PROYECTO / "docs"

FICHERO_EXCEL: Path = DIR_RAW / "EME_Caso_Practico_Datos.xlsx"
# El Excel incluye además una pestaña `LEEME` con documentación del caso, que no es
# un dato a procesar.
PESTANAS: tuple[str, ...] = ("VENTAS", "PRODUCTO", "STOCK", "COMPRAS")
PESTANA_DOC: str = "LEEME"

# --- Fechas ----------------------------------------------------------------
# FECHA_CORTE_DATOS es el "hoy" del caso: el último día con datos. Todo lo que
# signifique "a día de hoy" (compras vencidas, stock disponible, antigüedad de
# un drop) se mide contra esta fecha, en los TRES retos.
#
# SEMANA_ACTUAL es otra cosa: el periodo que analiza el informe semanal, y solo
# afecta al Reto 1. Coincide que su último día es la fecha de corte, pero son
# conceptos independientes: si el informe se mirase otra semana, FECHA_CORTE_DATOS
# no cambiaría.
FECHA_CORTE_DATOS: dt.date = dt.date(2025, 11, 9)
INICIO_DATOS: dt.date = dt.date(2024, 1, 1)

# --- Fechas de análisis del Reto 1 (semanas ISO, lunes a domingo) ----------
SEMANA_ACTUAL: tuple[dt.date, dt.date] = (dt.date(2025, 11, 3), dt.date(2025, 11, 9))
SEMANA_ANTERIOR: tuple[dt.date, dt.date] = (dt.date(2025, 10, 27), dt.date(2025, 11, 2))
SEMANA_ANO_ANTERIOR: tuple[dt.date, dt.date] = (dt.date(2024, 11, 4), dt.date(2024, 11, 10))

# El snapshot de stock está tomado a la fecha de corte.
FECHA_CIERRE_STOCK: dt.date = FECHA_CORTE_DATOS

# --- Parámetros de reposición ----------------------------------------------
LEAD_TIME_SEMANAS: int = 6
COBERTURA_OBJETIVO_SEMANAS: int = 8
HORIZONTE_ROTURA_SEMANAS: int = 4

# --- Etiquetas de negocio ---------------------------------------------------
ETIQUETA_REGALO: str = "influencers"
ETIQUETA_PRECIO_ESPECIAL: str = "special"


# --- Infraestructura del servicio del Reto 2 -------------------------------
# No son secretos: el ID de un Sheet no da acceso a nada por sí solo (el acceso
# lo controla con quién está compartido). Se pueden sobrescribir por entorno
# para que el servicio desplegado no dependa de valores escritos en el código.
# El montaje completo está documentado en docs/reto2_infraestructura.md.
PROYECTO_GCP: str = os.environ.get("EME_PROYECTO_GCP", "eme-reposicion")
REGION_GCP: str = os.environ.get("EME_REGION_GCP", "europe-southwest1")
CUENTA_SERVICIO: str = os.environ.get(
    "EME_CUENTA_SERVICIO", "reposicion-bot@eme-reposicion.iam.gserviceaccount.com"
)
ID_SHEET_PROPUESTA: str = os.environ.get(
    "EME_SHEET_ID", "16mATc295JLdg6XusheIa55NpjOHVUisGniq6ihc4FFk"
)
# URL pública del servicio del Reto 2. El informe del Reto 1 enlaza aquí: si
# queda vacía, el menú vuelve a mostrar el Reto 2 como pendiente en lugar de
# ofrecer un enlace roto.
URL_SERVICIO_RETO2: str = os.environ.get(
    "EME_URL_SERVICIO",
    "https://eme-reposicion-761842722633.europe-southwest1.run.app",
)


def asegurar_directorios() -> None:
    """Crea los directorios de salida si no existen."""
    raise NotImplementedError
