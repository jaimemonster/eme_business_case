"""Limpieza de datos y aplicación de las reglas de negocio.

Responsabilidad: convertir las tablas crudas en tablas limpias y tipadas listas
para analizar, y ser el ÚNICO lugar donde se aplican las reglas de negocio del
caso:

1. Los pedidos con etiqueta `influencers` son regalos y se excluyen de toda venta.
2. Los pedidos con etiqueta `special` se marcan con el flag `is_special`.
3. La llegada de compras usa la fecha real si existe y, si no, la estimada
   (`fecha_llegada_efectiva`).
4. Modelo = producto + color; cada talla es un SKU distinto (`modelo_id`).

Además aplica las decisiones de calidad de datos acordadas tras el perfilado
(ver docs/decisiones.md). Cada una deja traza en el resumen que devuelve
`ejecutar_limpieza`, que es lo que alimenta la página de decisiones del informe.

Toda corrección aplicada aquí debe quedar reflejada en docs/notas_calidad_datos.md.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List

import pandas as pd

from . import config, storage

# Variantes de escritura del mercado detectadas en el perfilado (decisión 7).
MERCADOS_NORMALIZADOS: Dict[str, str] = {
    "SPAIN": "ES",
    "ESP": "ES",
    "ESPANA": "ES",
}
MERCADO_DESCONOCIDO = "DESCONOCIDO"

# Etiquetas. El perfilado confirmó que cada línea lleva como mucho una, pero se
# parsea como lista por si aparecieran combinadas.
ETIQUETA_REGALO = "INFLUENCERS"
PREFIJO_PRECIO_ESPECIAL = "SPECIAL"
ETIQUETA_PROMOCION = "WELCOME10"


def _sin_acentos(texto: str) -> str:
    """Quita los acentos de una cadena manteniendo el resto de caracteres."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Pasa los nombres de columna a snake_case y sin acentos.

    Elimina además el contenido entre paréntesis, que en este Excel son unidades
    de medida: "PVP unitario (€)" -> "pvp_unitario", "Stock disponible (uds)" ->
    "stock_disponible".
    """
    def limpiar(nombre: str) -> str:
        nombre = re.sub(r"\(.*?\)", "", str(nombre))
        nombre = _sin_acentos(nombre).lower().strip()
        nombre = re.sub(r"[^a-z0-9]+", "_", nombre)
        return nombre.strip("_")

    return df.rename(columns={c: limpiar(c) for c in df.columns})


def _normalizar_sku(serie: pd.Series) -> pd.Series:
    """Normaliza el SKU a mayúsculas sin espacios (decisión 5).

    15 líneas de venta traen el SKU en minúsculas. Sin esto, se perderían al
    cruzar con el catálogo y desaparecerían 15 ventas en silencio.
    """
    return serie.astype(str).str.strip().str.upper()


def _parsear_etiquetas(serie: pd.Series) -> pd.Series:
    """Convierte la columna de etiquetas en una lista de etiquetas normalizadas."""
    def parsear(valor) -> List[str]:
        if pd.isna(valor):
            return []
        return [t.strip().upper() for t in re.split(r"[,;|]", str(valor)) if t.strip()]

    return serie.apply(parsear)


def limpiar_producto(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia el catálogo y crea la clave `modelo_id` (regla 4).

    Un modelo es producto + color; cada talla es un SKU distinto. `modelo_id` es
    la clave con la que se agrupa en todo el análisis.
    """
    p = normalizar_columnas(df).copy()
    p["sku"] = _normalizar_sku(p["sku"])
    for col in ("producto", "color", "talla", "seccion", "categoria", "subcategoria", "drop"):
        p[col] = p[col].astype(str).str.strip().str.upper()
    p["coste_unitario"] = p["coste_unitario"].astype(float)
    p["pvp"] = p["pvp"].astype(float)

    # Regla 4: modelo = producto + color.
    #
    # El identificador se construye con la REFERENCIA del SKU (EME045), no con el
    # nombre comercial. Motivo: hay 3 casos de productos distintos que comparten
    # nombre y color, lanzados en drops diferentes y con PVP distinto. "ECHO
    # BOMBER OLIVE" es a la vez una chaqueta de HOMBRE a 100 € (EME045, drop
    # 2024-05) y una de MUJER a 140 € (EME076, drop 2024-03). Agruparlos por
    # nombre los fusionaría en un modelo inexistente, con dos secciones y dos
    # precios. Ver docs/decisiones.md.
    partes = p["sku"].str.split("-", expand=True)
    p["referencia"] = partes[0]
    p["color_cod"] = partes[1]
    p["modelo_id"] = p["referencia"] + "-" + p["color_cod"]

    # Nombre para mostrar. Si dos modelos comparten nombre, se desambigua con el
    # drop para que nadie los confunda al leer el informe.
    p["modelo_nombre"] = p["producto"] + " " + p["color"]
    ambiguos = p.groupby("modelo_nombre")["modelo_id"].transform("nunique") > 1
    p.loc[ambiguos, "modelo_nombre"] = (
        p.loc[ambiguos, "modelo_nombre"] + " (" + p.loc[ambiguos, "drop"] + ")"
    )
    return p


def limpiar_ventas(df: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Limpia las líneas de pedido, parsea etiquetas y aplica las reglas 1 y 2.

    Devuelve solo las ventas reales (sin regalos), con el flag `is_special` y las
    métricas de línea calculadas (facturación neta y margen).
    """
    v = _preparar_ventas(df)

    # Regla 1: los regalos de influencers no son ventas.
    v = v[~v["es_regalo"]].copy()

    return _enriquecer_ventas(v, producto)


def extraer_regalos(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve las líneas etiquetadas como `influencers`, excluidas de la venta
    pero necesarias para entender el consumo de stock."""
    v = _preparar_ventas(df)
    return v[v["es_regalo"]].copy()


def _preparar_ventas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza tipos, mercados y etiquetas de VENTAS, y aplica las decisiones
    de calidad que no dependen del catálogo.

    Es el tronco común de `limpiar_ventas` y `extraer_regalos`: ambas necesitan
    exactamente el mismo tratamiento y solo se diferencian en qué mitad se quedan.
    """
    v = normalizar_columnas(df).copy()

    # Decisión 4: 25 pares de filas idénticas. Se elimina una de cada par.
    v = v.drop_duplicates().copy()

    v["sku"] = _normalizar_sku(v["sku"])  # decisión 5
    v["fecha"] = pd.to_datetime(v["fecha"])
    v["unidades"] = v["unidades"].astype(float).astype(int)
    v["pvp_unitario"] = v["pvp_unitario"].astype(float)
    v["descuento"] = v["descuento"].astype(float)

    # Decisión 7: variantes de escritura del mercado y nulos.
    mercado = v["mercado"].astype(str).str.strip().str.upper()
    mercado = mercado.replace(MERCADOS_NORMALIZADOS)
    v["mercado"] = mercado.where(v["mercado"].notna(), MERCADO_DESCONOCIDO)

    # Reglas 1 y 2 + decisión 1 (WELCOME10) y decisión 2 (variantes SPECIAL XX).
    etiquetas = _parsear_etiquetas(v["etiquetas"])
    v["etiquetas_norm"] = etiquetas.apply(lambda ts: ",".join(ts))
    v["es_regalo"] = etiquetas.apply(lambda ts: ETIQUETA_REGALO in ts)
    v["is_special"] = etiquetas.apply(
        lambda ts: any(t.startswith(PREFIJO_PRECIO_ESPECIAL) for t in ts)
    )
    v["es_promocion"] = etiquetas.apply(lambda ts: ETIQUETA_PROMOCION in ts)
    # El sufijo de "SPECIAL ES" es un mercado: se guarda para poder contrastarlo
    # con el mercado de la línea, no para analizar con él.
    v["mercado_etiqueta"] = etiquetas.apply(
        lambda ts: next(
            (t.split()[1] for t in ts if t.startswith(PREFIJO_PRECIO_ESPECIAL) and " " in t),
            None,
        )
    )

    # Decisión 3: las unidades negativas son devoluciones y se mantienen.
    v["es_devolucion"] = v["unidades"] < 0
    # Consecuencia de la decisión 3: en una devolución el descuento también se
    # revierte, así que debe llevar el mismo signo que las unidades. Sin esto,
    # una devolución con descuento restaría de más (ver docs/decisiones.md).
    v.loc[v["es_devolucion"] & (v["descuento"] > 0), "descuento"] *= -1

    return v


def _enriquecer_ventas(v: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Cruza las ventas con el catálogo y calcula las métricas de línea."""
    atributos = [
        "sku", "modelo_id", "modelo_nombre", "producto", "color", "talla",
        "seccion", "categoria", "subcategoria", "drop", "coste_unitario",
    ]
    v = v.merge(producto[atributos], on="sku", how="inner")

    v["importe_bruto"] = v["unidades"] * v["pvp_unitario"]
    v["facturacion_neta"] = v["importe_bruto"] - v["descuento"]
    v["coste_total"] = v["unidades"] * v["coste_unitario"]
    v["margen"] = v["facturacion_neta"] - v["coste_total"]

    # Semana ISO (lunes a domingo), base de todas las comparativas.
    iso = v["fecha"].dt.isocalendar()
    v["anio_iso"] = iso["year"].astype(int)
    v["semana_iso"] = iso["week"].astype(int)
    v["inicio_semana"] = v["fecha"] - pd.to_timedelta(iso["day"].astype(int) - 1, unit="D")
    return v


def limpiar_stock(df: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Limpia el stock a fecha de cierre y lo enriquece con `modelo_id`.

    Decisión 6: el SKU EME999-BLA-M tiene stock pero no existe en el catálogo.
    Se excluye (el `inner` del cruce) y se reporta en las notas de calidad.
    """
    s = normalizar_columnas(df).copy()
    s["sku"] = _normalizar_sku(s["sku"])
    s["stock_disponible"] = s["stock_disponible"].astype(float).astype(int)
    s["fecha_stock"] = pd.to_datetime(s["fecha_stock"])

    atributos = ["sku", "modelo_id", "modelo_nombre", "seccion", "categoria", "subcategoria", "talla", "drop"]
    return s.merge(producto[atributos], on="sku", how="inner")


def limpiar_compras(df: pd.DataFrame, producto: pd.DataFrame) -> pd.DataFrame:
    """Limpia las compras y calcula `fecha_llegada_efectiva` (regla 3).

    Marca además las compras vencidas: sin fecha real y con la estimada ya
    pasada a la fecha de corte de los datos. El perfilado encontró 37, y son
    determinantes para el Reto 2: contarlas como stock en camino llevaría a
    reponer de menos.
    """
    c = normalizar_columnas(df).copy()
    c["sku"] = _normalizar_sku(c["sku"])
    c["unidades"] = c["unidades"].astype(float).astype(int)
    c["proveedor"] = c["proveedor"].astype(str).str.strip().str.upper()
    c["fecha_llegada_estimada"] = pd.to_datetime(c["fecha_llegada_estimada"])
    c["fecha_llegada_real"] = pd.to_datetime(c["fecha_llegada_real"])

    # Regla 3: fecha real si existe; si no, la estimada.
    c["fecha_llegada_efectiva"] = c["fecha_llegada_real"].fillna(c["fecha_llegada_estimada"])
    c["origen_fecha_llegada"] = c["fecha_llegada_real"].notna().map({True: "real", False: "estimada"})

    corte = pd.Timestamp(config.FECHA_CORTE_DATOS)
    c["esta_vencida"] = c["fecha_llegada_real"].isna() & (c["fecha_llegada_estimada"] <= corte)
    c["ha_llegado"] = c["fecha_llegada_efectiva"] <= corte
    c["dias_retraso"] = (c["fecha_llegada_real"] - c["fecha_llegada_estimada"]).dt.days

    atributos = ["sku", "modelo_id", "modelo_nombre", "seccion", "categoria", "talla"]
    return c.merge(producto[atributos], on="sku", how="inner")


def ejecutar_limpieza(persistir: bool = True) -> Dict[str, pd.DataFrame]:
    """Orquesta la limpieza completa y persiste las tablas en data/interim.

    Devuelve las cuatro tablas limpias más `regalos` (las líneas de influencers,
    fuera de la venta pero útiles para el consumo de stock) y `resumen_limpieza`,
    la traza de cuántas filas ha tocado cada decisión.
    """
    crudas = storage.cargar_excel_crudo()

    producto = limpiar_producto(crudas["PRODUCTO"])
    ventas = limpiar_ventas(crudas["VENTAS"], producto)
    regalos = extraer_regalos(crudas["VENTAS"])
    stock = limpiar_stock(crudas["STOCK"], producto)
    compras = limpiar_compras(crudas["COMPRAS"], producto)

    tablas = {
        "producto": producto,
        "ventas": ventas,
        "regalos": regalos,
        "stock": stock,
        "compras": compras,
    }
    resumen = resumir_limpieza(crudas, tablas)

    if persistir:
        for nombre, df in tablas.items():
            storage.guardar_tabla(df, nombre, config.DIR_INTERIM)
        storage.guardar_tabla(resumen, "resumen_limpieza", config.DIR_INTERIM)

    tablas["resumen_limpieza"] = resumen
    return tablas


def resumir_limpieza(
    crudas: Dict[str, pd.DataFrame],
    limpias: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Cuenta cuántas filas ha afectado cada decisión, para poder auditarlas.

    Es la traza que alimenta la página de decisiones del informe: ninguna
    decisión debería aparecer ahí sin un número al lado.
    """
    ventas_crudas = normalizar_columnas(crudas["VENTAS"])
    duplicadas = int(ventas_crudas.duplicated().sum())
    minusculas = int((ventas_crudas["sku"].astype(str) != ventas_crudas["sku"].astype(str).str.upper()).sum())

    ventas, regalos, compras = limpias["ventas"], limpias["regalos"], limpias["compras"]
    stock_crudo = normalizar_columnas(crudas["STOCK"])

    filas = [
        ("4", "Líneas de venta duplicadas eliminadas", duplicadas),
        ("5", "SKUs de venta normalizados a mayúsculas", minusculas),
        ("1", "Líneas de regalo (influencers) excluidas de la venta", len(regalos)),
        ("2", "Líneas marcadas como precio especial", int(ventas["is_special"].sum())),
        ("1", "Líneas con promoción WELCOME10 (venta a precio completo)", int(ventas["es_promocion"].sum())),
        ("3", "Devoluciones conservadas (unidades negativas)", int(ventas["es_devolucion"].sum())),
        ("3", "Devoluciones a las que se revirtió el descuento", int((ventas["es_devolucion"] & (ventas["descuento"] < 0)).sum())),
        ("6", "SKUs de stock sin catálogo, excluidos", len(stock_crudo) - len(limpias["stock"])),
        ("7", "Líneas con mercado sin informar", int((ventas["mercado"] == MERCADO_DESCONOCIDO).sum())),
        ("8", "Compras vencidas sin confirmar", int(compras["esta_vencida"].sum())),
        ("8", "Compras que llegaron tarde", int((compras["dias_retraso"] > 0).sum())),
    ]
    return pd.DataFrame(filas, columns=["decision", "concepto", "n_filas"])
