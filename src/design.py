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


/* --- Cabecera --- */
header.top {{ padding-block: 0 32px; }}
.marca {{
  font-size: 12px; font-weight: 600; letter-spacing: 0.22em;
  text-transform: uppercase; color: var(--tinta-3); margin-bottom: 20px;
}}
h1 {{ font-size: 40px; font-weight: 600; letter-spacing: -0.025em; margin: 0 0 12px; line-height: 1.08; }}
.subtitulo {{ font-size: 20px; color: var(--tinta-2); margin: 0; font-weight: 400; }}

/* --- Layout: sidebar fija + panel de contenido --- */
.layout {{ display: grid; grid-template-columns: 258px minmax(0, 1fr); align-items: start; }}
.sidebar {{
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  border-right: 1px solid var(--linea); padding: 36px 20px 32px;
  background: var(--plano);
}}
.sidebar .marca {{ margin-bottom: 6px; }}
.sidebar-titulo {{
  font-size: 19px; font-weight: 600; letter-spacing: -0.015em;
  line-height: 1.25; margin: 0 0 4px;
}}
.sidebar-sub {{ font-size: 12px; color: var(--tinta-3); margin: 0 0 26px; line-height: 1.4; }}
.nav-grupo {{
  font-size: 11px; font-weight: 600; letter-spacing: 0.13em; text-transform: uppercase;
  color: var(--tinta-3); margin: 24px 0 8px; padding-left: 12px;
}}
.nav-item {{
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; margin-bottom: 2px; border-radius: 9px;
  color: var(--tinta-2); text-decoration: none; font-size: 14px;
  border: none; background: none; width: 100%; text-align: left;
  font-family: inherit; cursor: pointer; line-height: 1.35;
}}
.nav-item:hover {{ background: var(--acento-suave); color: var(--tinta); }}
.nav-item.activo {{ background: var(--acento-suave); color: var(--acento); font-weight: 600; }}
.nav-item.pendiente {{ color: var(--tinta-3); cursor: default; opacity: 0.65; }}
.nav-item.pendiente:hover {{ background: none; color: var(--tinta-3); }}
.nav-badge {{
  margin-left: auto; flex-shrink: 0; align-self: center; font-size: 10px; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--tinta-3); border: 1px solid var(--linea); border-radius: 20px; padding: 2px 7px;
}}

.contenido {{ padding: 56px 44px 96px; max-width: 1040px; min-width: 0; }}
.panel {{ display: none; }}
.panel.activo {{ display: block; }}

/* Cabecera de página: dónde estoy y qué es esto */
.pag-cabecera {{ margin-bottom: 36px; }}
.pag-ruta {{ font-size: 12px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--acento); margin-bottom: 10px; }}

/* Pie de página: ir a la siguiente */
.siguiente {{
  display: inline-flex; align-items: center; gap: 10px; margin-top: 8px;
  padding: 14px 20px; border: 1px solid var(--linea); border-radius: 12px;
  background: var(--superficie); color: var(--tinta); text-decoration: none;
  font-size: 15px; font-family: inherit; cursor: pointer;
}}
.siguiente:hover {{ border-color: var(--acento); color: var(--acento); }}
.siguiente .flecha {{ color: var(--acento); }}

/* Barra superior, solo en móvil */
.topbar {{ display: none; }}

/* --- Secciones --- */
section {{ margin-bottom: 64px; }}
section:last-of-type {{ margin-bottom: 32px; }}
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
.kpi-delta {{ display: flex; align-items: baseline; gap: 7px; font-size: 12px; }}
.kpi-delta .pos, .kpi-delta .neg {{ white-space: nowrap; }}
.kpi-delta-lbl {{ min-width: 0; }}
.kpi-delta .pos {{ color: var(--positivo); font-weight: 600; }}
.kpi-delta .neg {{ color: var(--negativo); font-weight: 600; }}
.kpi-delta-lbl {{ color: var(--tinta-3); white-space: nowrap; }}

/* --- Cifra destacada dentro de una tarjeta --- */
.dato {{ font-size: 32px; letter-spacing: -0.02em; line-height: 1.1; }}
.dato-lbl {{ font-size: 13px; color: var(--tinta-3); margin-top: 6px; }}
.dato.alerta {{ color: var(--negativo); }}

/* --- Selector segmentado (cambiar la métrica de un gráfico) --- */
.selector {{
  display: inline-flex; gap: 2px; padding: 3px;
  background: var(--superficie-2); border: 1px solid var(--linea);
  border-radius: 10px; margin-bottom: 18px;
}}
.selector button {{
  border: none; background: none; color: var(--tinta-2);
  font-family: inherit; font-size: 13px; padding: 6px 14px;
  border-radius: 7px; cursor: pointer; white-space: nowrap;
}}
.selector button:hover {{ color: var(--tinta); }}
.selector button.activo {{
  background: var(--superficie); color: var(--tinta); font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}}

/* Leyenda propia, para no depender de la de Plotly */
.leyenda {{ display: flex; gap: 20px; font-size: 13px; color: var(--tinta-2); margin-bottom: 4px; }}
.leyenda span {{ display: inline-flex; align-items: center; gap: 7px; }}
.leyenda i {{ width: 14px; height: 3px; border-radius: 2px; display: inline-block; }}

/* --- Tablas --- */
.tabla-scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{
  text-align: left; font-weight: 600; font-size: 12px; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--tinta-3);
  padding: 0 14px 12px 0; border-bottom: 1px solid var(--linea); white-space: nowrap;
}}
td {{ padding: 12px 14px 12px 0; border-bottom: 1px solid var(--linea); color: var(--tinta-2); white-space: nowrap; }}
/* La primera columna lleva nombres largos: se le da espacio para que no se
   parta en cuatro líneas, y es la única que puede envolver. */
td:first-child {{ color: var(--tinta); white-space: normal; min-width: 170px; }}
th:first-child {{ min-width: 170px; }}
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

@media (max-width: 1000px) {{
  .layout {{ grid-template-columns: 1fr; }}
  .topbar {{
    display: flex; align-items: center; gap: 12px;
    position: sticky; top: 0; z-index: 40;
    padding: 12px 16px; border-bottom: 1px solid var(--linea);
    background: color-mix(in srgb, var(--plano) 88%, transparent);
    backdrop-filter: saturate(180%) blur(20px);
  }}
  .topbar .marca {{ margin: 0; }}
  .topbar-actual {{ font-size: 14px; font-weight: 600; margin-left: auto; color: var(--tinta-2); }}
  .boton-menu {{
    border: 1px solid var(--linea); background: var(--superficie); color: var(--tinta);
    border-radius: 9px; padding: 7px 12px; font-family: inherit; font-size: 13px; cursor: pointer;
  }}
  .sidebar {{
    position: static; height: auto; border-right: none;
    border-bottom: 1px solid var(--linea); padding: 8px 16px 20px;
    display: none;
  }}
  .sidebar.abierta {{ display: block; }}
  .sidebar .cabecera-lateral {{ display: none; }}
  .contenido {{ padding: 32px 16px 72px; }}
}}
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
  .sidebar, .tema, .topbar, .siguiente {{ display: none !important; }}
  .panel {{ display: block !important; break-before: page; }}
  .layout {{ grid-template-columns: 1fr; }}
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

/* --- Navegación por páginas --------------------------------------------
   Los paneles están todos en el DOM pero solo uno es visible. Un gráfico de
   Plotly dibujado dentro de un contenedor oculto no conoce su ancho, así que
   al mostrar un panel hay que redimensionar los suyos. */

function graficosDe(panel) {{
  return panel ? panel.querySelectorAll(".js-plotly-plot") : [];
}}

function mostrar(id, empujarHistorial = true) {{
  const panel = document.getElementById("pag-" + id);
  if (!panel) return;

  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("activo"));
  panel.classList.add("activo");

  document.querySelectorAll(".nav-item").forEach((a) => {{
    a.classList.toggle("activo", a.dataset.pagina === id);
  }});

  const actual = document.querySelector(`.nav-item[data-pagina="${{id}}"]`);
  const rotulo = document.querySelector(".topbar-actual");
  if (actual && rotulo) rotulo.textContent = actual.dataset.etiqueta || actual.textContent.trim();

  graficosDe(panel).forEach((g) => Plotly.Plots.resize(g));
  document.querySelector(".sidebar").classList.remove("abierta");
  window.scrollTo({{ top: 0, behavior: "instant" }});
  if (empujarHistorial && location.hash !== "#" + id) history.pushState({{ id }}, "", "#" + id);
}}

/* Cambia qué métrica muestra un gráfico. Las series están todas dibujadas; solo
   se alterna su visibilidad, que es instantáneo y no vuelve a calcular nada. */
function cambiarMetrica(idGrafico, indice, boton) {{
  const g = document.getElementById(idGrafico);
  if (!g || !g.data) return;
  const visibles = g.data.map((t) => t._grupo === indice);
  Plotly.restyle(g, {{ visible: visibles }});

  const ejes = g._metricas && g._metricas[indice];
  if (ejes) Plotly.relayout(g, ejes);

  boton.parentElement.querySelectorAll("button").forEach((b) => b.classList.remove("activo"));
  boton.classList.add("activo");
}}

/* Registra a qué métrica pertenece cada serie y el formato de eje de cada una. */
function registrarMetricas(idGrafico, grupos, ejes) {{
  const g = document.getElementById(idGrafico);
  if (!g || !g.data) return;
  g.data.forEach((t, i) => {{ t._grupo = grupos[i]; }});
  g._metricas = ejes;
  Plotly.restyle(g, {{ visible: g.data.map((t) => t._grupo === 0) }});
  if (ejes && ejes[0]) Plotly.relayout(g, ejes[0]);
}}

function alternarMenu() {{
  document.querySelector(".sidebar").classList.toggle("abierta");
}}

window.addEventListener("popstate", () => {{
  mostrar((location.hash || "").replace("#", "") || PAGINA_INICIAL, false);
}});

window.addEventListener("resize", () => {{
  const activo = document.querySelector(".panel.activo");
  graficosDe(activo).forEach((g) => Plotly.Plots.resize(g));
}});

function alternarTema() {{
  const nuevo = esOscuro() ? "claro" : "oscuro";
  document.documentElement.setAttribute("data-theme", nuevo);
  document.querySelector(".tema").textContent = nuevo === "oscuro" ? "Tema claro" : "Tema oscuro";
  repintar();
}}

window.addEventListener("load", () => {{
  if (esOscuro()) repintar();
  mostrar((location.hash || "").replace("#", "") || PAGINA_INICIAL, false);
  document.querySelector(".tema").textContent = esOscuro() ? "Tema claro" : "Tema oscuro";
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {{
    if (!document.documentElement.dataset.theme) repintar();
  }});
}});
"""
