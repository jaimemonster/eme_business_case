"""Propuesta de reposición por SKU (Reto 2).

Responsabilidad: a partir de la demanda prevista, el stock disponible y las
compras pendientes de llegar, calcular qué reponer y cuántas unidades, con un
lead time de proveedor de 6 semanas y una cobertura objetivo de 8 semanas.

La fórmula es la de "nivel objetivo" clásico. El razonamiento importa más que la
expresión: si hoy se lanza un pedido, llega dentro de `lead_time` semanas, y a
partir de ese momento tiene que cubrir `cobertura_objetivo` semanas más. Es
decir, el pedido de hoy responde de la demanda de las próximas
`lead_time + cobertura_objetivo` semanas. De ahí se descuenta lo que ya se tiene
y lo que ya se ha pedido y va a llegar dentro de esa misma ventana:

    horizonte  = lead_time + cobertura_objetivo            (6 + 8 = 14 semanas)
    necesidad  = demanda(horizonte)
                 - stock_disponible
                 - en_transito(llegada <= horizonte)

Las compras **vencidas sin confirmar** no cuentan como stock en camino: su fecha
estimada ya pasó y no hay constancia de que hayan llegado. Contarlas llevaría a
reponer de menos para unidades que probablemente no estén. Se sacan en una tabla
aparte para que Compras las reclame al proveedor, que es una acción humana y no
un cálculo. Es el mismo criterio que usa `metrics.alertas_stock` en el Reto 1:
las dos cifras tienen que poder mirarse juntas sin contradecirse.

No se inventa lote mínimo de proveedor: no está en los datos. `UNIDADES_MINIMAS`
queda como parámetro configurable en 1 para que el día que exista se cambie aquí.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from . import config, demand, forecast

# Por debajo de estas unidades no se propone pedido. En 1 no filtra nada; existe
# para el día que el proveedor imponga un mínimo por referencia.
UNIDADES_MINIMAS: int = 1

# Etiquetas de prioridad, de más a menos urgente.
PRIORIDADES = ("critica", "alta", "normal")


def horizonte_semanas(
    lead_time_semanas: int = config.LEAD_TIME_SEMANAS,
    cobertura_objetivo_semanas: int = config.COBERTURA_OBJETIVO_SEMANAS,
) -> int:
    """Semanas de las que responde el pedido que se lance hoy."""
    return lead_time_semanas + cobertura_objetivo_semanas


def stock_en_transito(compras: pd.DataFrame, semanas: int) -> pd.DataFrame:
    """Unidades por SKU que van a llegar al almacén dentro de `semanas`.

    Solo cuentan las compras que (a) no han llegado todavía, (b) no están
    vencidas sin confirmar y (c) tienen fecha de llegada efectiva dentro de la
    ventana. Devuelve una fila por SKU con `en_transito`.
    """
    limite = pd.Timestamp(config.FECHA_CORTE_DATOS) + pd.Timedelta(weeks=semanas)
    en_camino = compras[
        (~compras["ha_llegado"])
        & (~compras["esta_vencida"])
        & (compras["fecha_llegada_efectiva"] <= limite)
    ]
    return (
        en_camino.groupby("sku", as_index=False)["unidades"]
        .sum()
        .rename(columns={"unidades": "en_transito"})
    )


def compras_a_confirmar(compras: pd.DataFrame) -> pd.DataFrame:
    """Compras vencidas sin fecha real de llegada: ni han llegado ni cuentan.

    No es un residuo del cálculo, es trabajo para Compras: hay que llamar al
    proveedor y confirmar si esas unidades están en camino o se han perdido.
    """
    vencidas = compras[compras["esta_vencida"]].copy()
    vencidas["dias_vencida"] = (
        pd.Timestamp(config.FECHA_CORTE_DATOS) - vencidas["fecha_llegada_efectiva"]
    ).dt.days
    columnas = [
        "pedido_proveedor", "sku", "modelo_nombre", "talla", "proveedor",
        "unidades", "fecha_llegada_estimada", "dias_vencida",
    ]
    return (
        vencidas[columnas]
        .sort_values("dias_vencida", ascending=False)
        .reset_index(drop=True)
    )


def proveedor_habitual(compras: pd.DataFrame) -> pd.DataFrame:
    """Proveedor al que se le compró cada SKU la última vez.

    Se usa el último, no el más frecuente: si se cambió de proveedor, el pedido
    nuevo va al actual. Los SKUs sin histórico de compra quedan sin proveedor y
    se marcan como tales en la propuesta.
    """
    con_fecha = compras.sort_values("fecha_llegada_efectiva")
    ultimo = con_fecha.groupby("sku", as_index=False).last()[["sku", "proveedor"]]
    return ultimo.rename(columns={"proveedor": "proveedor_habitual"})


def calcular_necesidad(
    prevision: pd.DataFrame,
    stock: pd.DataFrame,
    compras: pd.DataFrame,
    producto: pd.DataFrame,
    lead_time_semanas: int = config.LEAD_TIME_SEMANAS,
    cobertura_objetivo_semanas: int = config.COBERTURA_OBJETIVO_SEMANAS,
) -> pd.DataFrame:
    """Necesidad neta de reposición por SKU, con el porqué de cada cifra.

    El universo es el catálogo completo: un SKU con cero stock y demanda viva
    tiene que aparecer, y si se partiese de la tabla de stock se colaría solo por
    casualidad. Los SKUs sin histórico de ventas salen con demanda cero, que es
    la lectura correcta: no hay nada en qué basarse para pedir.
    """
    semanas = lead_time_semanas + cobertura_objetivo_semanas

    base = (
        producto[[
            "sku", "modelo_id", "modelo_nombre", "producto", "color", "talla",
            "seccion", "categoria", "subcategoria", "drop", "coste_unitario", "pvp",
        ]]
        .merge(stock[["sku", "stock_disponible"]], on="sku", how="left")
        .merge(
            prevision[["sku", "demanda_semanal", "historico_corto", "u"]]
            .rename(columns={"u": "uds_recientes"}),
            on="sku", how="left",
        )
        .merge(stock_en_transito(compras, semanas), on="sku", how="left")
        .merge(proveedor_habitual(compras), on="sku", how="left")
    )

    base["stock_disponible"] = base["stock_disponible"].fillna(0)
    base["demanda_semanal"] = base["demanda_semanal"].fillna(0)
    base["en_transito"] = base["en_transito"].fillna(0)
    base["historico_corto"] = base["historico_corto"].fillna(False).astype(bool)
    # Unidades realmente vendidas en la ventana reciente. No es lo mismo que la
    # demanda prevista: al repartir el total de categoría, hasta un producto
    # parado recibe una brizna de previsión. Para decidir qué está muerto hay que
    # mirar lo que se vendió, no lo que se predijo.
    base["uds_recientes"] = base["uds_recientes"].fillna(0)
    base["proveedor_habitual"] = base["proveedor_habitual"].fillna("sin histórico de compra")

    base["horizonte_semanas"] = semanas
    base["demanda_horizonte"] = (base["demanda_semanal"] * semanas).round(1)
    base["disponible_total"] = base["stock_disponible"] + base["en_transito"]

    # La necesidad en crudo puede ser negativa (sobra stock); se conserva sin
    # truncar porque mide el exceso, y el exceso también es información.
    base["necesidad_bruta"] = (base["demanda_horizonte"] - base["disponible_total"]).round(1)
    base["unidades_propuestas"] = (
        np.ceil(base["necesidad_bruta"].clip(lower=0)).astype(int)
    )
    base.loc[base["unidades_propuestas"] < UNIDADES_MINIMAS, "unidades_propuestas"] = 0

    # Semanas que aguanta el stock que hay hoy en el almacén, sin contar lo que
    # viene de camino: es lo que decide si da tiempo a que llegue el pedido.
    base["cobertura_semanas"] = (
        (base["stock_disponible"] / base["demanda_semanal"])
        .replace([np.inf, -np.inf], np.nan)
        .round(1)
    )

    base["prioridad"] = _clasificar_prioridad(base, lead_time_semanas, semanas)
    base["motivo"] = _explicar(base, lead_time_semanas, semanas)
    base["coste_pedido"] = (base["unidades_propuestas"] * base["coste_unitario"]).round(2)
    base["venta_en_riesgo"] = (
        base["necesidad_bruta"].clip(lower=0) * base["pvp"]
    ).round(2)

    return base


def _clasificar_prioridad(
    base: pd.DataFrame, lead_time_semanas: int, semanas: int
) -> pd.Series:
    """Prioridad por cuándo se rompe, no por cuánto se pide.

    `critica`: el stock se acaba antes de que pueda llegar un pedido lanzado hoy.
    Da igual lo que se pida: la rotura ya está comprada y lo único que se decide
    es cuánto dura.
    `alta`: aguanta hasta que llegue el pedido, pero se queda corto dentro del
    horizonte de cobertura.
    `normal`: el resto de lo que hay que reponer.
    """
    sin_demanda = base["demanda_semanal"] <= 0
    cobertura = base["cobertura_semanas"]

    prioridad = pd.Series("normal", index=base.index, dtype=object)
    prioridad[cobertura < semanas] = "alta"
    prioridad[cobertura < lead_time_semanas] = "critica"
    prioridad[base["unidades_propuestas"] <= 0] = ""
    prioridad[sin_demanda] = ""
    return prioridad


def _explicar(base: pd.DataFrame, lead_time_semanas: int, semanas: int) -> pd.Series:
    """Una frase por línea con el porqué de la cifra.

    Compras no tiene que fiarse del número: tiene que poder leer de dónde sale y
    discrepar con criterio. Sin esta columna la propuesta es una caja negra y
    acaba revisándose a ojo o ignorándose.
    """
    def frase(fila) -> str:
        if fila["demanda_semanal"] <= 0:
            return "Sin ventas en las últimas semanas: no se propone pedido."
        if fila["unidades_propuestas"] <= 0:
            sobra = -fila["necesidad_bruta"]
            return (
                f"Cubierto: {fila['disponible_total']:.0f} uds disponibles para una "
                f"demanda de {fila['demanda_horizonte']:.0f}. Sobran {sobra:.0f}."
            )
        partes = [
            f"{fila['demanda_semanal']:.1f} uds/semana × {semanas} semanas "
            f"= {fila['demanda_horizonte']:.0f}",
            f"− {fila['stock_disponible']:.0f} en almacén",
        ]
        if fila["en_transito"] > 0:
            partes.append(f"− {fila['en_transito']:.0f} que ya llegan")
        texto = " ".join(partes) + f" → pedir {fila['unidades_propuestas']}."
        if pd.notna(fila["cobertura_semanas"]) and fila["cobertura_semanas"] < lead_time_semanas:
            texto += (
                f" Aguanta {fila['cobertura_semanas']:.1f} semanas y el proveedor "
                f"tarda {lead_time_semanas}: va a romper igualmente."
            )
        if fila["historico_corto"]:
            texto += " Ojo: histórico corto, la previsión es menos fiable."
        return texto

    return base.apply(frase, axis=1)


def construir_propuesta(necesidad: pd.DataFrame) -> pd.DataFrame:
    """Las líneas que Compras tiene que revisar, ordenadas por urgencia.

    Se incluyen dos columnas vacías —`estado` y `unidades_aprobadas`— porque el
    entregable no es un informe: es un documento de trabajo donde se aprueba. Sin
    un sitio donde decir que sí, la propuesta no cierra el ciclo.
    """
    orden = {p: i for i, p in enumerate(PRIORIDADES)}
    prop = necesidad[necesidad["unidades_propuestas"] > 0].copy()
    prop["_orden"] = prop["prioridad"].map(orden).fillna(len(PRIORIDADES))

    prop = prop.sort_values(
        ["_orden", "venta_en_riesgo"], ascending=[True, False]
    ).drop(columns="_orden")

    prop["estado"] = ""
    prop["unidades_aprobadas"] = ""

    columnas = [
        "prioridad", "sku", "modelo_id", "modelo_nombre", "color", "talla", "seccion", "categoria",
        "proveedor_habitual", "demanda_semanal", "cobertura_semanas",
        "stock_disponible", "en_transito", "demanda_horizonte",
        "unidades_propuestas", "coste_pedido", "venta_en_riesgo",
        "estado", "unidades_aprobadas", "motivo",
    ]
    return prop[columnas].reset_index(drop=True)


def sin_rotacion(necesidad: pd.DataFrame) -> pd.DataFrame:
    """SKUs con stock parado: ninguna venta reciente y unidades en el almacén.

    Se mide sobre **ventas observadas**, no sobre demanda prevista. Al repartir el
    total de una categoría entre sus SKUs, hasta un producto que lleva meses sin
    venderse recibe una fracción de previsión, así que "demanda prevista cero"
    dejó de distinguir a los parados en cuanto la previsión pasó a ser jerárquica.

    No se reponen, pero no desaparecen: son candidatos a rebaja o fin de vida, y
    esa decisión también es de Compras.
    """
    sin_venta = necesidad[
        (necesidad["uds_recientes"] <= 0) & (necesidad["stock_disponible"] > 0)
    ].copy()
    sin_venta["capital_inmovilizado"] = (
        sin_venta["stock_disponible"] * sin_venta["coste_unitario"]
    ).round(2)
    columnas = [
        "sku", "modelo_nombre", "color", "talla", "seccion", "categoria", "drop",
        "stock_disponible", "capital_inmovilizado",
    ]
    return (
        sin_venta[columnas]
        .sort_values("capital_inmovilizado", ascending=False)
        .reset_index(drop=True)
    )


def resumen_propuesta(
    propuesta: pd.DataFrame,
    necesidad: pd.DataFrame,
    n_lineas_venta: int = 0,
) -> pd.DataFrame:
    """Las cifras de cabecera, para no tener que sumar columnas a mano."""
    filas = [
        ("Líneas de venta", n_lineas_venta),
        ("SKUs a reponer", len(propuesta)),
        ("SKUs en catálogo", len(necesidad)),
        ("Unidades propuestas", int(propuesta["unidades_propuestas"].sum())),
        ("Coste del pedido (€)", round(float(propuesta["coste_pedido"].sum()), 2)),
        ("Venta en riesgo (€)", round(float(propuesta["venta_en_riesgo"].sum()), 2)),
        ("Proveedores implicados", propuesta["proveedor_habitual"].nunique()),
        ("SKUs en prioridad crítica", int((propuesta["prioridad"] == "critica").sum())),
        # El recuento va en SKUs (modelo × talla), que es la unidad que se pide.
        # Se publica también en modelos porque «48 roturas» se lee como 48
        # modelos y son 45: la talla es lo que rompe, no el modelo entero.
        ("Modelos en prioridad crítica",
         int(propuesta.loc[propuesta["prioridad"] == "critica", "modelo_id"].nunique())),
        ("Modelos a reponer", int(propuesta["modelo_id"].nunique())),
        ("SKUs en prioridad alta", int((propuesta["prioridad"] == "alta").sum())),
    ]
    return pd.DataFrame(filas, columns=["concepto", "valor"])


def parametros_usados(
    lead_time_semanas: int = config.LEAD_TIME_SEMANAS,
    cobertura_objetivo_semanas: int = config.COBERTURA_OBJETIVO_SEMANAS,
    prevision: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Los parámetros del cálculo, para la pestaña de decisiones del Excel.

    Van en el propio entregable, no solo en la documentación: quien revise la
    propuesta tiene que poder ver con qué supuestos se construyó sin salir del
    fichero.
    """
    semanas = lead_time_semanas + cobertura_objetivo_semanas
    metodo = (
        prevision["metodo"].iloc[0]
        if prevision is not None and "metodo" in prevision and len(prevision)
        else "no registrado"
    )
    filas = [
        ("Fecha de corte de los datos", str(config.FECHA_CORTE_DATOS),
         "El 'hoy' del caso: el último día con datos."),
        ("Lead time de proveedor", f"{lead_time_semanas} semanas",
         "Lo que tarda en llegar un pedido lanzado hoy."),
        ("Cobertura objetivo", f"{cobertura_objetivo_semanas} semanas",
         "Lo que debe durar el stock una vez que el pedido llega."),
        ("Horizonte del cálculo", f"{semanas} semanas",
         "Suma de los dos anteriores: de lo que responde el pedido de hoy."),
        ("Método de previsión", metodo,
         "Elegido por backtesting entre cuatro candidatos; la comparativa está en el servicio."),
        ("Nivel de previsión", "sección × categoría, repartido a SKU",
         "A nivel de SKU la demanda semanal es ruido: 62 % de semanas a cero."),
        ("Semanas agotadas", "excluidas del cálculo de demanda",
         "Una semana sin stock no es falta de demanda. Afecta a 45 SKUs."),
        ("Ventas a precio especial", "excluidas",
         "Son liquidación, no demanda recurrente: inflarían la previsión."),
        ("Regalos a influencers", "excluidos",
         "No son venta. Regla de negocio del enunciado."),
        ("Compras vencidas sin confirmar", "no cuentan como stock en camino",
         "Su fecha estimada ya pasó y no hay constancia de que lleguen."),
        ("Lote mínimo de proveedor", f"{UNIDADES_MINIMAS} ud",
         "No está en los datos. Parámetro listo para el día que exista."),
    ]
    return pd.DataFrame(filas, columns=["parámetro", "valor", "por qué"])


def _serie_una(
    ventas: pd.DataFrame,
    stock_semanal: pd.DataFrame,
    compras: pd.DataFrame,
    futuro: pd.DataFrame,
    desde: pd.Timestamp,
    skus: set | None = None,
    pedido: float = 0.0,
) -> pd.DataFrame:
    """Venta y stock semanales observados, con la previsión pegada al final.

    `skus` acota a un modelo; sin él, todo el catálogo.

    La proyección de stock **suma lo que ya viene de camino**: hay 9.427 unidades
    pedidas que llegan en las próximas siete semanas, y una línea que las ignorase
    enseñaría el almacén vaciándose cuando en realidad va a crecer.

    Se devuelven dos proyecciones y la gracia es compararlas: `stock` es lo que
    quedaría **sin pedir nada más**, y `stock_con_pedido` añade las unidades
    propuestas el día que llegarían, seis semanas después de firmar.

    La venta se parte en dos: `demanda` es la venta a precio completo, que es la
    que alimenta la previsión, y `demanda_especial` es la liquidación. Sin esa
    separación la semana de Black Friday parece una caída de ventas cuando lo que
    cambia es el precio, no el volumen.
    """
    v = ventas[ventas["inicio_semana"] >= desde]
    s = stock_semanal
    c = compras[(~compras["ha_llegado"]) & (~compras["esta_vencida"])]
    if skus is not None:
        v, s, c = v[v["sku"].isin(skus)], s[s["sku"].isin(skus)], c[c["sku"].isin(skus)]

    venta = v[~v["is_special"]].groupby("inicio_semana")["unidades"].sum().rename("demanda")
    especial = v[v["is_special"]].groupby("inicio_semana")["unidades"].sum().rename("demanda_especial")
    stock = (
        s[s["inicio_semana"] >= desde]
        .groupby("inicio_semana")["stock_fin"].sum().rename("stock")
    )
    historico = pd.concat([venta, especial, stock], axis=1).reset_index()
    cols = ["demanda", "demanda_especial", "stock"]
    historico[cols] = historico[cols].fillna(0)
    historico["tipo"] = "observado"

    inicial = float(historico["stock"].iloc[-1]) if len(historico) else 0.0
    historico["stock_con_pedido"] = historico["stock"]

    # Lo que ya está pedido y llega dentro del horizonte, semana a semana.
    llegadas = (
        c.assign(sem=c["fecha_llegada_efectiva"].dt.to_period("W").dt.start_time)
        .groupby("sem")["unidades"].sum()
    )

    fut = futuro.copy()
    fut["llega"] = [float(llegadas.get(pd.Timestamp(w), 0.0)) for w in fut["inicio_semana"]]

    nivel, con = inicial, inicial
    sin_pedido, con_pedido = [], []
    for k, (demanda, llega) in enumerate(zip(fut["demanda"], fut["llega"]), start=1):
        nivel = max(nivel + float(llega) - float(demanda), 0.0)
        # El pedido que se firma hoy entra en el almacén cuando pasa el plazo del
        # proveedor, no antes. Por eso el escalón cae en la semana 6.
        con += float(llega) + (pedido if k == config.LEAD_TIME_SEMANAS else 0.0)
        con = max(con - float(demanda), 0.0)
        sin_pedido.append(nivel)
        con_pedido.append(con)
    fut["stock"] = sin_pedido
    fut["stock_con_pedido"] = con_pedido
    fut["demanda_especial"] = 0.0
    fut["tipo"] = "previsto"
    return pd.concat([historico, fut], ignore_index=True)


def historico_y_prevision(
    tablas: Dict[str, pd.DataFrame],
    curva: pd.DataFrame,
    curva_grupo: pd.DataFrame,
    prevision: pd.DataFrame,
    propuesta: pd.DataFrame,
    semanas_atras: int = 52,
) -> pd.DataFrame:
    """Las series del gráfico: el catálogo entero y cada modelo de la propuesta.

    Se calculan todas de una vez y viajan en una sola tabla con `modelo_id`
    (vacío para el total). Así el selector de la web solo filtra: no recalcula
    nada en cada visita.

    La curva de un modelo **hereda la forma estacional de su categoría**, que es
    donde el modelo tiene señal, escalada por el peso del modelo dentro de ella.
    Es el mismo reparto que usa la propuesta, no una segunda estimación.

    La venta observada excluye el precio especial, igual que la previsión: si una
    mitad del gráfico incluyera las liquidaciones y la otra no, el salto en el
    corte sería del método y no del negocio.
    """
    desde = pd.Timestamp(config.FECHA_CORTE_DATOS) - pd.Timedelta(weeks=semanas_atras)
    ventas, stock_semanal = tablas["ventas"], tablas["stock_semanal"]
    compras = tablas["compras"]

    pedidas = propuesta.groupby("modelo_id")["unidades_propuestas"].sum() \
        if "modelo_id" in propuesta.columns else pd.Series(dtype=float)

    total = curva[["inicio_semana", "unidades"]].rename(columns={"unidades": "demanda"})
    series = [
        _serie_una(ventas, stock_semanal, compras, total, desde, pedido=float(pedidas.sum()))
        .assign(modelo_id="", modelo_nombre="Todo el catálogo")
    ]

    por_grupo = curva_grupo.groupby("grupo") if "grupo" in curva_grupo.columns else None
    peso_grupo = prevision.groupby("grupo")["demanda_horizonte"].sum()

    # La propuesta va por SKU y no lleva `modelo_id`: se recupera del catálogo.
    # Solo entran los modelos que aparecen en la propuesta, que son los que a
    # Compras le interesa mirar de cerca.
    modelos = (
        tablas["producto"][tablas["producto"]["sku"].isin(propuesta["sku"])]
        [["modelo_id", "modelo_nombre"]]
        .drop_duplicates()
        .sort_values("modelo_nombre")
    )
    for _, m in modelos.iterrows():
        filas = prevision[prevision["modelo_id"] == m["modelo_id"]]
        if filas.empty:
            continue
        grupo = filas["grupo"].iloc[0]
        cuota = filas["demanda_horizonte"].sum() / max(peso_grupo.get(grupo, 0.0), 1e-9)
        if por_grupo is not None and grupo in curva_grupo["grupo"].values:
            forma = curva_grupo[curva_grupo["grupo"] == grupo]
        else:
            forma = curva
        fut = forma[["inicio_semana", "unidades"]].copy()
        fut["demanda"] = fut.pop("unidades") * cuota
        series.append(
            _serie_una(ventas, stock_semanal, compras, fut, desde, set(filas["sku"]),
                       pedido=float(pedidas.get(m["modelo_id"], 0.0)))
            .assign(modelo_id=m["modelo_id"], modelo_nombre=m["modelo_nombre"])
        )

    return pd.concat(series, ignore_index=True)


def generar_propuesta(tablas: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Orquesta forecast → necesidad → propuesta y devuelve todas las tablas.

    Recibe las tablas ya limpias de `clean.py`: aquí no se aplica ninguna regla
    de negocio, solo se calcula sobre ellas.
    """
    semanas = horizonte_semanas()
    # La previsión no la calcula este módulo: viene de `demand`, que elige el
    # método por backtesting y devuelve la tabla que lo justifica. Esa tabla
    # viaja hasta el entregable: el método no se defiende por convicción.
    prevision, comparativa, curva, curva_grupo = demand.generar_prevision(tablas, semanas)

    necesidad = calcular_necesidad(
        prevision, tablas["stock"], tablas["compras"], tablas["producto"]
    )
    propuesta = construir_propuesta(necesidad)

    return {
        "propuesta": propuesta,
        "necesidad": necesidad,
        "sin_rotacion": sin_rotacion(necesidad),
        "compras_a_confirmar": compras_a_confirmar(tablas["compras"]),
        "resumen": resumen_propuesta(propuesta, necesidad, len(tablas["ventas"])),
        "parametros": parametros_usados(prevision=prevision),
        "comparativa_metodos": comparativa,
        "curva_semanal": curva,
        "historico_prevision": historico_y_prevision(
            tablas, curva, curva_grupo, prevision, propuesta),
        "error_forecast": comparativa,
    }


# Las columnas que Compras necesita de verdad. La tabla interna tiene muchas más
# —sirven para calcular y para auditar— pero un entregable con veinte columnas no
# se revisa: se cierra.
COLUMNAS_ENTREGABLE = [
    "prioridad", "modelo_nombre", "talla", "proveedor_habitual",
    "stock_disponible", "en_transito", "unidades_propuestas", "coste_pedido",
    "estado", "unidades_aprobadas", "motivo",
]

NOMBRES_ENTREGABLE = {
    "prioridad": "Prioridad", "modelo_nombre": "Modelo", "talla": "Talla",
    "proveedor_habitual": "Proveedor", "stock_disponible": "Stock",
    "en_transito": "En camino", "unidades_propuestas": "PEDIR",
    "coste_pedido": "Coste (€)", "estado": "Estado",
    "unidades_aprobadas": "Uds aprobadas", "motivo": "Por qué",
}


def tablas_entregable(resultado: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Las cuatro pestañas del entregable, en el orden en que se miran.

    El cálculo produce siete tablas, pero entregarlas todas es trasladar al
    lector el trabajo de decidir cuál importa. Se reducen a cuatro:

      1. **Propuesta** · lo único sobre lo que hay que actuar.
      2. **Revisar** · lo que necesita una persona pero no es un pedido.
      3. **Cómo se ha calculado** · los parámetros y por qué este método.
      4. **Ejecuciones** · la traza de que el proceso corre solo (la escribe
         el servicio, no este módulo).
    """
    propuesta = resultado["propuesta"][COLUMNAS_ENTREGABLE].rename(
        columns=NOMBRES_ENTREGABLE
    )

    # Las dos listas de "mirar esto" se funden en una sola: para Compras son el
    # mismo tipo de tarea, no dos ficheros distintos.
    vencidas = resultado["compras_a_confirmar"]
    revisar = pd.DataFrame({
        "Qué revisar": ["Compra vencida sin confirmar"] * len(vencidas),
        "Modelo": vencidas["modelo_nombre"],
        "Talla": vencidas["talla"],
        "Proveedor": vencidas["proveedor"],
        "Unidades": vencidas["unidades"],
        "Detalle": vencidas["dias_vencida"].astype(int).astype(str)
                   + " días de retraso · pedido " + vencidas["pedido_proveedor"].astype(str),
    })
    parados = resultado["sin_rotacion"].head(25)
    revisar = pd.concat([revisar, pd.DataFrame({
        "Qué revisar": ["Sin ventas · candidato a rebaja"] * len(parados),
        "Modelo": parados["modelo_nombre"],
        "Talla": parados["talla"],
        "Proveedor": "",
        "Unidades": parados["stock_disponible"],
        "Detalle": parados["capital_inmovilizado"].round(0).astype(int).astype(str)
                   + " € inmovilizados",
    })], ignore_index=True)

    # Parámetros y comparativa de métodos, en una sola hoja legible.
    comp = resultado["comparativa_metodos"]
    metodos = pd.DataFrame({
        "parámetro": ["Método: " + m for m in comp["metodo"]],
        "valor": [
            f"error {mae} · desvío {sesgo} %" for mae, sesgo in
            zip(comp["mae"], comp["sesgo_abs_pct"])
        ],
        "por qué": [
            "ELEGIDO: es el que menos se equivoca" if e else "descartado por el backtesting"
            for e in comp["elegido"]
        ],
    })
    calculo = pd.concat([resultado["parametros"], metodos], ignore_index=True).rename(
        columns={"parámetro": "Concepto", "valor": "Valor", "por qué": "Por qué"}
    )

    return {
        "Propuesta": propuesta,
        "Revisar": revisar,
        "Cómo se ha calculado": calculo,
        "Glosario": glosario(),
    }


def glosario() -> pd.DataFrame:
    """Qué es cada pestaña y qué significa cada columna.

    Va dentro del propio fichero y no en un correo aparte: quien abra esto dentro
    de seis meses no va a tener el correo, pero sí el Sheet. Sustituye además a la
    hoja vacía que Google crea por defecto.
    """
    filas = [
        ("PESTAÑAS", "", ""),
        ("Propuesta", "Lo que hay que pedir esta semana, ordenado por urgencia.",
         "Rellena 'Estado' y 'Uds aprobadas' en cada línea."),
        ("Revisar", "Lo que necesita una persona pero no es un pedido: compras vencidas "
                    "sin confirmar y stock que lleva semanas parado.",
         "Llamar al proveedor, o decidir rebaja."),
        ("Cómo se ha calculado", "Los parámetros del cálculo y la comparativa de métodos "
                                 "de previsión.",
         "Consúltala si una cifra no te cuadra."),
        ("Histórico de ejecuciones", "Una línea por cada vez que el proceso se ha ejecutado "
                                     "solo, con su fecha y su duración.",
         "Sirve para comprobar que sigue corriendo."),
        ("", "", ""),
        ("COLUMNAS DE 'PROPUESTA'", "", ""),
        ("Prioridad", "crítica = se agota antes de que llegue el pedido · alta = se queda "
                      "corto dentro del horizonte · normal = el resto.",
         "Empieza por las críticas."),
        ("Stock", "Unidades en el almacén a fecha de cierre.", ""),
        ("En camino", "Unidades ya pedidas que llegan dentro del horizonte. Las compras "
                      "vencidas sin confirmar NO cuentan aquí.", ""),
        ("PEDIR", "Unidades propuestas = demanda prevista − stock − en camino.",
         "Es la cifra sobre la que decides."),
        ("Coste (€)", "Unidades propuestas × coste unitario.", ""),
        ("Estado", "Para rellenar: Aprobado / Ajustado / Rechazado.",
         "Sin esto no se emite ningún pedido."),
        ("Uds aprobadas", "Para rellenar si ajustas la cantidad propuesta.",
         "La diferencia con lo propuesto es lo que mejora el modelo."),
        ("Por qué", "El cálculo de esa línea, en una frase.",
         "Para no tener que fiarte del número a ciegas."),
        ("", "", ""),
        ("CÓMO SE GENERA", "Este fichero lo reescribe un proceso automático cada día a las "
                           "00:00 (hora de Madrid). No se edita a mano salvo las columnas "
                           "'Estado' y 'Uds aprobadas'.", ""),
    ]
    return pd.DataFrame(filas, columns=["Concepto", "Qué es", "Qué hacer"])


def exportar_propuesta(resultado: Dict[str, pd.DataFrame], destino: Path) -> Path:
    """Escribe el Excel que revisa Compras y devuelve la ruta.

    Una pestaña por cosa que hay que mirar, en el orden en que se miran: primero
    las cifras de cabecera, luego lo que hay que pedir, luego lo que requiere una
    llamada al proveedor, y al final cómo se ha calculado todo.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    hojas = tuple(tablas_entregable(resultado).items())
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        for nombre, df in hojas:
            df.to_excel(writer, sheet_name=nombre[:31], index=False)
    return destino
