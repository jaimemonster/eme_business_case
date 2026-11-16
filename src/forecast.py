"""Previsión de demanda por SKU (Reto 2).

Responsabilidad: estimar, a partir del histórico de ventas limpias, la demanda
semanal esperada de cada SKU para el horizonte que necesita la reposición
(lead time + cobertura objetivo). Incluye el tratamiento de SKUs sin histórico
suficiente y la medición del error del método elegido.

El Reto 1 también lo usa: las alertas de rotura necesitan saber cuánto se espera
vender en las próximas 4 semanas.

Método base: media móvil de las últimas `VENTANA_SEMANAS` semanas, excluyendo las
ventas a precio especial.

La ventana de 4 semanas no es arbitraria: sale del backtesting con origen móvil
sobre 13 cortes del último año (`evaluar_ventanas`). El negocio tiene una rampa
estacional muy marcada —de ~115 uds/semana en agosto a ~600 en octubre—, y una
ventana larga la persigue con retraso:

    ventana   MAE    sesgo
         2    2.34    +6.7 %
         4    2.09    +9.8 %   <- elegida
         8    2.05   +20.1 %
        12    2.13   +28.6 %

El MAE es casi plano entre 4 y 8 semanas, pero el sesgo se duplica. Con 4 semanas
se conserva casi toda la precisión y se reduce a la mitad la tendencia a
sobrepedir. Un sesgo ligeramente positivo es el lado correcto del error para
reponer: cuesta menos tener stock de más que romper.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

VENTANA_SEMANAS = 4


def serie_semanal_por_sku(
    ventas: pd.DataFrame,
    excluir_especial: bool = True,
) -> pd.DataFrame:
    """Construye la serie de unidades vendidas por SKU y semana ISO, rellenando
    con cero las semanas sin venta dentro del periodo de vida del SKU.

    Rellenar con cero es imprescindible: sin ello, un SKU que vende una semana sí
    y tres no tendría una media cuatro veces mayor de la real.

    `excluir_especial` deja fuera las ventas a precio rebajado. Son liquidación,
    no demanda recurrente: incluirlas inflaría la previsión de un producto que en
    realidad ya no se vende a tarifa.
    """
    v = ventas[~ventas["is_special"]] if excluir_especial else ventas

    serie = (
        v.groupby(["sku", "inicio_semana"], as_index=False)["unidades"]
        .sum()
        .rename(columns={"unidades": "unidades"})
    )

    # Rejilla completa de semanas por SKU: desde su primera venta hasta el final
    # del histórico, para que las semanas sin venta cuenten como cero.
    fin = serie["inicio_semana"].max()
    primeras = serie.groupby("sku")["inicio_semana"].min()
    rejilla = pd.concat(
        [
            pd.DataFrame(
                {
                    "sku": sku,
                    "inicio_semana": pd.date_range(inicio, fin, freq="W-MON"),
                }
            )
            for sku, inicio in primeras.items()
        ],
        ignore_index=True,
    )
    completa = rejilla.merge(serie, on=["sku", "inicio_semana"], how="left")
    completa["unidades"] = completa["unidades"].fillna(0)
    return completa


def prever_demanda_sku(
    serie: pd.DataFrame,
    horizonte_semanas: int,
    ventana: int = VENTANA_SEMANAS,
) -> pd.DataFrame:
    """Devuelve la demanda semanal prevista por SKU para el horizonte indicado.

    Para cada SKU: media de las últimas `ventana` semanas. Un SKU con menos
    histórico que la ventana usa las semanas que tenga, y se marca con
    `historico_corto` para que la propuesta de reposición pueda avisar de que esa
    cifra es menos fiable.
    """
    ultima = serie["inicio_semana"].max()
    corte = ultima - pd.Timedelta(weeks=ventana - 1)
    reciente = serie[serie["inicio_semana"] >= corte]

    previsiones = reciente.groupby("sku").agg(
        demanda_semanal=("unidades", "mean"),
        semanas_observadas=("inicio_semana", "nunique"),
    )
    previsiones["historico_corto"] = previsiones["semanas_observadas"] < ventana
    previsiones["demanda_horizonte"] = previsiones["demanda_semanal"] * horizonte_semanas
    previsiones["horizonte_semanas"] = horizonte_semanas
    return previsiones.reset_index()


def _error_en_corte(
    serie: pd.DataFrame,
    corte: pd.Timestamp,
    horizonte_semanas: int,
    ventana: int,
) -> dict | None:
    """Error de previsión en un corte concreto del histórico."""
    historico = serie[serie["inicio_semana"] <= corte]
    futuro = serie[
        (serie["inicio_semana"] > corte)
        & (serie["inicio_semana"] <= corte + pd.Timedelta(weeks=horizonte_semanas))
    ]
    if historico["inicio_semana"].nunique() < ventana or futuro.empty:
        return None

    real = futuro.groupby("sku")["unidades"].sum().rename("real")
    previsto = prever_demanda_sku(historico, horizonte_semanas, ventana).set_index("sku")[
        "demanda_horizonte"
    ]
    comp = pd.concat([real, previsto], axis=1).fillna(0)
    return {
        "mae": (comp["demanda_horizonte"] - comp["real"]).abs().mean(),
        "sesgo_pct": 100 * (comp["demanda_horizonte"].sum() - comp["real"].sum()) / comp["real"].sum(),
    }


def evaluar_forecast(
    serie: pd.DataFrame,
    horizonte_semanas: int,
    ventana: int = VENTANA_SEMANAS,
    n_cortes: int = 13,
) -> pd.DataFrame:
    """Backtesting con origen móvil: error medio sobre varios cortes del histórico.

    Evaluar en un único corte es engañoso en un negocio tan estacional: medido
    justo en plena rampa de otoño, cualquier media móvil parece quedarse un 25 %
    corta; medido en la bajada, parece pasarse. Se promedia sobre `n_cortes`
    repartidos por el último año para obtener una cifra representativa.
    """
    semanas = sorted(serie["inicio_semana"].unique())
    paso = max(1, horizonte_semanas)
    cortes = [pd.Timestamp(x) for x in semanas[-(n_cortes * paso + horizonte_semanas) : -horizonte_semanas : paso]]

    errores = [e for c in cortes if (e := _error_en_corte(serie, c, horizonte_semanas, ventana))]
    if not errores:
        return pd.DataFrame()

    df = pd.DataFrame(errores)
    return pd.DataFrame(
        [
            {
                "metodo": f"media movil {ventana} semanas",
                "horizonte_semanas": horizonte_semanas,
                "n_cortes": len(errores),
                "mae": round(df["mae"].mean(), 2),
                "sesgo_pct": round(df["sesgo_pct"].mean(), 1),
            }
        ]
    )


def evaluar_ventanas(
    serie: pd.DataFrame,
    horizonte_semanas: int,
    ventanas: tuple[int, ...] = (2, 3, 4, 6, 8, 12),
) -> pd.DataFrame:
    """Compara varias ventanas de media móvil con el mismo backtesting.

    Es la tabla que justifica la elección de `VENTANA_SEMANAS`, y la que hay que
    volver a mirar si cambia el comportamiento del negocio.
    """
    filas = [evaluar_forecast(serie, horizonte_semanas, v) for v in ventanas]
    return pd.concat([f for f in filas if not f.empty], ignore_index=True)


def generar_forecast(
    ventas: pd.DataFrame,
    horizonte_semanas: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Orquesta la previsión y devuelve (previsión, métricas de error)."""
    serie = serie_semanal_por_sku(ventas)
    return prever_demanda_sku(serie, horizonte_semanas), evaluar_forecast(serie, horizonte_semanas)
