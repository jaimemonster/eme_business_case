"""Generación del informe HTML del Reto 1.

Responsabilidad: convertir las tablas de métricas en un informe HTML
autocontenido (Plotly embebido + sistema de diseño de `design.py`) pensado para
que la dirección lo abra cada lunes. No calcula KPIs: solo los presenta.

El fichero resultante se abre con doble clic: no necesita servidor, ni conexión,
ni nada instalado.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, Iterable, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io
import plotly.offline

from . import config, design
from .design import TOKENS, kpi, plantilla_grafico

C = TOKENS["claro"]

# strftime depende del locale del sistema, que no podemos dar por supuesto.
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def fecha_larga(f) -> str:
    """4 de noviembre de 2025, sin depender del locale."""
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"

_contador = {"n": 0}


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------

def num(valor: float, dec: int = 0) -> str:
    """Formatea un número al estilo español: miles con punto, decimales con coma."""
    if pd.isna(valor):
        return "—"
    texto = f"{valor:,.{dec}f}"
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")


def eur(valor: float, dec: int = 0) -> str:
    return f"{num(valor, dec)} €"


def pct(valor: float, dec: int = 1) -> str:
    return f"{num(valor, dec)} %"


def delta(valor: float, dec: int = 1) -> str:
    """Variación con flecha, signo y color. La flecha evita depender del color."""
    if pd.isna(valor):
        return "—"
    clase = "pos" if valor >= 0 else "neg"
    flecha = "▲" if valor >= 0 else "▼"
    return f'<span class="{clase}">{flecha} {num(abs(valor), dec)} %</span>'


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def grafico(fig: go.Figure, div_id: str | None = None) -> str:
    """Inserta una figura. Plotly.js se embebe una sola vez, en el primero."""
    _contador["n"] += 1
    return plotly.io.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
    )


def selector(div_id: str, opciones: Sequence[str]) -> str:
    """Control segmentado que alterna qué métrica muestra un gráfico."""
    botones = "".join(
        f'<button class="{"activo" if i == 0 else ""}" '
        f"onclick=\"cambiarMetrica('{div_id}', {i}, this)\">{texto}</button>"
        for i, texto in enumerate(opciones)
    )
    return f'<div class="selector">{botones}</div>'


def leyenda(*entradas) -> str:
    """Leyenda propia, con más control tipográfico que la de Plotly.

    Una entrada puede llevar dos colores: entonces la muestra se parte en dos,
    que es lo honesto para una serie que cambia de color según el signo.
    """
    partes = []
    for texto, color in entradas:
        fondo = (
            f"linear-gradient(90deg, {color[0]} 50%, {color[1]} 50%)"
            if isinstance(color, tuple) else color
        )
        partes.append(f'<span><i style="background:{fondo}"></i>{texto}</span>')
    return f'<div class="leyenda">{"".join(partes)}</div>'


def registrar(div_id: str, grupos: Sequence[int], ejes: Sequence[dict]) -> str:
    """Script que asocia cada serie a su métrica y el formato de eje de cada una."""
    import json

    return (
        f"<script>registrarMetricas('{div_id}', {json.dumps(list(grupos))}, "
        f"{json.dumps(list(ejes))});</script>"
    )


def tabla_html(
    df: pd.DataFrame,
    columnas: Sequence[tuple[str, str, str]],
    destacar: Iterable[int] = (),
) -> str:
    """Renderiza un DataFrame como tabla HTML.

    `columnas` es una lista de (clave, encabezado, formato), donde el formato es
    'texto', 'num', 'eur', 'pct', 'delta' o 'crudo' (HTML ya construido).
    """
    cabecera = "".join(
        f'<th class="{"num" if f != "texto" else ""}">{titulo}</th>' for _, titulo, f in columnas
    )
    filas = []
    for i, (_, fila) in enumerate(df.iterrows()):
        celdas = []
        for clave, _, formato in columnas:
            valor = fila.get(clave)
            if formato == "texto":
                celdas.append(f"<td>{valor}</td>")
            else:
                render = {
                    "num": lambda v: num(v),
                    "num1": lambda v: num(v, 1),
                    "eur": lambda v: eur(v),
                    "eur2": lambda v: eur(v, 2),
                    "pct": lambda v: pct(v),
                    "delta": delta,
                    "crudo": str,
                }[formato]
                celdas.append(f'<td class="num">{render(valor)}</td>')
        clase = ' class="destacar"' if i in destacar else ""
        filas.append(f"<tr{clase}>{''.join(celdas)}</tr>")
    return (
        '<div class="tabla-scroll"><table><thead><tr>'
        f"{cabecera}</tr></thead><tbody>{''.join(filas)}</tbody></table></div>"
    )


def seccion(ruta: str, titulo: str, pid: str, conclusion: str, cuerpo: str) -> Dict[str, str]:
    """Una página del informe. Siempre empieza por la conclusión, no por el gráfico.

    Devuelve los metadatos que `construir_informe` necesita para montar el panel
    y su entrada en el menú lateral.
    """
    return {
        "id": pid,
        "ruta": ruta,
        "titulo": titulo,
        "html": (f'<p class="conclusion">{conclusion}</p>{cuerpo}' if conclusion.strip() else cuerpo),
    }


def bloque_decision_plegable(
    titulo: str,
    que_pasaba: str,
    ejemplo: str,
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
    bloque_ejemplo = f'<dt>Ejemplo real</dt><dd>{ejemplo}</dd>' if ejemplo else ""
    return f"""
<details>
  <summary>{titulo}</summary>
  <div class="detalle"><dl>
    <dt>Qué pasaba</dt><dd>{que_pasaba}</dd>
    {bloque_ejemplo}
    <dt>Qué decidimos y por qué</dt><dd>{decision}</dd>
    <dt>Impacto</dt><dd>{impacto}</dd>
  </dl></div>
</details>"""


def termino(nombre: str, definicion: str, formula: str = "", ejemplo: str = "") -> str:
    """Una entrada del glosario: qué es, cómo se calcula y un ejemplo real."""
    partes = [f"<h3>{nombre}</h3>", f"<p>{definicion}</p>"]
    if formula:
        partes.append(f'<div class="formula">{formula}</div>')
    if ejemplo:
        partes.append(f'<p class="nota">{ejemplo}</p>')
    return f'<div class="termino">{"".join(partes)}</div>'


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def _barras_horizontales(
    etiquetas: Sequence[str],
    valores: Sequence[float],
    texto: Sequence[str],
    colores: Sequence[str] | str = None,
    altura: int = None,
) -> go.Figure:
    """Barras horizontales con el valor etiquetado al final de cada barra.

    Etiquetar fuera de la barra evita el recorte en las barras cortas.
    """
    colores = colores if colores is not None else C["acento"]
    fig = go.Figure(
        go.Bar(
            x=list(valores),
            y=list(etiquetas),
            orientation="h",
            marker=dict(color=colores, line=dict(width=0)),
            text=list(texto),
            textposition="outside",
            textfont=dict(size=12, color=C["tinta_2"]),
            hovertemplate="%{y}: %{text}<extra></extra>",
            width=0.62,
        )
    )
    alto = altura or max(200, 34 * len(etiquetas) + 40)
    plantilla_grafico(fig, altura=alto)
    # Reservar espacio a la derecha para la etiqueta del valor: sin margen, la
    # barra más larga se come su propio texto.
    # El hueco depende de lo larga que sea la etiqueta: "16.248 € · 47 %" ocupa
    # bastante más que "81 %".
    maximo = max(valores) if len(valores) else 1
    holgura = 1.30 + 0.022 * max((len(t) for t in texto), default=4)
    fig.update_yaxes(autorange="reversed", showgrid=False, ticklabelstandoff=10)
    fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, maximo * holgura])
    fig.update_layout(margin=dict(l=0, r=12, t=4, b=4), bargap=0.38)
    return fig


METRICAS_EVOLUCION = [
    ("unidades", "Unidades", "", " uds"),
    ("facturacion_neta", "Facturación neta", "", " €"),
    ("margen", "Margen bruto", "", " €"),
]


def grafico_evolucion(df: pd.DataFrame, div_id: str) -> tuple[str, list[int], list[dict]]:
    """Evolución semanal frente a la misma semana del año anterior.

    Dos paneles con el mismo eje de tiempo: arriba las dos series en su unidad
    (euros o unidades), abajo la variación interanual en porcentaje. Van
    separados a propósito: meter un porcentaje y unos euros en el mismo eje
    obligaría a un segundo eje vertical, y la alineación entre dos escalas es
    arbitraria, así que inventa correlaciones que no están en el dato.

    Dibuja las tres métricas y deja visible solo la primera: el selector alterna
    la visibilidad, que es instantáneo y no recalcula nada.

    El año anterior va en gris de contexto y el actual en el color de acento. Es
    el patrón de énfasis, y la identidad la lleva además la leyenda. En las
    barras, verde y rojo distinguen subida de bajada, siempre con el signo
    delante para que el color no sea el único portador.
    """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.68, 0.32], vertical_spacing=0.08,
    )
    grupos: list[int] = []
    for i, (columna, _, _, sufijo) in enumerate(METRICAS_EVOLUCION):
        fig.add_trace(
            go.Scatter(
                x=df["inicio_semana"], y=df[f"{columna}_ly"],
                mode="lines", name="Año anterior",
                line=dict(color=C["referencia"], width=2, shape="spline", smoothing=0.5),
                hovertemplate="Año anterior: %{y:,.0f}" + sufijo + "<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["inicio_semana"], y=df[columna],
                mode="lines", name="Este año",
                line=dict(color=C["acento"], width=2.5, shape="spline", smoothing=0.5),
                # La variación va en el propio tooltip de la línea: es la
                # pregunta que uno se hace justo al comparar las dos series.
                customdata=df[f"{columna}_yoy"],
                hovertemplate=(
                    "Este año: %{y:,.0f}" + sufijo
                    + "<br>Variación interanual: %{customdata:+.1f} %<extra></extra>"
                ),
            ),
            row=1, col=1,
        )
        grupos += [i, i]

    for i, (columna, _, _, _) in enumerate(METRICAS_EVOLUCION):
        yoy = df[f"{columna}_yoy"]
        fig.add_trace(
            go.Bar(
                x=df["inicio_semana"], y=yoy, name="Variación interanual",
                marker=dict(
                    color=[C["positivo"] if v >= 0 else C["negativo"] for v in yoy.fillna(0)],
                    line=dict(width=0),
                ),
                hovertemplate="Variación interanual: %{y:+.1f} %<extra></extra>",
            ),
            row=2, col=1,
        )
        grupos.append(i)

    plantilla_grafico(fig, altura=420)
    fig.update_layout(margin=dict(l=0, r=16, t=12, b=8), hovermode="x unified", bargap=0.45)

    meses = df["inicio_semana"].dt.to_period("M").drop_duplicates()
    marcas = [m.to_timestamp() + pd.Timedelta(hours=6) for m in meses]
    fig.update_xaxes(
        tickmode="array", tickvals=marcas,
        ticktext=[MESES_CORTOS[m.month - 1] for m in marcas],
        hoverformat="Semana del %d/%m/%Y",
        showgrid=False, zeroline=False, showline=False, ticks="",
        tickfont=dict(size=12, color=C["tinta_3"]),
    )
    # El eje de la variación siempre es porcentaje, así que no cambia con el
    # selector; solo cambia el de arriba.
    fig.update_yaxes(ticksuffix=" %", zeroline=True, zerolinecolor=C["linea"],
                     zerolinewidth=1, row=2, col=1)
    ejes = [{"yaxis.ticksuffix": sufijo, "yaxis.tickformat": ",.0f"}
            for _, _, _, sufijo in METRICAS_EVOLUCION]
    return grafico(fig, div_id), grupos, ejes


METRICAS_ESPECIAL = [
    ("uds_completo", "uds_especial", "Unidades", " uds"),
    ("eur_completo", "eur_especial", "Facturación", " €"),
]


def grafico_estacionalidad(df: pd.DataFrame, div_id: str) -> tuple[str, list[int], list[dict]]:
    """Reparto mensual entre precio completo y precio especial.

    Las barras van **apiladas**, no superpuestas: los dos trozos suman el total
    del mes. Es la relación real entre ambos, y evita que se lean como dos
    series independientes, que es justo lo que sugería la versión superpuesta.

    El selector permite leerlo en unidades o en euros, que no cuentan lo mismo:
    una unidad rebajada factura en torno a un 40 % menos.
    """
    fig = go.Figure()
    grupos: list[int] = []
    for i, (col_completo, col_especial, _, sufijo) in enumerate(METRICAS_ESPECIAL):
        total = df[col_completo] + df[col_especial]
        for columna, nombre, color in (
            (col_completo, "A precio completo", C["referencia"]),
            (col_especial, "A precio especial", C["acento"]),
        ):
            fig.add_trace(
                go.Bar(
                    x=df["mes"], y=df[columna], name=nombre,
                    marker=dict(
                        color=color,
                        # Un hueco del color de la tarjeta separa los segmentos:
                        # se distinguen sin necesidad de dibujarles un borde.
                        line=dict(color=C["superficie"], width=2),
                    ),
                    customdata=total,
                    hovertemplate=(
                        nombre + ": %{y:,.0f}" + sufijo
                        + "<br>Total del mes: %{customdata:,.0f}" + sufijo
                        + "<extra></extra>"
                    ),
                )
            )
            grupos.append(i)

    plantilla_grafico(fig, altura=300)
    fig.update_layout(
        barmode="stack", bargap=0.3,
        margin=dict(l=0, r=8, t=12, b=8), hovermode="x unified",
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=[m + pd.Timedelta(hours=6) for m in df["mes"]],
        ticktext=[
            f"{MESES_CORTOS[m.month - 1]}<br>{m.year}" if m.month in (1, 7) else MESES_CORTOS[m.month - 1]
            for m in df["mes"]
        ],
        hoverformat="%m/%Y",
        tickfont=dict(size=10),
    )
    ejes = [{"yaxis.ticksuffix": sufijo, "yaxis.tickformat": ",.0f"}
            for _, _, _, sufijo in METRICAS_ESPECIAL]
    return grafico(fig, div_id), grupos, ejes


def grafico_curva_tallas(df: pd.DataFrame) -> go.Figure:
    """Reparto de la demanda frente al del stock, por talla.

    Dos series: la demanda en gris (contexto) y el stock en el color de acento
    (lo que decidimos nosotros). Es el patrón de énfasis: destacar uno, atenuar
    el resto. Además lleva leyenda y etiquetas directas, así que la identidad no
    depende del color.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Demanda (12 semanas)",
            x=df["talla"],
            y=df["pct_demanda"],
            marker=dict(color=C["referencia"], line=dict(width=0)),
            hovertemplate="Talla %{x}<br>%{y:.1f} % de la demanda<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Stock en almacén",
            x=df["talla"],
            y=df["pct_stock"],
            marker=dict(color=C["acento"], line=dict(width=0)),
            hovertemplate="Talla %{x}<br>%{y:.1f} % del stock<extra></extra>",
        )
    )
    plantilla_grafico(fig, altura=300)
    fig.update_layout(
        barmode="group",
        bargap=0.34,
        bargroupgap=0.08,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0,
            font=dict(size=12, color=C["tinta_2"]),
        ),
        margin=dict(l=0, r=8, t=36, b=8),
    )
    fig.update_yaxes(ticksuffix=" %")
    return fig


def grafico_drops(df: pd.DataFrame) -> go.Figure:
    """Sell-through por drop, ordenado por antigüedad.

    El drop atascado se resalta: es el único que rompe la curva.
    """
    d = df.sort_values("semanas_vida", ascending=False)
    atascado = d[(d["semanas_vida"] > 20) & (d["sell_through_pct"] < 40)]["drop"].tolist()
    colores = [C["negativo"] if x in atascado else C["acento"] for x in d["drop"]]
    fig = go.Figure(
        go.Bar(
            x=d["drop"],
            y=d["sell_through_pct"],
            marker=dict(color=colores, line=dict(width=0)),
            text=[f"{v:.0f} %" for v in d["sell_through_pct"]],
            textposition="outside",
            textfont=dict(size=11, color=C["tinta_2"]),
            customdata=d[["semanas_vida", "capital"]],
            hovertemplate=(
                "%{x}<br>Sell-through %{y:.1f} %<br>"
                "%{customdata[0]:.0f} semanas de vida<br>"
                "%{customdata[1]:,.0f} € en stock<extra></extra>"
            ),
        )
    )
    plantilla_grafico(fig, altura=300)
    fig.update_xaxes(tickangle=-45, tickfont=dict(size=11))
    fig.update_yaxes(ticksuffix=" %", range=[0, 80])
    fig.update_layout(bargap=0.35, margin=dict(l=0, r=8, t=20, b=8))
    return fig


def grafico_proveedores(df: pd.DataFrame) -> go.Figure:
    """Porcentaje de entregas que llegan después de la fecha estimada."""
    d = df.sort_values("pct_tarde", ascending=False)
    return _barras_horizontales(
        d["proveedor"],
        d["pct_tarde"],
        [f"{v:.0f} %" for v in d["pct_tarde"]],
        altura=200,
    )


# ---------------------------------------------------------------------------
# Ejemplos reales para la página de decisiones
# ---------------------------------------------------------------------------

def recopilar_ejemplos_decisiones(tablas_crudas: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """Extrae de las tablas CRUDAS las filas que ilustran cada decisión.

    Se toman de `data/raw` a propósito: el ejemplo tiene que enseñar el problema
    tal como estaba, no ya corregido.
    """
    from .clean import normalizar_columnas

    v = normalizar_columnas(tablas_crudas["VENTAS"])
    s = normalizar_columnas(tablas_crudas["STOCK"])
    p = normalizar_columnas(tablas_crudas["PRODUCTO"])

    def _celda(valor) -> str:
        """Las fechas se muestran en formato corto; el resto, tal cual."""
        if isinstance(valor, (pd.Timestamp, _dt.datetime, _dt.date)):
            return valor.strftime("%d/%m/%Y")
        if pd.isna(valor):
            return "(vacío)"
        return str(valor)

    def mini(df: pd.DataFrame, cols: Sequence[str], notas: Dict[int, str] = None) -> str:
        notas = notas or {}
        cab = "".join(f"<th>{c.replace('_', ' ')}</th>" for c in cols) + "<th></th>"
        filas = []
        for i, (_, f) in enumerate(df.iterrows()):
            celdas = "".join(f"<td>{_celda(f[c])}</td>" for c in cols)
            filas.append(f'<tr>{celdas}<td class="neg">{notas.get(i, "")}</td></tr>')
        return f'<div class="ejemplo"><table><thead><tr>{cab}</tr></thead><tbody>{"".join(filas)}</tbody></table></div>'

    ejemplos = {}

    dup = v[v.duplicated(subset=["pedido", "sku"], keep=False)].head(2)
    ejemplos["duplicados"] = mini(
        dup, ["fecha", "pedido", "sku", "unidades", "pvp_unitario"], {1: "← duplicada"}
    )

    neg = v[v["unidades"].astype(float) < 0].head(3)
    ejemplos["devoluciones"] = mini(
        neg, ["fecha", "pedido", "sku", "unidades", "pvp_unitario", "descuento"],
        {0: "← descuento positivo con unidades negativas"},
    )

    minus = v[v["sku"].astype(str) != v["sku"].astype(str).str.upper()].head(3)
    ejemplos["sku_minusculas"] = mini(minus, ["fecha", "pedido", "sku", "mercado", "unidades"])

    mal = v[v["mercado"].astype(str).isin(["Spain", "ESP", "es"]) | v["mercado"].isna()].head(4)
    ejemplos["mercados"] = mini(mal, ["fecha", "pedido", "sku", "mercado"])

    fantasma = s[s["sku"] == "EME999-BLA-M"]
    ejemplos["sku_fantasma"] = mini(
        fantasma, ["sku", "stock_disponible", "fecha_stock"], {0: "← no existe en PRODUCTO"}
    )

    etiquetas = v["etiquetas"].dropna().value_counts().reset_index()
    etiquetas.columns = ["etiqueta", "lineas"]
    ejemplos["etiquetas"] = mini(etiquetas, ["etiqueta", "lineas"])

    choque = p[p["sku"].isin(["EME045-OLI-M", "EME076-OLI-M"])]
    ejemplos["modelo_colision"] = mini(
        choque, ["sku", "producto", "color", "seccion", "drop", "pvp"],
        {0: "← dos productos distintos", 1: "← con el mismo nombre y color"},
    )
    return ejemplos


# ---------------------------------------------------------------------------
# Secciones del informe
# ---------------------------------------------------------------------------

def _hero(comparativa: pd.DataFrame, cupon: pd.Series) -> str:
    """Los cuatro KPIs de la semana, con su doble comparativa."""
    f = comparativa.iloc[0]
    tarjetas = [
        kpi("Unidades vendidas", f["unidades"], "uds", [
            ("semana anterior", f["unidades_vs_semana_anterior_pct"]),
            ("misma semana 2024", f["unidades_vs_ano_anterior_pct"]),
        ], pie=f'De ellas <strong>{num(cupon["unidades_con_cupon"])} con cupón WELCOME10</strong>'),
        kpi("Facturación neta", f["facturacion_neta"], "€", [
            ("semana anterior", f["facturacion_neta_vs_semana_anterior_pct"]),
            ("misma semana 2024", f["facturacion_neta_vs_ano_anterior_pct"]),
        ], pie=f'Ya descontados <strong>{eur(cupon["descuento_dado"], 2)}</strong> de cupones'),
        kpi("Margen bruto", f["margen"], "€", [
            ("semana anterior", f["margen_vs_semana_anterior_pct"]),
            ("misma semana 2024", f["margen_vs_ano_anterior_pct"]),
        ]),
        kpi("Margen sobre ventas", f["margen_pct"], "%", []),
    ]
    return f'<div class="grid g4" style="margin-bottom:28px">{"".join(tarjetas)}</div>'


def _seccion_semana(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    comp = m["comparativa"]
    comp = comp.assign(
        rango=comp.apply(
            lambda r: f"{pd.Timestamp(r['desde']):%d/%m/%y} – {pd.Timestamp(r['hasta']):%d/%m/%y}", axis=1
        )
    )
    tabla = tabla_html(comp, [
        ("periodo", "Periodo", "texto"),
        ("rango", "Fechas", "texto"),
        ("unidades", "Uds", "num"),
        ("facturacion_neta", "Facturación", "eur"),
        ("margen", "Margen", "eur"),
        ("margen_pct", "Margen %", "pct"),
        ("pedidos", "Pedidos", "num"),
        ("ticket_medio", "Ticket", "eur2"),
    ], destacar=[0])

    crec = m["crecimiento"]
    var = crec[crec["periodo"] == "variacion_pct"].iloc[0]
    mezcla = m["efecto_mezcla"].iloc[0]
    reparto = m["reparto_categoria_interanual"]
    chaqueta = reparto[reparto["categoria"] == "CHAQUETA"].iloc[0]
    chaqueta_ly, chaqueta_hoy = chaqueta["pct_referencia"], chaqueta["pct_actual"]
    desglose = f"""
<div class="grid g3" style="margin-top:20px">
  <div class="card"><div class="dato">{delta(var['pedidos'])}</div>
    <div class="dato-lbl">Pedidos — de {num(crec.iloc[1]['pedidos'])} a {num(crec.iloc[0]['pedidos'])}</div></div>
  <div class="card"><div class="dato">{delta(var['uds_por_pedido'])}</div>
    <div class="dato-lbl">Unidades por pedido — {num(crec.iloc[0]['uds_por_pedido'], 2)} frente a {num(crec.iloc[1]['uds_por_pedido'], 2)}</div></div>
  <div class="card"><div class="dato">{delta(var['precio_medio_ud'])}</div>
    <div class="dato-lbl">Facturación por unidad — {eur(crec.iloc[0]['precio_medio_ud'], 2)}
    frente a {eur(crec.iloc[1]['precio_medio_ud'], 2)}</div></div>
</div>
<p class="nota" style="max-width:70ch">La facturación por unidad es
<code>facturación neta ÷ unidades</code>: lo que deja de media cada prenda vendida, ya descontados los
cupones. Sube un {num(var['precio_medio_ud'], 1)}&nbsp;%, pero <strong>no porque se venda más caro</strong>:
con la mezcla de producto del año pasado habría <em>bajado</em> un {num(abs(mezcla['efecto_precio_pct']), 1)}&nbsp;%.
La subida es mezcla: la chaqueta pasa del {num(chaqueta_ly, 1)}&nbsp;% al {num(chaqueta_hoy, 1)}&nbsp;% de las
unidades y es la categoría más cara.</p>"""

    div_id = "g-evolucion"
    evol = m["evolucion_semanal"]
    html_grafico, grupos, ejes = grafico_evolucion(evol, div_id)
    cuerpo = f"""
<div class="card">
  {selector(div_id, [etiqueta for _, etiqueta, _, _ in METRICAS_EVOLUCION])}
  {leyenda(("Este año", C["acento"]), ("Misma semana del año anterior", C["referencia"]),
           ("Variación interanual", (C["positivo"], C["negativo"])))}
  {html_grafico}
  {registrar(div_id, grupos, ejes)}
  <p class="nota">Arriba, las últimas 26 semanas frente a la misma semana ISO del año anterior.
  Abajo, la variación interanual de cada una. Como en todo el informe, <strong>sin las ventas a precio
  especial</strong>: son liquidación de campaña y harían parecer buena una semana de rebajas.</p>
</div>
<div class="card" style="margin-top:20px">{tabla}</div>
<h3 style="margin-top:36px">De dónde sale el crecimiento interanual</h3>
{desglose}"""

    return seccion("Reto 1 · Pregunta 1", "Cómo fue la semana", "semana", "", cuerpo)


def _seccion_reparto(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    merc, sec, cat = m["desglose_mercado"], m["desglose_seccion"], m["desglose_categoria"]

    g_merc = grafico(_barras_horizontales(
        merc["mercado"], merc["facturacion_neta"],
        [f"{num(v)} €  ·  {p:.0f} %" for v, p in zip(merc["facturacion_neta"], merc["peso_pct"])],
    ))
    g_cat = grafico(_barras_horizontales(
        cat["categoria"], cat["facturacion_neta"],
        [f"{num(v)} €  ·  {p:.0f} %" for v, p in zip(cat["facturacion_neta"], cat["peso_pct"])],
    ))
    t_sec = tabla_html(sec, [
        ("seccion", "Sección", "texto"),
        ("unidades", "Unidades", "num"),
        ("facturacion_neta", "Facturación", "eur"),
        ("peso_pct", "Peso", "pct"),
        ("margen_pct", "Margen %", "pct"),
        ("pct_promocion", "Con WELCOME10", "pct"),
    ])
    # La columna de precio especial se cae de esta tabla: esta semana es 0 en
    # todos los mercados y una columna de ceros no informa, confunde.
    t_promo = tabla_html(merc, [
        ("mercado", "Mercado", "texto"),
        ("unidades", "Uds totales", "num"),
        ("unidades_promocion", "Uds con cupón", "num"),
        ("facturacion_neta", "Facturación", "eur"),
        ("pct_promocion", "% fact. con cupón", "pct"),
        ("coste_cupon", "Descuento dado", "eur2"),
    ])

    margen_promo = m["margen_cupon"].iloc[0]["margen_pct_con_cupon"]
    margen_sin = m["margen_cupon"].iloc[0]["margen_pct_sin_cupon"]

    div_id = "g-especial"
    html_grafico, grupos, ejes = grafico_estacionalidad(m["estacionalidad_especial"], div_id)

    cuerpo = f"""
<div class="grid g2">
  <div class="card"><h3>Por mercado</h3><p class="nota" style="margin-bottom:12px">Facturación neta y peso sobre el total</p>{g_merc}</div>
  <div class="card"><h3>Por categoría</h3><p class="nota" style="margin-bottom:12px">Facturación neta y peso sobre el total</p>{g_cat}</div>
</div>
<div class="card" style="margin-top:20px"><h3>Por sección</h3>{t_sec}</div>

<h3 style="margin-top:36px">El precio especial es estacional</h3>
<p>Las ventas a precio rebajado se concentran en campañas: rebajas de enero, rebajas de verano y
Black&nbsp;Friday.</p>
<div class="card" style="margin-top:16px">
  {selector(div_id, [etiqueta for _, _, etiqueta, _ in METRICAS_ESPECIAL])}
  {leyenda(("A precio especial", C["acento"]), ("A precio completo", C["referencia"]))}
  {html_grafico}
  {registrar(div_id, grupos, ejes)}
  <p class="nota">«A precio completo» es toda la venta que no es liquidación, e incluye las líneas con
  cupón WELCOME10. Los dos trozos de cada barra suman el total del mes. En euros el precio especial pesa
  menos que en unidades: cada unidad rebajada factura en torno a un 40&nbsp;% menos.</p>
</div>

<h3 style="margin-top:36px">Dónde pesa el cupón WELCOME10</h3>
<p>El cupón descuenta un 10&nbsp;% sobre tarifa. Cuenta como venta ordinaria, no como precio especial:
son cosas distintas, un cupón de bienvenida y una liquidación al 40&nbsp;%. <strong>El descuento ya está
restado de la facturación</strong>, así que el margen lo absorbe solo una vez. La última columna es lo
que el cupón deja de ingresar.</p>
<div class="card" style="margin-top:16px">{t_promo}
<p class="nota">Ojo con las dos bases: <strong>el porcentaje es sobre facturación, no sobre unidades</strong>,
y no coinciden porque el cupón no se reparte igual entre producto caro y barato. En Alemania son 9 de 53
unidades (el {pct(merc[merc.mercado == "DE"].iloc[0]["pct_promocion_uds"])}) pero el
{pct(merc[merc.mercado == "DE"].iloc[0]["pct_promocion"])} de la facturación.<br>
<strong>Descuento dado</strong> no lo calculamos nosotros: es la columna <code>Descuento (€)</code> del
Excel, en euros, sumada sobre esas líneas. Se <strong>resta</strong> del importe de tarifa, nunca se suma
ni se recalcula. Resulta ser el 10&nbsp;% del bruto, pero eso es un hecho del dato, no una fórmula nuestra.
Esta semana el cupón deja de ingresar
<strong>{eur(merc["coste_cupon"].sum(), 2)}</strong>, y el margen de sus líneas es del {pct(margen_promo)}
frente al {pct(margen_sin)} de las que no lo llevan.</p></div>"""

    return seccion(
        "Reto 1 · Pregunta 2", "Cómo se reparte, y qué se vendió rebajado", "reparto",
        "<strong>Esta semana no se ha vendido ni una unidad a precio especial</strong>, pero no es una "
        "anomalía: el precio especial en EME es estacional, no continuo. Lo que sí está activo es el "
        "cupón <strong>WELCOME10</strong>.",
        cuerpo,
    )


def _seccion_modelos(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    top, bottom = m["ranking_top"], m["ranking_bottom"]
    semanas_sin = int(m["ranking_ventana_ranking"].iloc[0]["semanas_sin_venta"])

    cols = [
        ("modelo_nombre", "Modelo", "texto"),
        ("categoria", "Categoría", "texto"),
        ("unidades_semana", "Esta semana", "num"),
        ("unidades_semana_anterior", "Semana anterior", "num"),
        ("uds_ano", "En el año", "num"),
        ("stock_actual", "Stock", "num"),
        ("sell_through_pct", "Sell-through", "pct"),
    ]
    t_sin = tabla_html(m["ranking_sin_venta_en_la_semana"], [
        ("modelo_nombre", "Modelo", "texto"),
        ("categoria", "Categoría", "texto"),
        ("unidades_vendidas", "Uds vendidas (histórico)", "num"),
        ("stock_actual", "Stock", "num"),
        ("sell_through_pct", "Sell-through", "pct"),
    ])
    conc = m["concentracion"]
    tiles = "".join(
        f'<div class="card"><div class="dato">{num(r["n_modelos"])}</div>'
        f'<div class="dato-lbl">modelos hacen el {int(r["pct_facturacion"])} % de la facturación '
        f'({int(r["pct_catalogo"])} % del catálogo)</div></div>'
        for _, r in conc.iterrows()
    )
    mejor, peor = top.iloc[0], bottom.iloc[0]
    familias = top["modelo_nombre"].str.split().str[0].value_counts().head(2)

    cuerpo = f"""
<div class="card"><h3>Los 10 que más venden</h3>
<p class="nota" style="margin-bottom:14px">Unidades de la semana analizada. Al lado, la semana anterior y
lo que lleva vendido el modelo en 2025, para saber si el dato de la semana es su ritmo normal.
El sell-through es de toda la vida del modelo.</p>
{tabla_html(top, cols)}</div>

<div class="card" style="margin-top:20px"><h3>Los 10 que menos venden</h3>
<p class="nota" style="margin-bottom:14px">Hay muchos modelos empatados a una unidad, así que entre ellos
ordena lo vendido en el año: peor está el que además lleva menos vendido.</p>
{tabla_html(bottom, cols)}</div>

<div class="card" style="margin-top:20px"><h3>Con stock y sin una sola venta en {semanas_sin} semanas</h3>
<p class="nota" style="margin-bottom:14px">No aparecen en ningún ranking porque no vendieron nada. No vender
una semana es normal; no vender en {semanas_sin}, con stock en el almacén, no.</p>
{t_sin}</div>

<h3 style="margin-top:36px">La facturación está muy concentrada</h3>
<div class="grid g3" style="margin-top:16px">{tiles}</div>"""

    return seccion(
        "Reto 1 · Pregunta 3", "Qué modelos tiran y cuáles no", "modelos",
        f"El más vendido de la semana es <strong>{mejor['modelo_nombre']}</strong> con "
        f"{num(mejor['unidades_semana'])} unidades, y las familias <strong>{familias.index[0]}</strong> y "
        f"<strong>{familias.index[1]}</strong> copan {int(familias.sum())} de los diez primeros puestos. "
        f"En la cola, modelos con una sola venta en la semana y sell-through por debajo del 10&nbsp;%: "
        f"<strong>{peor['modelo_nombre']}</strong> lleva {num(peor['uds_ano'])} unidades en todo el año y "
        f"{num(peor['stock_actual'])} en almacén.",
        cuerpo,
    )


def _seccion_stock(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    cg = m["cobertura_global"].iloc[0]
    rot, exc = m["rotura_por_modelo"], m["exceso_por_modelo"]
    valor_pvp = m["exceso_a_pvp"].iloc[0]["valor_pvp"]

    # La tabla se lee de izquierda a derecha como una resta: de estas tallas
    # esperamos vender tanto, tenemos tanto, y falta esto.
    rot = rot.assign(
        disponible=(rot["stock_tallas_rotura"] + rot["en_camino_tallas_rotura"]).round(0),
        tallas_txt=rot["tallas_rotas"] + " (de " + rot["tallas"].astype(int).astype(str) + ")",
    )
    t_rot = tabla_html(rot.head(12), [
        ("modelo_nombre", "Modelo", "texto"),
        ("tallas_txt", "Tallas que rompen", "texto"),
        ("demanda_tallas_rotura", "Demanda 4 sem", "num1"),
        ("disponible", "Disponible", "num"),
        ("deficit_unidades", "Faltan", "num1"),
        ("stock_modelo", "Stock del modelo", "num"),
    ])
    t_exc = tabla_html(exc.head(12), [
        ("modelo_nombre", "Modelo", "texto"),
        ("stock_disponible", "Stock", "num"),
        ("demanda_semanal", "Demanda/sem", "num1"),
        ("cobertura_semanas", "Cobertura (sem)", "num1"),
        ("unidades_exceso", "Uds sobrantes", "num"),
        ("capital_inmovilizado", "Capital parado", "eur"),
    ])
    cuerpo = f"""
<div class="grid g4">
  <div class="card"><div class="dato">{num(cg['stock_total_uds'])}</div><div class="dato-lbl">unidades en almacén</div></div>
  <div class="card"><div class="dato">{num(cg['cobertura_global_semanas'], 1)}</div><div class="dato-lbl">semanas de cobertura (objetivo: {int(cg['cobertura_objetivo_semanas'])})</div></div>
  <div class="card"><div class="dato alerta">{len(rot)}</div><div class="dato-lbl">modelos en rotura en 4 semanas · {int(rot['tallas_en_rotura'].sum())} tallas</div></div>
  <div class="card"><div class="dato">{eur(exc['capital_inmovilizado'].sum())}</div><div class="dato-lbl">capital parado en exceso de stock</div></div>
</div>

<h3 style="margin-top:36px">Modelos en rotura en 4 semanas</h3>
<p>Un modelo entra aquí si le falta <strong>alguna talla</strong>, no si le falta stock en conjunto.
No se puede vender una M con el stock de XL.</p>
<div class="card" style="margin-top:16px">{t_rot}
<p class="nota"><strong>Disponible</strong> = lo que hay en almacén de esas tallas más las compras que
llegan dentro de las 4 semanas. <strong>Faltan</strong> = demanda − disponible. La última columna es el
stock del modelo entero: el número que haría pensar que está sano.
Las 12 primeras de {len(rot)}.</p></div>

<h3 style="margin-top:36px">Modelos con exceso de stock</h3>
<p>Ordenados por <strong>capital inmovilizado</strong>, no por semanas de cobertura: la cobertura se
dispara en productos baratos que casi no rotan.</p>
<div class="card" style="margin-top:16px">{t_exc}
<p class="nota">Las 12 primeras de {len(exc)}. <strong>Unidades sobrantes</strong> = stock − demanda
semanal × 8 semanas de cobertura objetivo: lo que queda por encima de lo que la empresa quiere tener.
<strong>Capital parado</strong> = esas unidades <strong>a coste</strong>, no a PVP. Es el dinero que ya se
pagó al proveedor y sigue en la estantería; valorado a precio de venta serían {eur(valor_pvp)}, pero ese
dinero no se ha gastado. El umbral de exceso está en las <em>Asunciones</em>.</p></div>"""

    return seccion("Reto 1 · Pregunta 4", "Qué va a romper y qué sobra", "stock", "", cuerpo)


def _seccion_insights(m: Dict[str, pd.DataFrame]) -> str:
    """Lo que no pide el enunciado pero sale al leer las cuatro respuestas."""
    tallas = m["curva_tallas"]
    prov = m["fiabilidad_proveedores"]
    drops = m["sell_through_drop"]
    atascado = drops[(drops["semanas_vida"] > 20) & (drops["sell_through_pct"] < 40)]

    t_tallas = tabla_html(tallas, [
        ("talla", "Talla", "texto"),
        ("demanda", "Demanda 12 sem", "num"),
        ("pct_demanda", "% demanda", "pct"),
        ("stock", "Stock", "num"),
        ("pct_stock", "% stock", "pct"),
        ("desvio_uds", "Desvío en uds", "num"),
    ], destacar=[2, 4, 5])
    t_prov = tabla_html(prov.sort_values("pct_tarde", ascending=False), [
        ("proveedor", "Proveedor", "texto"),
        ("entregas", "Entregas", "num"),
        ("pct_tarde", "Llegan tarde", "pct"),
        ("retraso_medio", "Retraso medio (días)", "num1"),
        ("retraso_maximo", "Peor retraso (días)", "num"),
        ("vencidas", "Vencidas sin confirmar", "num"),
    ])
    t_drops = tabla_html(drops, [
        ("drop", "Drop", "texto"),
        ("semanas_vida", "Semanas de vida", "num"),
        ("vendido", "Vendido", "num"),
        ("stock", "Stock", "num"),
        ("sell_through_pct", "Sell-through", "pct"),
        ("capital", "Capital en stock", "eur"),
    ], destacar=[int(i) for i in atascado.index])

    sobra = tallas[tallas["desvio_uds"] > 0]["desvio_uds"].sum()
    return seccion("Reto 1 · Más allá del enunciado",
        "Cinco cosas que los datos dicen sin que nadie las pregunte", "insights",
        """Las cuatro preguntas del informe se responden solas. Estas cinco salen de mirar
  <em>por qué</em> salen esos números, y dos de ellas cambian lo que habría que hacer el lunes.""",
        f"""

  <h3>1 · El almacén tiene las tallas equivocadas</h3>
  <p>Es la explicación de la paradoja anterior: {num(m["cobertura_global"].iloc[0]["cobertura_global_semanas"], 1)}
  semanas de cobertura y aun así roturas. La <strong>M es el {pct(tallas[tallas.talla == "M"].iloc[0]["pct_demanda"])}
  de la demanda y solo el {pct(tallas[tallas.talla == "M"].iloc[0]["pct_stock"])} del stock</strong>. La XXL, al revés:
  el {pct(tallas[tallas.talla == "XXL"].iloc[0]["pct_demanda"])} de la demanda y el
  {pct(tallas[tallas.talla == "XXL"].iloc[0]["pct_stock"])} del almacén, cuatro veces y media más de lo que tocaría.
  Son <strong>{num(sobra)} unidades de más</strong> en las tallas sobrerrepresentadas —casi todas XL y XXL—
  mientras faltan {num(abs(tallas[tallas.talla == "M"].iloc[0]["desvio_uds"]))} M.</p>
  <div class="card" style="margin-top:16px">{grafico(grafico_curva_tallas(tallas))}</div>
  <div class="card" style="margin-top:20px">{t_tallas}</div>
  <p class="nota">Se arregla en el Reto 2 cambiando la curva de tallas del pedido, sin gastar un euro más.</p>

  <h3 style="margin-top:44px">2 · La fecha de entrega del proveedor no es una previsión</h3>
  <p>No hay un proveedor malo: <strong>los cuatro llegan tarde entre el 73&nbsp;% y el 81&nbsp;% de las veces</strong>,
  con un retraso medio casi idéntico de entre 5 y 6 días. Cuando todos fallan igual, el problema no son ellos:
  es que la fecha estimada se calcula optimista, en torno a una semana.</p>
  <div class="card" style="margin-top:16px">{grafico(grafico_proveedores(prov))}
  <p class="nota">Porcentaje de entregas que llegan después de su propia fecha estimada.</p></div>
  <div class="card" style="margin-top:20px">{t_prov}</div>
  <p class="nota">Acción inmediata y gratis: sumar seis días a toda fecha estimada. En el Reto 2 cambia el cálculo
  de lo que hay realmente en camino.</p>

  <h3 style="margin-top:44px">3 · El drop {atascado.iloc[0]["drop"] if len(atascado) else "—"} se ha quedado atascado</h3>
  <p>Los drops siguen una curva coherente: cuanto más viejo, más vendido. Uno se sale.
  <strong>{atascado.iloc[0]["drop"] if len(atascado) else "—"}</strong> lleva
  {int(atascado.iloc[0]["semanas_vida"]) if len(atascado) else 0} semanas en el mercado, nueve más que el siguiente,
  y vende doce puntos peor. Son <strong>{eur(atascado.iloc[0]["capital"]) if len(atascado) else "—"}</strong> parados
  en producto que lleva seis meses sin arrancar: el candidato natural para Black&nbsp;Friday.</p>
  <div class="card" style="margin-top:16px">{grafico(grafico_drops(drops))}</div>
  <div class="card" style="margin-top:20px">{t_drops}</div>

  <h3 style="margin-top:44px">4 · El crecimiento viene de más clientes, no de cestas más grandes</h3>
  <p>Ya está desglosado en la pregunta 1: los pedidos crecen un 46,6&nbsp;% y las unidades por pedido se quedan
  clavadas en 1,1. La captación funciona; <strong>la venta cruzada está sin explotar</strong>.</p>

  <h3 style="margin-top:44px">5 · Dieciséis modelos son la mitad del negocio</h3>
  <p>Y cuarenta y ocho modelos, el 39&nbsp;% del catálogo, aportan solo el 10&nbsp;% de la facturación. Con el exceso
  de stock encima, esto apunta a una decisión de surtido, no de reposición.</p>""")


def _seccion_glosario() -> str:
    """Qué significa cada término, con su fórmula y un ejemplo real."""
    terminos = [
        termino(
            "Modelo y SKU",
            "Un <strong>modelo</strong> es la combinación de producto y color: lo que se diseña y se compra. "
            "Un <strong>SKU</strong> es el modelo en una talla concreta: lo que está físicamente en la estantería "
            "y lo que se vende o se agota.",
            "NOVA BOMBER + GREY MELANGE  =  1 modelo\n  └─ EME095-GRE-XS / S / M / L / XL  =  5 SKUs",
            "En este catálogo: 123 modelos y 579 SKUs, unas 4,7 tallas por modelo.",
        ),
        termino(
            "Facturación neta",
            "Lo que entra en caja: el precio de venta por las unidades, menos <strong>todos</strong> los "
            "descuentos aplicados a la línea, incluido el cupón WELCOME10. Es «neta» por el descuento, "
            "no por el IVA.",
            "facturación neta  =  unidades × PVP unitario − descuento",
            "El PVP y el descuento vienen los dos del Excel; el descuento siempre se resta. "
            "Ejemplo real: 1 × 75,00 € = 75,00 € de bruto, menos 7,50 € de cupón, son 67,50 € de "
            "facturación neta. Los 7,50 € no entran en facturación en ningún momento.",
        ),
        termino(
            "Margen y margen %",
            "Lo que queda después de pagar el producto al proveedor. Es margen <strong>de producto</strong>: "
            "no descuenta envíos, devoluciones logísticas, marketing ni estructura.",
            "margen    =  facturación neta − unidades × coste unitario\nmargen %  =  margen / facturación neta",
            "Como parte de la facturación ya descontada, <strong>el descuento se resta una sola vez</strong>: "
            "no se vuelve a restar en el margen. Siguiendo el ejemplo del cupón: 261,00 € − 69,52 € = 191,48 €. "
            "El efecto del cupón se ve en el margen <em>porcentual</em>, que baja porque el coste no cambia.",
        ),
        termino(
            "Sell-through",
            "Qué parte de lo que se compró ya se ha vendido. Se calcula sobre <strong>toda la vida del modelo</strong>, "
            "no sobre la semana: en siete días daría cifras minúsculas y sin significado.",
            "sell-through  =  unidades vendidas / (unidades vendidas + stock actual)",
            "NOVA BOMBER GREY MELANGE: 105 vendidas y 43 en stock → 105 / 148 = 70,9 %. "
            "Por encima del 70 % funciona; por debajo del 30 % es candidato a rebaja.",
        ),
        termino(
            "Cobertura",
            "Cuántas semanas se puede seguir vendiendo con el stock actual. Es la unidad natural para hablar "
            "de stock: «300 unidades» no dice nada si no se sabe a qué ritmo salen.",
            "cobertura (semanas)  =  stock actual / demanda semanal prevista",
            "El objetivo de EME son 8 semanas. El almacén está hoy en 29,2.",
        ),
        termino(
            "Rotura de stock",
            "Un SKU va a romper si lo que hay más lo que llega no cubre lo que se espera vender. "
            "<strong>Se calcula por talla</strong>, nunca sumando el modelo entero: no se puede vender una M "
            "con el stock de XL.",
            "déficit  =  demanda 4 semanas − stock actual − unidades en camino\nrotura   =  déficit > 0",
            "Un modelo entra en la lista si le falta alguna talla, aunque en conjunto le sobre stock.",
        ),
        termino(
            "Exceso de stock y capital inmovilizado",
            "Stock muy por encima de lo que se va a vender. Se mide con la cobertura pero se ordena por dinero: "
            "la cobertura se dispara en productos baratos que casi no rotan, y eso no es lo que decide dirección.",
            "unidades sobrantes  =  stock − demanda semanal × 8 semanas\ncapital parado      =  unidades sobrantes × coste unitario",
            "LOGIC JOGGER BLACK: 293 uds a 4,8/semana → sobran 255 uds = 6.811 € parados.",
        ),
        termino(
            "Precio especial y promoción",
            "<strong>Precio especial</strong> son las ventas con etiqueta <code>special</code>: liquidación de campaña, "
            "con un 40&nbsp;% de descuento medio. <strong>Promoción</strong> es el cupón <code>WELCOME10</code>, un "
            "10&nbsp;% sobre una venta a tarifa, que sí cuenta como venta ordinaria.",
            "",
            "El precio especial queda fuera de todas las cifras del informe y se analiza aparte en la "
            "pregunta 2. La única excepción es el sell-through, que mide salida física de almacén. "
            "Los regalos a influencers quedan fuera de todo, por regla del enunciado.",
        ),
        termino(
            "Lead time y drop",
            "El <strong>lead time</strong> es lo que tarda el proveedor desde que se le pide hasta que la mercancía "
            "entra en almacén: 6 semanas. Un <strong>drop</strong> es una tanda de producto que sale al mercado en "
            "una fecha; EME hace seis al año.",
            "",
            "Si la cobertura baja de 6 semanas ya es tarde: aunque se pida hoy, se rompe antes de que llegue.",
        ),
    ]
    return seccion("Referencia · transversal a los tres retos", "Glosario", "glosario",
        """Cada cifra de este informe sale de una de estas definiciones. Si alguna no coincide con
        la que usa internamente EME, cambia el número, no el método.""",
        f'<div class="glosario">{"".join(terminos)}</div>')


def _seccion_asunciones(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """Qué viene del enunciado y qué hemos decidido nosotros."""
    DATO = '<span class="tag tag-dato">Enunciado</span>'
    MIO = '<span class="tag tag-mio">Decisión nuestra</span>'
    VALID = '<span class="tag tag-dato">Validado con datos</span>'
    filas = [
        ("Semana analizada", "3 – 9 nov 2025 (ISO 2025-W45)", DATO, "Lunes a domingo, como pide el enunciado."),
        ("Comparativa interanual", "2024-W45: 4 – 10 nov 2024", MIO,
         "Se compara por número de semana ISO, no por fecha, para que ambas tengan los mismos días de la semana."),
        ("Horizonte de rotura", "4 semanas", DATO, "Viene dado en la pregunta 4."),
        ("Cobertura objetivo", "8 semanas", DATO,
         "El enunciado lo da en el Reto 2, pero es la política de stock de la empresa: no cambia según qué informe se lea."),
        ("Umbral de exceso", "16 semanas (2 × objetivo)", MIO,
         "No viene en el enunciado. Da casi igual dónde se ponga: ver la tabla de sensibilidad debajo."),
        ("Ventana del forecast", "media móvil de 4 semanas", VALID,
         "Elegida por backtesting con origen móvil sobre 13 cortes del último año: MAE 2,09 y sesgo +9,8 %, frente a MAE 2,05 y sesgo +20,1 % con 8 semanas."),
        ("Precios sin IVA", "se asume que no lo llevan", MIO,
         "Nada en los datos ni en la hoja LEEME lo aclara. Si lo llevasen, facturación y margen bajarían de forma proporcional y ninguna comparativa cambiaría."),
        ("Sell-through", "sobre la vida del modelo", MIO,
         "Calcularlo sobre siete días daría cifras sin significado."),
        ("Margen", "solo coste de producto", MIO,
         "No hay datos de logística, marketing ni estructura. El margen real de contribución será menor."),
        ("WELCOME10", "cuenta como precio completo", MIO,
         "Descuenta un 10 % sobre tarifa, frente al 40 % del precio especial. Mezclarlos distorsionaría el margen del canal."),
        ("Precio especial", "excluido de todo el análisis", MIO,
         "KPIs, evolución, desgloses, rankings, previsión y alertas de stock son venta a tarifa. Es liquidación de campaña: incluirla haría parecer buena una semana de rebajas y la haría incomparable con una semana normal."),
        ("Sell-through", "sí incluye el precio especial", MIO,
         "Única excepción, por coherencia aritmética: mide salida física de almacén, y una unidad rebajada salió igual. Además el denominador usa el stock actual, que ya refleja esa salida."),
        ("Compras vencidas", "no cuentan como stock en camino", MIO,
         "37 pedidos con fecha estimada vencida y sin confirmación de llegada. Contarlos llevaría a reponer de menos."),
        ("Lead time real", "no es medible", VALID,
         "La tabla COMPRAS no trae fecha de pedido, solo de llegada. Las 6 semanas del enunciado se toman como dadas."),
    ]
    cuerpo = "".join(
        f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td style='color:var(--tinta-3)'>{d}</td></tr>"
        for a, b, c, d in filas
    )
    sens = tabla_html(m["sensibilidad_umbral"], [
        ("umbral_semanas", "Umbral (semanas)", "num"),
        ("modelos", "Modelos marcados", "num"),
        ("pct_catalogo", "% del catálogo", "pct"),
    ], destacar=[2])
    return seccion("Referencia · transversal a los tres retos", "Asunciones", "asunciones",
        """Todo lo que no viene dado por el enunciado y hemos tenido que decidir nosotros, marcado
        como tal. <strong>Siete de las doce son decisiones nuestras</strong>: si alguna no coincide con el
        criterio de EME, basta cambiar el parámetro y volver a ejecutar.""",
        f"""<div class="card"><div class="tabla-scroll"><table>
    <thead><tr><th>Parámetro</th><th>Valor</th><th>Origen</th><th>Por qué</th></tr></thead>
    <tbody>{cuerpo}</tbody>
  </table></div></div>

<h3 style="margin-top:44px">¿Cuánto depende el diagnóstico del umbral de exceso?</h3>
<p>Las 16 semanas las hemos elegido nosotros, así que conviene enseñar cuánto cambia el resultado si se
mueven: <strong>casi nada</strong>. Entre 8 y 16 semanas salen los mismos modelos, y hay que irse a un año
entero de cobertura para bajar de la mitad del catálogo. El umbral no es el problema: el sobrestock sí.</p>
<div class="card" style="margin-top:16px">{sens}</div>""")


def pagina_decisiones(ejemplos: Dict[str, str], resumen: pd.DataFrame) -> str:
    """Construye la página "Decisiones y calidad de datos" del informe.

    Cada decisión se muestra plegada; al abrirla aparecen el problema, un ejemplo
    con filas reales del dato original, la decisión con sus alternativas
    descartadas, y el impacto sobre las cifras.
    """
    n = dict(zip(resumen["concepto"], resumen["n_filas"]))

    bloques = [
        bloque_decision_plegable(
            f"Se excluyeron {num(n['Líneas de regalo (influencers) excluidas de la venta'])} líneas de regalo a influencers",
            "Los pedidos con la etiqueta <code>influencers</code> son regalos, no ventas. Descuentan el 100 % "
            "del importe: en 560 de 561 líneas el descuento es exactamente igual al importe bruto.",
            ejemplos["etiquetas"],
            "Regla del enunciado. Se excluyen de <strong>todo</strong> análisis de venta: unidades, facturación, "
            "margen, sell-through y demanda prevista. Se conservan en una tabla aparte porque sí consumen stock.",
            "559 líneas fuera de la venta. En la tabla se ven también las dos etiquetas que el enunciado no menciona: "
            "<code>WELCOME10</code> y las variantes <code>SPECIAL XX</code>.",
        ),
        bloque_decision_plegable(
            "WELCOME10 cuenta como venta a precio completo, no como precio especial",
            "Aparece una etiqueta que el enunciado no menciona, en 999 líneas (5,5 % del total). Descuenta "
            "exactamente un 10 %, frente al ~40 % de <code>special</code> y el 100 % de <code>influencers</code>.",
            "",
            "Es una venta a tarifa con un cupón promocional encima, no una liquidación. Entra en precio completo "
            "con un flag propio. <strong>Alternativa descartada:</strong> meterla en <code>special</code>, que "
            "mezclaría un 10 % con un 40 % y distorsionaría el margen del canal de precio completo.",
            "Cambia el reparto de la pregunta 2. Sin esta decisión, el «0 % a precio especial» de la semana sería "
            "un 8,8 % que no significaría lo mismo.",
        ),
        bloque_decision_plegable(
            "Las cuatro variantes de SPECIAL se unificaron en un solo flag",
            "La etiqueta aparece escrita de cuatro formas: <code>special</code> (851 líneas), <code>SPECIAL ES</code> "
            "(717), <code>SPECIAL US</code> (61) y <code>SPECIAL NL</code> (55). Todas descuentan en torno al 40 %.",
            "",
            "Cualquier etiqueta que empiece por <code>SPECIAL</code> marca precio especial. El sufijo es un mercado "
            "y se guarda aparte como dato de control, para poder contrastarlo con el mercado de la línea.",
            f"{num(n['Líneas marcadas como precio especial'])} líneas marcadas. Filtrando solo por <code>special</code> "
            "se habrían perdido 833, la mitad del precio especial del histórico.",
        ),
        bloque_decision_plegable(
            f"Se eliminaron {num(n['Líneas de venta duplicadas eliminadas'])} líneas de venta duplicadas",
            "25 pares de filas idénticas en todas sus columnas: mismo pedido, mismo SKU, misma fecha, mismo precio "
            "y una unidad cada una.",
            ejemplos["duplicados"],
            "Se elimina una de cada par. Un ERP agruparía dos unidades del mismo SKU en una línea con "
            "<code>unidades = 2</code>; dos líneas idénticas apuntan a un error de carga, y el enunciado avisa de "
            "que hay errores introducidos a propósito. <strong>Alternativa descartada:</strong> conservarlas, por si "
            "el sistema creara una línea por unidad.",
            "−25 líneas sobre 18.292 (0,1 %). De ellas, 2 eran regalos y 5 de precio especial.",
        ),
        bloque_decision_plegable(
            f"Las {num(n['Devoluciones conservadas (unidades negativas)'])} líneas con unidades negativas se conservan como devoluciones",
            "Diez líneas con <code>unidades = −1</code>. Además traen el descuento en positivo, lo que hacía que "
            "el importe neto restara de más: es el origen de las diez filas marcadas como «descuento mayor que el "
            "importe bruto» en el perfilado.",
            ejemplos["devoluciones"],
            "Se mantienen, marcadas como devolución, porque restan de la venta neta igual que haría un ERP. "
            "Además se revierte el signo del descuento para que acompañe al de las unidades. "
            "<strong>Alternativa descartada:</strong> excluirlas, que inventaría diez ventas que se devolvieron.",
            "Nueve devoluciones tras excluir los regalos. El ajuste del descuento afecta a <strong>una sola línea</strong>: "
            "una devolución de precio especial con 11,20 € de descuento.",
        ),
        bloque_decision_plegable(
            f"Se normalizaron {num(n['SKUs de venta normalizados a mayúsculas'])} SKUs escritos en minúsculas",
            "Quince líneas de venta traen el SKU en minúsculas (<code>eme010-bro-m</code> en lugar de "
            "<code>EME010-BRO-M</code>). Al cruzar con el catálogo aparecían como SKUs inexistentes.",
            ejemplos["sku_minusculas"],
            "Todos los SKUs pasan a mayúsculas sin espacios antes de cruzar nada. No hay alternativa razonable: "
            "son los mismos productos.",
            "Sin esta normalización se perderían <strong>quince ventas en silencio</strong>, sin ningún aviso.",
        ),
        bloque_decision_plegable(
            "Se normalizaron 26 mercados mal escritos y 14 quedaron como DESCONOCIDO",
            "El mercado aparece como <code>Spain</code> (10 líneas), <code>ESP</code> (9) y <code>es</code> (7). "
            "Otras 14 líneas no traen mercado.",
            ejemplos["mercados"],
            "Las 26 variantes pasan a <code>ES</code>. Los 14 nulos pasan a <code>DESCONOCIDO</code> y "
            "<strong>no se imputan</strong>: inventar un mercado para que cuadre un gráfico es peor que enseñar "
            "una categoría «desconocido».",
            "Los 14 nulos son el 0,08 % de las líneas y ninguno cae en la semana analizada, así que no aparecen "
            "en el desglose por mercado de este informe.",
        ),
        bloque_decision_plegable(
            "El SKU EME999-BLA-M se excluyó del análisis",
            "Tiene 14 unidades de stock en el almacén, pero no existe en el catálogo de producto y no se ha "
            "vendido nunca.",
            ejemplos["sku_fantasma"],
            "Se excluye del análisis: sin producto, color ni talla no se puede agregar por modelo ni calcular "
            "margen. Pero se reporta con nombre y apellidos, porque catorce unidades en almacén que el catálogo "
            "no conoce son un problema real de inventario.",
            "14 unidades fuera del análisis de stock. Es un aviso para almacén, no un error que podamos corregir "
            "desde los datos.",
        ),
        bloque_decision_plegable(
            "El identificador de modelo se construye con la referencia del SKU, no con el nombre",
            "La regla dice «modelo = producto + color», pero agrupando por el nombre comercial aparecen cuatro "
            "colisiones: productos distintos que comparten nombre y color. <code>ECHO BOMBER OLIVE</code> es a la "
            "vez una chaqueta de hombre a 100 € y una de mujer a 140 €, de drops diferentes.",
            ejemplos["modelo_colision"],
            "El identificador pasa a ser <strong>referencia del SKU + color</strong> (<code>EME045-OLI</code>), que "
            "es el producto de verdad. Para mostrar se usa el nombre comercial y, si dos lo comparten, se "
            "desambigua con el drop. <strong>Alternativa descartada:</strong> agrupar por nombre, que creaba "
            "modelos inexistentes con dos secciones y dos precios.",
            "De 119 a <strong>123 modelos</strong>. Sin esta corrección, cuatro modelos aparecerían fusionados en "
            "los rankings y en las alertas de stock, con un margen y un sell-through que no son de ninguno de los dos.",
        ),
        bloque_decision_plegable(
            "La rotura se calcula por talla, no sumando el modelo entero",
            "Agregando las tallas antes de comparar demanda con stock, la rotura desaparecía: ningún modelo rompía "
            "en conjunto, aunque 43 SKUs sí lo hacían.",
            "",
            "Se compara talla a talla y después se cuenta cuántas tallas del modelo están afectadas. Sumar tallas "
            "asume que son intercambiables, y no lo son: no se puede vender una M a quien necesita una M con el "
            "stock de XL.",
            "De <strong>0 modelos en rotura a 37 modelos y 43 tallas</strong>. Era el error más grave: el informe "
            "habría dicho que todo estaba bien.",
        ),
        bloque_decision_plegable(
            f"{num(n['Compras vencidas sin confirmar'])} compras vencidas no cuentan como stock en camino",
            f"37 pedidos a proveedor sin fecha real de llegada cuya fecha estimada ya pasó a la fecha de corte. "
            f"Además, {num(n['Compras que llegaron tarde'])} de 555 entregas llegaron tarde: el 77 %.",
            "",
            "Las compras vencidas se marcan y se excluyen del stock en camino al calcular la rotura. No hay "
            "constancia de que vayan a llegar, y contarlas llevaría a reponer de menos.",
            "Afecta a la pregunta 4 de este informe y será determinante en el Reto 2, donde la propuesta de "
            "reposición resta las compras pendientes.",
        ),
    ]
    return seccion("Referencia · transversal a los tres retos",
        "Decisiones y calidad de los datos", "decisiones",
        """Once decisiones han sido necesarias para que las cifras del informe existan. Ninguna es
        obvia y todas cambian algún número, así que están aquí con el dato original a la vista.
        <strong>Pulsa cualquiera para ver qué pasaba y cómo se trató.</strong>""",
        f"""
  {"".join(bloques)}

  <h3 style="margin-top:44px">Resumen auditable</h3>
  <p>Cuántas filas toca cada decisión. Se calcula al ejecutar la limpieza, no se escribe a mano.</p>
  <div class="card" style="margin-top:16px">{tabla_html(resumen, [
      ("concepto", "Concepto", "texto"),
      ("n_filas", "Filas", "num"),
  ])}</div>

  <h3 style="margin-top:44px">Lo que no hemos podido resolver</h3>
  <p>Tres cosas quedan abiertas y conviene tenerlas presentes al leer el informe:</p>
  <ul style="color:var(--tinta-2); max-width:70ch">
    <li style="margin-bottom:10px"><strong>Si los precios llevan IVA.</strong> Asumimos que no. Si lo llevasen,
    facturación y margen estarían sobrevalorados de forma proporcional, pero ninguna comparativa cambiaría.</li>
    <li style="margin-bottom:10px"><strong>El lead time real del proveedor no es medible.</strong> La tabla de
    compras no trae fecha de pedido, solo de llegada. Las 6 semanas del enunciado se toman como dadas.</li>
    <li><strong>Los 14 mercados desconocidos no se pueden recuperar.</strong> Aparecerán como categoría propia
    en cualquier desglose por mercado que los incluya.</li>
  </ul>""")


# ---------------------------------------------------------------------------
# Ensamblaje
# ---------------------------------------------------------------------------

# Estructura de la web. Cada entrada es un grupo del menú lateral con sus
# páginas. Los retos 2 y 3 ya figuran aquí para que la estructura se vea
# completa desde el principio; se rellenan cuando estén.
Pagina = tuple  # (id, etiqueta, badge)

ESTRUCTURA = [
    (
        "Reto 1 · Ventas y stock",
        [
            ("semana", "Cómo fue la semana", ""),
            ("reparto", "Reparto y precio especial", ""),
            ("modelos", "Modelos", ""),
            ("stock", "Rotura y exceso", ""),
            ("insights", "Más allá del enunciado", ""),
        ],
    ),
    (
        "Reto 2 · Reposición",
        [("reto2", "Propuesta semanal", "pendiente")],
    ),
    (
        "Reto 3 · Hoja de ruta",
        [("reto3", "IA a 6 meses", "pendiente")],
    ),
    (
        "Referencia",
        [
            ("glosario", "Glosario", ""),
            ("asunciones", "Asunciones", ""),
            ("decisiones", "Decisiones y datos", ""),
        ],
    ),
]

PAGINA_INICIAL = "semana"


def _menu_lateral() -> str:
    """Menú de navegación. Las páginas pendientes se ven, pero no se pulsan."""
    bloques = []
    for grupo, paginas in ESTRUCTURA:
        items = []
        for pid, etiqueta, badge in paginas:
            if badge:
                items.append(
                    f'<span class="nav-item pendiente">{etiqueta}'
                    f'<span class="nav-badge">{badge}</span></span>'
                )
            else:
                items.append(
                    f'<button class="nav-item" data-pagina="{pid}" data-etiqueta="{etiqueta}" '
                    f'onclick="mostrar(\'{pid}\')">{etiqueta}</button>'
                )
        bloques.append(f'<div class="nav-grupo">{grupo}</div>{"".join(items)}')
    return "".join(bloques)


def _siguiente_pagina(pid: str) -> str:
    """Enlace al siguiente apartado, para poder recorrer el informe en orden."""
    orden = [(p, e) for _, ps in ESTRUCTURA for p, e, b in ps if not b]
    ids = [p for p, _ in orden]
    if pid not in ids or pid == ids[-1]:
        return ""
    pid_sig, etiqueta = orden[ids.index(pid) + 1]
    return (
        f'<button class="siguiente" onclick="mostrar(\'{pid_sig}\')">'
        f'Siguiente: {etiqueta} <span class="flecha">→</span></button>'
    )


def _panel(pid: str, grupo: str, titulo: str, cuerpo: str) -> str:
    """Envuelve el contenido de una página con su cabecera y su enlace al siguiente."""
    return f"""
<div class="panel" id="pag-{pid}">
  <div class="pag-cabecera">
    <div class="pag-ruta">{grupo}</div>
    <h1>{titulo}</h1>
  </div>
  {cuerpo}
  {_siguiente_pagina(pid)}
</div>"""


def _panel_pendiente(pid: str, grupo: str, titulo: str, texto: str) -> str:
    """Hueco para un reto que todavía no está hecho. Se dice, no se disimula."""
    return f"""
<div class="panel" id="pag-{pid}">
  <div class="pag-cabecera"><div class="pag-ruta">{grupo}</div><h1>{titulo}</h1></div>
  <div class="card"><p>{texto}</p></div>
</div>"""


def construir_informe(
    metricas: Dict[str, pd.DataFrame],
    ejemplos: Dict[str, str],
    destino: Path,
) -> Path:
    """Ensambla la web completa y la escribe en `destino`. Devuelve la ruta.

    La web se navega por páginas, no por scroll: todos los paneles están en el
    documento pero solo uno es visible. Así los tres retos pueden convivir sin
    que el informe se convierta en un scroll interminable, y las secciones de
    referencia (glosario, asunciones, decisiones) quedan donde deben, fuera de
    cualquier reto porque valen para los tres.
    """
    _contador["n"] = 0
    ini, fin = config.SEMANA_ACTUAL

    paginas = [
        _seccion_semana(metricas),
        _seccion_reparto(metricas),
        _seccion_modelos(metricas),
        _seccion_stock(metricas),
        _seccion_insights(metricas),
        _seccion_glosario(),
        _seccion_asunciones(metricas),
        pagina_decisiones(ejemplos, metricas["resumen_limpieza"]),
    ]
    # El hero de KPIs encabeza la primera página del Reto 1.
    paginas[0]["html"] = _hero(metricas["comparativa"], metricas["margen_cupon"].iloc[0]) + paginas[0]["html"]

    paneles = [_panel(p["id"], p["ruta"], p["titulo"], p["html"]) for p in paginas]
    paneles.append(_panel_pendiente(
        "reto2", "Reto 2 · Reposición", "Propuesta semanal de reposición",
        "Pendiente. Aquí irá la propuesta automática de qué modelos y tallas reponer, "
        "con el plazo de entrega de 6 semanas y la cobertura objetivo de 8."))
    paneles.append(_panel_pendiente(
        "reto3", "Reto 3 · Hoja de ruta", "IA a 6 meses",
        "Pendiente. Aquí irá la hoja de ruta de IA para Compras, Ventas, Planificación, "
        "Logística, Producto, Marketing y Atención al cliente."))

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EME STUDIOS · Caso práctico AI Specialist</title>
<style>{design.css()}</style>
<script>{plotly.offline.get_plotlyjs()}</script>
<script>
const PAGINA_INICIAL = "{PAGINA_INICIAL}";
{design.js_tema()}
</script>
</head>
<body>
<div class="topbar">
  <button class="boton-menu" onclick="alternarMenu()">☰ Secciones</button>
  <span class="topbar-actual"></span>
</div>
<div class="layout">
  <aside class="sidebar">
    <div class="cabecera-lateral">
      <div class="marca">EME Studios</div>
      <p class="sidebar-titulo">Caso práctico<br>AI Specialist</p>
      <p class="sidebar-sub">Semana del {ini.day} al {fecha_larga(fin)}<br>Datos a cierre del {config.FECHA_CORTE_DATOS:%d/%m/%Y}</p>
    </div>
    <nav>{_menu_lateral()}</nav>
  </aside>
  <main class="contenido">
    {"".join(paneles)}
    <footer>
      <p>Generado automáticamente desde <code>EME_Caso_Practico_Datos.xlsx</code>.
      Reproducible con <code>python pipelines/run_reto1.py</code>.</p>
      <p>Las cifras excluyen los regalos a influencers y aplican las reglas de negocio del caso.
      El tratamiento de los datos está detallado en <em>Decisiones y datos</em>.</p>
    </footer>
  </main>
</div>
<button class="tema" onclick="alternarTema()">Tema oscuro</button>
</body>
</html>"""

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return destino
