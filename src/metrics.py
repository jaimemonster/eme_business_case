"""KPIs del Reto 1 (informe semanal de ventas y stock).

Responsabilidad: calcular, sobre las tablas limpias, los indicadores que responde
el informe semanal. No lee ficheros ni dibuja gráficos: recibe DataFrames y
devuelve DataFrames.
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from . import config, forecast

Periodo = Tuple[dt.date, dt.date]

# Orden natural de las tallas, para listarlas como se leen en una etiqueta.
ORDEN_TALLAS = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5, "U": 6}


def _orden_talla(talla: str) -> int:
    return ORDEN_TALLAS.get(talla, 99)


# Un modelo se considera con exceso de stock si su cobertura supera el doble de
# la cobertura objetivo. Umbral documentado en CLAUDE.md y revisable.
UMBRAL_EXCESO_SEMANAS = 2 * config.COBERTURA_OBJETIVO_SEMANAS


def solo_tarifa(ventas: pd.DataFrame) -> pd.DataFrame:
    """Ventas a precio completo: deja fuera las de precio especial.

    Es el criterio de TODO el análisis de resultado comercial (KPIs, evolución,
    desgloses, rankings, previsión de demanda). El precio especial es
    liquidación de campaña, no venta ordinaria: mezclarlo hace que una semana de
    rebajas parezca una buena semana de venta a tarifa.

    El precio especial no desaparece del informe: se analiza aparte, en la
    pregunta 2, y allí sí se usa la tabla completa.

    Las únicas excepciones son las métricas de **flujo físico** —sell-through y
    sell-through por drop—, donde cuenta toda unidad que salió del almacén,
    rebajada o no. Están marcadas como tales en su docstring.
    """
    return ventas[~ventas["is_special"]]


def _filtrar_periodo(ventas: pd.DataFrame, periodo: Periodo) -> pd.DataFrame:
    """Devuelve las líneas de venta dentro del periodo (ambos extremos incluidos)."""
    inicio, fin = (pd.Timestamp(d) for d in periodo)
    return ventas[(ventas["fecha"] >= inicio) & (ventas["fecha"] <= fin)]


def _agregar(df: pd.DataFrame) -> Dict[str, float]:
    """Agregado estándar de un conjunto de líneas de venta."""
    facturacion = df["facturacion_neta"].sum()
    margen = df["margen"].sum()
    return {
        "unidades": int(df["unidades"].sum()),
        "facturacion_neta": round(facturacion, 2),
        "margen": round(margen, 2),
        "margen_pct": round(100 * margen / facturacion, 1) if facturacion else 0.0,
        "pedidos": int(df["pedido"].nunique()),
        "ticket_medio": round(facturacion / df["pedido"].nunique(), 2) if len(df) else 0.0,
    }


def resumen_semanal(ventas: pd.DataFrame, semana: Periodo) -> pd.DataFrame:
    """Unidades, facturación neta y margen de una semana, separando precio especial.

    Devuelve tres filas: el total, la parte a precio completo y la parte a precio
    especial. `WELCOME10` cuenta como precio completo (es una venta a tarifa con
    un cupón), pero se desglosa aparte en `desglose_precio`.
    """
    w = _filtrar_periodo(ventas, semana)
    filas = [
        {"canal": "TOTAL", **_agregar(w)},
        {"canal": "Precio completo", **_agregar(w[~w["is_special"]])},
        {"canal": "Precio especial", **_agregar(w[w["is_special"]])},
    ]
    return pd.DataFrame(filas)


def comparativa_semanas(
    ventas: pd.DataFrame,
    semana_actual: Periodo,
    semana_anterior: Periodo,
    semana_ano_anterior: Periodo,
) -> pd.DataFrame:
    """Compara la semana de análisis contra la anterior y contra la misma semana ISO
    del año pasado, con variaciones absolutas y en porcentaje."""
    periodos = {
        "Semana actual": semana_actual,
        "Semana anterior": semana_anterior,
        "Misma semana 2024": semana_ano_anterior,
    }
    base = pd.DataFrame(
        [
            {"periodo": nombre, "desde": p[0], "hasta": p[1], **_agregar(_filtrar_periodo(ventas, p))}
            for nombre, p in periodos.items()
        ]
    ).set_index("periodo")

    metricas = ["unidades", "facturacion_neta", "margen"]
    actual = base.loc["Semana actual", metricas]
    for etiqueta, referencia in [("vs_semana_anterior", "Semana anterior"), ("vs_ano_anterior", "Misma semana 2024")]:
        previo = base.loc[referencia, metricas]
        for m in metricas:
            base.loc["Semana actual", f"{m}_{etiqueta}_pct"] = (
                round(100 * (actual[m] - previo[m]) / previo[m], 1) if previo[m] else None
            )
    return base.reset_index()


def desglose_por_dimension(ventas: pd.DataFrame, semana: Periodo, dimension: str) -> pd.DataFrame:
    """Reparto de la semana por mercado, sección o categoría.

    Recibe ya las ventas a tarifa, así que no lleva columna de precio especial:
    sería cero por construcción. El peso de la promoción WELCOME10 sí, porque
    esa sí es venta a tarifa con un cupón encima.
    """
    w = _filtrar_periodo(ventas, semana)
    total_facturacion = w["facturacion_neta"].sum()

    filas = []
    for valor, grupo in w.groupby(dimension):
        agregado = _agregar(grupo)
        con_cupon = grupo[grupo["es_promocion"]]
        promocion = con_cupon["facturacion_neta"].sum()
        filas.append(
            {
                dimension: valor,
                **agregado,
                "peso_pct": round(100 * agregado["facturacion_neta"] / total_facturacion, 1) if total_facturacion else 0.0,
                "pct_promocion": round(100 * promocion / agregado["facturacion_neta"], 1) if agregado["facturacion_neta"] else 0.0,
                # Lo que el cupón deja de ingresar. Ya está descontado de la
                # facturación: se muestra aparte para poder ponerle precio.
                "coste_cupon": round(con_cupon["descuento"].sum(), 2),
            }
        )
    return pd.DataFrame(filas).sort_values("facturacion_neta", ascending=False).reset_index(drop=True)


def sell_through(
    ventas: pd.DataFrame,
    stock: pd.DataFrame,
    periodo: Periodo | None = None,
    nivel: str = "modelo_id",
) -> pd.DataFrame:
    """Sell-through = unidades vendidas / (unidades vendidas + stock actual).

    Si `periodo` es None se calcula sobre **todo el histórico de vida del modelo**,
    que es la lectura útil en moda: cuánto se ha colocado de lo que se compró.
    Acotarlo a una semana daría cifras minúsculas y sin significado.

    **Esta métrica SÍ incluye el precio especial**, al contrario que el resto del
    informe. Es medida de flujo físico, no de resultado comercial: una unidad
    rebajada salió del almacén igual que una vendida a tarifa, y el denominador
    usa el stock actual, que ya refleja esa salida. Excluirla daría un
    sell-through artificialmente bajo y, además, incoherente consigo mismo.
    """
    v = _filtrar_periodo(ventas, periodo) if periodo else ventas
    vendido = v.groupby(nivel)["unidades"].sum().rename("unidades_vendidas")
    disponible = stock.groupby(nivel)["stock_disponible"].sum().rename("stock_actual")

    df = pd.concat([vendido, disponible], axis=1).fillna(0)
    total = df["unidades_vendidas"] + df["stock_actual"]
    df["sell_through_pct"] = (100 * df["unidades_vendidas"] / total).where(total > 0).round(1)
    return df.reset_index()


def ranking_modelos(
    ventas: pd.DataFrame,
    ventas_todas: pd.DataFrame,
    stock: pd.DataFrame,
    periodo: Periodo,
    top_n: int = 10,
) -> Dict[str, pd.DataFrame]:
    """Top y bottom de modelos por ventas, con su sell-through.

    El ranking se hace sobre las ventas **a tarifa** del periodo indicado, pero
    el sell-through que lo acompaña sale de `ventas_todas` y es el histórico del
    modelo: es flujo físico y mezclar ambos criterios en la misma columna
    engañaría.
    """
    w = _filtrar_periodo(ventas, periodo)
    st = sell_through(ventas_todas, stock).set_index("modelo_id")

    agregado = (
        w.groupby(["modelo_id", "modelo_nombre", "seccion", "categoria"])
        .agg(
            unidades=("unidades", "sum"),
            facturacion_neta=("facturacion_neta", "sum"),
            margen=("margen", "sum"),
        )
        .reset_index()
    )
    agregado["margen_pct"] = (100 * agregado["margen"] / agregado["facturacion_neta"]).round(1)
    agregado = agregado.merge(st[["unidades_vendidas", "stock_actual", "sell_through_pct"]], on="modelo_id", how="left")
    agregado = agregado.round(2).sort_values("unidades", ascending=False)

    # Los modelos sin ninguna venta en la semana no aparecen en el agregado: hay
    # que añadirlos para que el "bottom" sea honesto. Un modelo que no vendió
    # nada es peor noticia que uno que vendió una unidad.
    sin_venta = st[~st.index.isin(agregado["modelo_id"])].reset_index()
    sin_venta = sin_venta[sin_venta["stock_actual"] > 0]
    # Sin el nombre comercial la tabla es ilegible: nadie reconoce un modelo por
    # su referencia.
    nombres = (
        ventas_todas[["modelo_id", "modelo_nombre", "seccion", "categoria"]]
        .drop_duplicates("modelo_id")
    )
    sin_venta = sin_venta.merge(nombres, on="modelo_id", how="left")

    return {
        "top": agregado.head(top_n).reset_index(drop=True),
        "bottom": agregado.tail(top_n).sort_values("unidades").reset_index(drop=True),
        "sin_venta_en_la_semana": sin_venta.sort_values("stock_actual", ascending=False).reset_index(drop=True),
    }


def alertas_stock(
    ventas: pd.DataFrame,
    stock: pd.DataFrame,
    compras: pd.DataFrame,
    producto: pd.DataFrame,
    horizonte_semanas: int = config.HORIZONTE_ROTURA_SEMANAS,
) -> Dict[str, pd.DataFrame]:
    """Modelos en riesgo de rotura en el horizonte indicado y modelos con exceso
    de stock, según las definiciones documentadas en CLAUDE.md.

    Rotura: `stock + compras que llegan en <= horizonte < demanda prevista`.
    Las compras vencidas sin confirmar **no cuentan** como stock en camino: su
    fecha estimada ya pasó y no hay constancia de que hayan llegado.
    """
    # `ventas` llega ya sin precio especial, así que el filtro propio del
    # forecast no tiene nada que quitar. Se deja por si se le pasa otra tabla.
    prevision, _ = forecast.generar_forecast(ventas, horizonte_semanas)
    corte = pd.Timestamp(config.FECHA_CORTE_DATOS)
    limite = corte + pd.Timedelta(weeks=horizonte_semanas)

    en_camino = compras[
        (~compras["ha_llegado"])
        & (~compras["esta_vencida"])
        & (compras["fecha_llegada_efectiva"] <= limite)
    ]
    en_camino = en_camino.groupby("sku")["unidades"].sum().rename("en_camino")

    base = (
        stock.groupby(["sku", "modelo_id", "modelo_nombre", "seccion", "categoria", "talla"], as_index=False)[
            "stock_disponible"
        ]
        .sum()
        .merge(prevision[["sku", "demanda_semanal", "demanda_horizonte"]], on="sku", how="left")
        .merge(en_camino, on="sku", how="left")
    )
    base[["demanda_semanal", "demanda_horizonte", "en_camino"]] = base[
        ["demanda_semanal", "demanda_horizonte", "en_camino"]
    ].fillna(0)

    base["disponible_total"] = base["stock_disponible"] + base["en_camino"]
    # Sin demanda prevista la cobertura es infinita: se deja como NaN y el caso
    # se trata aparte, en "sin rotación".
    base["cobertura_semanas"] = (
        (base["stock_disponible"] / base["demanda_semanal"])
        .replace([np.inf, -np.inf], np.nan)
        .round(1)
    )
    base["deficit"] = (base["demanda_horizonte"] - base["disponible_total"]).round(1)

    # Agregado a modelo: es el nivel al que decide dirección.
    por_modelo = (
        base.groupby(["modelo_id", "modelo_nombre", "seccion", "categoria"], as_index=False)
        .agg(
            stock_disponible=("stock_disponible", "sum"),
            en_camino=("en_camino", "sum"),
            demanda_semanal=("demanda_semanal", "sum"),
            demanda_horizonte=("demanda_horizonte", "sum"),
            tallas=("sku", "count"),
        )
        .round(1)
    )
    por_modelo["disponible_total"] = por_modelo["stock_disponible"] + por_modelo["en_camino"]
    por_modelo["cobertura_semanas"] = (
        (por_modelo["stock_disponible"] / por_modelo["demanda_semanal"])
        .replace([np.inf, -np.inf], np.nan)
        .round(1)
    )

    en_rotura_sku = base[base["deficit"] > 0]

    # Un modelo está en rotura si le falta ALGUNA talla, no si le falta stock en
    # conjunto. Sumar tallas antes de comparar esconde el problema: un modelo con
    # exceso de XL y cero de M parece sano y no lo está. No se puede vender una M
    # a quien necesita una M con el stock de XL.
    rotura = (
        en_rotura_sku.groupby(["modelo_id", "modelo_nombre", "seccion", "categoria"], as_index=False)
        .agg(
            tallas_en_rotura=("sku", "count"),
            tallas_sin_stock=("stock_disponible", lambda x: int((x == 0).sum())),
            deficit_unidades=("deficit", "sum"),
            # Las tres cifras siguientes son SOLO de las tallas en rotura, para
            # que el déficit se pueda comprobar restando. El stock del modelo
            # entero va aparte: mezclarlos hace que las cuentas no cuadren.
            demanda_tallas_rotura=("demanda_horizonte", "sum"),
            stock_tallas_rotura=("stock_disponible", "sum"),
            en_camino_tallas_rotura=("en_camino", "sum"),
            tallas_rotas=("talla", lambda t: ", ".join(sorted(t, key=_orden_talla))),
        )
        .merge(por_modelo[["modelo_id", "tallas", "stock_disponible", "en_camino"]], on="modelo_id")
        .rename(columns={"stock_disponible": "stock_modelo", "en_camino": "en_camino_modelo"})
        .round(1)
        .sort_values("deficit_unidades", ascending=False)
    )

    exceso = _marcar_exceso(por_modelo, producto)
    sin_rotacion = por_modelo[
        (por_modelo["demanda_semanal"] == 0) & (por_modelo["stock_disponible"] > 0)
    ].sort_values("stock_disponible", ascending=False)

    return {
        "rotura_por_modelo": rotura.reset_index(drop=True),
        "rotura_por_sku": en_rotura_sku.sort_values("deficit", ascending=False).reset_index(drop=True),
        "exceso_por_modelo": exceso.reset_index(drop=True),
        "sin_rotacion": sin_rotacion.reset_index(drop=True),
        "cobertura_global": _cobertura_global(por_modelo),
    }


def _marcar_exceso(por_modelo: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Modelos con exceso de stock, ordenados por capital inmovilizado.

    La cobertura en semanas sola no sirve para priorizar: con el stock actual,
    100 de los 119 modelos superan el umbral, y una lista de 100 no es una lista
    de acciones. Lo que decide dirección es **cuánto dinero** hay parado, así que
    se valora el exceso a coste.
    """
    coste_medio = producto.groupby("modelo_id")["coste_unitario"].mean().rename("coste_unitario")
    exceso = por_modelo.merge(coste_medio, on="modelo_id", how="left")
    exceso = exceso[
        (exceso["demanda_semanal"] > 0)
        & (exceso["cobertura_semanas"] > UMBRAL_EXCESO_SEMANAS)
    ].copy()

    # Unidades por encima de la cobertura objetivo: lo que sobra de verdad.
    exceso["unidades_exceso"] = (
        exceso["stock_disponible"] - exceso["demanda_semanal"] * config.COBERTURA_OBJETIVO_SEMANAS
    ).round(0)
    exceso["capital_inmovilizado"] = (exceso["unidades_exceso"] * exceso["coste_unitario"]).round(0)
    return exceso.sort_values("capital_inmovilizado", ascending=False)


def _cobertura_global(por_modelo: pd.DataFrame) -> pd.DataFrame:
    """Foto de conjunto del stock: cuántas semanas de venta hay en el almacén."""
    stock_total = por_modelo["stock_disponible"].sum()
    demanda_semanal = por_modelo["demanda_semanal"].sum()
    return pd.DataFrame(
        [
            {
                "stock_total_uds": int(stock_total),
                "demanda_semanal_prevista": round(demanda_semanal, 1),
                "cobertura_global_semanas": round(stock_total / demanda_semanal, 1) if demanda_semanal else None,
                "cobertura_objetivo_semanas": config.COBERTURA_OBJETIVO_SEMANAS,
                "modelos_por_encima_del_umbral": int(
                    (por_modelo["cobertura_semanas"] > UMBRAL_EXCESO_SEMANAS).sum()
                ),
                "modelos_totales": len(por_modelo),
            }
        ]
    )


def calcular_todas_las_metricas(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Orquesta el cálculo de todos los KPIs del informe y los persiste en
    data/processed.

    Aquí se decide qué tabla recibe cada métrica, y es la única decisión que hay
    que entender para leer el informe:

    - `tarifa`  (sin precio especial) → todo el resultado comercial: KPIs,
      evolución, desgloses, rankings, previsión de demanda y alertas de stock.
    - `ventas`  (completa)            → el análisis del precio especial, que es
      su objeto, y las métricas de flujo físico (sell-through).
    """
    from . import storage

    ventas, stock, compras = tablas["ventas"], tablas["stock"], tablas["compras"]
    producto = tablas["producto"]
    tarifa = solo_tarifa(ventas)
    semana = config.SEMANA_ACTUAL

    metricas: Dict[str, pd.DataFrame] = {
        # El resumen semanal es la excepción deliberada: su objeto es enseñar el
        # reparto entre tarifa y precio especial, así que necesita la tabla entera.
        "resumen_semanal": resumen_semanal(ventas, semana),
        "comparativa": comparativa_semanas(
            tarifa, semana, config.SEMANA_ANTERIOR, config.SEMANA_ANO_ANTERIOR
        ),
    }
    for dimension in ("mercado", "seccion", "categoria"):
        metricas[f"desglose_{dimension}"] = desglose_por_dimension(tarifa, semana, dimension)

    metricas.update(
        {f"ranking_{k}": v for k, v in ranking_modelos(tarifa, ventas, stock, semana).items()}
    )
    metricas.update(alertas_stock(tarifa, stock, compras, producto))

    metricas.update(
        {
            "evolucion_semanal": evolucion_semanal(tarifa),
            "estacionalidad_especial": estacionalidad_precio_especial(ventas),
            "curva_tallas": curva_tallas(tarifa, stock),
            "margen_cupon": margen_del_cupon(tarifa, semana),
            "efecto_mezcla": efecto_mezcla(tarifa, semana, config.SEMANA_ANO_ANTERIOR),
            "reparto_categoria_interanual": reparto_categoria_interanual(
                tarifa, semana, config.SEMANA_ANO_ANTERIOR
            ),
            "fiabilidad_proveedores": fiabilidad_proveedores(compras),
            "sell_through_drop": sell_through_por_drop(ventas, stock, producto),
            "crecimiento": descomposicion_crecimiento(tarifa, semana, config.SEMANA_ANO_ANTERIOR),
            "concentracion": concentracion_ventas(tarifa),
            "sensibilidad_umbral": sensibilidad_umbral_exceso(tarifa, stock, compras, producto),
            "resumen_limpieza": tablas["resumen_limpieza"],
        }
    )

    for nombre, df in metricas.items():
        storage.guardar_tabla(df, nombre, config.DIR_PROCESSED)
    return metricas


# ---------------------------------------------------------------------------
# Indicadores adicionales. No los pide el enunciado, pero responden a las
# preguntas que surgen al leer las cuatro obligatorias.
# ---------------------------------------------------------------------------


def evolucion_semanal(ventas: pd.DataFrame, n_semanas: int = 26) -> pd.DataFrame:
    """Serie semanal de las últimas semanas, con la misma semana ISO del año anterior.

    La comparación se hace por **número de semana ISO**, no por fecha: así ambas
    series tienen los mismos días de la semana y la estacionalidad cuadra.
    """
    por_semana = ventas.groupby(["anio_iso", "semana_iso"], as_index=False).agg(
        inicio_semana=("inicio_semana", "min"),
        unidades=("unidades", "sum"),
        facturacion_neta=("facturacion_neta", "sum"),
        margen=("margen", "sum"),
    )
    reciente = por_semana.sort_values("inicio_semana").tail(n_semanas).copy()

    anterior = por_semana.copy()
    anterior["anio_iso"] += 1  # para cruzar con la misma semana del año siguiente
    anterior = anterior[["anio_iso", "semana_iso", "unidades", "facturacion_neta", "margen"]]

    g = reciente.merge(anterior, on=["anio_iso", "semana_iso"], how="left", suffixes=("", "_ly"))
    g["margen_pct"] = (100 * g["margen"] / g["facturacion_neta"]).round(1)

    # Variación interanual de cada métrica, semana a semana.
    for columna in ("unidades", "facturacion_neta", "margen"):
        previo = g[f"{columna}_ly"]
        g[f"{columna}_yoy"] = (100 * (g[columna] - previo) / previo).where(previo > 0).round(1)
    return g.reset_index(drop=True)


def estacionalidad_precio_especial(ventas: pd.DataFrame) -> pd.DataFrame:
    """Unidades a precio especial y a precio completo por mes.

    Responde al "0 % esta semana": el precio especial no es continuo, se
    concentra en campañas.
    """
    v = ventas.copy()
    v["mes"] = v["fecha"].dt.to_period("M").dt.to_timestamp()
    g = (
        v.groupby("mes")
        .apply(
            lambda x: pd.Series(
                {
                    "uds_especial": x.loc[x["is_special"], "unidades"].sum(),
                    "uds_total": x["unidades"].sum(),
                    "eur_especial": x.loc[x["is_special"], "facturacion_neta"].sum(),
                    "eur_total": x["facturacion_neta"].sum(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    g["pct_especial"] = (100 * g["uds_especial"] / g["uds_total"]).round(1)
    g["pct_especial_eur"] = (100 * g["eur_especial"] / g["eur_total"]).round(1)
    # La parte a precio completo, explícita: apilada con la especial suma el
    # total, que es la relación real entre ambas y evita leerlas como series
    # independientes.
    g["uds_completo"] = g["uds_total"] - g["uds_especial"]
    g["eur_completo"] = g["eur_total"] - g["eur_especial"]
    return g


def efecto_mezcla(ventas: pd.DataFrame, actual: Periodo, referencia: Periodo) -> pd.DataFrame:
    """Separa cuánto del cambio en el precio medio por unidad es mezcla de producto.

    El precio medio por unidad sube tanto si se sube el precio como si se vende
    más producto caro. Para distinguirlo se recalcula el precio medio del periodo
    actual aplicando el **reparto por categoría del periodo de referencia**: lo
    que quede de diferencia es precio; el resto, mezcla.
    """
    hoy, antes = _filtrar_periodo(ventas, actual), _filtrar_periodo(ventas, referencia)
    if not len(hoy) or not len(antes):
        return pd.DataFrame()

    real_hoy = hoy["facturacion_neta"].sum() / hoy["unidades"].sum()
    real_antes = antes["facturacion_neta"].sum() / antes["unidades"].sum()

    precio_hoy = hoy.groupby("categoria").apply(
        lambda x: x["facturacion_neta"].sum() / x["unidades"].sum(), include_groups=False
    )
    reparto_antes = antes.groupby("categoria")["unidades"].sum()
    reparto_antes = reparto_antes / reparto_antes.sum()
    # Precio medio de hoy si se hubiese vendido la mezcla de entonces.
    con_mezcla_antigua = (reparto_antes * precio_hoy).dropna().sum()

    return pd.DataFrame([{
        "precio_medio_actual": round(real_hoy, 2),
        "precio_medio_referencia": round(real_antes, 2),
        "precio_medio_con_mezcla_antigua": round(con_mezcla_antigua, 2),
        "efecto_precio_pct": round(100 * (con_mezcla_antigua - real_antes) / real_antes, 1),
        "efecto_mezcla_pct": round(100 * (real_hoy - con_mezcla_antigua) / real_antes, 1),
    }])


def reparto_categoria_interanual(
    ventas: pd.DataFrame, actual: Periodo, referencia: Periodo
) -> pd.DataFrame:
    """Peso de cada categoría sobre las unidades, en ambos periodos.

    Es la evidencia del efecto mezcla: enseña qué se ha movido.
    """
    def peso(periodo: Periodo) -> pd.Series:
        uds = _filtrar_periodo(ventas, periodo).groupby("categoria")["unidades"].sum()
        return (100 * uds / uds.sum()).round(1)

    df = pd.concat([peso(actual).rename("pct_actual"), peso(referencia).rename("pct_referencia")], axis=1)
    return df.fillna(0).reset_index().sort_values("pct_actual", ascending=False)


def margen_del_cupon(ventas: pd.DataFrame, semana: Periodo) -> pd.DataFrame:
    """Qué margen deja una venta con cupón frente a una sin él.

    El descuento del cupón sale de la facturación, así que el margen en euros
    cae igual; lo que se ve aquí es cuántos puntos de margen cuesta.
    """
    w = _filtrar_periodo(ventas, semana)

    def margen_pct(df: pd.DataFrame) -> float:
        facturacion = df["facturacion_neta"].sum()
        return round(100 * df["margen"].sum() / facturacion, 1) if facturacion else 0.0

    con, sin = w[w["es_promocion"]], w[~w["es_promocion"]]
    return pd.DataFrame([{
        "margen_pct_con_cupon": margen_pct(con),
        "margen_pct_sin_cupon": margen_pct(sin),
        "descuento_dado": round(con["descuento"].sum(), 2),
        "facturacion_con_cupon": round(con["facturacion_neta"].sum(), 2),
    }])


def curva_tallas(ventas: pd.DataFrame, stock: pd.DataFrame, semanas: int = 12) -> pd.DataFrame:
    """Compara el reparto de la demanda reciente por talla con el del stock.

    Es la explicación de la paradoja de tener mucho stock y a la vez roturas:
    el almacén no está mal dimensionado, está mal repartido.
    """
    desde = ventas["fecha"].max() - pd.Timedelta(weeks=semanas)
    reciente = ventas[ventas["fecha"] >= desde]

    demanda = reciente.groupby("talla")["unidades"].sum().rename("demanda")
    disponible = stock.groupby("talla")["stock_disponible"].sum().rename("stock")

    df = pd.concat([demanda, disponible], axis=1).fillna(0)
    df["pct_demanda"] = (100 * df["demanda"] / df["demanda"].sum()).round(1)
    df["pct_stock"] = (100 * df["stock"] / df["stock"].sum()).round(1)
    df["desvio_pp"] = (df["pct_stock"] - df["pct_demanda"]).round(1)
    # Unidades que sobran o faltan si el stock siguiera la curva de la demanda.
    df["stock_ideal"] = (df["demanda"] / df["demanda"].sum() * df["stock"].sum()).round(0)
    df["desvio_uds"] = (df["stock"] - df["stock_ideal"]).round(0)

    return df.reset_index().sort_values("talla", key=lambda s: s.map(_orden_talla)).reset_index(drop=True)


def fiabilidad_proveedores(compras: pd.DataFrame) -> pd.DataFrame:
    """Puntualidad de cada proveedor frente a su propia fecha estimada."""
    llegadas = compras[compras["fecha_llegada_real"].notna()]
    g = llegadas.groupby("proveedor").agg(
        entregas=("sku", "size"),
        retraso_medio=("dias_retraso", "mean"),
        pct_tarde=("dias_retraso", lambda x: 100 * (x > 0).mean()),
        retraso_maximo=("dias_retraso", "max"),
    )
    vencidas = compras[compras["esta_vencida"]].groupby("proveedor").size().rename("vencidas")
    return g.join(vencidas).fillna(0).round(1).reset_index()


def sell_through_por_drop(
    ventas: pd.DataFrame, stock: pd.DataFrame, producto: pd.DataFrame
) -> pd.DataFrame:
    """Sell-through de cada drop junto a su antigüedad.

    La antigüedad es imprescindible para leerlo: un drop nuevo con sell-through
    bajo es normal; uno viejo con sell-through bajo está atascado.

    Como el sell-through por modelo, **incluye el precio especial**: mide salida
    física de almacén. Un drop se puede liquidar, y eso cuenta como colocado.
    """
    vendido = ventas.groupby("drop")["unidades"].sum().rename("vendido")
    disponible = stock.groupby("drop")["stock_disponible"].sum().rename("stock")
    primera = ventas.groupby("drop")["fecha"].min().rename("primera_venta")
    coste = producto.groupby("drop")["coste_unitario"].mean().rename("coste_medio")

    df = pd.concat([primera, vendido, disponible, coste], axis=1).fillna(0)
    df["semanas_vida"] = (
        (pd.Timestamp(config.FECHA_CORTE_DATOS) - df["primera_venta"]).dt.days // 7
    )
    df["sell_through_pct"] = (100 * df["vendido"] / (df["vendido"] + df["stock"])).round(1)
    df["capital"] = (df["stock"] * df["coste_medio"]).round(0)
    return df.reset_index().sort_values("semanas_vida", ascending=False).reset_index(drop=True)


def descomposicion_crecimiento(
    ventas: pd.DataFrame, semana_actual: Periodo, semana_referencia: Periodo
) -> pd.DataFrame:
    """Descompone la variación de facturación en pedidos x cesta x precio medio.

    Facturación = pedidos x unidades por pedido x precio medio por unidad. Saber
    cuál de los tres factores se mueve cambia la decisión: no es lo mismo crecer
    por captación que por subida de precio.
    """
    filas = []
    for nombre, periodo in [("actual", semana_actual), ("referencia", semana_referencia)]:
        w = _filtrar_periodo(ventas, periodo)
        pedidos = w["pedido"].nunique()
        unidades = w["unidades"].sum()
        facturacion = w["facturacion_neta"].sum()
        filas.append(
            {
                "periodo": nombre,
                "pedidos": pedidos,
                "uds_por_pedido": round(unidades / pedidos, 2),
                "precio_medio_ud": round(facturacion / unidades, 2),
                "ticket_medio": round(facturacion / pedidos, 2),
                "facturacion_neta": round(facturacion, 2),
            }
        )
    df = pd.DataFrame(filas).set_index("periodo")
    variacion = (100 * (df.loc["actual"] / df.loc["referencia"] - 1)).round(1)
    variacion.name = "variacion_pct"
    return pd.concat([df, variacion.to_frame().T]).reset_index(names="periodo")


def concentracion_ventas(ventas: pd.DataFrame, semanas: int = 12) -> pd.DataFrame:
    """Cuántos modelos concentran el 50 %, 80 % y 90 % de la facturación."""
    desde = ventas["fecha"].max() - pd.Timedelta(weeks=semanas)
    reciente = ventas[ventas["fecha"] >= desde]
    por_modelo = reciente.groupby("modelo_id")["facturacion_neta"].sum().sort_values(ascending=False)
    acumulado = por_modelo.cumsum() / por_modelo.sum()
    total_catalogo = ventas["modelo_id"].nunique()

    filas = []
    for umbral in (0.5, 0.8, 0.9):
        n = int((acumulado <= umbral).sum()) + 1
        filas.append(
            {
                "pct_facturacion": int(100 * umbral),
                "n_modelos": n,
                "pct_catalogo": round(100 * n / total_catalogo, 0),
            }
        )
    return pd.DataFrame(filas)


def sensibilidad_umbral_exceso(
    ventas: pd.DataFrame, stock: pd.DataFrame, compras: pd.DataFrame, producto: pd.DataFrame
) -> pd.DataFrame:
    """Cuántos modelos quedan marcados como exceso según dónde se ponga el umbral.

    Hace transparente una decisión que es nuestra, no del enunciado: si el
    resultado apenas cambia entre 8 y 16 semanas, el umbral deja de ser el
    problema.
    """
    alertas = alertas_stock(ventas, stock, compras, producto)
    cobertura = alertas["exceso_por_modelo"]["cobertura_semanas"]
    total = ventas["modelo_id"].nunique()
    filas = [
        {
            "umbral_semanas": u,
            "modelos": int((cobertura > u).sum()),
            "pct_catalogo": round(100 * int((cobertura > u).sum()) / total, 0),
        }
        for u in (8, 12, 16, 20, 24, 32, 52)
    ]
    return pd.DataFrame(filas)
