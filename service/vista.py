"""Páginas HTML del servicio.

Responsabilidad: presentar. No calcula nada: recibe las tablas ya construidas por
`src/replenishment.py` y las convierte en páginas.

Criterio de diseño: **un diagrama en lugar de tres párrafos.** Esto se enseña en
una entrevista, y nadie lee un muro de texto mientras le explican algo. Cada
página responde a una pregunta y cabe en una pantalla y media.
"""

from __future__ import annotations

import datetime as dt
import html
from typing import Dict, List

import pandas as pd

from src import config
from . import decisiones as mod_decisiones
from .estilo import css

PAGINAS = (
    ("/", "Propuesta"),
    ("/metodo", "Cómo funciona"),
    ("/produccion", "En producción"),
    ("/decisiones", "Decisiones"),
    ("/historico", "Ejecuciones"),
)

MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "sep", "oct", "nov", "dic")

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")

HORIZONTE = config.LEAD_TIME_SEMANAS + config.COBERTURA_OBJETIVO_SEMANAS


# --- formato ---------------------------------------------------------------

def num(valor, dec: int = 0) -> str:
    """Número al estilo español: miles con punto, decimales con coma."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    return f"{valor:,.{dec}f}".replace(",", "·").replace(".", ",").replace("·", ".")


def eur(valor, dec: int = 0) -> str:
    return f"{num(valor, dec)} €"


def fecha_larga(f) -> str:
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


def esc(t) -> str:
    return html.escape(str(t)) if t is not None else ""


# --- esqueleto -------------------------------------------------------------

def layout(titulo: str, activo: str, cuerpo: str) -> str:
    nav = "".join(
        f'<a href="{r}" class="{"activo" if r == activo else ""}">{e}</a>'
        for r, e in PAGINAS
    )
    return f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)} · EME STUDIOS</title>
<style>{css()}</style>
</head><body>
<header class="top"><div class="top-fila">
  <div class="marca">EME Studios <span>· Reposición automática</span></div>
  <nav>{nav}</nav>
</div></header>
<main>{cuerpo}
<footer><p>Reto 2 del caso práctico de AI Specialist · el proceso se ejecuta solo cada
día a las 00:00 y deja la propuesta en el Sheet de Compras · datos con cierre el
{fecha_larga(config.FECHA_CORTE_DATOS)}.</p></footer></main></body></html>"""


def cabecera(ojo: str, titulo: str, lede: str = "") -> str:
    extra = f'<p class="lede">{lede}</p>' if lede else ""
    return (f'<div class="cabecera"><span class="ojo">{esc(ojo)}</span>'
            f'<h1>{esc(titulo)}</h1>{extra}</div>')


def kpi(et: str, v: str, sub: str = "") -> str:
    s = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return f'<div class="kpi"><span class="et">{esc(et)}</span><span class="v">{v}</span>{s}</div>'


def tarjeta(et: str, titulo: str, cuerpo: str) -> str:
    return (f'<div class="tarjeta"><span class="et">{esc(et)}</span>'
            f'<h3>{esc(titulo)}</h3>{cuerpo}</div>')


# --- diagramas -------------------------------------------------------------

_FLECHAS = """<defs>
<marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path class="d-mk" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="fp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path class="d-mp" d="M0,0 L10,5 L0,10 z"/></marker>
</defs>"""

# Los cinco pasos van siempre en las mismas posiciones, en los dos diagramas: así
# el segundo se lee sin volver a aprender nada.
_X = (20, 245, 470, 695, 920)
_ANCHO = 180


def diagrama_calculo(r: Dict[str, pd.DataFrame]) -> str:
    """Cómo se obtiene el número de un SKU concreto, de arriba abajo.

    El flujo horizontal anterior enseñaba las etapas pero no el cálculo. Esto
    sigue una sola línea de la propuesta desde la categoría hasta las unidades a
    pedir, que es la pregunta que de verdad se hace quien lo mira: *de dónde sale
    este 25*.
    """
    nec = r["necesidad"]
    p = r["propuesta"]
    # Se elige la línea con más stock: enseña la resta completa en vez de un caso
    # degenerado con el almacén a cero.
    ej = p.nlargest(1, "stock_disponible").iloc[0]
    fila = nec[nec["sku"] == ej["sku"]].iloc[0]
    grupo = f"{fila['seccion']} · {fila['categoria']}".title()
    total_grupo = nec[
        (nec["seccion"] == fila["seccion"]) & (nec["categoria"] == fila["categoria"])
    ]["demanda_horizonte"].sum()
    cuota = 100 * fila["demanda_horizonte"] / total_grupo if total_grupo else 0

    señales = ["cómo viene vendiendo", "qué hizo el año pasado",
               "si sube o baja", "edad de sus drops"]
    chips = "".join(
        f'<rect class="bx-su" x="{40 + i * 270}" y="34" width="230" height="30" rx="8"/>'
        f'<text class="d-s" x="{155 + i * 270}" y="53" text-anchor="middle">{t}</text>'
        for i, t in enumerate(señales)
    )
    flechas = "".join(
        f'<line class="d-ln" x1="{155 + i * 270}" y1="64" x2="{155 + i * 270}" y2="84" '
        f'marker-end="url(#f)"/>' for i in range(4)
    )

    return f"""<figure style="margin:0"><div class="figura">
<svg viewBox="0 0 1120 470" role="img" aria-label="El cálculo de una línea: el modelo
predice la demanda de la categoría a 14 semanas, se reparte entre modelos y tallas hasta
llegar al SKU, y de ahí se resta el stock y lo que viene en camino para obtener las
unidades a pedir.">
{_FLECHAS}
<text class="d-n d-gr" x="40" y="22">LO QUE MIRA EL MODELO</text>
{chips}{flechas}

<rect class="bx-ac" x="40" y="90" width="1040" height="86" rx="12"/>
<text class="d-n d-ac" x="64" y="114">PASO 1 · SE PREDICE LA CATEGORÍA, QUE ES DONDE HAY SEÑAL</text>
<text class="d-t" x="64" y="141">{esc(grupo)}</text>
<text class="d-s" x="64" y="161">21 uds/semana de media · solo el 6 % de semanas a cero</text>
<text class="d-v d-ac" x="1056" y="145" text-anchor="end">{num(total_grupo)} uds</text>
<text class="d-s" x="1056" y="163" text-anchor="end">previstas en {HORIZONTE} semanas</text>

<line class="d-ln" x1="560" y1="176" x2="560" y2="200" marker-end="url(#f)"/>
<text class="d-s" x="576" y="193">se reparte según lo que viene vendiendo cada uno</text>

<rect class="bx-ac" x="40" y="206" width="1040" height="86" rx="12"/>
<text class="d-n d-ac" x="64" y="230">PASO 2 · SE REPARTE HASTA LA TALLA</text>
<text class="d-t" x="64" y="257">{esc(ej['modelo_nombre'])} · talla {esc(ej['talla'])}</text>
<text class="d-s" x="64" y="277">se lleva el {num(cuota, 1)} % de su categoría</text>
<text class="d-v d-ac" x="1056" y="261" text-anchor="end">{num(fila['demanda_horizonte'])} uds</text>
<text class="d-s" x="1056" y="279" text-anchor="end">para este SKU</text>

<line class="d-ln" x1="560" y1="292" x2="560" y2="316" marker-end="url(#f)"/>
<text class="d-s" x="576" y="309">y se le resta lo que ya se tiene</text>

<rect class="bx-ok" x="40" y="322" width="1040" height="124" rx="12"/>
<text class="d-n d-ok" x="64" y="346">PASO 3 · SE RESTA LO QUE YA HAY</text>
<text class="d-s" x="64" y="372">demanda prevista</text>
<text class="d-s" x="400" y="372" text-anchor="end">{num(fila['demanda_horizonte'])}</text>
<text class="d-s" x="64" y="392">− en el almacén hoy</text>
<text class="d-s" x="400" y="392" text-anchor="end">{num(fila['stock_disponible'])}</text>
<text class="d-s" x="64" y="412">− ya viene de camino</text>
<text class="d-s" x="400" y="412" text-anchor="end">{num(fila['en_transito'])}</text>
<line class="g-eje" x1="64" y1="422" x2="400" y2="422"/>
<text class="d-t" x="64" y="440">a pedir</text>
<text class="d-t" x="400" y="440" text-anchor="end">{num(ej['unidades_propuestas'])}</text>
<text class="d-v d-ok" x="1056" y="390" text-anchor="end">pedir {num(ej['unidades_propuestas'])} uds</text>
<text class="d-s" x="1056" y="410" text-anchor="end">{eur(ej['coste_pedido'])} a precio de coste</text>
</svg></div>
<p class="pie">Una línea real de la propuesta de hoy, de arriba abajo. El modelo predice
la categoría, donde hay señal, y baja al SKU por el reparto.</p>
</figure>"""


def grafico_curva(curva: pd.DataFrame) -> str:
    """La demanda prevista semana a semana, con el ritmo actual como referencia.

    Es el gráfico que desmonta la lectura de que la previsión sea "el ritmo de
    ahora multiplicado por 14": la línea de puntos es justo eso, y las barras son
    lo que dice el modelo.
    """
    ritmo = curva.attrs.get("ritmo_reciente", 0) or 0
    maximo = max(float(curva["unidades"].max()), ritmo) * 1.14
    x0, x1, y0, y1 = 52, 1100, 44, 222
    paso = (x1 - x0) / len(curva)
    ancho = paso * 0.62

    def alto(v):
        return (v / maximo) * (y1 - y0)

    barras = []
    for i, f in curva.reset_index(drop=True).iterrows():
        cx = x0 + paso * (i + 0.5)
        h = alto(f["unidades"])
        clase = "g-barra" if f["unidades"] >= ritmo * 0.6 else "g-barra-baja"
        barras.append(
            f'<rect class="{clase}" x="{cx - ancho / 2:.1f}" y="{y1 - h:.1f}" '
            f'width="{ancho:.1f}" height="{h:.1f}" rx="3"/>'
            f'<text class="g-val" x="{cx:.1f}" y="{y1 - h - 6:.1f}" text-anchor="middle">'
            f'{num(f["unidades"])}</text>'
            f'<text class="g-sem" x="{cx:.1f}" y="{y1 + 15:.1f}" text-anchor="middle">'
            f'{f["inicio_semana"].day} {MESES_CORTOS[f["inicio_semana"].month - 1]}</text>'
        )

    y_ref = y1 - alto(ritmo)
    referencia = (
        f'<line class="g-ref" x1="{x0}" y1="{y_ref:.1f}" x2="{x1}" y2="{y_ref:.1f}"/>'
        f'<text class="g-ref-t" x="{x0 + 6}" y="{y_ref - 7:.1f}">'
        f'ritmo de ahora ({num(ritmo)} uds/sem) proyectado plano</text>'
    )
    eje = f'<line class="g-eje" x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}"/>'

    total = curva["unidades"].sum()
    return f"""<figure style="margin:0"><div class="figura">
<svg viewBox="0 0 1120 250" role="img" aria-label="Demanda prevista semana a semana
durante las 14 semanas siguientes al corte. Arranca en torno a 426 unidades, se
mantiene alta en diciembre y cae por debajo de 150 en enero.">
{referencia}{eje}{"".join(barras)}</svg></div>
<p class="pie">Cada barra es una semana prevista por el modelo. <strong>No es un ritmo
plano:</strong> entre la primera semana y la peor de enero hay un factor de
{num(curva["unidades"].max() / max(curva["unidades"].min(), 1), 1)}. Proyectar el ritmo
actual sin más daría {num(ritmo * len(curva))} uds; el modelo dice {num(total)}.</p>
</figure>"""


def grafico_historico(serie: pd.DataFrame) -> str:
    """Stock y venta semanales, con la previsión del modelo pegada al final.

    Dos paneles que comparten el eje de tiempo en lugar de dos ejes en el mismo
    marco: el stock se mueve entre 13.000 y 16.000 unidades y la venta entre 150
    y 500, así que superponerlos obligaría a un segundo eje y a creerse la escala.

    A la izquierda de la línea de corte todo es dato observado; a la derecha, lo
    que dice el modelo. El stock previsto es el que quedaría sin reponer nada.
    """
    x0, x1 = 58, 1100
    paso = (x1 - x0) / (len(serie) - 1)
    n_obs = int((serie["tipo"] == "observado").sum())
    x_corte = x0 + paso * (n_obs - 1)

    def ruta(col, desde, hasta, y_sup, y_inf, techo, cerrada=False):
        puntos = [
            f"{x0 + paso * i:.1f},{y_inf - (serie[col].iloc[i] / techo) * (y_inf - y_sup):.1f}"
            for i in range(desde, hasta)
        ]
        d = "M" + "L".join(puntos)
        if cerrada:
            d += f"L{x0 + paso * (hasta - 1):.1f},{y_inf}L{x0 + paso * desde:.1f},{y_inf}Z"
        return d

    techo_stock = float(serie["stock"].max()) * 1.12
    techo_venta = float(serie["demanda"].max()) * 1.18
    paneles = []
    for col, titulo, y_sup, y_inf, techo, gris in (
        ("stock", "Unidades en el almacén", 34, 140, techo_stock, True),
        ("demanda", "Unidades vendidas por semana", 196, 296, techo_venta, False),
    ):
        clase = "g-linea gris" if gris else "g-linea"
        masa = (
            f'<path class="g-masa" d="{ruta(col, 0, len(serie), y_sup, y_inf, techo, True)}"/>'
            if gris else ""
        )
        paneles.append(
            f'<text class="g-tit" x="{x0}" y="{y_sup - 12:.0f}">{titulo}</text>'
            f'{masa}'
            f'<line class="g-eje" x1="{x0}" y1="{y_inf}" x2="{x1}" y2="{y_inf}"/>'
            f'<path class="{clase}" d="{ruta(col, 0, n_obs, y_sup, y_inf, techo)}"/>'
            f'<path class="{clase} prev" d="{ruta(col, n_obs - 1, len(serie), y_sup, y_inf, techo)}"/>'
            f'<line class="g-corte" x1="{x_corte:.1f}" y1="{y_sup - 6}" '
            f'x2="{x_corte:.1f}" y2="{y_inf}"/>'
            f'<text class="g-val" x="{x1}" y="{y_sup - 12:.0f}" text-anchor="end">'
            f'{num(serie[col].iloc[n_obs - 1])} hoy</text>'
        )

    # Una marca de mes cada cuatro semanas, para no apelmazar el eje.
    marcas = "".join(
        f'<text class="g-sem" x="{x0 + paso * i:.1f}" y="312" text-anchor="middle">'
        f'{serie["inicio_semana"].iloc[i].day} {MESES_CORTOS[serie["inicio_semana"].iloc[i].month - 1]}</text>'
        for i in range(0, len(serie), 5)
    )
    sombra = (f'<rect class="g-area-prev" x="{x_corte:.1f}" y="28" '
              f'width="{x1 - x_corte:.1f}" height="268" rx="4"/>')

    cae = serie["stock"].iloc[-1] - serie["stock"].iloc[n_obs - 1]
    return f"""<figure style="margin:0"><div class="figura">
<svg viewBox="0 0 1120 322" role="img" aria-label="Stock semanal en el almacén y unidades
vendidas por semana durante el último año, con las {len(serie) - n_obs} semanas siguientes
previstas por el modelo.">
{sombra}{"".join(paneles)}{marcas}</svg></div>
<p class="pie">Línea continua, dato observado. Discontinua, previsión del modelo.
El stock de la derecha es el que quedaría <strong>sin reponer nada</strong>: en
{len(serie) - n_obs} semanas bajaría {num(abs(cae))} unidades, de {num(serie["stock"].iloc[n_obs - 1])}
a {num(serie["stock"].iloc[-1])}. Esa es la forma del problema: la venta sube y baja con la
temporada y el almacén apenas se mueve.</p>
</figure>"""


def diagrama_actual() -> str:
    """Lo que está desplegado ahora mismo, con sus piezas reales.

    Va antes que el de producción a propósito: primero lo que se puede abrir y
    tocar, después lo que sería en la empresa. Así la comparación se hace sobre
    algo que existe, no entre dos dibujos.
    """
    cajas = [
        ("EL CÓDIGO", "GitHub", "código + Excel del caso", "bx-su", "d-gr"),
        ("LA IMAGEN", "Cloud Build", "construye el contenedor", "bx-ac", "d-ac"),
        ("EL SERVICIO", "Cloud Run", "web + el cálculo", "bx-ac", "d-ac"),
        ("EL ENTREGABLE", "Google Sheets", "propuesta + histórico", "bx-ac", "d-ac"),
        ("QUIEN DECIDE", "Compras", "aprueba o ajusta", "bx-ok", "d-ok"),
    ]
    # 5 cajas de 184 + 4 huecos de 40 = 1080, con 20 px de margen a cada lado del
    # lienzo de 1120. Antes sumaban 1125 y la última caja se salía por la derecha.
    x0, ancho, hueco = 20, 184, 40
    xs = [x0 + i * (ancho + hueco) for i in range(5)]
    partes = [_FLECHAS]

    xr = xs[2]
    partes.append(
        f'<rect class="bx-su" x="{xr}" y="10" width="{ancho}" height="42" rx="9"/>'
        f'<text class="d-n d-gr" x="{xr + ancho / 2}" y="28" text-anchor="middle">EL RELOJ</text>'
        f'<text class="d-s" x="{xr + ancho / 2}" y="44" text-anchor="middle">Cloud Scheduler · 00:00</text>'
        f'<line class="d-ln" x1="{xr + ancho / 2}" y1="52" x2="{xr + ancho / 2}" y2="76" marker-end="url(#f)"/>'
    )
    for (ojo, titulo, sub, clase_bx, clase_n), x in zip(cajas, xs):
        cx = x + ancho / 2
        partes.append(
            f'<rect class="{clase_bx}" x="{x}" y="82" width="{ancho}" height="94" rx="11"/>'
            f'<text class="d-n {clase_n}" x="{cx}" y="105" text-anchor="middle">{ojo}</text>'
            f'<text class="d-t" x="{cx}" y="130" text-anchor="middle">{titulo}</text>'
            f'<text class="d-s" x="{cx}" y="152" text-anchor="middle">{sub}</text>'
        )
    for x, etiqueta in zip(xs[:-1], ["gcloud run deploy", "despliega", "escribe", "revisa"]):
        partes.append(
            f'<line class="d-ln" x1="{x + ancho}" y1="130" x2="{x + ancho + hueco - 6}" y2="130" '
            f'marker-end="url(#f)"/>'
            f'<text class="g-sem" x="{x + ancho + hueco / 2 - 3}" y="121" text-anchor="middle">{etiqueta}</text>'
        )
    partes.append(
        '<rect class="bx-warn-l" x="20" y="196" width="1080" height="44" rx="11"/>'
        '<text class="d-n d-gr" x="42" y="215">SI FALLA</text>'
        '<text class="d-s" x="42" y="232">Cloud Scheduler reintenta 3 veces con espera creciente · '
        'si el Sheet falla, la propuesta sigue viva en la web y descargable en Excel</text>'
    )
    return f"""<figure style="margin:0"><div class="figura">
<svg viewBox="0 0 1120 252" role="img" aria-label="Lo desplegado hoy: el código vive en
GitHub, Cloud Build construye la imagen, Cloud Run sirve la web y hace el cálculo cuando
Cloud Scheduler lo dispara a las 00:00, y el resultado va a Google Sheets donde Compras
aprueba.">{"".join(partes)}</svg></div>
<p class="pie">Esto es lo que puedes abrir ahora mismo. El Excel del caso viaja dentro del
contenedor, que es la única diferencia de fondo con el esquema de abajo.</p></figure>"""


def diagrama_produccion() -> str:
    """La arquitectura de producción, con el stack que se usaría de verdad.

    Responde en el dibujo a las cuatro preguntas del enunciado: de dónde salen los
    datos (izquierda), cada cuánto se ejecuta (el reloj), dónde interviene una
    persona (la caja final, marcada aparte) y qué pasa si falla (el carril de
    abajo).
    """
    cajas = [
        ("DE DÓNDE SALEN", "ERP · tienda · almacén", "ventas, stock y pedidos", "bx-su", "d-gr"),
        ("INGESTA", "Fivetran", "copia cada noche", "bx-ac", "d-ac"),
        ("DATOS", "BigQuery", "crudo → limpio (dbt)", "bx-ac", "d-ac"),
        ("EL CÁLCULO", "Cloud Run Job", "previsión + reposición", "bx-ac", "d-ac"),
        ("PUBLICACIÓN", "Cloud Run + Sheets", "propuesta y web", "bx-ac", "d-ac"),
        ("QUIEN DECIDE", "Compras", "aprueba o ajusta", "bx-ok", "d-ok"),
    ]
    x0, ancho, hueco = 10, 160, 28
    xs = [x0 + i * (ancho + hueco) for i in range(6)]

    partes = [_FLECHAS]
    # El reloj, encima del cálculo: es lo que contesta a "cada cuánto".
    xr = xs[3]
    partes.append(
        f'<rect class="bx-su" x="{xr}" y="10" width="{ancho}" height="42" rx="9"/>'
        f'<text class="d-n d-gr" x="{xr + ancho / 2}" y="28" text-anchor="middle">CADA CUÁNTO</text>'
        f'<text class="d-s" x="{xr + ancho / 2}" y="44" text-anchor="middle">Cloud Scheduler · lunes 06:00</text>'
        f'<line class="d-ln" x1="{xr + ancho / 2}" y1="52" x2="{xr + ancho / 2}" y2="76" marker-end="url(#f)"/>'
    )
    for (ojo, titulo, sub, clase_bx, clase_n), x in zip(cajas, xs):
        cx = x + ancho / 2
        partes.append(
            f'<rect class="{clase_bx}" x="{x}" y="82" width="{ancho}" height="96" rx="11"/>'
            f'<text class="d-n {clase_n}" x="{cx}" y="105" text-anchor="middle">{ojo}</text>'
            f'<text class="d-t" x="{cx}" y="130" text-anchor="middle">{titulo}</text>'
            f'<text class="d-s" x="{cx}" y="152" text-anchor="middle">{sub}</text>'
        )
    etiquetas = ["cada noche", "limpieza", "lee", "escribe", "revisa"]
    for x, etiqueta in zip(xs[:-1], etiquetas):
        partes.append(
            f'<line class="d-ln" x1="{x + ancho}" y1="130" x2="{x + ancho + hueco - 5}" y2="130" '
            f'marker-end="url(#f)"/>'
            f'<text class="g-sem" x="{x + ancho + hueco / 2 - 2}" y="122" text-anchor="middle">{etiqueta}</text>'
        )

    # La vuelta: lo aprobado se convierte en pedido y reentra por la ingesta.
    partes.append(
        f'<polyline class="d-lp" points="{xs[5] + ancho / 2},178 {xs[5] + ancho / 2},202 '
        f'{xs[0] + ancho / 2},202 {xs[0] + ancho / 2},182" marker-end="url(#fp)"/>'
        f'<text class="d-s d-acento" x="560" y="197" text-anchor="middle">'
        f'el pedido aprobado vuelve al ERP</text>'
    )
    # El carril de fallos.
    partes.append(
        '<rect class="bx-warn-l" x="10" y="226" width="1100" height="62" rx="11"/>'
        '<text class="d-n d-gr" x="30" y="247">QUÉ PASA SI FALLA</text>'
        '<text class="d-s" x="30" y="265">Falta un dato → no se calcula y avisa  ·  '
        'El cálculo revienta → 3 reintentos y alerta a Slack  ·  '
        'Cifra fuera de rango → se publica marcada «revisar»</text>'
        '<text class="d-s" x="30" y="280">Falla el Sheet → sigue en la web y en Excel  ·  '
        'En todos los casos se mantiene visible la propuesta anterior con su fecha</text>'
    )

    # Ciclo de vida del código: lo que pasa cuando se cambia el cálculo. Va en un
    # carril aparte porque es otro ritmo —se despliega cuando hay cambios, no cada
    # lunes— y confundirlo con el flujo del dato es un error habitual al dibujar.
    cicd = [("GitHub", "alguien cambia el código"),
            ("GitHub Actions", "pasa los tests y construye"),
            ("Cloud Run", "versión nueva, sin parar nada")]
    partes.append(
        '<rect class="bx-su" x="20" y="308" width="1080" height="78" rx="11"/>'
        '<text class="d-n d-gr" x="42" y="330">CUANDO CAMBIA EL CÓDIGO · CI/CD</text>'
    )
    for i, (titulo, sub) in enumerate(cicd):
        bx = 42 + i * 350
        partes.append(
            f'<text class="d-t" x="{bx}" y="356">{titulo}</text>'
            f'<text class="d-s" x="{bx}" y="374">{sub}</text>'
        )
        if i < 2:
            partes.append(
                f'<line class="d-ln" x1="{bx + 240}" y1="352" x2="{bx + 320}" y2="352" '
                f'marker-end="url(#f)"/>'
            )

    return f"""<figure style="margin:0"><div class="figura">
<svg viewBox="0 0 1120 400" role="img" aria-label="Arquitectura en producción: ERP,
tienda y almacén alimentan cada noche una ingesta que carga BigQuery; Cloud Scheduler
arranca los lunes un Cloud Run Job que calcula la propuesta; se publica en Cloud Run y
Google Sheets, y Compras aprueba. Lo aprobado vuelve al ERP. Abajo, el carril de
fallos y el carril de despliegue continuo.">{"".join(partes)}</svg></div>
<p class="pie">Verde, el único paso que no hace la máquina. Abajo, las dos cosas que ocurren
fuera del flujo semanal: qué pasa si algo falla, y cómo entra una versión nueva del código
sin parar el proceso.</p>
</figure>"""


# --- página 1 · propuesta --------------------------------------------------

def pagina_propuesta(r: Dict[str, pd.DataFrame], ejecutado: dt.datetime) -> str:
    p, res = r["propuesta"], r["resumen"].set_index("concepto")["valor"]
    nec = r["necesidad"]
    demanda = nec["demanda_horizonte"].sum()
    disponible = nec["stock_disponible"].sum() + nec["en_transito"].sum()

    kpis = "".join([
        kpi("A reponer", num(res["SKUs a reponer"]), f"de {num(res['SKUs en catálogo'])} SKUs"),
        kpi("Unidades", num(res["Unidades propuestas"])),
        kpi("Coste", eur(res["Coste del pedido (€)"])),
        kpi("Venta en riesgo", eur(res["Venta en riesgo (€)"]), "si no se repone"),
        kpi("Rotura inminente", num(res["SKUs en prioridad crítica"]), "se agotan antes de que llegue"),
    ])

    filas = "".join(
        f'<tr data-pri="{esc(f["prioridad"] or "normal")}" data-prov="{esc(f["proveedor_habitual"])}">'
        f'<td><span class="pri {esc(f["prioridad"] or "normal")}">{esc(f["prioridad"] or "normal")}</span></td>'
        f'<td><strong>{esc(f["modelo_nombre"])}</strong> · {esc(f["talla"])}<br>'
        f'<span style="color:var(--tinta-3);font-size:.78rem">{esc(f["sku"])}</span></td>'
        f'<td>{esc(f["proveedor_habitual"])}</td>'
        f'<td class="num">{num(f["stock_disponible"])}</td>'
        f'<td class="num">{num(f["en_transito"])}</td>'
        f'<td class="num"><strong>{num(f["unidades_propuestas"])}</strong></td>'
        f'<td class="num">{eur(f["coste_pedido"])}</td>'
        f'<td class="motivo">{esc(f["motivo"])}</td></tr>'
        for _, f in p.iterrows()
    )
    provs = "".join(f'<option value="{esc(x)}">{esc(x)}</option>'
                    for x in sorted(p["proveedor_habitual"].unique()))

    cuerpo = f"""
{cabecera("Generada automáticamente", "Qué reponer",
          f"Calculado el {fecha_larga(ejecutado)} a las {ejecutado:%H:%M}.")}
<div class="kpis">{kpis}</div>
<div class="aviso" style="margin-top:20px"><strong>Lo primero que hay que mirar:</strong>
hay {num(disponible)} uds entre almacén y camino para una demanda de {num(demanda)} uds en
{HORIZONTE} semanas, unas {num(disponible / demanda, 1)} veces lo necesario. La propuesta sale
pequeña porque el problema no es comprar poco: es que el stock está en los SKUs equivocados.</div>
<div class="barra">
  <button class="btn primario" id="btn-sheet">Exportar a Google Sheets</button>
  <a class="btn" href="/descargar/excel">Descargar Excel</a>
  <input type="search" id="buscar" placeholder="Buscar modelo o SKU…">
  <select id="fpri"><option value="">Toda prioridad</option>
    <option value="critica">Rotura inminente</option><option value="alta">Prioridad alta</option></select>
  <select id="fprov"><option value="">Todos los proveedores</option>{provs}</select>
  <span id="aviso-exporta"></span>
</div>
<div class="tabla-caja"><table id="tabla"><thead><tr>
  <th>Prioridad</th><th>Modelo</th><th>Proveedor</th>
  <th style="text-align:right">Stock</th><th style="text-align:right">En camino</th>
  <th style="text-align:right">Pedir</th><th style="text-align:right">Coste</th><th>Por qué</th>
</tr></thead><tbody>{filas}</tbody></table></div>
<script>
const t=document.getElementById('tabla'),b=document.getElementById('buscar'),
      a=document.getElementById('fpri'),c=document.getElementById('fprov');
function filtrar(){{const q=b.value.toLowerCase();
  for(const f of t.tBodies[0].rows){{
    f.hidden=(q&&!f.innerText.toLowerCase().includes(q))||(a.value&&f.dataset.pri!==a.value)
      ||(c.value&&f.dataset.prov!==c.value);}}}}
[b,a,c].forEach(e=>e.addEventListener('input',filtrar));
const bt=document.getElementById('btn-sheet'),av=document.getElementById('aviso-exporta');
bt.addEventListener('click',async()=>{{bt.disabled=true;av.textContent='Escribiendo…';
  try{{const r=await fetch('/exportar/sheet',{{method:'POST'}});const d=await r.json();
    av.innerHTML=d.ok?'Listo · <a href="'+d.url+'" target="_blank" rel="noopener">abrir el Sheet</a>'
      :'No se pudo: '+d.error;}}catch(e){{av.textContent='No se pudo: '+e.message;}}
  bt.disabled=false;}});
</script>"""
    return layout("Propuesta", "/", cuerpo)


# --- página 2 · cómo funciona ---------------------------------------------

def pagina_metodo(r: Dict[str, pd.DataFrame]) -> str:
    comp = r["comparativa_metodos"]
    nombres = {"modelo": "Modelo entrenado", "plano": "Media móvil",
               "estacional": "Media móvil estacional", "ano_anterior": "Año anterior"}
    filas = "".join(
        f'<tr><td>{"<strong>" if f["elegido"] else ""}{esc(nombres.get(f["metodo"], f["metodo"]))}'
        f'{" ← el que usamos</strong>" if f["elegido"] else ""}</td>'
        f'<td class="num">{num(f["mae"], 2)}</td>'
        f'<td class="num">{num(f["sesgo_abs_pct"], 1)} %</td></tr>'
        for _, f in comp.iterrows()
    )
    # Prophet se midió con este mismo backtesting pero no se ejecuta en cada
    # visita: añadiría ~100 MB de dependencias y 13 s por carga para quedar quinto.
    filas += ('<tr><td>Prophet <span style="color:var(--tinta-3)">· probado y '
              'descartado</span></td><td class="num">14,69</td>'
              '<td class="num">74,4 %</td></tr>')

    # Un SKU bien cubierto: demanda alta pero stock y mercancía en camino de sobra.
    nec = r["necesidad"]
    cubiertos = nec[(nec["stock_disponible"] > 0) & (nec["en_transito"] > 0)
                    & (nec["unidades_propuestas"] == 0)]
    cub = cubiertos.nlargest(1, "demanda_horizonte").iloc[0]

    cuerpo = f"""
{cabecera("Método", "Cómo funciona", "El proceso entero, de las ventas al pedido.")}
{diagrama_calculo(r)}

<section class="bloque">
<h2>Un año de venta y de stock, y lo que viene</h2>
{grafico_historico(r["historico_prevision"])}
</section>

<section class="bloque">
<h2>Cómo se predice la demanda</h2>
<p class="nota">Un modelo entrenado con las 95 semanas de histórico. Mira cuatro cosas de
cada categoría —<strong>cómo viene vendiendo</strong>, <strong>qué hizo en esta misma época
el año pasado</strong>, <strong>si está subiendo o bajando</strong> y <strong>en qué momento
de su vida están sus drops</strong>— y predice cuántas unidades venderá
<strong>en cada una de las {HORIZONTE} semanas siguientes</strong>, una por una.</p>
<p class="nota" style="margin-top:10px">Después ese total se reparte entre los modelos y las
tallas de la categoría. Se hace así porque un SKU vende 0,79 uds por semana y está a cero el
62 % de las semanas: a ese nivel la demanda es ruido. Una categoría vende 21 uds por semana y
solo está a cero el 6 %. <strong>Se predice donde hay señal y se reparte después.</strong></p>
</section>

<section class="bloque">
<h2>La previsión sigue la estacionalidad</h2>
{grafico_curva(r["curva_semanal"])}
<p class="nota" style="margin-top:14px">Diciembre tira y enero se desploma, y el modelo lo ha
visto en el histórico. Un método que proyectase el ritmo actual compraría para un enero que no
va a llegar.</p>
</section>

<section class="bloque">
<h2>Por qué este modelo</h2>
<ol class="razones">
  <li><b>Gana el backtesting.</b> 12 cortes del histórico, entrenando en cada uno solo con lo
  anterior. Es el que menos se equivoca de los cinco probados.</li>
  <li><b>Entrena las diez categorías juntas.</b> Estima la estacionalidad con diez veces más
  datos que un modelo por serie.</li>
  <li><b>Le bastan 95 semanas.</b> Un modelo con más grados de libertad necesita más ciclos
  anuales y se desboca con los que hay.</li>
  <li><b>Cabe en el contenedor.</b> scikit-learn ya viene; Prophet añadiría 100 MB y 13 s a
  cada ejecución.</li>
  <li><b>Es determinista.</b> La misma entrada da la misma propuesta, y Compras puede auditar
  línea a línea de dónde sale cada unidad.</li>
</ol>
<p class="nota" style="margin-top:16px">Es un <strong>gradient boosting sobre árboles</strong>
(<code>HistGradientBoostingRegressor</code>). La tabla es el backtesting completo: error medio
por SKU y desvío sobre el total.</p>
<div class="tabla-caja" style="margin-top:12px;max-height:none"><table style="min-width:480px">
<thead><tr><th>Método</th><th style="text-align:right">Error por SKU</th>
<th style="text-align:right">Desvío del total</th></tr></thead><tbody>{filas}</tbody></table></div>
<p class="nota" style="margin-top:12px"><strong>Sobre Prophet:</strong> se probó en cinco
configuraciones. Pierde, y mejora cuanto más se le ata la tendencia. Ésa es la firma de un
modelo con demasiados grados de libertad para 95 semanas de datos, menos de dos ciclos anuales
con los que estimar una estacionalidad anual.</p>
</section>

<section class="bloque">
<h2>Y una línea donde no se pide nada</h2>
<p class="nota">La propuesta es corta porque casi todo el catálogo está cubierto de sobra.</p>
<div class="calculo">{esc(cub['modelo_nombre'])} · talla {esc(cub['talla'])}

  demanda prevista a {HORIZONTE} semanas  = {num(cub['demanda_horizonte'])} uds
  − en almacén                    = {num(cub['stock_disponible'])}
  − ya vienen de camino           = {num(cub['en_transito'])}
  ──────────────────────────────────────
  = <span style="color:var(--tinta-3)">no se pide nada</span>   ·   sobran {num(cub['stock_disponible'] + cub['en_transito'] - cub['demanda_horizonte'])} uds</div>
<p class="nota" style="margin-top:12px">La prioridad la marca <em>cuándo rompe</em>. Si el stock
no aguanta las {config.LEAD_TIME_SEMANAS} semanas que tarda el proveedor, la rotura ya está
comprada.</p>
</section>

<section class="bloque">
<h2>Lo que no hace</h2>
<div class="tarjetas">
  {tarjeta("Límite", "Productos nuevos",
           "<p>Un modelo sin lanzar no tiene ventas de las que aprender, así que sale con demanda cero.</p>")}
  {tarjeta("Límite", "Rebajas dentro del horizonte",
           "<p>Las últimas semanas caen en rebajas. Comprar a coste completo para vender con "
           "descuento sale caro. El horizonte debería acotarse al fin de temporada.</p>")}
</div>
</section>"""
    return layout("Cómo funciona", "/metodo", cuerpo)


# --- página 3 · producción -------------------------------------------------

def pagina_produccion() -> str:
    cuerpo = f"""
{cabecera("Esquema", "En producción",
          "Primero lo que está funcionando hoy, después lo que sería dentro de la empresa.")}

<section class="bloque" style="margin-top:0">
<h2>Lo que está desplegado ahora</h2>
{diagrama_actual()}
</section>

<section class="bloque">
<h2>Lo que sería en producción</h2>
{diagrama_produccion()}
</section>

<section class="bloque">
<div class="tarjetas">
  {tarjeta("Pregunta 1", "De dónde salen los datos",
           "<ul><li><strong>Ventas</strong> · ERP y tienda online</li>"
           "<li><strong>Catálogo</strong> · gestor de producto</li>"
           "<li><strong>Stock</strong> · sistema de almacén</li>"
           "<li><strong>Compras</strong> · pedidos del ERP</li></ul>"
           "<p style='margin-top:8px'>Se copian cada noche a BigQuery, donde se les aplican "
           "las reglas de negocio una sola vez para toda la empresa.</p>")}
  {tarjeta("Pregunta 2", "Cada cuánto se ejecuta",
           "<p><strong>Lunes a las 06:00.</strong> El pedido a proveedor es semanal y Compras "
           "lo quiere encima de la mesa al llegar.</p>"
           "<p style='margin-top:8px'>Más una pasada diaria que no propone pedidos: solo "
           "vigila roturas y avisa.</p>")}
  {tarjeta("Pregunta 3", "Dónde interviene una persona",
           "<ul><li><strong>Compras</strong> aprueba o ajusta cada línea, cada semana. "
           "Sin aprobación no hay pedido</li>"
           "<li><strong>Planificación</strong> revisa plazo y cobertura cada trimestre</li>"
           "<li><strong>Datos</strong> atiende la alerta cuando algo falla</li></ul>")}
  {tarjeta("Pregunta 4", "Qué pasa si falla",
           "<ul><li>Falta un dato → no se calcula y avisa</li>"
           "<li>El cálculo revienta → 3 reintentos y alerta</li>"
           "<li>Cifra fuera de rango → se publica marcada</li>"
           "<li>Falla el Sheet → sigue en web y Excel</li></ul>"
           "<p style='margin-top:8px'>Nunca se publica una propuesta a medias.</p>")}
</div>
<div class="aviso" style="margin-top:18px"><strong>El sistema nunca pide por su cuenta.</strong>
Lo que Compras cambia se guarda y se compara con lo propuesto. Es la mejor señal para afinar
el modelo.</div>
</section>

<section class="bloque">
<h2>Si esto crece</h2>
<p class="nota"><strong>50.000 SKUs</strong> · el cálculo se mueve a BigQuery y el Job se parte
por sección.<br>
<strong>Varios almacenes</strong> · la rotura pasa a ser local, y aparece una decisión nueva:
mover stock entre almacenes antes que pedir.<br>
<strong>Más proveedores</strong> · plazo por proveedor medido de su histórico, en lugar de
{config.LEAD_TIME_SEMANAS} semanas para todos.</p>
</section>"""
    return layout("En producción", "/produccion", cuerpo)


# --- página 4 · decisiones -------------------------------------------------

def pagina_decisiones() -> str:
    """Las seis decisiones sin las que no se entienden las cifras de la propuesta.

    Se marcan en `docs/decisiones.md` con el campo `Clave`. El resto del log sigue
    ahí con su contexto y su evidencia; esta página no es el historial.
    """
    ds = [d for d in mod_decisiones.del_reto("2") if d.campos.get("clave")]
    bloques = "".join(
        f'<details><summary>{esc(d.titulo)}<span class="fecha">{esc(d.fecha)}</span></summary>'
        f'<div class="cuerpo">'
        + (f'<div class="campo"><span class="et">Qué cambia en las cifras</span>'
           f'<span class="tx">{esc(d.campos["impacto"])}</span></div>'
           if d.campos.get("impacto") else "")
        + '</div></details>'
        for d in ds
    )
    cuerpo = f"""
{cabecera("Trazabilidad", "Decisiones",
          f"Las {len(ds)} que cambian las cifras. Pulsa cada una para ver cuál.")}
<div class="aviso">Se genera desde <code>docs/decisiones.md</code>, donde está el log completo
con su contexto y su evidencia.</div>
<div style="margin-top:20px">{bloques}</div>"""
    return layout("Decisiones", "/decisiones", cuerpo)


# --- página 5 · histórico --------------------------------------------------

def pagina_historico(ejecuciones: List[dict]) -> str:
    if ejecuciones:
        filas = "".join(
            f'<tr><td>{esc(e["momento"])}</td>'
            f'<td><span class="pri {"alta" if e["disparo"] == "reloj" else "normal"}">'
            f'{esc(e["disparo"])}</span></td>'
            f'<td class="num">{num(e["skus"])}</td><td class="num">{num(e["unidades"])}</td>'
            f'<td class="num">{num(e["segundos"], 1)} s</td><td>{esc(e["resultado"])}</td></tr>'
            for e in reversed(ejecuciones)
        )
        tabla = f"""<div class="tabla-caja" style="max-height:none">
<table style="min-width:620px"><thead><tr><th>Momento</th><th>Disparo</th>
<th style="text-align:right">SKUs</th><th style="text-align:right">Unidades</th>
<th style="text-align:right">Duración</th><th>Resultado</th></tr></thead>
<tbody>{filas}</tbody></table></div>"""
    else:
        tabla = '<div class="aviso">Todavía no hay ejecuciones. La primera entra a las 00:00.</div>'

    cuerpo = f"""
{cabecera("Automatización", f"{len(ejecuciones)} ejecuciones",
          "Las marcadas como reloj no las ha lanzado nadie.")}
{tabla}
<div class="aviso" style="margin-top:20px"><strong>Por qué se repiten las cifras:</strong>
los datos del caso están congelados, así que cada ejecución parte del mismo punto y llega al
mismo resultado. Este historial enseña el mecanismo.</div>"""
    return layout("Ejecuciones", "/historico", cuerpo)
