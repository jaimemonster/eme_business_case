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

# Un modelo se considera con exceso de stock si su cobertura supera el doble de
# la cobertura objetivo. Umbral documentado en CLAUDE.md y revisable.
UMBRAL_EXCESO_SEMANAS = 2 * config.COBERTURA_OBJETIVO_SEMANAS


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
    """Reparto de la semana por mercado, sección o categoría, con el peso del
    precio especial y de la promoción sobre el total."""
    w = _filtrar_periodo(ventas, semana)
    total_facturacion = w["facturacion_neta"].sum()

    filas = []
    for valor, grupo in w.groupby(dimension):
        agregado = _agregar(grupo)
        especial = grupo[grupo["is_special"]]["facturacion_neta"].sum()
        promocion = grupo[grupo["es_promocion"]]["facturacion_neta"].sum()
        filas.append(
            {
                dimension: valor,
                **agregado,
                "peso_pct": round(100 * agregado["facturacion_neta"] / total_facturacion, 1) if total_facturacion else 0.0,
                "pct_precio_especial": round(100 * especial / agregado["facturacion_neta"], 1) if agregado["facturacion_neta"] else 0.0,
                "pct_promocion": round(100 * promocion / agregado["facturacion_neta"], 1) if agregado["facturacion_neta"] else 0.0,
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
    stock: pd.DataFrame,
    periodo: Periodo,
    top_n: int = 10,
) -> Dict[str, pd.DataFrame]:
    """Top y bottom de modelos por ventas, con su sell-through.

    El ranking se hace sobre el periodo indicado (la semana), pero el
    sell-through que lo acompaña es el histórico del modelo: mezclar ambos en la
    misma ventana no diría nada.
    """
    w = _filtrar_periodo(ventas, periodo)
    st = sell_through(ventas, stock).set_index("modelo_id")

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
            demanda_horizonte=("demanda_horizonte", "sum"),
        )
        .merge(por_modelo[["modelo_id", "tallas", "stock_disponible", "en_camino"]], on="modelo_id")
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
    data/processed."""
    from . import storage

    ventas, stock, compras = tablas["ventas"], tablas["stock"], tablas["compras"]
    semana = config.SEMANA_ACTUAL

    metricas: Dict[str, pd.DataFrame] = {
        "resumen_semanal": resumen_semanal(ventas, semana),
        "comparativa": comparativa_semanas(
            ventas, semana, config.SEMANA_ANTERIOR, config.SEMANA_ANO_ANTERIOR
        ),
    }
    for dimension in ("mercado", "seccion", "categoria"):
        metricas[f"desglose_{dimension}"] = desglose_por_dimension(ventas, semana, dimension)

    metricas.update({f"ranking_{k}": v for k, v in ranking_modelos(ventas, stock, semana).items()})
    metricas.update(alertas_stock(ventas, stock, compras, tablas["producto"]))

    for nombre, df in metricas.items():
        storage.guardar_tabla(df, nombre, config.DIR_PROCESSED)
    return metricas
