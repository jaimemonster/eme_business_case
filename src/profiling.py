"""Perfilado de calidad de datos.

Responsabilidad: describir el estado de las tablas crudas (tipos, nulos,
duplicados, cardinalidades, rangos, valores imposibles, claves huérfanas) para
poder decidir cómo limpiarlas. No transforma nada: solo observa y reporta.

Su salida alimenta docs/notas_calidad_datos.md.
"""

from __future__ import annotations

import collections
from typing import Dict, List

import pandas as pd

from . import config

# Columna que identifica el producto en cada tabla.
COLUMNA_SKU = "SKU"


def perfilar_tabla(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    """Devuelve un resumen por columna: tipo, % nulos, nº únicos, min/max y ejemplos.

    Se apoya en que las tablas se cargan con `dtype=object`, así que puede contar
    los tipos reales celda a celda y detectar columnas con tipos mezclados.
    """
    filas = []
    for col in df.columns:
        serie = df[col]
        tipos = collections.Counter(
            type(v).__name__ for v in serie if not pd.isna(v)
        )
        no_nulos = serie.dropna()
        try:
            minimo, maximo = no_nulos.min(), no_nulos.max()
        except TypeError:  # tipos no comparables entre sí
            minimo = maximo = "(tipos mezclados)"
        filas.append(
            {
                "tabla": nombre,
                "columna": col,
                "tipos": dict(tipos),
                "n_nulos": int(serie.isna().sum()),
                "pct_nulos": round(100 * serie.isna().mean(), 2),
                "n_unicos": int(no_nulos.nunique()),
                "min": minimo,
                "max": maximo,
                "ejemplos": list(no_nulos.unique()[:3]),
            }
        )
    return pd.DataFrame(filas)


def detectar_duplicados(df: pd.DataFrame, claves: List[str]) -> pd.DataFrame:
    """Devuelve las filas duplicadas según el conjunto de claves indicado."""
    return df[df.duplicated(subset=claves, keep=False)].sort_values(claves)


def detectar_claves_huerfanas(tablas: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Busca SKUs de VENTAS/STOCK/COMPRAS que no existen en PRODUCTO (y viceversa).

    Distingue los huérfanos *reales* de los que solo lo son por diferencias de
    mayúsculas/minúsculas o espacios, porque el tratamiento es muy distinto:
    los primeros hay que decidirlos, los segundos se arreglan normalizando.
    """
    catalogo = set(tablas["PRODUCTO"][COLUMNA_SKU])
    catalogo_norm = {s.upper().strip() for s in catalogo}

    filas = []
    for nombre in ("VENTAS", "STOCK", "COMPRAS"):
        df = tablas[nombre]
        huerfanos = sorted(set(df[COLUMNA_SKU]) - catalogo)
        reales = [s for s in huerfanos if s.upper().strip() not in catalogo_norm]
        por_formato = [s for s in huerfanos if s.upper().strip() in catalogo_norm]
        filas.append(
            {
                "tabla": nombre,
                "n_huerfanos": len(huerfanos),
                "n_filas_afectadas": int(df[COLUMNA_SKU].isin(huerfanos).sum()),
                "huerfanos_reales": reales,
                "huerfanos_por_formato": por_formato[:10],
            }
        )

    # Cobertura inversa: catálogo sin stock y catálogo sin ventas.
    ventas_norm = {s.upper().strip() for s in tablas["VENTAS"][COLUMNA_SKU]}
    stock_norm = {s.upper().strip() for s in tablas["STOCK"][COLUMNA_SKU]}
    filas.append(
        {
            "tabla": "PRODUCTO (cobertura inversa)",
            "n_huerfanos": len(catalogo_norm - stock_norm),
            "n_filas_afectadas": len(catalogo_norm - ventas_norm),
            "huerfanos_reales": sorted(catalogo_norm - stock_norm)[:10],
            "huerfanos_por_formato": "n_filas_afectadas = SKUs sin ninguna venta",
        }
    )
    return pd.DataFrame(filas)


def detectar_valores_imposibles(
    tablas: Dict[str, pd.DataFrame],
    fecha_referencia: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Marca valores fuera de rango: unidades/precios negativos, fechas fuera del
    periodo, descuentos superiores al importe, costes mayores que el PVP, etc.

    `fecha_referencia` es el "hoy" contra el que se juzga si una compra está
    vencida. Por defecto, la fecha de corte de los datos (`FECHA_CORTE_DATOS`),
    que es independiente de la semana que analice el informe del Reto 1.
    """
    if fecha_referencia is None:
        fecha_referencia = pd.Timestamp(config.FECHA_CORTE_DATOS)
    ventas = tablas["VENTAS"]
    compras = tablas["COMPRAS"]
    producto = tablas["PRODUCTO"]
    stock = tablas["STOCK"]

    unidades = ventas["Unidades"].astype(float)
    pvp = ventas["PVP unitario (€)"].astype(float)
    descuento = ventas["Descuento (€)"].astype(float)
    bruto = unidades * pvp

    estimada = pd.to_datetime(compras["Fecha llegada estimada"])
    real = pd.to_datetime(compras["Fecha llegada real"])

    comprobaciones = [
        ("VENTAS", "unidades <= 0", int((unidades <= 0).sum())),
        ("VENTAS", "pvp unitario <= 0", int((pvp <= 0).sum())),
        ("VENTAS", "descuento negativo", int((descuento < 0).sum())),
        ("VENTAS", "descuento > importe bruto", int((descuento > bruto).sum())),
        ("COMPRAS", "unidades <= 0", int((compras["Unidades"].astype(float) <= 0).sum())),
        ("COMPRAS", "fecha real anterior a la estimada", int((real < estimada).sum())),
        ("COMPRAS", "sin fecha real y estimada ya vencida", int((real.isna() & (estimada <= fecha_referencia)).sum())),
        ("STOCK", "stock negativo", int((stock["Stock disponible (uds)"].astype(float) < 0).sum())),
        ("PRODUCTO", "coste >= PVP", int((producto["Coste unitario (€)"].astype(float) >= producto["PVP (€)"].astype(float)).sum())),
        ("PRODUCTO", "coste <= 0", int((producto["Coste unitario (€)"].astype(float) <= 0).sum())),
    ]
    return pd.DataFrame(comprobaciones, columns=["tabla", "comprobacion", "n_filas"])


def perfilar_categoricas(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
    """Frecuencia de los valores de las columnas categóricas clave.

    Es donde aparecen las variantes de escritura (`ES` / `Spain` / `ESP` / `es`)
    y las etiquetas no documentadas en el enunciado.
    """
    ventas = tablas["VENTAS"]
    producto = tablas["PRODUCTO"]
    return {
        "VENTAS.Mercado": ventas["Mercado"].value_counts(dropna=False),
        "VENTAS.Etiquetas": ventas["Etiquetas"].value_counts(dropna=False),
        "PRODUCTO.Sección": producto["Sección"].value_counts(),
        "PRODUCTO.Categoría": producto["Categoría"].value_counts(),
        "PRODUCTO.Drop": producto["Drop"].value_counts(),
    }


def comparar_precios_venta_catalogo(tablas: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compara el PVP de la línea de venta con el PVP del catálogo.

    Si no hay discrepancias, se puede usar indistintamente uno u otro y se elimina
    un supuesto del análisis.
    """
    ventas = tablas["VENTAS"].copy()
    ventas["sku_norm"] = ventas[COLUMNA_SKU].str.upper().str.strip()
    cruce = ventas.merge(
        tablas["PRODUCTO"][[COLUMNA_SKU, "PVP (€)"]],
        left_on="sku_norm",
        right_on=COLUMNA_SKU,
        how="left",
        suffixes=("", "_cat"),
    )
    distintos = cruce["PVP unitario (€)"].astype(float) != cruce["PVP (€)"].astype(float)
    return pd.DataFrame(
        [
            {
                "lineas_comparadas": int(cruce["PVP (€)"].notna().sum()),
                "lineas_con_pvp_distinto": int(distintos.sum()),
                "pct": round(100 * distintos.mean(), 2),
            }
        ]
    )


def perfilar_descuento_por_etiqueta(tablas: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Descuento medio por etiqueta, para entender qué significa cada una.

    Permite comprobar si `influencers` descuenta el 100 % (regalo) y cuánto
    descuenta realmente cada variante de `special`.
    """
    ventas = tablas["VENTAS"].copy()
    ventas["etiqueta"] = ventas["Etiquetas"].fillna("(sin etiqueta)")
    ventas["bruto"] = ventas["Unidades"].astype(float) * ventas["PVP unitario (€)"].astype(float)
    ventas["desc"] = ventas["Descuento (€)"].astype(float)
    agregado = ventas.groupby("etiqueta").agg(
        lineas=("etiqueta", "size"),
        bruto=("bruto", "sum"),
        descuento=("desc", "sum"),
    )
    agregado["pct_descuento"] = (100 * agregado["descuento"] / agregado["bruto"]).round(1)
    return agregado.reset_index()


def generar_informe_perfilado(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Ejecuta todos los perfilados y devuelve las tablas de hallazgos."""
    resumen = pd.concat(
        [perfilar_tabla(df, nombre) for nombre, df in tablas.items()],
        ignore_index=True,
    )
    return {
        "resumen_columnas": resumen,
        "duplicados_ventas": detectar_duplicados(tablas["VENTAS"], ["Pedido", "SKU"]),
        "claves_huerfanas": detectar_claves_huerfanas(tablas),
        "valores_imposibles": detectar_valores_imposibles(tablas),
        "precios_venta_vs_catalogo": comparar_precios_venta_catalogo(tablas),
        "descuento_por_etiqueta": perfilar_descuento_por_etiqueta(tablas),
    }
