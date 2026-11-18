"""Motor de previsión de demanda del Reto 2.

Responsabilidad: estimar cuántas unidades va a vender cada SKU en las próximas
`horizonte` semanas (14 = 6 de plazo de proveedor + 8 de cobertura objetivo),
que es el número del que se resta el stock para decidir qué reponer.

---------------------------------------------------------------------------
POR QUÉ ESTE DISEÑO (y no un modelo por SKU)
---------------------------------------------------------------------------

Los datos obligan. A nivel de SKU la demanda semanal es ruido, no señal:

    nivel              series   uds/semana   % ceros   ruido (std/media)
    sección×categoría      10        21,47       6,4              0,96
    modelo                123         3,43      25,0              1,34
    SKU                   561         0,79      62,2              1,90

Un modelo que intente predecir una serie de ceros y unos tiene un suelo de error
que ningún algoritmo baja. Pero la previsión se descompone en dos decisiones
independientes:

    NIVEL    ¿cuánto va a vender la categoría en total?
    REPARTO  ¿qué parte se lleva cada modelo y cada talla?

Y se midió cuál de las dos es el problema. Dándole al método el total de
categoría REAL (un oráculo imposible, pero marca el techo), sobre 4 cortes:

    método                                       MAE    |sesgo|
    media móvil por SKU (el método anterior)    3,72      44,1 %
    total real + reparto crudo                  3,14       7,9 %
    total real + reparto con encogimiento       3,06       7,9 %

Dos conclusiones, y las dos dirigen el diseño:

1. **Casi todo el error es de nivel.** Acertando el total de categoría el sesgo
   cae del 44 % al 8 % sin tocar el reparto. Por eso aquí el esfuerzo de
   modelado está **íntegramente en el nivel**.
2. **El reparto tiene un techo bajo.** Refinarlo con encogimiento estadístico
   mejora un 2 % (3,14 → 3,06). Se aplica porque es barato y correcto, pero sin
   fingir que es donde está la inteligencia: no lo es.

---------------------------------------------------------------------------
LAS VENTAS NO SON LA DEMANDA
---------------------------------------------------------------------------

Una semana con cero ventas puede ser "nadie lo quería" o "estaba agotado", y en
los datos las dos se ven igual. Contar las roturas como demanda cero castiga
justo a los productos que se agotan porque funcionan.

`clean.reconstruir_stock_semanal` reconstruye el almacén semana a semana, y aquí
la demanda se calcula **solo sobre las semanas en que había producto que vender**.
Afecta al 4,9 % de las semanas sin venta y a 45 SKUs: es un efecto modesto en el
agregado pero grande en los SKUs implicados, que además son los que más importan.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

import numpy as np
import pandas as pd

from . import config

# Ventana para estimar el nivel reciente y los repartos.
VENTANA_NIVEL = 4
VENTANA_REPARTO = 13

# Fuerza del encogimiento de la curva de tallas hacia la de su categoría.
# Elegido por backtesting (ver `comparar_metodos`): el error baja de forma
# monótona hasta k≈20 y a partir de ahí se estanca.
K_ENCOGIMIENTO = 20

NIVEL_GRUPO = ["seccion", "categoria"]


# ---------------------------------------------------------------------------
# Serie de demanda corregida por disponibilidad
# ---------------------------------------------------------------------------

def serie_demanda(
    ventas: pd.DataFrame,
    producto: pd.DataFrame,
    stock_semanal: pd.DataFrame | None = None,
    excluir_especial: bool = True,
) -> pd.DataFrame:
    """Unidades por SKU y semana, con el flag de disponibilidad.

    `excluir_especial` deja fuera las ventas a precio rebajado: son liquidación,
    no demanda recurrente, e inflarían la previsión de un producto que ya no se
    vende a tarifa.

    Cada fila lleva `disponible` y `en_vida`, que es lo que permite más adelante
    no confundir una rotura con una falta de demanda.
    """
    v = ventas[~ventas["is_special"]] if excluir_especial else ventas
    serie = (
        v.groupby(["sku", "inicio_semana"], as_index=False)["unidades"].sum()
    )
    serie["inicio_semana"] = pd.to_datetime(serie["inicio_semana"])

    if stock_semanal is None:
        # Sin reconstrucción de stock se asume disponibilidad siempre: es el
        # comportamiento anterior, peor, y solo se usa como salvavidas.
        rejilla = serie.copy()
        rejilla["disponible"] = True
        rejilla["en_vida"] = True
        return rejilla

    base = stock_semanal[stock_semanal["en_vida"]][
        ["sku", "inicio_semana", "disponible", "en_vida"]
    ].copy()
    base["inicio_semana"] = pd.to_datetime(base["inicio_semana"])

    completa = base.merge(serie, on=["sku", "inicio_semana"], how="left")
    completa["unidades"] = completa["unidades"].fillna(0)

    # Solo SKUs que existen en el catálogo.
    return completa[completa["sku"].isin(producto["sku"])].reset_index(drop=True)


def _con_grupo(serie: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Añade a la serie el modelo y el grupo (sección × categoría)."""
    cols = ["sku", "modelo_id", "talla"] + NIVEL_GRUPO
    s = serie.merge(producto[cols], on="sku", how="left")
    s["grupo"] = s["seccion"].astype(str) + " · " + s["categoria"].astype(str)
    return s


def demanda_grupo(serie_con_grupo: pd.DataFrame) -> pd.DataFrame:
    """Unidades por grupo y semana: la serie donde sí hay señal."""
    return (
        serie_con_grupo.groupby(["grupo", "inicio_semana"], as_index=False)["unidades"]
        .sum()
        .sort_values(["grupo", "inicio_semana"])
    )


# ---------------------------------------------------------------------------
# Modelos de NIVEL · todos devuelven unidades totales por grupo en el horizonte
# ---------------------------------------------------------------------------

def nivel_plano(hist: pd.DataFrame, corte: pd.Timestamp, horizonte: int) -> pd.Series:
    """Baseline 1: el ritmo de las últimas semanas, proyectado plano.

    Es el método que había antes. Se conserva como suelo: cualquier cosa más
    compleja tiene que batirlo o no merece existir.
    """
    rec = hist[hist["inicio_semana"] > corte - pd.Timedelta(weeks=VENTANA_NIVEL)]
    return rec.groupby("grupo")["unidades"].sum() / VENTANA_NIVEL * horizonte


def _perfil_estacional(hist: pd.DataFrame) -> pd.Series:
    """Índice de estacionalidad por semana ISO, estimado con TODOS los grupos.

    Agrupar es lo que hace viable estimarlo: con 95 semanas hay menos de dos
    ciclos completos, así que una curva por categoría sería ruido. Juntando las
    diez se estima un perfil común, que es la forma de exprimir datos escasos.
    """
    h = hist.copy()
    h["iso"] = h["inicio_semana"].dt.isocalendar().week.astype(int)
    total = h.groupby(["iso", "inicio_semana"])["unidades"].sum().reset_index()
    perfil = total.groupby("iso")["unidades"].mean()
    return perfil / perfil.mean()


def nivel_estacional(hist: pd.DataFrame, corte: pd.Timestamp, horizonte: int) -> pd.Series:
    """Baseline 2: el ritmo reciente, corregido por la forma del año.

    Proyectar plano 14 semanas en un negocio que va de 115 a 600 uds/semana es
    el error que dispara el sesgo. Esto reescala el nivel reciente por la
    relación entre la estacionalidad del futuro y la del pasado inmediato.
    """
    perfil = _perfil_estacional(hist)
    base_iso = [(corte - pd.Timedelta(weeks=k)).isocalendar()[1] for k in range(VENTANA_NIVEL)]
    fut_iso = [(corte + pd.Timedelta(weeks=k + 1)).isocalendar()[1] for k in range(horizonte)]

    f_base = np.mean([perfil.get(i, 1.0) for i in base_iso])
    f_fut = np.sum([perfil.get(i, 1.0) for i in fut_iso])
    if f_base <= 0:
        return nivel_plano(hist, corte, horizonte)

    rec = hist[hist["inicio_semana"] > corte - pd.Timedelta(weeks=VENTANA_NIVEL)]
    ritmo = rec.groupby("grupo")["unidades"].sum() / VENTANA_NIVEL
    return ritmo * (f_fut / f_base)


def nivel_ano_anterior(hist: pd.DataFrame, corte: pd.Timestamp, horizonte: int) -> pd.Series:
    """Baseline 3: lo que pasó en estas mismas semanas el año pasado, ajustado
    por cuánto ha crecido el negocio desde entonces.

    En moda suele ser sorprendentemente competitivo: la forma del año se repite,
    y el único ajuste que hace falta es de escala.
    """
    futuro_ly = [
        (corte + pd.Timedelta(weeks=k + 1) - pd.Timedelta(weeks=52)) for k in range(horizonte)
    ]
    base_ly = [(corte - pd.Timedelta(weeks=k) - pd.Timedelta(weeks=52)) for k in range(VENTANA_NIVEL)]

    ly_fut = hist[hist["inicio_semana"].isin(futuro_ly)].groupby("grupo")["unidades"].sum()
    ly_base = hist[hist["inicio_semana"].isin(base_ly)].groupby("grupo")["unidades"].sum()
    rec = hist[hist["inicio_semana"] > corte - pd.Timedelta(weeks=VENTANA_NIVEL)]
    hoy_base = rec.groupby("grupo")["unidades"].sum()

    grupos = hist["grupo"].unique()
    ly_fut = ly_fut.reindex(grupos).fillna(0.0)
    ly_base = ly_base.reindex(grupos).fillna(0.0)
    hoy_base = hoy_base.reindex(grupos).fillna(0.0)

    # Factor de crecimiento interanual, acotado para que un grupo con dos ventas
    # el año pasado no genere un multiplicador absurdo.
    crecimiento = (hoy_base / ly_base.replace(0, np.nan)).clip(0.25, 4.0)
    crecimiento = crecimiento.fillna(1.0)

    prevision = ly_fut * crecimiento
    # Si no hay histórico del año anterior, no hay nada que extrapolar.
    sin_ly = ly_fut <= 0
    if sin_ly.any():
        respaldo = nivel_estacional(hist, corte, horizonte).reindex(grupos).fillna(0.0)
        prevision[sin_ly] = respaldo[sin_ly]
    return prevision


def _rasgos_ml(hist: pd.DataFrame, corte: pd.Timestamp, horizonte: int) -> pd.DataFrame:
    """Variables de entrada del modelo, para un corte dado.

    Una fila por (grupo, semana futura). Todas las variables se calculan con
    datos anteriores o iguales al corte: si alguna mirase al futuro, la
    validación saldría preciosa y el modelo no serviría para nada.
    """
    perfil = _perfil_estacional(hist)
    filas = []
    for grupo, g in hist.groupby("grupo"):
        serie = g.set_index("inicio_semana")["unidades"]
        rec = {v: serie[serie.index > corte - pd.Timedelta(weeks=v)].sum() / v for v in (2, 4, 8, 13)}
        previo = serie[
            (serie.index <= corte - pd.Timedelta(weeks=13))
            & (serie.index > corte - pd.Timedelta(weeks=26))
        ].sum() / 13
        tendencia = rec[13] / previo if previo > 0 else 1.0

        for k in range(1, horizonte + 1):
            objetivo = corte + pd.Timedelta(weeks=k)
            iso = objetivo.isocalendar()[1]
            ly = serie.get(objetivo - pd.Timedelta(weeks=52), np.nan)
            filas.append({
                "grupo": grupo,
                "inicio_semana": objetivo,
                "h": k,
                "iso": iso,
                "mes": objetivo.month,
                "ritmo_2": rec[2], "ritmo_4": rec[4], "ritmo_8": rec[8], "ritmo_13": rec[13],
                "tendencia": np.clip(tendencia, 0.2, 5.0),
                "estacionalidad": perfil.get(iso, 1.0),
                "ano_anterior": ly,
                "semanas_hist": serie.index.nunique(),
            })
    return pd.DataFrame(filas)


def entrenar_modelo_nivel(hist: pd.DataFrame, horizonte: int, cortes_entrenamiento: int = 40):
    """Entrena un modelo de nivel con el histórico disponible.

    Un único modelo para las diez categorías a la vez: el grupo entra como una
    variable más. Con menos de dos años de histórico, estimar un modelo por
    categoría sería ajustar ruido; agrupándolas, el modelo aprende el patrón
    común y usa el grupo para desviarse de él.

    Se entrena con muchos cortes históricos simulados, cada uno con sus
    variables calculadas solo con lo anterior al corte. Así el modelo ve el
    mismo problema que tendrá que resolver en producción.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor  # import perezoso

    semanas = np.sort(hist["inicio_semana"].unique())
    # Deja fuera el arranque (sin histórico con el que construir las variables) y
    # las últimas `horizonte` semanas (sin futuro con el que comparar). Con poco
    # histórico se reduce el calentamiento antes que quedarse sin ejemplos.
    calentamiento = min(26, max(8, len(semanas) // 3))
    candidatos = semanas[calentamiento:-horizonte] if len(semanas) > calentamiento + horizonte else []
    if len(candidatos) < 5:
        # Sin ejemplos suficientes no se entrena: quien llame debe recurrir a un
        # baseline. Fingir un modelo con cuatro filas sería peor que no tenerlo.
        return None
    if len(candidatos) > cortes_entrenamiento:
        candidatos = candidatos[-cortes_entrenamiento:]

    X, y = [], []
    for corte in candidatos:
        corte = pd.Timestamp(corte)
        h_corte = hist[hist["inicio_semana"] <= corte]
        rasgos = _rasgos_ml(h_corte, corte, horizonte)
        real = hist.set_index(["grupo", "inicio_semana"])["unidades"]
        rasgos["objetivo"] = [
            real.get((g, w), np.nan) for g, w in zip(rasgos["grupo"], rasgos["inicio_semana"])
        ]
        rasgos = rasgos.dropna(subset=["objetivo"])
        X.append(rasgos)
        y.append(rasgos["objetivo"])

    datos = pd.concat(X, ignore_index=True)
    objetivo = pd.concat(y, ignore_index=True)

    columnas = [c for c in datos.columns if c not in ("objetivo", "inicio_semana")]
    datos = datos[columnas].copy()
    datos["grupo"] = datos["grupo"].astype("category")

    modelo = HistGradientBoostingRegressor(
        # Deliberadamente pequeño: con ~5.000 filas y menos de dos ciclos
        # estacionales, un modelo grande memoriza el histórico en vez de
        # aprender el patrón.
        max_depth=4,
        max_iter=250,
        learning_rate=0.06,
        min_samples_leaf=25,
        l2_regularization=1.0,
        categorical_features=["grupo"],
        random_state=42,
    )
    modelo.fit(datos, objetivo)
    return modelo, columnas


def nivel_ml(
    hist: pd.DataFrame, corte: pd.Timestamp, horizonte: int, modelo_entrenado=None
) -> pd.Series:
    """Nivel previsto por el modelo entrenado, sumado sobre el horizonte."""
    if modelo_entrenado is None:
        modelo_entrenado = entrenar_modelo_nivel(hist, horizonte)
    if modelo_entrenado is None:
        # Histórico insuficiente para entrenar. Se cae al mejor baseline en vez
        # de devolver un número inventado.
        return nivel_estacional(hist, corte, horizonte)
    modelo, columnas = modelo_entrenado

    rasgos = _rasgos_ml(hist, corte, horizonte)
    X = rasgos[columnas].copy()
    X["grupo"] = X["grupo"].astype("category")
    rasgos["prediccion"] = np.clip(modelo.predict(X), 0, None)
    return rasgos.groupby("grupo")["prediccion"].sum()


METODOS_NIVEL: Dict[str, Callable] = {
    "plano": nivel_plano,
    "estacional": nivel_estacional,
    "ano_anterior": nivel_ano_anterior,
    "modelo": nivel_ml,
}


# ---------------------------------------------------------------------------
# REPARTO · de la categoría al SKU
# ---------------------------------------------------------------------------

def repartos(
    serie: pd.DataFrame,
    corte: pd.Timestamp,
    ventana: int = VENTANA_REPARTO,
    k: int = K_ENCOGIMIENTO,
) -> pd.DataFrame:
    """Qué fracción de su categoría se lleva cada SKU.

    Dos pasos, porque se comportan distinto:

    1. **Share del modelo dentro de su categoría.** Es estable en el tiempo
       (r = 0,77 entre dos periodos consecutivos de 13 semanas), así que se usa
       el observado tal cual.

    2. **Share de la talla dentro de su modelo**, encogido hacia la curva de
       tallas de la categoría. Aquí el observado es poco fiable: un modelo que
       vendió 4 unidades reparte sus tallas con una muestra de 4. El encogimiento
       mezcla lo observado con la curva de la categoría, dando más peso a lo
       observado cuanto más ha vendido ese modelo:

           peso = uds_modelo / (uds_modelo + k)

       Un modelo con 200 uds usa casi solo su propia curva; uno con 3 usa casi
       solo la de su categoría. Es lo correcto: con 3 unidades no se puede saber
       si esa talla vende más, solo que tuvo suerte.

    Esto es además lo que arregla la curva de tallas que el informe del Reto 1
    dejó marcada como pendiente.
    """
    w = serie[
        (serie["inicio_semana"] <= corte)
        & (serie["inicio_semana"] > corte - pd.Timedelta(weeks=ventana))
    ]
    uds = w.groupby("sku")["unidades"].sum().rename("u")

    d = (
        serie.groupby("sku")[["modelo_id", "grupo", "talla"]].first()
        .join(uds).fillna({"u": 0.0}).reset_index()
    )

    # 1 · share del modelo dentro de la categoría
    por_modelo = d.groupby(["grupo", "modelo_id"], as_index=False)["u"].sum().rename(
        columns={"u": "u_modelo"}
    )
    por_modelo["share_modelo"] = por_modelo["u_modelo"] / por_modelo.groupby("grupo")[
        "u_modelo"
    ].transform("sum")
    d = d.merge(por_modelo[["modelo_id", "u_modelo", "share_modelo"]], on="modelo_id", how="left")

    # 2 · curva de tallas de la categoría, como referencia a la que encoger
    curva = d.groupby(["grupo", "talla"], as_index=False)["u"].sum()
    curva["curva_categoria"] = curva["u"] / curva.groupby("grupo")["u"].transform("sum")
    d = d.merge(curva[["grupo", "talla", "curva_categoria"]], on=["grupo", "talla"], how="left")

    d["share_talla_obs"] = (
        (d["u"] / d["u_modelo"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    # La curva de la categoría, renormalizada a las tallas que ese modelo tiene.
    d["curva_modelo"] = (
        d["curva_categoria"] / d.groupby("modelo_id")["curva_categoria"].transform("sum")
    ).fillna(0.0)

    peso = d["u_modelo"] / (d["u_modelo"] + k)
    d["share_talla"] = peso * d["share_talla_obs"] + (1 - peso) * d["curva_modelo"]

    d["share_categoria"] = d["share_modelo"].fillna(0.0) * d["share_talla"]
    return d[[
        "sku", "modelo_id", "grupo", "talla", "u", "u_modelo",
        "share_modelo", "share_talla", "share_categoria",
    ]]


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------

def prever(
    serie: pd.DataFrame,
    corte: pd.Timestamp,
    horizonte: int,
    metodo: str = "modelo",
    modelo_entrenado=None,
) -> pd.DataFrame:
    """Demanda prevista por SKU para el horizonte: nivel × reparto."""
    hist = serie[serie["inicio_semana"] <= corte]
    grupo_hist = demanda_grupo(hist)

    fn = METODOS_NIVEL[metodo]
    if metodo == "modelo":
        nivel = fn(grupo_hist, corte, horizonte, modelo_entrenado)
    else:
        nivel = fn(grupo_hist, corte, horizonte)
    nivel = nivel.clip(lower=0)

    rep = repartos(hist, corte)
    rep["demanda_horizonte"] = rep["grupo"].map(nivel).fillna(0.0) * rep["share_categoria"]
    rep["demanda_semanal"] = rep["demanda_horizonte"] / horizonte
    rep["horizonte_semanas"] = horizonte
    # Un SKU con poco histórico lleva más curva de categoría que dato propio: se
    # marca para que la propuesta pueda avisar de que esa cifra es menos sólida.
    rep["historico_corto"] = rep["u_modelo"] < K_ENCOGIMIENTO
    return rep


def curva_semanal(
    serie: pd.DataFrame,
    corte: pd.Timestamp,
    horizonte: int,
    modelo_entrenado=None,
) -> pd.DataFrame:
    """Unidades previstas **semana a semana**, no solo el total del horizonte.

    Existe porque el total esconde la forma. El modelo predice cada una de las 14
    semanas por separado y después se suman; enseñar solo la suma hace parecer que
    la previsión es un ritmo plano multiplicado por 14, que es justo lo que no es:
    entre la primera semana y la peor de enero hay un factor de más de tres.

    Devuelve una fila por semana con la fecha, el número de semana vista desde el
    corte y las unidades previstas.
    """
    hist = demanda_grupo(serie[serie["inicio_semana"] <= corte])
    if modelo_entrenado is None:
        modelo_entrenado = entrenar_modelo_nivel(hist, horizonte)
    if modelo_entrenado is None:
        # Sin modelo no hay curva: se reparte el total del baseline a partes
        # iguales y se marca como plana para que nadie la lea como estacional.
        total = nivel_estacional(hist, corte, horizonte).clip(lower=0).sum()
        semanas = [corte + pd.Timedelta(weeks=k + 1) for k in range(horizonte)]
        return pd.DataFrame({
            "inicio_semana": semanas,
            "h": range(1, horizonte + 1),
            "unidades": total / horizonte,
            "estimada": False,
        })

    modelo, columnas = modelo_entrenado
    rasgos = _rasgos_ml(hist, corte, horizonte)
    X = rasgos[columnas].copy()
    X["grupo"] = X["grupo"].astype("category")
    rasgos["unidades"] = np.clip(modelo.predict(X), 0, None)
    curva = rasgos.groupby(["h", "inicio_semana"], as_index=False)["unidades"].sum()
    curva["estimada"] = True
    return curva.sort_values("h").reset_index(drop=True)


def ritmo_reciente(serie: pd.DataFrame, corte: pd.Timestamp) -> float:
    """Unidades por semana de las últimas `VENTANA_NIVEL` semanas.

    Es la cifra que un método plano proyectaría hacia delante sin tocar. Se usa
    como referencia en el gráfico: enseña cuánto corrige el modelo.
    """
    hist = serie[
        (serie["inicio_semana"] <= corte)
        & (serie["inicio_semana"] > corte - pd.Timedelta(weeks=VENTANA_NIVEL))
    ]
    return float(hist["unidades"].sum()) / VENTANA_NIVEL


def comparar_metodos(
    serie: pd.DataFrame,
    horizonte: int,
    n_cortes: int = 4,
    metodos: Tuple[str, ...] = ("plano", "estacional", "ano_anterior", "modelo"),
    paso: int | None = None,
) -> pd.DataFrame:
    """Backtesting con origen móvil: el error de cada método, en igualdad de trato.

    Para cada corte se entrena **solo con lo anterior al corte** y se compara
    contra lo que pasó de verdad en las 14 semanas siguientes. Es la tabla que
    decide qué método se usa, y la que hay que volver a mirar cuando cambie el
    comportamiento del negocio.

    Se reportan dos errores porque miden cosas distintas:
      · **MAE**: cuánto se desvía por SKU, sin importar la dirección.
      · **|sesgo|**: cuánto se desvía el TOTAL, en valor absoluto. Es el que
        importa para comprar: equivocarse arriba y abajo por SKU se compensa en
        el almacén, pero pasarse un 40 % en el total son miles de euros de más.

    El sesgo se toma en valor absoluto a propósito: promediando con signo, un
    corte de +103 % y otro de −62 % se cancelan y el método parece bueno.
    """
    # `paso` separa los cortes. Por defecto, el propio horizonte: ventanas de
    # evaluación que no se solapan, que es lo limpio. Con solo 95 semanas de
    # histórico eso deja 4 cortes, así que se puede pedir un paso menor para
    # tener más puntos de medida, a cambio de que se solapen y sus errores estén
    # correlacionados. Sirve para comprobar que el orden entre métodos aguanta,
    # no para presumir de precisión.
    paso = paso or horizonte
    semanas = np.sort(serie["inicio_semana"].unique())
    cortes = [pd.Timestamp(x) for x in semanas[-(n_cortes * paso + horizonte):-horizonte:paso]]

    filas = []
    for metodo in metodos:
        errores = []
        for corte in cortes:
            hist = serie[serie["inicio_semana"] <= corte]
            fut = serie[
                (serie["inicio_semana"] > corte)
                & (serie["inicio_semana"] <= corte + pd.Timedelta(weeks=horizonte))
            ]
            if hist["inicio_semana"].nunique() < 26 or fut.empty:
                continue
            real = fut.groupby("sku")["unidades"].sum().rename("real")
            pred = prever(hist, corte, horizonte, metodo).set_index("sku")["demanda_horizonte"]
            comp = pd.concat([real, pred.rename("pred")], axis=1).fillna(0.0)
            if comp["real"].sum() <= 0:
                continue
            errores.append({
                "mae": (comp["pred"] - comp["real"]).abs().mean(),
                "sesgo_abs": 100 * abs(comp["pred"].sum() - comp["real"].sum()) / comp["real"].sum(),
                "sesgo": 100 * (comp["pred"].sum() - comp["real"].sum()) / comp["real"].sum(),
            })
        if errores:
            e = pd.DataFrame(errores)
            filas.append({
                "metodo": metodo,
                "n_cortes": len(e),
                "mae": round(e["mae"].mean(), 2),
                "sesgo_abs_pct": round(e["sesgo_abs"].mean(), 1),
                "sesgo_pct": round(e["sesgo"].mean(), 1),
            })
    return pd.DataFrame(filas).sort_values("mae").reset_index(drop=True)


def generar_prevision(
    tablas: Dict[str, pd.DataFrame],
    horizonte: int,
    metodo: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Punto de entrada: devuelve (previsión por SKU, comparativa de métodos).

    Si `metodo` es None se elige el que gana el backtesting. Es a propósito: el
    método no se decide por convicción, se decide por la medición, y la tabla
    que lo justifica viaja con el resultado hasta el informe.
    """
    serie = _con_grupo(
        serie_demanda(tablas["ventas"], tablas["producto"], tablas.get("stock_semanal")),
        tablas["producto"],
    )
    # 12 cortes con paso de 4 semanas, no 4 cortes sin solapar: con 95 semanas de
    # histórico cuatro puntos son pocos para distinguir métodos, y las cifras que
    # se citan en la documentación salen de esta misma llamada.
    comparativa = comparar_metodos(serie, horizonte, n_cortes=12, paso=4)
    if metodo is None:
        metodo = comparativa.iloc[0]["metodo"] if not comparativa.empty else "estacional"

    corte = pd.Timestamp(config.FECHA_CORTE_DATOS)
    corte_semana = corte - pd.Timedelta(days=corte.weekday())
    prevision = prever(serie, corte_semana, horizonte, metodo)
    prevision["metodo"] = metodo
    comparativa["elegido"] = comparativa["metodo"] == metodo

    # La curva semanal viaja con la previsión: es lo que permite enseñar que la
    # cifra no es un ritmo plano multiplicado por el horizonte.
    curva = curva_semanal(serie, corte_semana, horizonte)
    curva.attrs["ritmo_reciente"] = ritmo_reciente(demanda_grupo(serie), corte_semana)
    return prevision, comparativa, curva
