"""Servicio web de la propuesta de reposición (Reto 2).

Dos cosas en un solo proceso:

  · **La web** (`GET /…`) que abre quien quiera ver la propuesta.
  · **El trabajo** (`POST /jobs/reposicion`) que dispara el reloj cada día a las
    00:00 y que recalcula y escribe el Sheet.

No guarda estado en disco a propósito: el cálculo es determinista —con los mismos
datos sale el mismo resultado— así que recalcular al vuelo sale más barato y más
simple que mantener una base de datos. El único estado que importa, el histórico
de ejecuciones, vive en el propio Sheet.

Arranque en local:
    uvicorn service.app:app --reload
"""

from __future__ import annotations

import datetime as dt
import io
import os
import time
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from src import config, replenishment
from src.clean import ejecutar_limpieza

from . import sheets, vista

app = FastAPI(title="EME STUDIOS · Reposición", docs_url=None, redoc_url=None)

# Caché en memoria. El cálculo tarda unos segundos; recalcularlo en cada visita
# haría la web lenta sin que el resultado cambiase, porque los datos del caso son
# fijos. Se recalcula cuando lo pide el reloj o cuando caduca.
_cache: Dict[str, object] = {"resultado": None, "momento": None}
MINUTOS_CACHE = 30

# Histórico de ejecuciones de este proceso. Se mantiene en memoria para pintarlo
# rápido, pero el registro que perdura es el del Sheet: si el contenedor se
# reinicia, esto se vacía y aquél no.
_ejecuciones: List[dict] = []

# Secreto compartido con el reloj. La web es pública para que se pueda abrir sin
# cuenta de Google, así que la dirección que dispara el cálculo queda expuesta:
# sin esta comprobación, cualquiera que diera con la URL podría lanzarlo.
TOKEN_TRABAJO = os.environ.get("EME_TOKEN_TRABAJO", "")


def _calcular() -> Dict[str, pd.DataFrame]:
    """Ejecuta el pipeline completo: limpieza, previsión y propuesta."""
    tablas = ejecutar_limpieza(persistir=False)
    return replenishment.generar_propuesta(tablas)


def _resultado(forzar: bool = False) -> Dict[str, pd.DataFrame]:
    """Devuelve la propuesta, recalculándola si hace falta."""
    momento = _cache.get("momento")
    caducada = (
        momento is None
        or (dt.datetime.now() - momento).total_seconds() > MINUTOS_CACHE * 60
    )
    if forzar or caducada or _cache.get("resultado") is None:
        _cache["resultado"] = _calcular()
        _cache["momento"] = dt.datetime.now()
    return _cache["resultado"]  # type: ignore[return-value]


# --- páginas ---------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def propuesta() -> str:
    return vista.pagina_propuesta(_resultado(), _cache["momento"])  # type: ignore[arg-type]


@app.get("/metodo", response_class=HTMLResponse)
def metodo() -> str:
    return vista.pagina_metodo(_resultado())


@app.get("/decisiones", response_class=HTMLResponse)
def decisiones() -> str:
    return vista.pagina_decisiones()


@app.get("/produccion", response_class=HTMLResponse)
def produccion() -> str:
    return vista.pagina_produccion()


@app.get("/historico", response_class=HTMLResponse)
def historico() -> str:
    """El historial sale del Sheet, no de la memoria de esta instancia.

    Si el Sheet no responde se cae a lo que haya visto este proceso: es peor
    —parcial y volátil— pero mejor que una página rota.
    """
    try:
        ejecuciones = sheets.leer_historico()
    except sheets.SheetsNoDisponible:
        ejecuciones = _ejecuciones
    return vista.pagina_historico(ejecuciones)


# --- descargas y exportación ----------------------------------------------

@app.get("/descargar/excel")
def descargar_excel() -> Response:
    """El mismo contenido que el Sheet, en un fichero descargable.

    Comparte `tablas_entregable` con la escritura en Sheets a propósito: si cada
    canal armase sus propias pestañas, acabarían diciendo cosas distintas.
    """
    r = _resultado()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre, df in replenishment.tablas_entregable(r).items():
            df.to_excel(writer, sheet_name=nombre[:31], index=False)
    hoy = dt.date.today().isoformat()
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="propuesta_reposicion_{hoy}.xlsx"'},
    )


@app.get("/api/propuesta.json")
def api_propuesta() -> JSONResponse:
    """La propuesta en JSON, por si alguien quiere engancharla a otra cosa."""
    r = _resultado()
    return JSONResponse({
        "generada": _cache["momento"].isoformat() if _cache["momento"] else None,
        "corte_datos": str(config.FECHA_CORTE_DATOS),
        "lead_time_semanas": config.LEAD_TIME_SEMANAS,
        "cobertura_objetivo_semanas": config.COBERTURA_OBJETIVO_SEMANAS,
        "resumen": r["resumen"].set_index("concepto")["valor"].to_dict(),
        "lineas": r["propuesta"].to_dict(orient="records"),
    })


@app.post("/exportar/sheet")
def exportar_sheet() -> JSONResponse:
    """Escribe el Sheet bajo demanda, desde el botón de la web."""
    try:
        destino = sheets.escribir_propuesta(_resultado())
    except sheets.SheetsNoDisponible as e:
        return JSONResponse({"ok": False, "error": str(e)[:400]}, status_code=200)
    return JSONResponse({"ok": True, "url": destino})


# --- el trabajo que dispara el reloj --------------------------------------

@app.post("/jobs/reposicion")
def job_reposicion(
    request: Request,
    x_eme_token: Optional[str] = Header(default=None),
) -> JSONResponse:
    """Recalcula la propuesta y la escribe en el Sheet. Lo llama el reloj.

    Devuelve siempre el detalle de lo ocurrido, incluso cuando falla el Sheet: el
    cálculo y la publicación son dos cosas distintas y conviene saber cuál se ha
    roto. Si el Sheet falla, la propuesta sigue viva en la web.
    """
    if TOKEN_TRABAJO and x_eme_token != TOKEN_TRABAJO:
        raise HTTPException(status_code=403, detail="Token no válido")

    inicio = time.monotonic()
    disparo = "reloj" if x_eme_token else "manual"
    r = _resultado(forzar=True)
    res = r["resumen"].set_index("concepto")["valor"]

    resultado_txt, destino = "ok", None
    try:
        destino = sheets.escribir_propuesta(r)
    except sheets.SheetsNoDisponible as e:
        resultado_txt = f"calculado, Sheet falló: {str(e)[:120]}"

    ejecucion = {
        "momento": sheets.momento_ahora(),
        "disparo": disparo,
        "skus": int(res["SKUs a reponer"]),
        "unidades": int(res["Unidades propuestas"]),
        "coste": float(res["Coste del pedido (€)"]),
        "segundos": time.monotonic() - inicio,
        "resultado": resultado_txt,
    }
    _ejecuciones.append(ejecucion)

    try:
        sheets.registrar_ejecucion(ejecucion)
    except sheets.SheetsNoDisponible:
        pass  # ya queda reflejado en `resultado`

    return JSONResponse({"ok": resultado_txt == "ok", "url": destino, **ejecucion})


@app.get("/health")
def health() -> JSONResponse:
    """Comprobación de vida, para el despliegue."""
    return JSONResponse({
        "ok": True,
        "calculado": _cache["momento"].isoformat() if _cache["momento"] else None,
        "ejecuciones": len(_ejecuciones),
    })
