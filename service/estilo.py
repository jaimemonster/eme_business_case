"""Hoja de estilo del servicio.

Reutiliza los tokens de color del informe del Reto 1 (`src/design.py`) para que
las dos entregas se lean como la misma pieza de trabajo y no como dos proyectos
distintos pegados.
"""

from __future__ import annotations

from src.design import TOKENS

C = TOKENS["claro"]
O = TOKENS["oscuro"]


def css() -> str:
    """CSS del servicio.

    Tema claro único, a propósito: es el modo en el que se presenta y en el que se
    leen los diagramas. Un servicio que cambia de aspecto según el portátil desde
    el que se abra es un riesgo innecesario el día de la entrevista.
    """
    return f"""
:root {{
  --plano:{C['plano']}; --superficie:{C['superficie']}; --superficie-2:{C['superficie_2']};
  --tinta:{C['tinta']}; --tinta-2:{C['tinta_2']}; --tinta-3:{C['tinta_3']};
  --linea:{C['linea']}; --acento:{C['acento']}; --acento-suave:{C['acento_suave']};
  --positivo:{C['positivo']}; --negativo:{C['negativo']};
  --critica:#c7211f; --alta:#b8730a; --normal:{C['tinta_3']};
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plano);color:var(--tinta);font-family:var(--sans);
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}}
a{{color:var(--acento);text-decoration:none}}
a:hover{{text-decoration:underline}}
h1,h2,h3{{margin:0;letter-spacing:-.02em;text-wrap:balance}}
h1{{font-size:clamp(1.6rem,1.2rem+1.6vw,2.2rem);font-weight:650}}
h2{{font-size:1.25rem;font-weight:620;margin-bottom:.35rem}}
h3{{font-size:1rem;font-weight:600}}
p{{margin:0}}

header.top{{position:sticky;top:0;z-index:20;background:var(--superficie);
  border-bottom:1px solid var(--linea);padding:0 clamp(16px,4vw,40px)}}
.top-fila{{max-width:1180px;margin:0 auto;display:flex;align-items:center;
  gap:24px;min-height:58px;flex-wrap:wrap}}
.marca{{font-weight:650;letter-spacing:-.02em;white-space:nowrap}}
.marca span{{color:var(--tinta-3);font-weight:450}}
nav{{display:flex;gap:4px;flex-wrap:wrap;margin-left:auto}}
nav a{{padding:7px 12px;border-radius:7px;color:var(--tinta-2);font-size:.88rem;
  white-space:nowrap}}
nav a:hover{{background:var(--superficie-2);text-decoration:none}}
nav a.activo{{background:var(--acento-suave);color:var(--acento);font-weight:550}}

main{{max-width:1180px;margin:0 auto;padding:clamp(24px,4vw,44px) clamp(16px,4vw,40px) 80px}}
.cabecera{{display:flex;flex-direction:column;gap:10px;margin-bottom:28px;max-width:72ch}}
.ojo{{font-size:.72rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
  color:var(--tinta-3)}}
.lede{{color:var(--tinta-2);font-size:1.02rem}}
section.bloque{{margin-top:38px}}
.nota{{color:var(--tinta-2);font-size:.92rem;max-width:72ch}}

.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:1px;
  background:var(--linea);border:1px solid var(--linea);border-radius:12px;overflow:hidden}}
.kpi{{background:var(--superficie);padding:16px 18px;display:flex;flex-direction:column;gap:3px}}
.kpi .et{{font-size:.76rem;color:var(--tinta-3);text-transform:uppercase;letter-spacing:.07em}}
.kpi .v{{font-size:1.5rem;font-weight:620;letter-spacing:-.025em;font-variant-numeric:tabular-nums}}
.kpi .sub{{font-size:.82rem;color:var(--tinta-2)}}

.barra{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:22px 0 14px}}
.btn{{display:inline-flex;align-items:center;gap:7px;padding:9px 15px;border-radius:9px;
  border:1px solid var(--linea);background:var(--superficie);color:var(--tinta);
  font-size:.88rem;font-weight:550;cursor:pointer;font-family:inherit}}
.btn:hover{{background:var(--superficie-2);text-decoration:none}}
.btn.primario{{background:var(--acento);border-color:var(--acento);color:#fff}}
.btn.primario:hover{{opacity:.92}}
.btn:disabled{{opacity:.5;cursor:default}}
input[type=search],select{{padding:8px 12px;border-radius:9px;border:1px solid var(--linea);
  background:var(--superficie);color:var(--tinta);font-size:.88rem;font-family:inherit}}

.tabla-caja{{border:1px solid var(--linea);border-radius:12px;overflow:auto;
  background:var(--superficie);max-height:70vh}}
table{{border-collapse:collapse;width:100%;font-size:.86rem;min-width:900px}}
thead th{{position:sticky;top:0;background:var(--superficie-2);text-align:left;
  padding:10px 13px;font-size:.72rem;letter-spacing:.07em;text-transform:uppercase;
  color:var(--tinta-3);font-weight:600;border-bottom:1px solid var(--linea);z-index:1}}
td{{padding:10px 13px;border-bottom:1px solid var(--linea);vertical-align:top}}
tbody tr:last-child td{{border-bottom:0}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.motivo{{color:var(--tinta-2);font-size:.82rem;min-width:300px}}
.pri{{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.72rem;
  font-weight:600;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}}
.pri.critica{{background:rgba(199,33,31,.12);color:var(--critica)}}
.pri.alta{{background:rgba(184,115,10,.14);color:var(--alta)}}
.pri.normal{{background:var(--superficie-2);color:var(--normal)}}

details{{border:1px solid var(--linea);border-radius:11px;background:var(--superficie);
  margin-bottom:9px;overflow:hidden}}
summary{{padding:14px 18px;cursor:pointer;font-weight:560;display:flex;gap:12px;
  align-items:baseline;list-style:none}}
summary::-webkit-details-marker{{display:none}}
summary::before{{content:"+";color:var(--acento);font-weight:600;width:12px;flex:none}}
details[open] summary::before{{content:"−"}}
details[open] summary{{border-bottom:1px solid var(--linea)}}
.fecha{{margin-left:auto;font-size:.76rem;color:var(--tinta-3);font-family:var(--mono)}}
.cuerpo{{padding:16px 18px 18px 42px;display:flex;flex-direction:column;gap:12px}}
.campo{{display:flex;flex-direction:column;gap:2px}}
.campo .et{{font-size:.7rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  color:var(--tinta-3)}}
.campo .tx{{color:var(--tinta-2);font-size:.92rem;white-space:pre-wrap}}

.tarjetas{{display:grid;grid-template-columns:repeat(auto-fit,minmax(265px,1fr));gap:16px}}
.tarjeta{{background:var(--superficie);border:1px solid var(--linea);border-radius:12px;
  padding:18px;display:flex;flex-direction:column;gap:7px}}
.tarjeta .et{{font-size:.72rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  color:var(--acento)}}
.tarjeta p{{color:var(--tinta-2);font-size:.92rem}}
.tarjeta ul{{margin:0;padding-left:18px;color:var(--tinta-2);font-size:.92rem}}
.tarjeta li{{margin-bottom:5px}}

.calculo{{background:var(--superficie);border:1px solid var(--linea);border-radius:12px;
  padding:18px 20px;font-family:var(--mono);font-size:.84rem;line-height:1.95;
  overflow-x:auto;white-space:pre}}
code{{font-family:var(--mono);font-size:.88em;background:var(--superficie-2);
  border:1px solid var(--linea);border-radius:5px;padding:1px 5px}}
.gana{{color:var(--positivo);font-weight:600}}
.aviso{{background:var(--acento-suave);border-left:3px solid var(--acento);
  padding:13px 16px;border-radius:0 9px 9px 0;font-size:.92rem;max-width:74ch}}
/* --- diagramas --- */
.figura{{background:var(--superficie);border:1px solid var(--linea);border-radius:14px;
  padding:22px 18px;overflow-x:auto;margin-top:6px}}
.figura svg{{display:block;width:100%;min-width:760px;height:auto;color:var(--tinta-3)}}
.figura svg text{{font-family:var(--sans)}}
.pie{{color:var(--tinta-2);font-size:.88rem;margin-top:11px;max-width:74ch}}
.bx{{fill:var(--superficie);stroke:var(--linea);stroke-width:1.4}}
.bx-ac{{fill:var(--superficie);stroke:var(--acento);stroke-width:1.7}}
.bx-ok{{fill:var(--superficie);stroke:var(--positivo);stroke-width:1.7}}
.bx-su{{fill:var(--superficie-2);stroke:var(--linea);stroke-width:1}}
.d-n{{font-size:9.5px;font-weight:700;letter-spacing:1.3px}}
.d-ac{{fill:var(--acento)}} .d-acento{{fill:var(--acento)}} .d-ok{{fill:var(--positivo)}} .d-gr{{fill:var(--tinta-3)}}
.d-t{{font-size:13.5px;font-weight:650;fill:var(--tinta)}}
.d-v{{font-size:19px;font-weight:680;fill:var(--tinta);letter-spacing:-.02em}}
.d-s{{font-size:10.5px;fill:var(--tinta-2)}}
.d-f{{font-size:9px;font-weight:700;letter-spacing:1.1px;fill:var(--tinta-3)}}
.d-ln{{fill:none;stroke:currentColor;stroke-width:1.5}}
.d-lp{{fill:none;stroke:var(--acento);stroke-width:1.5;stroke-dasharray:6 5}}
.d-mk{{fill:currentColor}} .d-mp{{fill:var(--acento)}}
.g-barra{{fill:var(--acento)}}
.g-barra-baja{{fill:var(--acento);opacity:.42}}
.g-ref{{stroke:var(--tinta-3);stroke-width:1.3;stroke-dasharray:5 4;fill:none}}
.g-eje{{stroke:var(--linea);stroke-width:1}}
.g-val{{font-size:9.5px;fill:var(--tinta-2);font-variant-numeric:tabular-nums}}
.g-sem{{font-size:9px;fill:var(--tinta-3)}}
.g-ref-t{{font-size:10px;fill:var(--tinta-3)}}
.bx-warn-l{{fill:var(--superficie-2);stroke:var(--linea);stroke-width:1;stroke-dasharray:5 4}}
.leyenda{{display:flex;gap:20px;flex-wrap:wrap;margin-top:12px;font-size:.8rem;color:var(--tinta-2)}}
.leyenda span{{display:inline-flex;align-items:center;gap:7px}}
.pastilla{{width:22px;height:3px;border-radius:2px;display:inline-block}}
.pastilla.ok{{background:var(--positivo)}} .pastilla.ac{{background:var(--acento)}}

footer{{border-top:1px solid var(--linea);margin-top:56px;padding-top:20px;
  color:var(--tinta-3);font-size:.82rem;max-width:74ch}}
#aviso-exporta{{font-size:.86rem;color:var(--tinta-2)}}
@media (max-width:620px){{nav{{margin-left:0;width:100%}} .top-fila{{padding:10px 0}}}}
"""
