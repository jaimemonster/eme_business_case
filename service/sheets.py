"""Escritura de la propuesta en Google Sheets.

Responsabilidad: volcar las tablas al Sheet que revisa Compras y dejar constancia
de cada ejecución.

Autenticación sin claves. No existe ningún fichero de credenciales, ni aquí ni en
el contenedor, porque la organización prohíbe descargarlas (y hace bien: una
clave descargada no caduca y funciona desde cualquier sitio). En su lugar:

  · **Desplegado**: el servicio corre *como* la cuenta de servicio. Las
    credenciales las pide al entorno en cada arranque y caducan en una hora.
  · **En local**: se impersona esa misma cuenta, lo que requiere el rol
    `roles/iam.serviceAccountTokenCreator` sobre ella. El Sheet se escribe con la
    misma identidad en los dos casos, así que lo que se prueba es lo que pasa.

El montaje está documentado en `docs/reto2_infraestructura.md`.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Dict, List, Optional

import pandas as pd

from src import config

ALCANCES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

HOJA_HISTORICO = "Histórico de ejecuciones"

# Pestañas que generaron versiones anteriores del entregable. Se borran al
# escribir: sin esto el Sheet acumula hojas huérfanas con datos caducados, que es
# peor que no tenerlas porque parecen vigentes. Solo se tocan éstas, nunca una
# pestaña que haya podido añadir una persona.
HOJAS_OBSOLETAS = (
    "Resumen", "A confirmar con proveedor", "Sin rotación",
    "Decisiones y parámetros", "Comparativa de métodos",
    # La hoja vacía que Google crea al nacer el documento. La sustituye el glosario.
    "Hoja 1", "Hoja1", "Sheet1",
)

CABECERA_HISTORICO = [
    "Momento", "Disparo", "SKUs propuestos", "Unidades", "Coste (€)",
    "Duración (s)", "Resultado",
]


class SheetsNoDisponible(RuntimeError):
    """El Sheet no se pudo escribir. Nunca debe tumbar el resto del servicio."""


def _credenciales():
    """Credenciales con permiso de Sheets, sin clave descargada."""
    import google.auth
    from google.auth import impersonated_credentials

    # Cloud Run define K_SERVICE. Allí el proceso ya ES la cuenta de servicio y
    # puede pedir directamente los alcances que necesita.
    if os.environ.get("K_SERVICE"):
        credenciales, _ = google.auth.default(scopes=ALCANCES)
        return credenciales

    origen, _ = google.auth.default()
    return impersonated_credentials.Credentials(
        source_credentials=origen,
        target_principal=config.CUENTA_SERVICIO,
        target_scopes=ALCANCES,
        lifetime=3600,
    )


def _servicio():
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=_credenciales(), cache_discovery=False)


def _valores(df: pd.DataFrame) -> List[List]:
    """DataFrame a la matriz de valores que espera la API.

    Las fechas se pasan a texto y los nulos a cadena vacía: la API rechaza
    `NaT` y `NaN`, y un error de serialización a mitad del volcado dejaría el
    Sheet a medias.
    """
    limpio = df.copy()
    for col in limpio.columns:
        if pd.api.types.is_datetime64_any_dtype(limpio[col]):
            limpio[col] = limpio[col].dt.strftime("%Y-%m-%d")
    limpio = limpio.astype(object).where(pd.notna(limpio), "")
    return [list(limpio.columns)] + limpio.values.tolist()


def _asegurar_hojas(servicio, id_sheet: str, nombres: List[str], limpiar: bool = False) -> None:
    """Crea las pestañas que falten y, si se pide, borra las obsoletas.

    Idempotente: se ejecuta en cada escritura.
    """
    meta = servicio.spreadsheets().get(spreadsheetId=id_sheet).execute()
    existentes = {h["properties"]["title"]: h["properties"]["sheetId"] for h in meta["sheets"]}
    peticiones = [
        {"addSheet": {"properties": {"title": n}}}
        for n in nombres if n not in existentes
    ]
    if limpiar:
        peticiones += [
            {"deleteSheet": {"sheetId": existentes[n]}}
            for n in HOJAS_OBSOLETAS if n in existentes
        ]
    if peticiones:
        servicio.spreadsheets().batchUpdate(
            spreadsheetId=id_sheet, body={"requests": peticiones}
        ).execute()


def escribir_propuesta(
    resultado: Dict[str, pd.DataFrame],
    id_sheet: Optional[str] = None,
) -> str:
    """Vuelca la propuesta al Sheet maestro y devuelve su URL.

    Siempre el mismo documento, sobrescrito: Compras entra por su marcador y ve
    lo de hoy, sin tener que buscar cuál es el último fichero.
    """
    id_sheet = id_sheet or config.ID_SHEET_PROPUESTA
    from src.replenishment import tablas_entregable

    hojas = tablas_entregable(resultado)

    try:
        servicio = _servicio()
        _asegurar_hojas(servicio, id_sheet, list(hojas) + [HOJA_HISTORICO], limpiar=True)

        # Se limpia antes de escribir: si la propuesta de hoy tiene menos filas
        # que la de ayer, sin limpiar quedarían filas viejas haciéndose pasar por
        # actuales, que es la peor forma posible de fallar.
        servicio.spreadsheets().values().batchClear(
            spreadsheetId=id_sheet, body={"ranges": [f"'{n}'!A:ZZ" for n in hojas]}
        ).execute()

        servicio.spreadsheets().values().batchUpdate(
            spreadsheetId=id_sheet,
            body={
                "valueInputOption": "RAW",
                "data": [
                    {"range": f"'{nombre}'!A1", "values": _valores(df)}
                    for nombre, df in hojas.items()
                ],
            },
        ).execute()
    except Exception as e:  # noqa: BLE001 - se reporta, no se traga en silencio
        raise SheetsNoDisponible(str(e)) from e

    return f"https://docs.google.com/spreadsheets/d/{id_sheet}/edit"


def registrar_ejecucion(ejecucion: dict, id_sheet: Optional[str] = None) -> None:
    """Añade una línea al histórico de ejecuciones del propio Sheet.

    El histórico vive en el Sheet y no en una base de datos a propósito: es el
    sitio donde ya mira Compras, no hay nada más que mantener, y sirve a la vez
    de registro de auditoría.
    """
    id_sheet = id_sheet or config.ID_SHEET_PROPUESTA
    try:
        servicio = _servicio()
        _asegurar_hojas(servicio, id_sheet, [HOJA_HISTORICO])

        actual = servicio.spreadsheets().values().get(
            spreadsheetId=id_sheet, range=f"'{HOJA_HISTORICO}'!A1:G1"
        ).execute()
        if not actual.get("values"):
            servicio.spreadsheets().values().update(
                spreadsheetId=id_sheet,
                range=f"'{HOJA_HISTORICO}'!A1",
                valueInputOption="RAW",
                body={"values": [CABECERA_HISTORICO]},
            ).execute()

        fila = [
            ejecucion["momento"], ejecucion["disparo"], ejecucion["skus"],
            ejecucion["unidades"], ejecucion["coste"],
            round(ejecucion["segundos"], 1), ejecucion["resultado"],
        ]
        servicio.spreadsheets().values().append(
            spreadsheetId=id_sheet,
            range=f"'{HOJA_HISTORICO}'!A:G",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [fila]},
        ).execute()
    except Exception as e:  # noqa: BLE001
        raise SheetsNoDisponible(str(e)) from e


def url(id_sheet: Optional[str] = None) -> str:
    return f"https://docs.google.com/spreadsheets/d/{id_sheet or config.ID_SHEET_PROPUESTA}/edit"


def momento_ahora() -> str:
    """Marca temporal en hora de Madrid, que es la que entiende quien lo lee."""
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001 - sin tzdata, UTC marcado como tal
        return dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + " UTC"


def leer_historico(id_sheet: Optional[str] = None) -> List[dict]:
    """Lee el histórico de ejecuciones del Sheet.

    La web lo lee de aquí y no de la memoria del proceso: Cloud Run puede
    levantar varias instancias y apagarlas cuando nadie las usa, así que un
    historial en memoria mostraría solo lo que haya visto esa instancia concreta
    y se vaciaría en cada arranque. El Sheet es el único registro que perdura.
    """
    id_sheet = id_sheet or config.ID_SHEET_PROPUESTA
    try:
        servicio = _servicio()
        datos = servicio.spreadsheets().values().get(
            spreadsheetId=id_sheet, range=f"'{HOJA_HISTORICO}'!A2:G"
        ).execute()
    except Exception as e:  # noqa: BLE001
        raise SheetsNoDisponible(str(e)) from e

    def numero(valor, entero=True):
        try:
            return int(float(valor)) if entero else float(valor)
        except (TypeError, ValueError):
            return 0

    filas = []
    for f in datos.get("values", []):
        f = list(f) + [""] * (7 - len(f))
        filas.append({
            "momento": f[0], "disparo": f[1],
            "skus": numero(f[2]), "unidades": numero(f[3]),
            "coste": numero(f[4], entero=False),
            "segundos": numero(f[5], entero=False),
            "resultado": f[6],
        })
    return filas
