"""Reto 3 · Hoja de ruta de IA a 6 meses.

Este módulo es **contenido, no presentación**: las preguntas, las iniciativas,
el calendario y los supuestos viven aquí como estructuras de datos. De ellas
salen tanto las páginas del informe HTML (`report.py`) como el documento
`docs/reto3_roadmap_ia.md`, para que no haya dos versiones que se contradigan.

Las cifras de partida (`cifras_de_partida`) no se escriben a mano: se leen de
las tablas que ya calculó el Reto 1. Si cambian los datos, cambia la hoja de
ruta.

Dos ideas sostienen todo lo que hay debajo:

1. **La IA aparece dos veces.** En cómo se construye (un agente escribe el
   código: tipo `A`) y en qué se ejecuta en producción (un LLM o un modelo
   dentro del proceso: tipo `B`). Hay un tercer tipo, `C`, que es la IA en
   manos del propio equipo. Casi todo el valor está en `A`, y lo que corre en
   producción sigue siendo código determinista y auditable.
2. **El esfuerzo ya no lo marca programar.** Lo marcan el acceso al dato, quién
   valida el resultado y cuántas vueltas hacen falta hasta que alguien lo usa.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from . import config, storage

# ---------------------------------------------------------------------------
# Supuestos para poder poner números
# ---------------------------------------------------------------------------
# Van declarados, no escondidos: cualquiera puede rehacer las cuentas con los
# suyos. Los marcados como «dato» salen del propio caso; el resto son
# estimaciones razonables para una marca de este tamaño.

COSTE_HORA = 25.0          # € por hora, coste empresa
CONTACTOS_POR_PEDIDO = 0.30  # contactos de cliente por pedido
DESCUENTO_LIQUIDACION = 0.40  # descuento medio para dar salida al exceso
PCT_EXCESO_A_LIQUIDAR = 0.15  # qué parte del exceso se mueve en 6 meses

SUPUESTOS = [
    ("Coste hora interno", "25 €/h", "Perfil administrativo medio, coste empresa.", "estimado"),
    ("Plantilla", "≈14 personas", "Compras 2 · Planificación 1 · Logística 3 · Producto 2 · Marketing 2 · Atención 2 · Dirección 2.", "estimado"),
    ("Contactos de cliente", "0,30 por pedido", "≈69 a la semana. El caso no trae datos de atención.", "estimado"),
    ("Drops al año", "6", "12 drops en 22 meses.", "dato"),
    ("Modelos nuevos por drop", "≈10", "123 modelos en 12 drops.", "dato"),
    ("Margen medio por unidad", "42,1 €", "558 k€ sobre 13.260 unidades.", "dato"),
    ("Exceso de stock", "11.705 uds · 191 k€ a coste", "103 de 123 modelos sobre el umbral.", "dato"),
    ("Liquidación", "40 % de descuento sobre el 15 % del exceso", "Al 25 % el retorno sería de 58.900 €.", "estimado"),
    ("Iniciativa 10", "Solo cuentan sus horas", "Los 35.300 € de liquidación ya están contados en la 4.", "regla"),
    ("Capital y ahorro", "Columnas distintas", "El capital se libera una vez. Las horas se ahorran cada año.", "regla"),
]


# ---------------------------------------------------------------------------
# Punto 1 del enunciado · El método y las preguntas
# ---------------------------------------------------------------------------

METODO = [
    ("Inventariar", "Qué entrega cada equipo cada semana",
     "El fichero, el mensaje o la decisión que sale de su mesa."),
    ("Descomponer", "Cada entregable, en tareas con verbo",
     "«Enséñame los tres últimos y hazlo delante de mí.»"),
    ("Puntuar", "Horas al año, dato disponible, coste del error",
     "De aquí salen los dos ejes de la matriz."),
    ("Decidir cuánto se automatiza", "Qué hace la máquina y qué firma una persona",
     "Casi todo arranca con la máquina proponiendo y alguien aprobando."),
]

# El verbo de la tarea decide la tecnología. Es la parte del método que evita
# poner un modelo de lenguaje donde basta una resta.
VERBOS = [
    ("Recoger", "Descargar, copiar, consolidar", "Integración. Nada de IA."),
    ("Calcular", "Aplicar una regla fija", "Código determinista. Nada de IA."),
    ("Juzgar", "Decidir con criterio", "La persona. La IA propone y explica."),
    ("Comunicar", "Escribir, responder, traducir", "LLM."),
]

ESCALERA = [
    ("0", "Manual", "Como está hoy"),
    ("1", "Asistido", "Plantilla, buscador, borrador"),
    ("2", "Propone y alguien aprueba", "La puerta de entrada"),
    ("3", "Automático con excepciones", "Solo lo raro llega a una persona"),
    ("4", "Automático", "Se mira el KPI"),
]

# Seis preguntas iguales para todos: una por casilla de la ficha de puntuación.
PREGUNTAS_COMUNES = [
    ("¿Qué entregas cada semana?", "Qué sale de su mesa."),
    ("Enséñame los tres últimos.", "Las excepciones están en el fichero."),
    ("¿De dónde sacas cada dato de ahí?", "Quién tiene la llave. Suele ser el bloqueante."),
    ("¿Qué parte sigue una regla que podrías escribir?", "Separa lo que se automatiza de lo que se asiste."),
    ("¿Qué pasa si sale mal y quién se entera?", "Decide el peldaño."),
    ("¿Qué harías con ese tiempo?", "Si no hay respuesta, la iniciativa da igual."),
]

DEPARTAMENTOS = [
    {
        "nombre": "Compras", "peso": "Alto",
        "preguntas": [
            "¿Con qué plazo planificas: el del contrato o el real de cada proveedor?",
            "¿Cómo decides la curva de tallas de un pedido?",
        ],
        "hipotesis": "Se planifica con 6 semanas fijas y el 72 % de las entregas llega tarde.",
    },
    {
        "nombre": "Planificación", "peso": "Alto",
        "preguntas": [
            "¿Cómo decides cuántas unidades comprar de un modelo que todavía no existe?",
            "¿Quién decide cuándo un modelo pasa a rebaja, y con qué criterio?",
        ],
        "hipotesis": "Nadie mira la cobertura por modelo. Hay 103 de 123 sobre el umbral.",
    },
    {
        "nombre": "Atención al cliente", "peso": "Alto",
        "preguntas": [
            "¿Qué os preguntan, y en qué idioma?",
            "¿Qué pasa con un mensaje que entra un sábado a las 21:00?",
        ],
        "hipotesis": "El motivo no se registra. Constan 7 devoluciones en 12 meses.",
    },
    {
        "nombre": "Producto", "peso": "Medio",
        "preguntas": [
            "¿Cuánto pasa desde que llega la muestra hasta que el drop está publicado?",
            "¿Quién escribe las descripciones, y en cuántos idiomas?",
        ],
        "hipotesis": "El contenido retrasa el lanzamiento del drop.",
    },
    {
        "nombre": "Marketing", "peso": "Medio",
        "preguntas": [
            "¿Cómo eliges qué modelo empujar cada semana?",
            "¿Miras el stock antes de lanzar una campaña?",
        ],
        "hipotesis": "La campaña se decide sin mirar el stock.",
    },
    {
        "nombre": "Ventas y dirección", "peso": "Medio-alto",
        "preguntas": [
            "¿Qué miras el lunes por la mañana, y de dónde lo sacas?",
            "¿Qué número te gustaría tener y no tienes?",
        ],
        "hipotesis": "El informe se monta a mano y llega con la semana empezada.",
    },
    {
        "nombre": "Logística", "peso": "Bajo",
        "preguntas": [
            "¿Cuándo sabes de verdad que va a llegar un contenedor?",
            "¿Cómo planificas el personal de una semana de recepción?",
        ],
        "hipotesis": "La fecha estimada del proveedor se trata como firme.",
    },
]


# ---------------------------------------------------------------------------
# Punto 2 del enunciado · Las 12 iniciativas
# ---------------------------------------------------------------------------
# Campos de cada ficha:
#   tipo          A = construida con agente, ejecuta código determinista
#                 B = lleva un LLM o un modelo dentro del proceso
#                 C = capacitación del equipo (va aparte, no numerada)
#   horas         horas de persona liberadas al año
#   euros_rec     € de ahorro o margen recurrente al año
#   euros_unavez  € de capital liberado una sola vez
#   esfuerzo      semanas hasta estar en producción, no semanas de programar
#   dato          2 = accesible · 1 = existe disperso · 0 = hay que crearlo
#   peldano       nivel de la escalera con el que arranca

INICIATIVAS: List[Dict] = [
    {
        "n": 1, "dept": "Compras", "tipo": "A",
        "nombre": "Reposición semanal automática",
        "problema": "La propuesta se monta a mano cada semana. Hay 37 modelos que rompen en cuatro semanas, 249 unidades de déficit.",
        "que_hace": "Prevé la demanda por SKU, descuenta stock y tránsito, y deja la propuesta en un Sheet que firma Compras. Ya está desplegada.",
        "horas": 312, "euros_rec": 7800, "euros_unavez": 0,
        "error": "Comprar lo que ya sobra.",
        "formula": "6 h/semana × 52 × 25 €/h = 7.800 €/año. Aparte protege 10.500 € de margen (249 uds × 42,1 €).",
        "esfuerzo": 2, "dato": 2, "peldano": 2,
        "mes_ini": 1, "mes_fin": 1, "quick": True, "hecho": True,
        "kpi": "Pedidos de compra que salen de la propuesta sin editar",
        "base": "0 %", "objetivo": "70 %",
    },
    {
        "n": 2, "dept": "Compras", "tipo": "A",
        "nombre": "Plazo real de cada proveedor",
        "problema": "427 de 592 entregas llegaron tarde, 5,8 días de media. Compras planifica con 6 semanas fijas para los cuatro.",
        "que_hace": "Mide el plazo que cumple de verdad cada proveedor y se lo pasa al motor de reposición. Avisa del pedido vencido sin confirmar.",
        "horas": 104, "euros_rec": 9200, "euros_unavez": 0,
        "error": "Planificar con una fecha que falla tres de cada cuatro veces.",
        "formula": "2 h/semana de seguimiento = 2.600 €. Más 6.600 €, el 65 % del déficit de 249 uds × 42,1 € de margen.",
        "esfuerzo": 1, "dato": 2, "peldano": 3,
        "mes_ini": 1, "mes_fin": 1, "quick": False, "hecho": False,
        "kpi": "Entregas dentro de la fecha planificada",
        "base": "28 %", "objetivo": "60 %",
    },
    {
        "n": 3, "dept": "Compras", "tipo": "A",
        "nombre": "Repartir cada pedido por tallas",
        "problema": "Los pedidos se reparten casi a partes iguales entre tallas. Sobran 1.959 unidades en XL y XXL y faltan 1.240 de la M.",
        "que_hace": "Calcula cuánto pesa cada talla en la venta real de esa categoría y reparte el pedido con esos pesos.",
        "horas": 0, "euros_rec": 8000, "euros_unavez": 0,
        "error": "Comprar tallas que no se venden, drop tras drop.",
        "formula": "Evitar la mitad de las 2.017 uds que hoy sobran son 16.500 € que no se gastan. Se imputa la mitad al año.",
        "esfuerzo": 2, "dato": 2, "peldano": 2,
        "mes_ini": 3, "mes_fin": 3, "quick": False, "hecho": False,
        "kpi": "SKUs sin una sola venta en 6 meses",
        "base": "21", "objetivo": "menos de 10",
    },
    {
        "n": 4, "dept": "Planificación", "tipo": "A",
        "nombre": "Plan de liquidación del exceso",
        "problema": "103 de 123 modelos pasan el umbral de cobertura: 11.705 unidades y 191 k€ a coste, con 51 semanas de cobertura mediana.",
        "que_hace": "Ordena el exceso por capital parado y por lo que aún vende, y propone descuento y mercado sin bajar de un suelo de margen.",
        "horas": 0, "euros_rec": 0, "euros_unavez": 35300,
        "error": "Rebajar lo que ya se vendía solo.",
        "formula": "1.756 uds (el 15 %) × (60,8 € de PVP − 40 % − 16,35 € de coste) = 35.300 €.",
        "esfuerzo": 3, "dato": 2, "peldano": 2,
        "mes_ini": 2, "mes_fin": 3, "quick": True, "hecho": False,
        "kpi": "Cobertura global de stock",
        "base": "29,2 semanas", "objetivo": "menos de 22",
    },
    {
        "n": 5, "dept": "Planificación", "tipo": "A+B",
        "nombre": "Cuánto comprar de un modelo que aún no existe",
        "problema": "Seis drops al año, diez modelos nuevos en cada uno. Sin ventas previas, la primera compra se decide a ojo.",
        "que_hace": "Busca modelos parecidos en categoría, sección, precio y color entre los 123 con histórico, y usa su curva de venta como punto de partida.",
        "horas": 0, "euros_rec": 18000, "euros_unavez": 0,
        "error": "Fallar la primera compra de 62 modelos al año.",
        "formula": "217 k€ de compra anual a coste. Un 8 % menos de error son 18.000 €.",
        "esfuerzo": 5, "dato": 1, "peldano": 1,
        "mes_ini": 4, "mes_fin": 6, "quick": False, "hecho": False,
        "kpi": "Desviación de la primera compra frente a la venta real",
        "base": "sin medir", "objetivo": "menos del 20 %",
    },
    {
        "n": 6, "dept": "Atención al cliente", "tipo": "B",
        "nombre": "Agente de chat y voz multiidioma",
        "problema": "El 45 % de la facturación viene de seis países fuera de España. Fuera de horario no contesta nadie.",
        "que_hace": "Responde estado del pedido, disponibilidad y dudas de talla, tramita devoluciones y pasa a una persona con el contexto. Chat primero, voz después.",
        "horas": 200, "euros_rec": 11800, "euros_unavez": 0,
        "error": "Perder la venta por no contestar un sábado en alemán.",
        "formula": "3.566 contactos al año, 55 % resueltos, 6 min cada uno: 200 h = 5.000 €. Más 6.800 € de preventa recuperada.",
        "esfuerzo": 4, "dato": 0, "peldano": 3,
        "mes_ini": 3, "mes_fin": 4, "quick": False, "hecho": False,
        "kpi": "Contactos resueltos sin intervención de una persona",
        "base": "0 %", "objetivo": "55 %",
    },
    {
        "n": 7, "dept": "Atención al cliente", "tipo": "B",
        "nombre": "Por qué devuelven, y arreglar el tallaje",
        "problema": "En 12 meses constan 7 devoluciones y ninguna trae motivo. La M se agota y la XXL se queda, sin saber si es demanda o patrón.",
        "que_hace": "El agente etiqueta cada devolución con un motivo fijo (talla, calidad, envío, cambio de opinión). A los tres meses Producto los cruza con la venta por talla y corrige los patrones que fallan.",
        "horas": 0, "euros_rec": 6500, "euros_unavez": 0,
        "error": "Repetir el patrón que genera la devolución.",
        "formula": "Sin línea base, la crea ella misma. Si el 1 % se devuelve por talla y se corrige la mitad: 119 × 75,87 € × 71,5 %.",
        "esfuerzo": 2, "dato": 0, "peldano": 2,
        "mes_ini": 4, "mes_fin": 6, "quick": False, "hecho": False,
        "kpi": "Devoluciones con motivo registrado",
        "base": "≈0 %", "objetivo": "90 %",
    },
    {
        "n": 8, "dept": "Producto", "tipo": "B",
        "nombre": "Ficha de producto automática y multiidioma",
        "problema": "62 modelos nuevos al año para siete mercados. El contenido retrasa cada lanzamiento.",
        "que_hace": "Del catálogo y la foto saca nombre, descripción, atributos, texto alternativo y SEO en seis idiomas. Producto revisa y publica.",
        "horas": 93, "euros_rec": 5300, "euros_unavez": 0,
        "error": "Publicar el drop tarde, o solo en español.",
        "formula": "62 modelos × 6 idiomas × 15 min = 93 h = 2.325 €. Más 3.000 € por adelantar una semana cada drop.",
        "esfuerzo": 3, "dato": 2, "peldano": 2,
        "mes_ini": 2, "mes_fin": 3, "quick": False, "hecho": False,
        "kpi": "Días desde la muestra hasta la ficha publicada",
        "base": "sin medir", "objetivo": "menos de 3",
    },
    {
        "n": 9, "dept": "Ventas y dirección", "tipo": "B",
        "nombre": "Preguntar a los datos en lenguaje natural",
        "problema": "Cada pregunta nueva pasa por alguien que sepa cruzar tablas. Las que no son urgentes no llegan a preguntarse.",
        "que_hace": "«¿Cómo va la chaqueta en Francia?» se traduce a SQL sobre las tablas limpias. Enseña la consulta que ha escrito y devuelve el resultado. Solo lectura.",
        "horas": 156, "euros_rec": 3900, "euros_unavez": 0,
        "error": "Decidir con la única pregunta que a alguien le dio tiempo a contestar.",
        "formula": "3 h/semana de montar consultas a mano × 52 × 25 € = 3.900 €.",
        "esfuerzo": 3, "dato": 2, "peldano": 1,
        "mes_ini": 5, "mes_fin": 5, "quick": False, "hecho": False,
        "kpi": "Preguntas respondidas sin pasar por una persona",
        "base": "0 %", "objetivo": "50 %",
    },
    {
        "n": 10, "dept": "Marketing", "tipo": "A",
        "nombre": "Qué promocionar esta semana, según el stock",
        "problema": "37 modelos a punto de romper y 103 con exceso. La campaña de la semana no mira ninguno de los dos.",
        "que_hace": "Lista semanal de qué empujar (exceso que aún vende) y qué dejar quieto (lo que va a romper). Es el canal de salida de la 4.",
        "horas": 52, "euros_rec": 1300, "euros_unavez": 0,
        "error": "Gastar en promocionar lo que ya no hay.",
        "formula": "1 h/semana × 52 × 25 € = 1.300 €. Los 35.300 € de la 4 no se cuentan aquí.",
        "esfuerzo": 1, "dato": 2, "peldano": 2,
        "mes_ini": 2, "mes_fin": 2, "quick": False, "hecho": False,
        "kpi": "Gasto de promoción sobre modelos con exceso",
        "base": "sin medir", "objetivo": "más del 60 %",
    },
    {
        "n": 11, "dept": "Ventas y dirección", "tipo": "A+B",
        "nombre": "Informe del lunes automático",
        "problema": "El informe existe desde el Reto 1, pero se lanza a mano.",
        "que_hace": "Se genera los lunes a las 7:00 y manda un resumen con los tres cambios de la semana y lo que hay que decidir.",
        "horas": 208, "euros_rec": 5200, "euros_unavez": 0,
        "error": "Decidir el lunes con los números del lunes anterior.",
        "formula": "4 h/semana de montar y revisar × 52 × 25 € = 5.200 €.",
        "esfuerzo": 1, "dato": 2, "peldano": 4,
        "mes_ini": 1, "mes_fin": 1, "quick": True, "hecho": False,
        "kpi": "Lunes con el informe disponible antes de las 8:00",
        "base": "0 %", "objetivo": "100 %",
    },
    {
        "n": 12, "dept": "Logística", "tipo": "A",
        "nombre": "Plan semanal de entradas al almacén",
        "problema": "El almacén planifica con la fecha estimada del proveedor. Hay 37 pedidos vencidos sin confirmar.",
        "que_hace": "Calendario de lo que entra cada semana con la fecha corregida por el retraso real. Avisa si lo retrasado afecta a un modelo en rotura.",
        "horas": 104, "euros_rec": 2600, "euros_unavez": 0,
        "error": "Montar el turno de recepción para un camión que no llega.",
        "formula": "2 h/semana de replanificación × 52 × 25 € = 2.600 €.",
        "esfuerzo": 2, "dato": 2, "peldano": 3,
        "mes_ini": 3, "mes_fin": 3, "quick": False, "hecho": False,
        "kpi": "Entradas con fecha fiable a 7 días vista",
        "base": "sin medir", "objetivo": "85 %",
    },
]


# Hace posibles las doce, así que va en el mes 1 y no compite en la matriz.
CIMIENTO = {
    "nombre": "Capa de validación del dato en la entrada",
    "que_hace": "Valida cada fichero que entra (SKUs huérfanos, duplicados, tipos mezclados, fechas imposibles) y para el proceso antes de que el error llegue a un informe.",
    "porque": "En el Reto 1 la limpieza se llevó media vuelta de trabajo: 25 líneas duplicadas, un SKU fuera del catálogo, mercados escritos de tres formas y descuentos imposibles.",
}

# Tipo C: la IA en manos del equipo. Es la palanca de adopción, así que vive en
# la página de éxito y no en la matriz.
CAPACITACION = [
    ("Un champion por departamento", "La persona que ya tenía ganas."),
    ("Una sesión al mes por área", "Sobre su trabajo de esa semana."),
    ("La herramienta vive donde ya trabajan", "Sheets, correo, chat."),
    ("Se sube de peldaño con el KPI", "Nada pasa a automático porque toque."),
]

CALENDARIO_FOCO = {
    1: "Cimientos y lo que ya está hecho",
    2: "El dinero parado",
    3: "Compras afinada y el agente en marcha",
    4: "Atención al cliente completa",
    5: "Lo nuevo, y preguntar a los datos",
    6: "Cerrar el círculo del tallaje",
}


# ---------------------------------------------------------------------------
# Las cifras de partida salen de los datos, no de la memoria
# ---------------------------------------------------------------------------

def cifras_de_partida() -> Dict[str, float]:
    """Magnitudes del negocio que justifican el reparto de iniciativas.

    Se leen de las tablas que ya produjeron la limpieza y el Reto 1, así que la
    hoja de ruta se recalcula sola si cambian los datos. La ventana es de 12
    meses hacia atrás desde la fecha de corte, no la semana del informe: una
    hoja de ruta se decide con el año, no con una semana.
    """
    ventas = storage.cargar_tabla("ventas", config.DIR_INTERIM)
    stock = storage.cargar_tabla("stock", config.DIR_INTERIM)
    producto = storage.cargar_tabla("producto", config.DIR_INTERIM)
    compras = storage.cargar_tabla("compras", config.DIR_INTERIM)

    cobertura = storage.cargar_tabla("cobertura_global", config.DIR_PROCESSED).iloc[0]
    exceso = storage.cargar_tabla("exceso_por_modelo", config.DIR_PROCESSED)
    concentracion = storage.cargar_tabla("concentracion", config.DIR_PROCESSED)
    rotura = storage.cargar_tabla("rotura_por_modelo", config.DIR_PROCESSED)
    tallas = storage.cargar_tabla("curva_tallas", config.DIR_PROCESSED)
    proveedores = storage.cargar_tabla("fiabilidad_proveedores", config.DIR_PROCESSED)

    inicio = pd.Timestamp(config.FECHA_CORTE_DATOS) - pd.Timedelta(days=364)
    v12 = ventas[ventas["fecha"] >= inicio]
    fact = v12["facturacion_neta"].sum()
    fuera = v12[~v12["mercado"].isin(["ES", "DESCONOCIDO"])]["facturacion_neta"].sum()

    # Stock muerto: SKUs con existencias que no han vendido ni una unidad en
    # los últimos 12 meses. Se calcula aquí y no se toma del Reto 2 para que el
    # informe siga generándose con `run_reto1.py` a secas.
    vendidos = set(v12.loc[v12["unidades"] > 0, "sku"])
    con_stock = stock[stock["stock_disponible"] > 0].merge(
        producto[["sku", "coste_unitario"]], on="sku", how="left")
    muertos = con_stock[~con_stock["sku"].isin(vendidos)]

    llegadas = compras[compras["ha_llegado"]]
    conc50 = concentracion[concentracion["pct_facturacion"] == 50].iloc[0]

    return {
        "facturacion_12m": fact,
        "margen_12m": v12["margen"].sum(),
        "margen_pct": 100 * v12["margen"].sum() / fact,
        "unidades_12m": v12["unidades"].sum(),
        "pedidos_12m": len(v12),
        "pedidos_semana": len(v12) / 52,
        "margen_unidad": v12["margen"].sum() / v12["unidades"].sum(),
        "pct_fuera_es": 100 * fuera / fact,
        "mercados": v12["mercado"].nunique() - 1,
        "stock_uds": stock["stock_disponible"].sum(),
        "cobertura_semanas": cobertura["cobertura_global_semanas"],
        "modelos_exceso": int(cobertura["modelos_por_encima_del_umbral"]),
        "modelos_total": int(cobertura["modelos_totales"]),
        "exceso_uds": exceso["unidades_exceso"].sum(),
        "exceso_coste": exceso["capital_inmovilizado"].sum(),
        "exceso_pvp": exceso["valor_pvp"].sum(),
        "cobertura_mediana": exceso["cobertura_semanas"].median(),
        "conc_modelos": int(conc50["n_modelos"]),
        "conc_pct_catalogo": conc50["pct_catalogo"],
        "modelos_rotura": len(rotura),
        "deficit_uds": rotura["deficit_unidades"].sum(),
        "margen_en_riesgo": rotura["deficit_unidades"].sum() * v12["margen"].sum() / v12["unidades"].sum(),
        "skus_muertos": len(muertos),
        "capital_muerto": (muertos["stock_disponible"] * muertos["coste_unitario"]).sum(),
        "tallas_sobran": tallas[tallas["desvio_uds"] > 0]["desvio_uds"].sum(),
        "tallas_faltan_m": abs(tallas[tallas["talla"] == "M"].iloc[0]["desvio_uds"]),
        "entregas": len(llegadas),
        "entregas_tarde": int((llegadas["dias_retraso"] > 0).sum()),
        "pct_tarde": 100 * (llegadas["dias_retraso"] > 0).mean(),
        "retraso_medio": llegadas["dias_retraso"].mean(),
        "vencidas": int(compras["esta_vencida"].sum()),
        "proveedores": compras["proveedor"].nunique(),
        "drops": producto["drop"].nunique(),
        "modelos_por_drop": producto.groupby("drop")["modelo_id"].nunique().mean(),
    }


def totales() -> Dict[str, float]:
    """Suma de impactos. Separa lo recurrente del capital que se libera una vez."""
    return {
        "horas": sum(i["horas"] for i in INICIATIVAS),
        "euros_rec": sum(i["euros_rec"] for i in INICIATIVAS),
        "euros_unavez": sum(i["euros_unavez"] for i in INICIATIVAS),
        "con_ia_dentro": sum(1 for i in INICIATIVAS if "B" in i["tipo"]),
    }


def quick_wins() -> List[Dict]:
    """Las tres victorias de los primeros 60 días."""
    return [i for i in INICIATIVAS if i["quick"]]


# ---------------------------------------------------------------------------
# El documento markdown sale de las mismas estructuras que el informe
# ---------------------------------------------------------------------------

def _fila(*celdas) -> str:
    return "| " + " | ".join(str(c) for c in celdas) + " |"


def documento_markdown() -> str:
    """`docs/reto3_roadmap_ia.md`, generado. No se edita a mano.

    Es la misma información que las cinco páginas del informe, en el formato
    que pide CLAUDE.md. Si las dos versiones se escribieran por separado, en dos
    semanas se contradirían.
    """
    c = cifras_de_partida()
    t = totales()
    e = lambda v: f"{v:,.0f}".replace(",", ".")          # miles con punto
    d = lambda v: f"{v:,.1f}".replace(".", ",")          # un decimal, coma española

    partes = [
        "# Reto 3 · Hoja de ruta de IA a 6 meses",
        "",
        "> Generado por `pipelines/run_reto3.py` desde `src/roadmap.py`. No se edita a mano.",
        "> La versión navegable está en el informe: `output/reto1/informe_semanal.html`,",
        "> sección **Reto 3**.",
        "",
        "## 0 · Dónde duele",
        "",
        f"- Margen de 12 meses: **{e(c['margen_12m'])} €** sobre {e(c['facturacion_12m'])} € de facturación neta.",
        f"- Capital parado en exceso: **{e(c['exceso_coste'])} €** a coste ({e(c['exceso_pvp'])} € a PVP), "
        f"en {int(c['modelos_exceso'])} de {int(c['modelos_total'])} modelos.",
        f"- Cobertura global: **{d(c['cobertura_semanas'])} semanas** frente a las "
        f"{config.COBERTURA_OBJETIVO_SEMANAS} de objetivo.",
        f"- Entregas de proveedor que llegan tarde: **{c['pct_tarde']:.0f} %** "
        f"({int(c['entregas_tarde'])} de {int(c['entregas'])}), {d(c['retraso_medio'])} días de media.",
        f"- Facturación fuera de España: **{c['pct_fuera_es']:.0f} %**, en {int(c['mercados']) - 1} países.",
        f"- Concentración: **{int(c['conc_modelos'])} modelos** ({c['conc_pct_catalogo']:.0f} % del catálogo) "
        "hacen la mitad de la facturación.",
        "",
        "De ahí el reparto: Compras y Planificación se llevan cinco iniciativas de doce, y Logística una.",
        "",
        "## 1 · El método y las preguntas",
        "",
        "La unidad de análisis es la tarea recurrente, y la evidencia es el fichero que produce.",
        "",
        _fila("Paso", "Qué se hace", "Cómo"),
        _fila("---", "---", "---"),
        *[_fila(f"**{n}. {tit}**", que, como) for n, (tit, que, como) in enumerate(METODO, 1)],
        "",
        "### El verbo de la tarea decide la tecnología",
        "",
        _fila("Verbo", "Qué es", "Qué lo automatiza"),
        _fila("---", "---", "---"),
        *[_fila(f"**{v}**", q, tec) for v, q, tec in VERBOS],
        "",
        "### Las seis preguntas comunes a todos los departamentos",
        "",
        *[f"{n}. **{p}** — {busco}" for n, (p, busco) in enumerate(PREGUNTAS_COMUNES, 1)],
        "",
        "### Las tres preguntas propias de cada departamento",
        "",
        _fila("Departamento", "Peso", "Preguntas", "Hipótesis que pone a prueba"),
        _fila("---", "---", "---", "---"),
        *[_fila(d["nombre"], d["peso"], "<br>".join(f"· {q}" for q in d["preguntas"]), d["hipotesis"])
          for d in DEPARTAMENTOS],
        "",
        "## 2 · Las 12 iniciativas",
        "",
        f"**{e(t['horas'])} horas** de persona al año, **{e(t['euros_rec'])} €** de ahorro recurrente y "
        f"**{e(t['euros_unavez'])} €** de capital liberado una sola vez. "
        f"Solo **{t['con_ia_dentro']} de 12** llevan IA dentro del proceso.",
        "",
        "Tipo **A**, la IA escribe el código y en producción corre lógica determinista. "
        "Tipo **B**, la IA está dentro del proceso.",
        "",
        _fila("#", "Dept.", "Iniciativa", "Tipo", "Problema", "h/año", "€ 1er año", "Esf."),
        _fila("---", "---", "---", "---", "---", "---", "---", "---"),
        *[_fila(i["n"], i["dept"], i["nombre"], i["tipo"], i["problema"],
                i["horas"] or "—",
                e(i["euros_rec"] + i["euros_unavez"]) + " €" if i["euros_rec"] + i["euros_unavez"] else "habilitadora",
                f"{i['esfuerzo']} sem")
          for i in INICIATIVAS],
        "",
        "### Detalle de cada iniciativa",
        "",
    ]

    for i in INICIATIVAS:
        peldano = dict((n, tx) for n, tx, _ in ESCALERA)[str(i["peldano"])]
        partes += [
            f"#### {i['n']} · {i['nombre']} ({i['dept']})",
            "",
            f"- **Qué pasa hoy**: {i['problema']}",
            f"- **Qué hace**: {i['que_hace']}",
            f"- **De dónde sale el número**: {i['formula']}",
            f"- **Error que evita**: {i['error']}",
            f"- **Peldaño {i['peldano']}**: {peldano}.",
            f"- **KPI**: {i['kpi']} — de {i['base']} a {i['objetivo']}.",
            "",
        ]

    partes += [
        f"### Cimiento · {CIMIENTO['nombre']}",
        "",
        CIMIENTO["que_hace"], "", CIMIENTO["porque"], "",
        "## 3 · Matriz de impacto × esfuerzo",
        "",
        "El eje de esfuerzo son **semanas hasta producción**. Dentro va conseguir el acceso al dato, "
        "acordar quién valida y las vueltas hasta que alguien lo usa. El gráfico está en el informe HTML.",
        "",
        _fila("Cuadrante", "Iniciativas"),
        _fila("---", "---"),
        _fila("Hazlo ya — alto impacto, bajo esfuerzo",
              ", ".join(str(i["n"]) for i in INICIATIVAS
                        if i["esfuerzo"] <= 2 and i["euros_rec"] + i["euros_unavez"] > 7500)),
        _fila("Proyecto con dueño — alto impacto, alto esfuerzo",
              ", ".join(str(i["n"]) for i in INICIATIVAS
                        if i["esfuerzo"] > 2 and i["euros_rec"] + i["euros_unavez"] > 7500)),
        _fila("Rápidas — bajo esfuerzo",
              ", ".join(str(i["n"]) for i in INICIATIVAS
                        if i["esfuerzo"] <= 2 and i["euros_rec"] + i["euros_unavez"] <= 7500)),
        _fila("Justifícala por otra cosa — alto esfuerzo, poco €",
              ", ".join(str(i["n"]) for i in INICIATIVAS
                        if i["esfuerzo"] > 2 and i["euros_rec"] + i["euros_unavez"] <= 7500)),
        "",
        "## 4 · Calendario",
        "",
        _fila("Mes", "Foco", "Iniciativas"),
        _fila("---", "---", "---"),
        *[_fila(m, foco, ", ".join(str(i["n"]) for i in INICIATIVAS
                                   if i["mes_ini"] <= m <= i["mes_fin"]) or "—")
          for m, foco in CALENDARIO_FOCO.items()],
        "",
        "### Tres victorias rápidas en los primeros 60 días",
        "",
        *[f"{n}. **{i['nombre']}** — {i['kpi']}: de {i['base']} a {i['objetivo']}."
          for n, i in enumerate(quick_wins(), 1)],
        "",
        "## 5 · Cómo se mide el éxito y cómo se consigue la adopción",
        "",
        "Casi todas entran por el **peldaño 2**, el de proponer y que alguien apruebe. Se sube cuando "
        "el KPI lo permite.",
        "",
        _fila("Peldaño", "Qué significa", "Cuándo"),
        _fila("---", "---", "---"),
        *[_fila(f"**{n}**", tx, cu) for n, tx, cu in ESCALERA],
        "",
        "### Un KPI por iniciativa",
        "",
        _fila("#", "Iniciativa", "Cómo se mide", "Hoy", "A 6 meses"),
        _fila("---", "---", "---", "---", "---"),
        *[_fila(i["n"], i["nombre"], i["kpi"], i["base"], i["objetivo"]) for i in INICIATIVAS],
        "",
        "Por encima de las doce hay un KPI de la hoja de ruta entera: **cuántas siguen usándose tres "
        "meses después de entregarse**.",
        "",
        "### Adopción",
        "",
        *[f"- **{tit}** — {d}" for tit, d in CAPACITACION],
        "",
        "## 6 · Supuestos sobre los que se ha priorizado",
        "",
        _fila("Supuesto", "Valor", "Origen", "De dónde sale"),
        _fila("---", "---", "---", "---"),
        *[_fila(f"**{con}**", val, org, por) for con, val, por, org in SUPUESTOS],
        "",
        "Construir rápido con un agente traslada el riesgo al mantenimiento. La regla del repositorio "
        "lo cubre: todo en código, pipeline reproducible y decisiones fechadas.",
        "",
    ]
    return "\n".join(partes)
