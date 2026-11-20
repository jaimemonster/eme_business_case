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
from typing import Dict, Iterable, List, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io
import plotly.offline

from . import config, design, roadmap
from .metrics import UMBRAL_EXCESO_SEMANAS
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
    """Cuánto se desvía el stock de cada talla respecto a lo que pide la demanda.

    Una sola serie con el cero en medio: a la derecha lo que sobra, a la
    izquierda lo que falta. Comparar dos series de porcentajes obligaba a hacer
    la resta mentalmente; así la resta ya está hecha.

    Un solo color a propósito: ni sobrar ni faltar es bueno, así que verde y
    rojo mentirían. El signo y la etiqueta llevan el significado.
    """
    d = df.iloc[::-1]  # el eje y se dibuja de abajo arriba
    fig = go.Figure(
        go.Bar(
            x=d["desvio_uds"], y=d["talla"], orientation="h",
            marker=dict(color=C["acento"], line=dict(width=0)),
            text=[f"{'+' if v > 0 else ''}{num(v)} uds" for v in d["desvio_uds"]],
            textposition="outside",
            textfont=dict(size=12, color=C["tinta_2"]),
            width=0.6,
            hovertemplate="Talla %{y}<br>%{text}<extra></extra>",
        )
    )
    plantilla_grafico(fig, altura=300)
    tope = max(abs(d["desvio_uds"].min()), abs(d["desvio_uds"].max())) * 1.45
    fig.update_xaxes(showgrid=False, showticklabels=False, range=[-tope, tope],
                     zeroline=True, zerolinecolor=C["linea"], zerolinewidth=1)
    fig.update_yaxes(showgrid=False, ticklabelstandoff=10)
    fig.update_layout(margin=dict(l=0, r=8, t=4, b=4), bargap=0.3)
    return fig


def grafico_mapa_modelos(df: pd.DataFrame) -> go.Figure:
    """Cada modelo del catálogo situado por lo que vende y por lo que ha rotado.

    El tamaño del punto es el stock que queda, así que los problemas pesan
    visualmente: un punto grande abajo a la izquierda es mucho producto parado
    que además no se vende.

    Dos colores de énfasis, no de identidad: en rojo los que caen en la zona de
    poca rotación y poca venta. La línea del umbral y la nota dicen lo mismo que
    el color, así que no depende de distinguirlo.
    """
    umbral = df["umbral_sell_through"].iloc[0]
    problema = df["rota_poco"] & df["vende_poco"]
    tamanos = (df["stock_actual"] / df["stock_actual"].max() * 16 + 7).round(1)

    fig = go.Figure()
    for mascara, nombre, color in (
        (~problema, "Resto del catálogo", C["acento"]),
        (problema, "Ni venden ni rotan", C["negativo"]),
    ):
        d = df[mascara]
        fig.add_trace(
            go.Scatter(
                x=d["uds_semana"], y=d["sell_through_pct"],
                mode="markers", name=nombre,
                marker=dict(
                    color=color, size=tamanos[mascara], opacity=0.7,
                    line=dict(color=C["superficie"], width=1.5),
                ),
                customdata=d[["modelo_nombre", "stock_actual"]],
                hovertemplate=(
                    "%{customdata[0]}<br>%{x:.0f} uds esta semana<br>"
                    "Sell-through %{y:.1f} %<br>%{customdata[1]:,.0f} uds en stock<extra></extra>"
                ),
            )
        )
    plantilla_grafico(fig, altura=360)
    # La línea del umbral usa el gris de contexto, no el de rejilla: con el de
    # rejilla se perdía contra el fondo de la tarjeta.
    fig.add_hline(y=umbral, line=dict(color=C["referencia"], width=1))
    fig.add_annotation(
        x=1, xref="paper", y=umbral, yanchor="bottom", xanchor="right",
        text=f"sell-through {umbral:.0f} %", showarrow=False,
        font=dict(size=11, color=C["tinta_3"]),
    )
    fig.update_xaxes(
        title=dict(text="Unidades vendidas esta semana", font=dict(size=12, color=C["tinta_3"])),
        showgrid=False, range=[-1.2, df["uds_semana"].max() * 1.06],
    )
    fig.update_yaxes(ticksuffix=" %")
    fig.update_layout(margin=dict(l=0, r=8, t=8, b=36))
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
    # Etiquetas en dos líneas en vez de giradas: se leen sin inclinar la cabeza
    # y el gráfico no pierde alto por el ángulo.
    fig.update_xaxes(
        tickmode="array", tickvals=list(d["drop"]),
        ticktext=[x.replace(" DROP ", "<br>DROP ") for x in d["drop"]],
        tickfont=dict(size=11),
    )
    fig.update_yaxes(ticksuffix=" %", range=[0, 80])
    fig.update_layout(bargap=0.35, margin=dict(l=0, r=8, t=20, b=8))
    return fig


def grafico_proveedores(df: pd.DataFrame) -> go.Figure:
    """Puntualidad por proveedor: cuántas entregas llegan tarde y cuánto."""
    d = df.sort_values("pct_tarde", ascending=False)
    return _barras_horizontales(
        d["proveedor"],
        d["pct_tarde"],
        [f"{num(p)} % tarde  ·  {num(r, 1)} días de media" for p, r in zip(d["pct_tarde"], d["retraso_medio"])],
        altura=210,
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
<code>facturación neta ÷ unidades</code>, ya descontados los cupones. Sube un {num(var['precio_medio_ud'], 1)}&nbsp;%.
Con la mezcla de producto del año pasado habría <em>bajado</em> un {num(abs(mezcla['efecto_precio_pct']), 1)}&nbsp;%.
Lo que cambia es el peso de la chaqueta, que pasa del {num(chaqueta_ly, 1)}&nbsp;% al
{num(chaqueta_hoy, 1)}&nbsp;% de las unidades y es la categoría más cara.</p>"""

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
  <p class="nota">Arriba, las últimas 26 semanas frente a la misma semana ISO del año anterior. Abajo,
  la variación interanual. Como en todo el informe, <strong>sin las ventas a precio especial</strong>.</p>
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

    esp = m["parte_precio_especial"]
    ano = esp.iloc[1]
    pct_uds_ano, pct_eur_ano = num(ano["pct_uds"], 1), num(ano["pct_eur"], 1)
    # El porcentaje va en la misma celda que el absoluto: con una columna por
    # cada uno, la tabla no cabía en el ancho de la página.
    esp = esp.assign(
        uds_esp=[f'{num(u)} <span style="color:var(--tinta-3)">· {num(p, 1)} %</span>'
                 for u, p in zip(esp["uds_especial"], esp["pct_uds"])],
        eur_esp=[f'{eur(e)} <span style="color:var(--tinta-3)">· {num(p, 1)} %</span>'
                 for e, p in zip(esp["eur_especial"], esp["pct_eur"])],
    )
    t_especial = tabla_html(esp, [
        ("periodo", "Periodo", "texto"),
        ("unidades", "Uds totales", "num"),
        ("uds_esp", "A precio especial", "crudo"),
        ("facturacion_neta", "Facturación", "eur"),
        ("eur_esp", "A precio especial", "crudo"),
    ], destacar=[0])

    div_id = "g-especial"
    html_grafico, grupos, ejes = grafico_estacionalidad(m["estacionalidad_especial"], div_id)

    cuerpo = f"""
<div class="grid g2">
  <div class="card"><h3>Por mercado</h3><p class="nota" style="margin-bottom:12px">Facturación neta y peso sobre el total</p>{g_merc}</div>
  <div class="card"><h3>Por categoría</h3><p class="nota" style="margin-bottom:12px">Facturación neta y peso sobre el total</p>{g_cat}</div>
</div>
<div class="card" style="margin-top:20px"><h3>Por sección</h3>{t_sec}</div>

<h3 style="margin-top:36px">Qué parte se vendió a precio especial</h3>
<p>Ninguna esta semana. Esta tabla es el único sitio del informe donde aparece su peso. En lo que va
de año es el {pct_uds_ano}&nbsp;% de las unidades y el {pct_eur_ano}&nbsp;% de la facturación, porque
cada unidad rebajada ingresa un 40&nbsp;% menos.</p>
<div class="card" style="margin-top:16px">{t_especial}</div>

<h3 style="margin-top:36px">Y se concentra en campañas</h3>
<p>Rebajas de enero, rebajas de verano y Black&nbsp;Friday. Fuera de esas ventanas es prácticamente cero.</p>
<div class="card" style="margin-top:16px">
  {selector(div_id, [etiqueta for _, _, etiqueta, _ in METRICAS_ESPECIAL])}
  {leyenda(("A precio especial", C["acento"]), ("A precio completo", C["referencia"]))}
  {html_grafico}
  {registrar(div_id, grupos, ejes)}
  <p class="nota">«A precio completo» es toda la venta que no es liquidación, incluidas las líneas con
  cupón WELCOME10. Los dos trozos de cada barra suman el total del mes. Cada unidad rebajada factura en
  torno a un 40&nbsp;% menos.</p>
</div>

<h3 style="margin-top:36px">Dónde pesa el cupón WELCOME10</h3>
<p>El cupón descuenta un 10&nbsp;% sobre tarifa y cuenta como venta ordinaria, no como liquidación al
40&nbsp;%. <strong>El descuento ya está restado de la facturación</strong>, así que el margen lo absorbe
una sola vez. La última columna es lo que el cupón deja de ingresar.</p>
<div class="card" style="margin-top:16px">{t_promo}
<p class="nota"><strong>El porcentaje es sobre facturación, no sobre unidades</strong>, y no coinciden
porque el cupón no se reparte igual entre producto caro y barato. En Alemania son 9 de 53 unidades
(el {pct(merc[merc.mercado == "DE"].iloc[0]["pct_promocion_uds"])}) y el
{pct(merc[merc.mercado == "DE"].iloc[0]["pct_promocion"])} de la facturación.<br>
<strong>Descuento dado</strong> es la columna <code>Descuento (€)</code> del Excel sumada sobre esas
líneas, y se <strong>resta</strong> del importe de tarifa. Esta semana el cupón deja de ingresar
<strong>{eur(merc["coste_cupon"].sum(), 2)}</strong>, y el margen de sus líneas es del {pct(margen_promo)}
frente al {pct(margen_sin)} de las que no lo llevan.</p></div>"""

    return seccion(
        "Reto 1 · Pregunta 2", "Cómo se reparte, y qué se vendió rebajado", "reparto",
        "<strong>Esta semana no se ha vendido ni una unidad a precio especial</strong>. En EME el precio "
        "especial es estacional y se concentra en campañas. Lo que sí está activo es el cupón "
        "<strong>WELCOME10</strong>.",
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
    mapa = m["mapa_modelos"]
    problema = mapa[mapa["rota_poco"] & mapa["vende_poco"]]
    mediana = mapa["mediana_uds"].iloc[0]
    umbral_st = mapa["umbral_sell_through"].iloc[0]
    g_mapa = grafico(grafico_mapa_modelos(mapa))

    cuerpo = f"""
<div class="card">
  {leyenda(("Resto del catálogo", C["acento"]), ("Venden poco y rotan poco", C["negativo"]))}
  {g_mapa}
  <p class="nota"><strong>Un punto = un modelo.</strong> A la derecha, lo vendido esta semana. Arriba, la
  parte de lo comprado que ya se ha colocado. El tamaño del punto es el stock que queda.<br>
  <strong>En rojo</strong>, los que vendieron {num(mediana)} unidades o menos esta semana <em>y</em> están
  por debajo del {num(umbral_st)}&nbsp;% de sell-through: <strong>{num(len(problema))} modelos</strong> con
  <strong>{num(problema["stock_actual"].sum())} unidades</strong> en el almacén.
  <strong>En azul</strong>, los {num(len(mapa) - len(problema))} restantes.</p></div>

<div class="card" style="margin-top:20px"><h3>Los 10 que más venden</h3>
<p class="nota" style="margin-bottom:14px">Unidades de la semana analizada, con la semana anterior y lo
vendido en 2025 al lado para situar el ritmo. El sell-through es de toda la vida del modelo.</p>
{tabla_html(top, cols)}</div>

<div class="card" style="margin-top:20px"><h3>Los 10 que menos venden</h3>
<p class="nota" style="margin-bottom:14px">Muchos modelos empatan a una unidad, así que entre ellos
ordena lo vendido en el año.</p>
{tabla_html(bottom, cols)}</div>

<div class="card" style="margin-top:20px"><h3>Con stock y sin una sola venta en {semanas_sin} semanas</h3>
<p class="nota" style="margin-bottom:14px">No aparecen en los rankings porque no vendieron nada. No vender
una semana es normal; no vender en {semanas_sin}, con stock en el almacén, no.</p>
{t_sin}</div>

<h3 style="margin-top:36px">La facturación está muy concentrada</h3>
<div class="grid g3" style="margin-top:16px">{tiles}</div>"""

    return seccion(
        "Reto 1 · Pregunta 3", "Qué modelos tiran y cuáles no", "modelos", "",
        cuerpo,
    )


def _seccion_stock(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    cg = m["cobertura_global"].iloc[0]
    rot, exc = m["rotura_por_modelo"], m["exceso_por_modelo"]
    valor_pvp = m["exceso_a_pvp"].iloc[0]["valor_pvp"]
    umbral, objetivo = UMBRAL_EXCESO_SEMANAS, config.COBERTURA_OBJETIVO_SEMANAS
    comp = m["composicion_stock"]
    g_comp = grafico(_barras_horizontales(
        comp["grupo"], comp["stock_uds"],
        [f"{num(u)} uds  ·  {num(n)} modelos" for u, n in zip(comp["stock_uds"], comp["modelos"])],
        colores=[C["negativo"]] + [C["acento"]] * (len(comp) - 1),
        altura=210,
    ))
    n_exceso = len(exc)

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
  <div class="card"><div class="dato">{num(cg['stock_total_uds'])}</div>
    <div class="dato-lbl">unidades en el almacén a fecha de cierre</div></div>
  <div class="card"><div class="dato">{num(cg['cobertura_global_semanas'], 1)}</div>
    <div class="dato-lbl">semanas que aguanta ese stock al ritmo de venta previsto, sin reponer nada.
    EME quiere tener {int(cg['cobertura_objetivo_semanas'])}</div></div>
  <div class="card"><div class="dato alerta">{len(rot)}</div>
    <div class="dato-lbl">modelos a los que les faltará alguna talla dentro de 4 semanas
    ({int(rot['tallas_en_rotura'].sum())} tallas en total)</div></div>
  <div class="card"><div class="dato">{eur(exc['capital_inmovilizado'].sum())}</div>
    <div class="dato-lbl">valor a coste de las unidades que sobran por encima de las
    {int(cg['cobertura_objetivo_semanas'])} semanas objetivo</div></div>
</div>

<div class="card" style="margin-top:28px">
  {leyenda(("Le falta una talla y le sobra otra", C["negativo"]), ("Resto del catálogo", C["acento"]))}
  {g_comp}
  <p class="nota">Los {num(cg["modelos_totales"])} modelos repartidos por su estado de stock.
  <strong>{num(comp.iloc[0]["modelos"])} están en rotura y en exceso a la vez</strong>, con una talla a cero
  y otra con stock para meses, y acumulan {num(comp.iloc[0]["stock_uds"])} unidades. El problema está en
  cómo se reparte el stock.</p>
</div>

<h3 style="margin-top:36px">Modelos en rotura en 4 semanas</h3>
<p>Un modelo entra aquí si le falta <strong>alguna talla</strong>. No se puede vender una M con el
stock de XL.</p>
<div class="card" style="margin-top:16px">{t_rot}
<p class="nota"><strong>Disponible</strong> = lo que hay en almacén de esas tallas más las compras que
llegan dentro de las 4 semanas. <strong>Faltan</strong> = demanda − disponible. La última columna es el
stock del modelo entero. Las 12 primeras de {len(rot)}.</p></div>

<h3 style="margin-top:36px">Modelos con exceso de stock</h3>
<p>Un modelo entra aquí si su cobertura supera las <strong>{umbral} semanas</strong>, el doble de la
objetivo. Da casi igual dónde se ponga el umbral. Entre 8 y 16 semanas salen los mismos {n_exceso}
modelos (<em>Asunciones</em> lleva la tabla).</p>
<p>La lista va ordenada por <strong>capital inmovilizado</strong>. La cobertura se dispara en productos
baratos que casi no rotan, y lo que decide dirección es cuánto dinero hay parado.</p>
<div class="card" style="margin-top:16px">{t_exc}
<p class="nota">Las 12 primeras de {len(exc)}. Son dos parámetros distintos: las {umbral} semanas deciden
<em>quién entra</em> en la lista y las {objetivo} de cobertura objetivo, <em>cuánto sobra</em>.
<strong>Unidades sobrantes</strong> = stock − demanda semanal × {objetivo} semanas.
<strong>Capital parado</strong> = esas unidades <strong>a coste</strong>. A precio de venta serían
{eur(valor_pvp)}, pero ese dinero no se ha gastado.</p></div>"""

    return seccion("Reto 1 · Pregunta 4", "Qué va a romper y qué sobra", "stock", "", cuerpo)


def _seccion_insights(m: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """Lo que no pide el enunciado pero sale al leer las cuatro respuestas.

    Tres hallazgos, uno por gráfico, sin tablas que repitan lo que el gráfico ya
    dice. Se han quitado dos que estaban en el informe por duplicado: el origen
    del crecimiento vive en la pregunta 1 y la concentración de catálogo en la 3.
    """
    tallas = m["curva_tallas"]
    n_rotura = len(m["rotura_por_modelo"])
    prov = m["fiabilidad_proveedores"]
    drops = m["sell_through_drop"]
    atascado = drops[(drops["semanas_vida"] > 20) & (drops["sell_through_pct"] < 40)]

    talla_m = tallas[tallas["talla"] == "M"].iloc[0]
    sobran = tallas[tallas["desvio_uds"] > 0]["desvio_uds"].sum()
    tarde = prov["pct_tarde"].min(), prov["pct_tarde"].max()
    retraso = prov["retraso_medio"].mean()
    vencidas = int(prov["vencidas"].sum())
    d = atascado.iloc[0] if len(atascado) else None

    cuerpo = f"""
<h3>1 · El almacén tiene las tallas equivocadas</h3>
<p>Hay stock de sobra y aun así {n_rotura} modelos van a romper. Faltan
<strong>{num(abs(talla_m["desvio_uds"]))} unidades de la M</strong>, la talla que más se vende, y sobran
<strong>{num(sobran)}</strong> en XL y XXL.</p>
<div class="card" style="margin-top:16px">{grafico(grafico_curva_tallas(tallas))}
<p class="nota">Diferencia entre el stock de cada talla y el que le tocaría con el reparto de la demanda
de las últimas 12 semanas. Se arregla en el Reto 2 cambiando la curva del pedido.</p></div>

<h3 style="margin-top:44px">2 · Los cuatro proveedores llegan tarde por igual</h3>
<p><strong>Llegan tarde entre el {num(tarde[0], 0)}&nbsp;% y el {num(tarde[1], 0)}&nbsp;% de las
veces</strong>, con un retraso medio casi idéntico de {num(retraso, 1)} días. Cuando todos fallan igual,
el problema está en la fecha.</p>
<div class="card" style="margin-top:16px">{grafico(grafico_proveedores(prov))}
<p class="nota">Además hay <strong>{vencidas} pedidos vencidos sin confirmar</strong>, con la fecha
estimada pasada y ninguna constancia de que hayan llegado. Sumar una semana a toda fecha estimada sale
gratis.</p></div>

<h3 style="margin-top:44px">3 · El drop {d["drop"] if d is not None else "—"} se ha quedado atascado</h3>
<p>Cuanto más viejo es un drop, más vendido está. <strong>{d["drop"] if d is not None else "—"}</strong>
se sale de la curva: lleva {int(d["semanas_vida"]) if d is not None else 0} semanas en el mercado y vende
peor que drops más nuevos. Son <strong>{eur(d["capital"]) if d is not None else "—"}</strong> parados en
producto que no arranca.</p>
<div class="card" style="margin-top:16px">{grafico(grafico_drops(drops))}
<p class="nota">Sell-through de cada drop, ordenados del más antiguo al más reciente. Es el candidato
natural para Black&nbsp;Friday, a dos o tres semanas.</p></div>"""

    return seccion(
        "Reto 1 · Más allá del enunciado",
        "Tres cosas que los datos dicen sin que nadie las pregunte",
        "insights",
        "Las cuatro preguntas del informe se responden solas. Estas tres salen de mirar <em>por qué</em> "
        "salen esos números, y las tres cambian algo del Reto 2.",
        cuerpo,
    )


def _seccion_glosario(catalogo: pd.Series) -> Dict[str, str]:
    """Qué significa cada término, con su fórmula y un ejemplo real."""
    terminos = [
        termino(
            "Modelo y SKU",
            "Un <strong>modelo</strong> es la combinación de producto y color: lo que se diseña y se compra. "
            "Un <strong>SKU</strong> es el modelo en una talla concreta: lo que está físicamente en la estantería "
            "y lo que se vende o se agota.",
            "NOVA BOMBER + GREY MELANGE  =  1 modelo\n  └─ EME095-GRE-XS / S / M / L / XL  =  5 SKUs",
            f"En este catálogo: {num(catalogo['modelos'])} modelos y {num(catalogo['skus'])} SKUs, "
            f"unas {num(catalogo['tallas_por_modelo'], 1)} tallas por modelo.",
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
            "Stock muy por encima de lo que se va a vender. Se mide con la cobertura y se ordena por dinero, "
            "porque la cobertura se dispara en productos baratos que casi no rotan.",
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
<p>Las 16 semanas las elegimos nosotros. Mover el umbral cambia poco: entre 8 y 16 semanas salen los
mismos modelos, y hay que irse a un año entero de cobertura para bajar de la mitad del catálogo.</p>
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
            "Regla del enunciado. Fuera de todo análisis de venta. Se conservan en una tabla aparte porque sí "
            "consumen stock.",
            "559 líneas fuera de la venta. En la tabla se ven también <code>WELCOME10</code> y las variantes "
            "<code>SPECIAL XX</code>, que el enunciado no menciona.",
        ),
        bloque_decision_plegable(
            "WELCOME10 cuenta como venta a precio completo, no como precio especial",
            "Aparece una etiqueta que el enunciado no menciona, en 999 líneas (5,5 % del total). Descuenta "
            "exactamente un 10 %, frente al ~40 % de <code>special</code> y el 100 % de <code>influencers</code>.",
            "",
            "Es una venta a tarifa con un cupón encima. Entra en precio completo con un flag propio. "
            "<strong>Alternativa descartada:</strong> meterla en <code>special</code>, que mezclaría un 10 % "
            "con un 40 %.",
            "Cambia el reparto de la pregunta 2. Sin esto, el «0 % a precio especial» de la semana sería un 8,8 %.",
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
            "<code>unidades = 2</code>, así que dos líneas idénticas apuntan a un error de carga. "
            "<strong>Alternativa descartada:</strong> conservarlas, por si el sistema creara una línea por unidad.",
            "−25 líneas sobre 18.292 (0,1 %). De ellas, 2 eran regalos y 5 de precio especial.",
        ),
        bloque_decision_plegable(
            f"Las {num(n['Devoluciones conservadas (unidades negativas)'])} líneas con unidades negativas se conservan como devoluciones",
            "Diez líneas con <code>unidades = −1</code>. Además traen el descuento en positivo, lo que hacía que "
            "el importe neto restara de más: es el origen de las diez filas marcadas como «descuento mayor que el "
            "importe bruto» en el perfilado.",
            ejemplos["devoluciones"],
            "Se mantienen marcadas como devolución, porque restan de la venta neta igual que haría un ERP, y se "
            "revierte el signo del descuento. <strong>Alternativa descartada:</strong> excluirlas, que inventaría "
            "diez ventas que se devolvieron.",
            "Nueve devoluciones tras excluir los regalos. El ajuste del descuento afecta a <strong>una sola línea</strong>: "
            "una devolución de precio especial con 11,20 € de descuento.",
        ),
        bloque_decision_plegable(
            f"Se normalizaron {num(n['SKUs de venta normalizados a mayúsculas'])} SKUs escritos en minúsculas",
            "Quince líneas de venta traen el SKU en minúsculas (<code>eme010-bro-m</code> en lugar de "
            "<code>EME010-BRO-M</code>). Al cruzar con el catálogo aparecían como SKUs inexistentes.",
            ejemplos["sku_minusculas"],
            "Todos los SKUs pasan a mayúsculas sin espacios antes de cruzar nada. Son los mismos productos.",
            "Sin esta normalización se perderían <strong>quince ventas en silencio</strong>, sin ningún aviso.",
        ),
        bloque_decision_plegable(
            "Se normalizaron 26 mercados mal escritos y 14 quedaron como DESCONOCIDO",
            "El mercado aparece como <code>Spain</code> (10 líneas), <code>ESP</code> (9) y <code>es</code> (7). "
            "Otras 14 líneas no traen mercado.",
            ejemplos["mercados"],
            "Las 26 variantes pasan a <code>ES</code>. Los 14 nulos pasan a <code>DESCONOCIDO</code> y "
            "<strong>no se imputan</strong>, porque no hay forma de saber de dónde venían.",
            "Los 14 nulos son el 0,08 % de las líneas y ninguno cae en la semana analizada, así que no aparecen "
            "en el desglose por mercado de este informe.",
        ),
        bloque_decision_plegable(
            "El SKU EME999-BLA-M se excluyó del análisis",
            "Tiene 14 unidades de stock en el almacén, pero no existe en el catálogo de producto y no se ha "
            "vendido nunca.",
            ejemplos["sku_fantasma"],
            "Sin producto, color ni talla no se puede agregar por modelo ni calcular margen, así que queda fuera. "
            "Se reporta por su nombre: catorce unidades que el catálogo no conoce son un problema de inventario.",
            "14 unidades fuera del análisis de stock. Es un aviso para almacén.",
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
            "De 119 a <strong>123 modelos</strong>. Sin esto, cuatro aparecerían fusionados en los rankings con un "
            "margen y un sell-through que no son de ninguno de los dos.",
        ),
        bloque_decision_plegable(
            "La rotura se calcula por talla, no sumando el modelo entero",
            "Agregando las tallas antes de comparar demanda con stock, la rotura desaparecía: ningún modelo rompía "
            "en conjunto, aunque 43 SKUs sí lo hacían.",
            "",
            "Se compara talla a talla y después se cuenta cuántas tallas del modelo están afectadas. Sumarlas asume "
            "que son intercambiables.",
            "De <strong>0 modelos en rotura a 37 modelos y 43 tallas</strong>. Con la versión anterior el informe "
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
# ---------------------------------------------------------------------------
# Reto 3 · Hoja de ruta de IA
# ---------------------------------------------------------------------------
# El contenido vive en `src/roadmap.py`; aquí solo se dibuja. Son cinco
# páginas, una por punto del enunciado, pensadas para explicarse en metro y
# medio cada una: la conclusión de arriba es literalmente la frase que se dice
# en voz alta, y el detalle queda plegado para las preguntas.

def grafico_r3_dolor(c: Dict[str, float]) -> go.Figure:
    """Lo que se vende en un año contra lo que duerme en el almacén."""
    cl = design.TOKENS["claro"]
    fig = _barras_horizontales(
        ["Vendido en 12 meses", "En el almacén hoy"],
        [c["unidades_12m"], c["stock_uds"]],
        [f'{num(c["unidades_12m"])} uds', f'{num(c["stock_uds"])} uds'],
        colores=[cl["referencia"], cl["acento"]],
        altura=150,
    )
    return fig


def grafico_r3_matriz() -> go.Figure:
    """Impacto × esfuerzo. El tamaño de cada burbuja son las horas liberadas."""
    cl = design.TOKENS["claro"]
    ini = roadmap.INICIATIVAS
    x = [i["esfuerzo"] for i in ini]
    y = [i["euros_rec"] + i["euros_unavez"] for i in ini]
    horas = [i["horas"] for i in ini]
    tam = [16 + (h / 312) * 22 for h in horas]
    simbolo = ["diamond" if "B" in i["tipo"] else "circle" for i in ini]

    fig = go.Figure()
    # Las dos líneas que parten los cuadrantes. El corte de impacto en 7.500 €
    # y el de esfuerzo en dos semanas y media son convenciones, no verdades:
    # sirven para leer el gráfico, no para decidir por sí solas.
    fig.add_vline(x=2.5, line_width=1, line_dash="dot", line_color=cl["linea"])
    fig.add_hline(y=7500, line_width=1, line_dash="dot", line_color=cl["linea"])
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers+text",
        marker=dict(size=tam, color=cl["acento"], opacity=0.85, symbol=simbolo,
                    line=dict(width=0)),
        text=[str(i["n"]) for i in ini],
        textposition="middle center",
        textfont=dict(size=11, color="#ffffff", family=design.TIPOGRAFIA),
        customdata=[[i["nombre"], i["dept"], i["horas"], i["esfuerzo"]] for i in ini],
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                       "%{y:,.0f} € el primer año · %{customdata[2]} h/año<br>"
                       "%{customdata[3]} semanas hasta producción<extra></extra>"),
    ))
    for xq, yq, texto in [
        (1.05, 34000, "Hazlo ya"), (4.6, 34000, "Proyecto con dueño"),
        (1.05, 600, "Rápidas"), (4.6, 600, "Justifícala por otra cosa"),
    ]:
        fig.add_annotation(x=xq, y=yq, text=texto, showarrow=False,
                           font=dict(size=11, color=cl["tinta_3"]),
                           xanchor="left" if xq < 2.5 else "right")
    fig = design.plantilla_grafico(fig, altura=420, margen_izq=60)
    fig.update_xaxes(title=None, range=[0.3, 5.7], dtick=1,
                     ticksuffix=" sem", showgrid=False)
    fig.update_yaxes(title=None, range=[-2500, 38000], tickprefix="",
                     ticksuffix=" €", tickformat=",.0f")
    return fig


def grafico_r3_calendario() -> go.Figure:
    """Las once iniciativas repartidas en seis meses."""
    cl = design.TOKENS["claro"]
    ini = sorted(roadmap.INICIATIVAS, key=lambda i: (i["mes_ini"], i["n"]))
    etiquetas = [f'{i["n"]} · {i["nombre"]}' for i in ini]
    base = [i["mes_ini"] - 1 for i in ini]
    largo = [i["mes_fin"] - i["mes_ini"] + 1 for i in ini]
    # Las victorias rápidas se pintan con el acento; el resto en gris, para que
    # los primeros 60 días salten a la vista sin leer una sola palabra.
    colores = [cl["acento"] if i["quick"] else cl["referencia"] for i in ini]

    fig = go.Figure(go.Bar(
        x=largo, y=etiquetas, base=base, orientation="h",
        marker=dict(color=colores), width=0.62,
        customdata=[[i["dept"], roadmap.CALENDARIO_FOCO[i["mes_ini"]]] for i in ini],
        hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
    ))
    fig.add_vline(x=2, line_width=1, line_dash="dot", line_color=cl["acento"])
    fig.add_annotation(x=2, y=1.04, yref="paper", text="60 días", showarrow=False,
                       xanchor="left", font=dict(size=11, color=cl["acento"]))
    fig = design.plantilla_grafico(fig, altura=430, margen_izq=240)
    fig.update_xaxes(range=[0, 6], tickvals=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
                     ticktext=[f"Mes {n}" for n in range(1, 7)], showgrid=True,
                     gridcolor=cl["linea"])
    fig.update_yaxes(autorange="reversed", showgrid=False,
                     tickfont=dict(size=12, color=cl["tinta_2"]))
    return fig


def _ficha_iniciativa(i: Dict) -> str:
    """Una iniciativa plegada: cerrada se ve el titular, abierta el porqué."""
    peldano = dict((n, t) for n, t, _ in roadmap.ESCALERA)[str(i["peldano"])]
    estado = " · <strong>ya construida</strong>" if i.get("hecho") else ""
    return f"""
<details>
  <summary>{i["n"]} · {i["nombre"]} <span class="nota" style="margin:0;border:0;padding:0">
    — {i["dept"]}{estado}</span></summary>
  <div class="detalle"><dl>
    <dt>Qué pasa hoy</dt><dd>{i["problema"]}</dd>
    <dt>Qué hace</dt><dd>{i["que_hace"]}</dd>
    <dt>De dónde sale el número</dt><dd>{i["formula"]}</dd>
    <dt>Error que evita</dt><dd>{i["error"]}</dd>
    <dt>Peldaño {i["peldano"]}</dt><dd>{peldano}. Se mide con «{i["kpi"]}»,
      de {i["base"]} a {i["objetivo"]}.</dd>
  </dl></div>
</details>"""


def _seccion_r3_dolor(c: Dict[str, float]) -> Dict[str, str]:
    """Antes de proponer nada: dónde está el dinero de esta marca."""
    tarjetas = [
        kpi("Margen en 12 meses", c["margen_12m"], "€", [],
            pie=f'Sobre {eur(c["facturacion_12m"])} de facturación neta'),
        kpi("Capital parado en exceso", c["exceso_coste"], "€", [],
            pie=f'{int(c["modelos_exceso"])} de {int(c["modelos_total"])} modelos por encima del umbral'),
        kpi("Entregas que llegan tarde", c["pct_tarde"], "%", [],
            pie=f'{int(c["entregas_tarde"])} de {int(c["entregas"])} entregas, {num(c["retraso_medio"], 1)} días de media'),
        kpi("Facturación fuera de España", c["pct_fuera_es"], "%", [],
            pie=f'Repartida en {int(c["mercados"]) - 1} países y seis idiomas'),
    ]

    cuerpo = f"""
<div class="grid g4" style="margin-bottom:28px">{"".join(tarjetas)}</div>

<div class="card">
  <h3 style="margin-top:0">Hay más ropa en el almacén que la vendida en todo el año</h3>
  {grafico(grafico_r3_dolor(c))}
  <p class="nota">Cobertura global de <strong>{num(c["cobertura_semanas"], 1)} semanas</strong> contra las 8 de
  objetivo, y la mediana de los modelos con exceso llega a {num(c["cobertura_mediana"], 0)}. Aun así hay
  <strong>{int(c["modelos_rotura"])} modelos que rompen</strong> en cuatro semanas.</p>
</div>

<p class="nota" style="margin-top:28px">Las cuatro cifras salen de las mismas tablas que el
informe del Reto 1 y se recalculan con él.</p>"""

    return seccion(
        "Reto 3 · Hoja de ruta", "Dónde duele antes de proponer nada", "r3_dolor",
        f'Hay <strong>{eur(c["exceso_coste"])} parados</strong> en el almacén y '
        f'<strong>{int(c["conc_modelos"])} modelos</strong> hacen la mitad de la facturación. '
        "De ahí sale el reparto de los seis meses.",
        cuerpo,
    )


def _seccion_r3_metodo() -> Dict[str, str]:
    """Punto 1 del enunciado: cómo se desgrana el trabajo de la gente."""
    pasos = "".join(
        f'<div class="card"><div class="dato">{n}</div>'
        f'<div class="dato-lbl" style="font-size:15px;color:var(--tinta);margin-top:10px">'
        f'<strong>{titulo}</strong></div>'
        f'<p style="font-size:13px;margin:8px 0 0">{que}</p>'
        f'<p class="nota">{como}</p></div>'
        for n, (titulo, que, como) in enumerate(roadmap.METODO, start=1)
    )

    verbos = tabla_html(pd.DataFrame([
        {"v": f"<strong>{v}</strong>", "q": q, "t": t} for v, q, t in roadmap.VERBOS
    ]), [("v", "Verbo", "crudo"), ("q", "Qué es", "texto"), ("t", "Qué lo automatiza", "texto")])

    comunes = "".join(
        f'<li><strong>{p}</strong><br><span class="nota" style="margin:0;border:0;padding:0">{busco}</span></li>'
        for p, busco in roadmap.PREGUNTAS_COMUNES
    )

    deptos = tabla_html(pd.DataFrame([
        {"d": f'<strong>{d["nombre"]}</strong>',
         "p": "<br>".join(f"· {q}" for q in d["preguntas"])}
        for d in roadmap.DEPARTAMENTOS
    ]), [("d", "Departamento", "crudo"), ("p", "Las dos preguntas propias", "crudo")])

    return seccion(
        "Reto 3 · Hoja de ruta", "Cómo desgrano el trabajo de cada equipo", "r3_metodo",
        "Pido <strong>los tres últimos ficheros que hicieron</strong> y parto el trabajo en tareas. "
        "Cada tarea cae en uno de cuatro verbos, y el verbo decide la tecnología.",
        f"""
<div class="grid g4">{pasos}</div>

<h3 style="margin-top:44px">El verbo de la tarea decide la tecnología</h3>
<p>De las once iniciativas, <strong>{roadmap.totales()["con_ia_dentro"]} llevan IA dentro del
proceso</strong>. El resto es código determinista, escrito con un agente. Por eso caben once en seis
meses.</p>
{verbos}

<h3 style="margin-top:44px">Seis preguntas para todos</h3>
<p>Una por casilla de la ficha. Lo propio de cada equipo son las dos de la tabla siguiente.</p>
<div class="card"><ol style="margin:0;padding-left:20px;line-height:1.6">{comunes}</ol>
<p class="nota">La sexta filtra más que las otras cinco.</p></div>

<h3 style="margin-top:44px">Las preguntas propias de cada departamento</h3>
{deptos}""",
    )


def _seccion_r3_iniciativas() -> Dict[str, str]:
    """Punto 2 del enunciado: las once, con su impacto y su esfuerzo."""
    t = roadmap.totales()
    cabecera = "".join([
        kpi("Horas de persona al año", t["horas"], "uds", [],
            pie="Trabajo que hoy se hace a mano y deja de hacerse"),
        kpi("Ahorro recurrente", t["euros_rec"], "€", [],
            pie="Al año, cuando las once estén en marcha"),
        kpi("Capital liberado", t["euros_unavez"], "€", [],
            pie="Una sola vez, al dar salida al exceso. No es recurrente y no se suma"),
        kpi("Llevan IA dentro", t["con_ia_dentro"], "uds", [],
            pie="De once. Las otras cinco son código escrito con un agente"),
    ])

    filas = pd.DataFrame([{
        "n": i["n"],
        "dept": i["dept"],
        "nombre": (f'<strong>{i["nombre"]}</strong>'
                   + (' <span class="tag tag-dato">hecho</span>' if i.get("hecho") else "")),
        "tipo": i["tipo"],
        "horas": i["horas"] or None,
        # Las dos iniciativas sin euros propios se marcan como habilitadoras en
        # vez de enseñar un cero, que se leería como «no sirve».
        "euros": (eur(i["euros_rec"] + i["euros_unavez"])
                  if i["euros_rec"] + i["euros_unavez"] else "habilitadora"),
        "esf": f'{i["esfuerzo"]} sem',
    } for i in roadmap.INICIATIVAS])
    tabla = tabla_html(filas, [
        ("n", "#", "num"), ("dept", "Departamento", "texto"),
        ("nombre", "Iniciativa", "crudo"), ("tipo", "Tipo", "texto"),
        ("horas", "Horas/año", "num"), ("euros", "€ primer año", "crudo"),
        ("esf", "Esfuerzo", "texto"),
    ])

    fichas = "".join(_ficha_iniciativa(i) for i in roadmap.INICIATIVAS)

    return seccion(
        "Reto 3 · Hoja de ruta", "Once iniciativas, repartidas donde duele", "r3_iniciativas",
        f'Once iniciativas para siete departamentos. <strong>{t["con_ia_dentro"]} llevan IA dentro</strong> '
        "del proceso. Las otras cinco son código, escrito con un agente.",
        f"""
<div class="grid g4" style="margin-bottom:28px">{cabecera}</div>

{leyenda(("A · la IA construye el código; en producción corre lógica determinista", design.TOKENS["claro"]["referencia"]),
         ("B · la IA está dentro del proceso: lenguaje, voz o modelo", design.TOKENS["claro"]["acento"]))}
{tabla}
<p class="nota">Horas a 25 €/h de coste empresa. El capital de la 4 se libera una vez y no se mezcla
con el ahorro anual. De la 9 solo se cuentan sus horas: los euros de liquidación ya están en la 3.</p>

<h3 style="margin-top:44px">Cada una, por dentro</h3>
{fichas}

<h3 style="margin-top:44px">El cimiento de las once</h3>
<div class="card">
  <h3 style="margin-top:0">{roadmap.CIMIENTO["nombre"]}</h3>
  <p>{roadmap.CIMIENTO["que_hace"]}</p>
  <p class="nota">{roadmap.CIMIENTO["porque"]}</p>
</div>""",
    )


def _seccion_r3_prioridad() -> Dict[str, str]:
    """Puntos 3 y 4 del enunciado: la matriz y el calendario, juntos.

    Van en la misma página a propósito: son la misma historia contada dos veces
    —así las priorizo, así caen en el tiempo— y separarlas obligaba a saltar de
    página en mitad de la frase.
    """
    rapidas = "".join(
        f'<div class="card"><div class="dato">{i["n"]}</div>'
        f'<div class="dato-lbl" style="font-size:15px;color:var(--tinta);margin-top:10px">'
        f'<strong>{i["nombre"]}</strong></div>'
        f'<p class="nota">{i["kpi"]}: de {i["base"]} a {i["objetivo"]}.</p></div>'
        for i in roadmap.quick_wins()
    )

    return seccion(
        "Reto 3 · Hoja de ruta", "Cómo las priorizo y cuándo caen", "r3_prioridad",
        "El esfuerzo lo marcan <strong>el acceso al dato y quién valida el resultado</strong>. "
        "Programar ya no es el cuello de botella.",
        f"""
<div class="card">
  <h3 style="margin-top:0">Impacto × esfuerzo</h3>
  {grafico(grafico_r3_matriz())}
  <p class="nota" style="border:0;padding:0;margin-top:14px">
  <strong>●</strong> la IA solo construye el código &nbsp;·&nbsp; <strong>◆</strong> la IA va dentro del proceso</p>
  <p class="nota">Eje horizontal, <strong>semanas hasta producción</strong>. Dentro va conseguir el dato,
  acordar quién valida y las vueltas hasta que alguien lo usa. Eje vertical, euros del primer año.
  El tamaño de la burbuja son las horas liberadas al año.</p>
</div>

<div class="card" style="margin-top:28px">
  <h3 style="margin-top:0">Seis meses</h3>
  {grafico(grafico_r3_calendario())}
  <p class="nota">En azul, las tres victorias de los primeros 60 días. El mes 1 arranca con lo que ya
  está construido y con la capa de validación del dato.</p>
</div>

<h3 style="margin-top:44px">Las tres victorias de los primeros 60 días</h3>
<p>Una ya está desplegada, otra necesita un reloj que la dispare y la tercera se construye con datos
que ya están.</p>
<div class="grid g3">{rapidas}</div>
<p class="nota">La cuarta candidata era el agente de atención al cliente. Necesita conectar pedidos y
seguimiento de envíos, y ese permiso no llega en ocho semanas. Arranca en el mes 3.</p>""",
    )


def _seccion_r3_exito() -> Dict[str, str]:
    """Punto 5 del enunciado, y el cierre obligatorio de supuestos.

    Tres bloques y nada más: la escalera en una línea, un KPI por iniciativa y
    cuatro reglas de adopción. Los supuestos van plegados; tienen que estar, pero
    no son lo que se lee aquí.
    """
    escalera = " &nbsp;→&nbsp; ".join(
        f'<strong style="color:var(--acento)">{n} {t.lower()}</strong>' if n == "2"
        else f'{n} {t.lower()}'
        for n, t, _ in roadmap.ESCALERA
    )

    kpis = tabla_html(pd.DataFrame([{
        "nombre": f'<strong>{i["n"]}</strong> · {i["nombre"]}',
        "kpi": i["kpi"],
        "mov": f'{i["base"]} <span style="color:var(--tinta-3)">→</span> <strong>{i["objetivo"]}</strong>',
    } for i in roadmap.INICIATIVAS]), [
        ("nombre", "Iniciativa", "crudo"), ("kpi", "Se mide con", "texto"),
        ("mov", "Hoy → a seis meses", "crudo"),
    ])

    adopcion = "".join(f'<li><strong>{t}</strong> — {d}</li>' for t, d in roadmap.CAPACITACION)

    supuestos = tabla_html(pd.DataFrame([{
        "c": f"<strong>{c}</strong>", "v": v, "p": p,
        "o": ('<span class="tag tag-dato">dato</span>' if o == "dato"
              else '<span class="tag tag-mio">estimado</span>'),
    } for c, v, p, o in roadmap.SUPUESTOS]), [
        ("c", "Supuesto", "crudo"), ("v", "Valor", "texto"),
        ("o", "Origen", "crudo"), ("p", "De dónde sale", "texto"),
    ])

    return seccion(
        "Reto 3 · Hoja de ruta", "Cómo se mide y cómo consigo que lo usen", "r3_exito",
        "Un KPI por iniciativa, y ninguna entra en automático el primer día.",
        f"""
<div class="card" style="text-align:center;font-size:14px;color:var(--tinta-2)">
  {escalera}
  <p class="nota" style="border:0;padding:0;margin-top:14px">Casi todas arrancan en el peldaño 2.
  Se sube cuando el KPI lo permite. Cada corrección que hace la persona sirve además para afinar
  el cálculo.</p>
</div>

<h3 style="margin-top:44px">Un KPI por iniciativa</h3>
{kpis}
<p class="nota">Donde hoy no hay nada medido queda escrito. Lo primero que hace esa iniciativa es
crear la medida. Y por encima de las once hay uno más: <strong>cuántas siguen usándose tres meses
después de entregarse</strong>.</p>

<h3 style="margin-top:44px">Cuatro reglas para que se use</h3>
<div class="card"><ul style="margin:0;padding-left:20px;line-height:1.7">{adopcion}</ul></div>

<h3 style="margin-top:44px">Supuestos</h3>
<details><summary>Los números con los que se ha priorizado</summary>
  <div class="detalle">{supuestos}
  <p class="nota">Construir rápido con un agente traslada el riesgo al mantenimiento. La regla del
  repositorio lo cubre: todo en código, pipeline reproducible y decisiones fechadas.</p></div>
</details>""",
    )


def paginas_reto3() -> List[Dict[str, str]]:
    """Las cinco páginas del Reto 3, en orden."""
    c = roadmap.cifras_de_partida()
    return [
        _seccion_r3_dolor(c),
        _seccion_r3_metodo(),
        _seccion_r3_iniciativas(),
        _seccion_r3_prioridad(),
        _seccion_r3_exito(),
    ]


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
        [("reto2", "Propuesta semanal", "online")],
    ),
    (
        "Reto 3 · Hoja de ruta",
        [
            ("r3_dolor", "Dónde duele", ""),
            ("r3_metodo", "Método y preguntas", ""),
            ("r3_iniciativas", "11 iniciativas", ""),
            ("r3_prioridad", "Prioridad y calendario", ""),
            ("r3_exito", "Éxito y adopción", ""),
        ],
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


# Páginas que no viven en este fichero sino en un servicio aparte. Se abren en
# una pestaña nueva para no perder el informe que se está leyendo.
ENLACES_EXTERNOS = {"reto2": config.URL_SERVICIO_RETO2}


def _menu_lateral() -> str:
    """Menú de navegación. Las páginas pendientes se ven, pero no se pulsan."""
    bloques = []
    for grupo, paginas in ESTRUCTURA:
        items = []
        for pid, etiqueta, badge in paginas:
            destino = ENLACES_EXTERNOS.get(pid)
            if destino:
                items.append(
                    f'<a class="nav-item externo" href="{destino}" target="_blank" rel="noopener">'
                    f'{etiqueta}<span class="nav-badge">{badge} ↗</span></a>'
                )
            elif badge:
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


def _panel_servicio(pid: str, grupo: str, titulo: str, destino: str) -> str:
    """Página que anuncia un reto que vive fuera de este fichero.

    El Reto 2 no es un informe sino un proceso que se ejecuta solo, así que no
    tendría sentido congelarlo dentro de este HTML: lo que hay que enseñar es el
    servicio en marcha, con su historial de ejecuciones.
    """
    return f"""
<div class="panel" id="pag-{pid}">
  <div class="pag-cabecera"><div class="pag-ruta">{grupo}</div><h1>{titulo}</h1></div>
  <div class="card">
    <p>El Reto 2 es un <strong>proceso desplegado</strong> que se ejecuta solo cada día a las
    00:00 y deja la propuesta en el Google Sheet que revisa Compras. Por eso vive en su propia
    dirección y no dentro de este fichero.</p>
    <p style="margin-top:14px">Allí están la propuesta de la semana, cómo se calcula, las
    decisiones que la explican, el esquema de producción y el historial de ejecuciones.</p>
    <p style="margin-top:18px">
      <a class="siguiente" href="{destino}" target="_blank" rel="noopener"
         style="display:inline-flex;text-decoration:none">
        Abrir el servicio de reposición <span class="flecha">↗</span></a>
    </p>
  </div>
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
        *paginas_reto3(),
        _seccion_glosario(metricas['catalogo'].iloc[0]),
        _seccion_asunciones(metricas),
        pagina_decisiones(ejemplos, metricas["resumen_limpieza"]),
    ]
    # El hero de KPIs encabeza la primera página del Reto 1.
    paginas[0]["html"] = _hero(metricas["comparativa"], metricas["margen_cupon"].iloc[0]) + paginas[0]["html"]

    paneles = [_panel(p["id"], p["ruta"], p["titulo"], p["html"]) for p in paginas]
    paneles.append(_panel_servicio(
        "reto2", "Reto 2 · Reposición", "Propuesta semanal de reposición",
        config.URL_SERVICIO_RETO2))

    html = f"""<!doctype html>
<!-- data-theme="claro" fuerza el tema claro al abrir, aunque el sistema esté en
     oscuro: es el modo en el que se diseñaron los gráficos y en el que se va a
     presentar. El botón de la esquina sigue permitiendo cambiarlo. -->
<html lang="es" data-theme="claro">
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
