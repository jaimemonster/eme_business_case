"""Sistema de diseño del informe.

Responsabilidad: los tokens visuales (color, tipografía, espaciado), la plantilla
de los gráficos y los componentes HTML reutilizables. `report.py` compone
secciones con estas piezas; aquí no hay nada de negocio.

Dirección estética: páginas de producto de Apple. Sobrio, mucho aire, jerarquía
clara, un único color de acento. El verde y el rojo se reservan para las
variaciones (▲▼) y nunca decoran.

Paleta validada con el validador de la skill `dataviz` (seis checks) contra las
dos superficies reales del informe:

    acento claro  #0071e3 sobre #fbfbfd -> los 6 checks PASS
    acento oscuro #0a84ff sobre #161617 -> los 6 checks PASS

El verde y el rojo de las variaciones no superan la separación CVD entre sí
(ningún par rojo/verde lo hace). Es aceptable aquí porque el color nunca va
solo: siempre lleva la flecha ▲▼ y el número con signo, que son la codificación
secundaria que exige la regla.
"""

from __future__ import annotations

from typing import Iterable

import plotly.graph_objects as go

# --- Tokens de color --------------------------------------------------------
# Cada rol tiene su valor en claro y en oscuro. El oscuro no es una inversión
# automática: son pasos elegidos contra la superficie oscura.
TOKENS = {
    "claro": {
        "plano": "#f5f5f7",       # fondo de página
        "superficie": "#ffffff",  # tarjetas
        "superficie_2": "#fbfbfd",# superficie de los gráficos
        "tinta": "#1d1d1f",       # texto principal
        "tinta_2": "#6e6e73",     # texto secundario
        "tinta_3": "#86868b",     # ejes, etiquetas
        "linea": "#e8e8ed",       # bordes y rejilla
        "acento": "#0071e3",
        "acento_suave": "rgba(0,113,227,0.10)",
        "referencia": "#c7c7cc",  # series de contexto (la gris de "emphasis")
        "positivo": "#0a7d2e",
        "negativo": "#c7211f",
    },
    "oscuro": {
        "plano": "#000000",
        "superficie": "#1c1c1e",
        "superficie_2": "#161617",
        "tinta": "#f5f5f7",
        "tinta_2": "#a1a1a6",
        "tinta_3": "#8e8e93",
        "linea": "#2c2c2e",
        "acento": "#0a84ff",
        "acento_suave": "rgba(10,132,255,0.16)",
        "referencia": "#5a5a5f",
        "positivo": "#30b14e",
        "negativo": "#ff544a",
    },
}

# Mapa claro -> oscuro que usa el JS para repintar los gráficos al cambiar de
# tema. Plotly escribe los colores en línea, así que no los alcanza el CSS.
MAPA_TEMA = {
    TOKENS["claro"][k]: TOKENS["oscuro"][k]
    for k in ("acento", "referencia", "positivo", "negativo", "tinta", "tinta_2", "tinta_3", "linea")
}

TIPOGRAFIA = (
    '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", '
    '"Helvetica Neue", Helvetica, Arial, sans-serif'
)


def plantilla_grafico(fig: go.Figure, altura: int = 320, margen_izq: int = 0) -> go.Figure:
    """Aplica la plantilla común: sin cromo innecesario, ejes en gris, sin fondo.

    El fondo transparente es lo que permite que el mismo gráfico funcione en
    claro y en oscuro: hereda el color de la tarjeta que lo contiene.
    """
    c = TOKENS["claro"]
    fig.update_layout(
        height=altura,
        margin=dict(l=margen_izq, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=TIPOGRAFIA, size=13, color=c["tinta_3"]),
        showlegend=False,
        hoverlabel=dict(
            bgcolor=c["superficie"],
            bordercolor=c["linea"],
            font=dict(family=TIPOGRAFIA, size=13, color=c["tinta"]),
        ),
        dragmode=False,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        ticks="",
        tickfont=dict(size=12, color=c["tinta_3"]),
        title=None,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=c["linea"],
        gridwidth=1,
        zeroline=False,
        showline=False,
        ticks="",
        tickfont=dict(size=12, color=c["tinta_3"]),
        title=None,
    )
    return fig


def _fmt(valor: float, unidad: str) -> str:
    """Formatea un número al estilo español: miles con punto, decimales con coma."""
    if unidad == "€":
        texto = f"{valor:,.0f}".replace(",", ".")
        return f"{texto} €"
    if unidad == "%":
        return f"{valor:,.1f}".replace(".", ",") + " %"
    return f"{valor:,.0f}".replace(",", ".")


def kpi(titulo: str, valor: float, unidad: str, deltas: Iterable[tuple[str, float]]) -> str:
    """Tarjeta de KPI del hero: cifra grande y sus variaciones.

    Cada variación lleva flecha, signo y color. La flecha y el signo son la
    codificación secundaria: quien no distinga verde de rojo lee igual el dato.
    """
    filas = []
    for etiqueta, pct in deltas:
        if pct is None:
            continue
        signo = "▲" if pct >= 0 else "▼"
        clase = "pos" if pct >= 0 else "neg"
        texto = f"{abs(pct):,.1f}".replace(".", ",")
        filas.append(
            f'<div class="kpi-delta"><span class="{clase}">{signo} {texto} %</span>'
            f'<span class="kpi-delta-lbl">{etiqueta}</span></div>'
        )
    return (
        f'<div class="kpi"><div class="kpi-tit">{titulo}</div>'
        f'<div class="kpi-val">{_fmt(valor, unidad)}</div>'
        f'<div class="kpi-deltas">{"".join(filas)}</div></div>'
    )


def css() -> str:
    """Hoja de estilos completa del informe.

    Los colores se declaran como variables CSS en `:root` y se redefinen en los
    dos ámbitos que exige un tema conmutable: la media query del sistema y el
    atributo `data-theme` del selector manual, que debe ganar en ambos sentidos.
    """
    c, o = TOKENS["claro"], TOKENS["oscuro"]
    # Las claves del diccionario usan guion bajo (Python) y las variables CSS
    # guion medio: se traducen aquí para no tener dos nomenclaturas.
    vars_claro = "\n".join(f"      --{k.replace('_', '-')}: {v};" for k, v in c.items())
    vars_oscuro = "\n".join(f"      --{k.replace('_', '-')}: {v};" for k, v in o.items())
    return f"""
:root {{
  color-scheme: light;
{vars_claro}
  --radio: 18px;
  --ancho: 1080px;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="claro"]) {{
    color-scheme: dark;
{vars_oscuro}
  }}
}}
:root[data-theme="oscuro"] {{
  color-scheme: dark;
{vars_oscuro}
}}

* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--plano);
  color: var(--tinta);
  font-family: {TIPOGRAFIA};
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{ max-width: var(--ancho); margin: 0 auto; padding-block: 0 96px; padding-left: 24px; padding-right: 24px; }}

/* --- Cabecera --- */
header.top {{ padding-block: 72px 28px; }}
.marca {{
  font-size: 12px; font-weight: 600; letter-spacing: 0.22em;
  text-transform: uppercase; color: var(--tinta-3); margin-bottom: 20px;
}}
h1 {{ font-size: 52px; font-weight: 600; letter-spacing: -0.025em; margin: 0 0 12px; line-height: 1.08; }}
.subtitulo {{ font-size: 20px; color: var(--tinta-2); margin: 0; font-weight: 400; }}

/* --- Navegación --- */
nav.indice {{
  position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--plano) 86%, transparent);
  backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--linea);
  margin-bottom: 40px;
}}
nav.indice ul {{
  max-width: var(--ancho); margin: 0 auto; padding: 0 24px;
  list-style: none; display: flex; gap: 28px; overflow-x: auto;
  scrollbar-width: none; -ms-overflow-style: none;
}}
nav.indice ul::-webkit-scrollbar {{ display: none; }}
nav.indice a {{
  display: block; padding: 14px 0; color: var(--tinta-2);
  text-decoration: none; font-size: 14px; white-space: nowrap;
  border-bottom: 2px solid transparent;
}}
nav.indice a:hover {{ color: var(--tinta); border-bottom-color: var(--acento); }}

/* --- Secciones --- */
section {{ margin-bottom: 72px; scroll-margin-top: 72px; }}
.sec-num {{ font-size: 12px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: var(--acento); margin-bottom: 10px; }}
h2 {{ font-size: 34px; font-weight: 600; letter-spacing: -0.02em; margin: 0 0 14px; line-height: 1.15; }}
h3 {{ font-size: 20px; font-weight: 600; margin: 0 0 6px; letter-spacing: -0.01em; }}
.conclusion {{
  font-size: 21px; line-height: 1.45; color: var(--tinta); margin: 0 0 28px;
  max-width: 62ch; font-weight: 400;
}}
.conclusion strong {{ font-weight: 600; }}
p {{ color: var(--tinta-2); max-width: 70ch; }}
.nota {{ font-size: 14px; color: var(--tinta-3); margin-top: 12px; }}

/* --- Tarjetas --- */
.card {{
  background: var(--superficie); border-radius: var(--radio);
  padding: 28px; border: 1px solid var(--linea);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.grid {{ display: grid; gap: 20px; }}
/* Sin esto, un item de grid toma min-width:auto y crece hasta el ancho de su
   contenido: una tabla ancha desborda la página entera en lugar de activar el
   scroll horizontal de su propio contenedor. */
.grid > *, .glosario > *, .card, .kpi, .termino {{ min-width: 0; }}
.tabla-scroll {{ max-width: 100%; }}
.g2 {{ grid-template-columns: repeat(2, 1fr); }}
.g3 {{ grid-template-columns: repeat(3, 1fr); }}
.g4 {{ grid-template-columns: repeat(4, 1fr); }}

/* --- KPIs del hero --- */
.kpi {{
  background: var(--superficie); border-radius: var(--radio);
  padding: 24px; border: 1px solid var(--linea);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.kpi-tit {{ font-size: 13px; color: var(--tinta-3); margin-bottom: 10px; }}
.kpi-val {{ font-size: 40px; letter-spacing: -0.03em; line-height: 1.05; margin-bottom: 14px; }}
.kpi-deltas {{ display: flex; flex-direction: column; gap: 4px; }}
.kpi-delta {{ display: flex; align-items: baseline; gap: 8px; font-size: 13px; }}
.kpi-delta .pos, .kpi-delta .neg {{ white-space: nowrap; }}
.kpi-delta-lbl {{ min-width: 0; }}
.kpi-delta .pos {{ color: var(--positivo); font-weight: 600; }}
.kpi-delta .neg {{ color: var(--negativo); font-weight: 600; }}
.kpi-delta-lbl {{ color: var(--tinta-3); }}

/* --- Cifra destacada dentro de una tarjeta --- */
.dato {{ font-size: 32px; letter-spacing: -0.02em; line-height: 1.1; }}
.dato-lbl {{ font-size: 13px; color: var(--tinta-3); margin-top: 6px; }}
.dato.alerta {{ color: var(--negativo); }}

/* --- Tablas --- */
.tabla-scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{
  text-align: left; font-weight: 600; font-size: 12px; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--tinta-3);
  padding: 0 14px 12px 0; border-bottom: 1px solid var(--linea); white-space: nowrap;
}}
td {{ padding: 12px 14px 12px 0; border-bottom: 1px solid var(--linea); color: var(--tinta-2); }}
td:first-child {{ color: var(--tinta); }}
tr:last-child td {{ border-bottom: none; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.pos {{ color: var(--positivo); }}
.neg {{ color: var(--negativo); }}
.destacar td {{ background: var(--acento-suave); }}

/* --- Bloques plegables de decisiones --- */
details {{
  background: var(--superficie); border: 1px solid var(--linea);
  border-radius: 14px; margin-bottom: 10px; overflow: hidden;
}}
summary {{
  padding: 18px 22px; cursor: pointer; font-size: 16px; font-weight: 600;
  list-style: none; display: flex; align-items: center; gap: 14px;
}}
summary::-webkit-details-marker {{ display: none; }}
summary::before {{
  content: "+"; color: var(--acento); font-weight: 400; font-size: 20px;
  width: 18px; flex-shrink: 0; transition: transform 0.2s;
}}
details[open] summary::before {{ content: "−"; }}
summary:hover {{ background: var(--acento-suave); }}
.detalle {{ padding: 4px 22px 22px 54px; }}
.detalle dt {{
  font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--tinta-3); font-weight: 600; margin-top: 18px;
}}
.detalle dd {{ margin: 6px 0 0; color: var(--tinta-2); }}
.detalle dd:first-of-type {{ margin-top: 6px; }}
.ejemplo {{
  background: var(--superficie-2); border: 1px solid var(--linea);
  border-radius: 10px; padding: 14px; margin-top: 8px; overflow-x: auto;
}}
.ejemplo table {{ font-size: 13px; }}
.ejemplo td, .ejemplo th {{ padding: 6px 14px 6px 0; }}

/* --- Glosario --- */
.glosario {{ display: grid; gap: 18px; }}
.termino {{
  background: var(--superficie); border: 1px solid var(--linea);
  border-radius: 14px; padding: 20px 22px;
}}
.formula {{
  font-family: "SF Mono", ui-monospace, Menlo, Consolas, monospace;
  font-size: 13px; background: var(--superficie-2); border: 1px solid var(--linea);
  border-radius: 8px; padding: 10px 14px; margin-top: 10px;
  color: var(--tinta); overflow-x: auto; white-space: pre;
}}

/* --- Etiquetas de origen --- */
.tag {{
  display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
  padding: 3px 9px; border-radius: 20px; white-space: nowrap;
}}
.tag-dato {{ background: var(--acento-suave); color: var(--acento); }}
.tag-mio {{ background: color-mix(in srgb, var(--negativo) 12%, transparent); color: var(--negativo); }}

footer {{
  border-top: 1px solid var(--linea); padding-top: 28px; margin-top: 72px;
  font-size: 13px; color: var(--tinta-3);
}}

/* --- Selector de tema --- */
.tema {{
  position: fixed; bottom: 22px; right: 22px; z-index: 50;
  background: var(--superficie); border: 1px solid var(--linea);
  color: var(--tinta-2); border-radius: 999px; padding: 9px 16px;
  font-family: inherit; font-size: 13px; cursor: pointer;
  box-shadow: 0 2px 10px rgba(0,0,0,0.10);
}}
.tema:hover {{ color: var(--tinta); }}

@media (max-width: 860px) {{
  .g4 {{ grid-template-columns: repeat(2, 1fr); }}
  .g3, .g2 {{ grid-template-columns: 1fr; }}
  h1 {{ font-size: 36px; }}
  h2 {{ font-size: 26px; }}
  .conclusion {{ font-size: 18px; }}
  .kpi-val {{ font-size: 32px; }}
  .wrap {{ padding-left: 16px; padding-right: 16px; }}
  nav.indice ul {{ padding: 0 16px; gap: 20px; }}
  .detalle {{ padding-left: 22px; }}
}}
@media (max-width: 520px) {{
  .g4 {{ grid-template-columns: 1fr; }}
}}
@media print {{
  nav.indice, .tema {{ display: none; }}
  details {{ break-inside: avoid; }}
  details > div {{ display: block !important; }}
}}
"""


def js_tema() -> str:
    """Selector de tema y repintado de los gráficos.

    Plotly escribe los colores en los atributos del SVG, así que el CSS no los
    alcanza: al cambiar de tema hay que recorrer los gráficos y sustituir cada
    color por su equivalente del otro modo.
    """
    import json

    mapa = json.dumps(MAPA_TEMA)
    inverso = json.dumps({v: k for k, v in MAPA_TEMA.items()})
    return f"""
const MAPA_OSCURO = {mapa};
const MAPA_CLARO = {inverso};

function esOscuro() {{
  const t = document.documentElement.dataset.theme;
  if (t) return t === "oscuro";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}}

function traducir(valor, mapa) {{
  if (typeof valor === "string") return mapa[valor] || valor;
  if (Array.isArray(valor)) return valor.map((v) => traducir(v, mapa));
  return valor;
}}

function repintar() {{
  const mapa = esOscuro() ? MAPA_OSCURO : MAPA_CLARO;
  document.querySelectorAll(".js-plotly-plot").forEach((g) => {{
    if (!g.data) return;
    g.data.forEach((t) => {{
      if (t.marker && t.marker.color) t.marker.color = traducir(t.marker.color, mapa);
      if (t.marker && t.marker.line && t.marker.line.color) t.marker.line.color = traducir(t.marker.line.color, mapa);
      if (t.line && t.line.color) t.line.color = traducir(t.line.color, mapa);
      if (t.textfont && t.textfont.color) t.textfont.color = traducir(t.textfont.color, mapa);
    }});
    const lay = g.layout || {{}};
    const tinta3 = mapa["{TOKENS['claro']['tinta_3']}"] || "{TOKENS['claro']['tinta_3']}";
    const linea = mapa["{TOKENS['claro']['linea']}"] || "{TOKENS['claro']['linea']}";
    const sup = esOscuro() ? "{TOKENS['oscuro']['superficie']}" : "{TOKENS['claro']['superficie']}";
    const tinta = esOscuro() ? "{TOKENS['oscuro']['tinta']}" : "{TOKENS['claro']['tinta']}";
    Plotly.relayout(g, {{
      "font.color": tinta3,
      "xaxis.tickfont.color": tinta3,
      "yaxis.tickfont.color": tinta3,
      "yaxis.gridcolor": linea,
      "xaxis.gridcolor": linea,
      "hoverlabel.bgcolor": sup,
      "hoverlabel.bordercolor": linea,
      "hoverlabel.font.color": tinta,
    }});
    Plotly.redraw(g);
  }});
}}

function alternarTema() {{
  const nuevo = esOscuro() ? "claro" : "oscuro";
  document.documentElement.setAttribute("data-theme", nuevo);
  document.querySelector(".tema").textContent = nuevo === "oscuro" ? "Tema claro" : "Tema oscuro";
  repintar();
}}

window.addEventListener("load", () => {{
  if (esOscuro()) repintar();
  document.querySelector(".tema").textContent = esOscuro() ? "Tema claro" : "Tema oscuro";
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {{
    if (!document.documentElement.dataset.theme) repintar();
  }});
}});
"""
