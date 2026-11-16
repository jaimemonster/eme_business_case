# Log de decisiones y supuestos

> Toda decisión o supuesto que no sea evidente a partir de los datos se registra
> aquí, con fecha. Formato: una entrada por decisión.

## Formato

```
### [AAAA-MM-DD] Título corto de la decisión
- **Contexto:** qué problema o ambigüedad lo motiva.
- **Opciones consideradas:** alternativas descartadas y por qué.
- **Decisión:** qué se hace.
- **Reto:** 1 | 2 | 3 | transversal  (se usa para filtrar al construir los entregables).
- **Impacto:** a qué KPIs o entregables afecta.
- **Estado:** supuesto pendiente de validar | validado con los datos | confirmado con negocio.
```

---

## Decisiones

### [2026-11-14] Estructura inicial del repositorio y supuestos de partida
- **Contexto:** arranque del caso, antes de mirar los datos.
- **Decisión:** se fija la estructura del repositorio, los parámetros del caso
  (semanas de análisis, lead time 6 semanas, cobertura objetivo 8 semanas) y las
  definiciones preliminares de KPIs recogidas en `CLAUDE.md`.
- **Reto:** transversal.
- **Impacto:** transversal a los tres retos.
- **Estado:** supuestos pendientes de validar tras el perfilado.

<!-- Nuevas entradas al final -->

### [2026-11-14] `src/io.py` pasa a llamarse `src/storage.py`
- **Contexto:** `io` colisiona con el módulo `io` de la librería estándar de Python.
  Aunque dentro del paquete `src` los imports son absolutos y no rompe nada, ejecutar
  código desde dentro de `src/` podría sombrear la stdlib.
- **Decisión:** renombrar el módulo a `storage.py`. Responsabilidad sin cambios:
  leer el Excel de `data/raw` y persistir/recuperar tablas en parquet.
- **Reto:** transversal.
- **Impacto:** imports del proyecto y árbol de carpetas en README.
- **Estado:** confirmado.

### [2026-11-14] Supuestos resueltos por la pestaña `LEEME` del Excel
- **Contexto:** el Excel trae una quinta pestaña, `LEEME`, con documentación del caso
  que no estaba descrita en el enunciado PDF.
- **Decisión:** se dan por confirmados dos supuestos que estaban pendientes:
  (a) el **descuento viene en euros**, como importe por línea, y el importe bruto es
  `unidades × PVP`; (b) la etiqueta de precio especial aparece en **variantes**
  (`special`, `SPECIAL XX`), por lo que hay que normalizarla antes de filtrar.
  Sigue pendiente si los precios llevan IVA: se asume que **no**.
- **Reto:** 1 y 2.
- **Impacto:** definición de facturación neta y margen (Reto 1), y filtrado de
  etiquetas en `clean.py`.
- **Estado:** validado con los datos (origen: pestaña `LEEME`).

### [2026-11-14] El PVP de la línea de venta manda sobre el del catálogo
- **Contexto:** `VENTAS` tiene `PVP unitario (€)` y `PRODUCTO` tiene `PVP (€)`.
  Pueden no coincidir.
- **Decisión:** para facturación y margen se usa el **PVP de la línea de venta**, que
  es el precio al que se vendió de verdad. El PVP de catálogo se usa solo como
  referencia para medir el descuento efectivo sobre tarifa.
- **Reto:** 1.
- **Impacto:** facturación neta, margen, análisis de precio especial.
- **Estado:** supuesto pendiente de validar con el volumen real de discrepancias.

### [2026-11-14] CORRECCIÓN: el PVP de venta y el de catálogo coinciden siempre
- **Contexto:** se registró una decisión sobre cuál de los dos PVP usar. El
  perfilado la deja sin objeto: coinciden en las **18.292 líneas** (0 discrepancias).
- **Reto:** 1 y 2.
- **Decisión:** se usa el de la línea de venta, pero deja de ser un supuesto con
  riesgo. No hay que medir ninguna discrepancia.
- **Estado:** validado con los datos.

### [2026-11-14] `WELCOME10` es venta a precio completo, no precio especial
- **Contexto:** aparece una etiqueta que el enunciado no menciona, en 999 líneas
  (5,5 %). Descuenta exactamente el 10 %, frente al ~40 % de `special` y el 100 %
  de `influencers`.
- **Opciones consideradas:** tratarla como `special`. Descartada: mezclaría un
  cupón del 10 % con liquidaciones del 40 % y distorsionaría el margen del canal
  de precio completo.
- **Decisión:** es una venta a tarifa con un cupón promocional encima. Entra en
  precio completo, con flag propio `es_promocion` para poder medirla aparte.
- **Reto:** 1.
- **Impacto:** reparto precio completo vs. especial; margen por canal.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Las variantes `SPECIAL XX` se unifican en `is_special`
- **Contexto:** `special` (851), `SPECIAL ES` (717), `SPECIAL US` (61),
  `SPECIAL NL` (55). Todas descuentan ~40 %, luego son lo mismo.
- **Decisión:** cualquier etiqueta que empiece por `SPECIAL` marca `is_special`.
  El sufijo se guarda en `mercado_etiqueta` como dato de control, para contrastarlo
  con el mercado de la línea, no para analizar con él.
- **Reto:** 1 y 2.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Las unidades negativas son devoluciones y se conservan
- **Contexto:** 10 líneas con `unidades = -1` (0,05 % del total).
- **Opciones consideradas:** excluirlas. Descartada: inventaría 10 ventas que se
  devolvieron. Es lo que haría un ERP: restan de la venta neta.
- **Decisión:** se mantienen, marcadas con `es_devolucion`.
- **Reto:** 1 y 2.
- **Impacto:** despreciable en las cifras; relevante para la honestidad del dato.
- **Estado:** confirmado con el usuario.

### [2026-11-14] En una devolución, el descuento se revierte con las unidades
- **Contexto:** consecuencia mecánica de la decisión anterior. Las 10 devoluciones
  traen las unidades en negativo pero el descuento en positivo, así que
  `bruto − descuento` restaría de más. Es el origen de las 10 filas que el
  perfilado marcó como "descuento > importe bruto".
- **Decisión:** en las líneas con `es_devolucion`, el descuento se multiplica por
  −1 para que lleve el mismo signo que las unidades.
- **Reto:** 1 y 2.
- **Impacto:** **1 sola línea** tras excluir los regalos (una devolución
  `SPECIAL ES` con 11,20 € de descuento). El resto tenía descuento 0.
- **Estado:** decidido durante la limpieza; no estaba en la lista original de 8.

### [2026-11-14] Las 25 líneas de venta duplicadas se eliminan
- **Contexto:** 25 pares de filas idénticas en todas sus columnas (mismo pedido,
  mismo SKU, misma fecha, mismo precio, 1 unidad cada una).
- **Opciones consideradas:** conservarlas, por si el sistema crease una línea por
  unidad. Descartada: un ERP agruparía 2 unidades en una línea con `unidades = 2`,
  y el enunciado avisa de que hay errores introducidos a propósito.
- **Decisión:** se elimina una de cada par.
- **Reto:** 1 y 2.
- **Impacto:** −25 líneas sobre 18.292 (0,1 %). De ellas, 2 eran regalos y 5 eran
  de precio especial.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Normalizaciones de formato: SKU y mercado
- **Contexto:** 15 líneas traen el SKU en minúsculas (`eme010-bro-m`), y 26 traen
  el mercado escrito de otra forma (`Spain` 10, `ESP` 9, `es` 7). Además hay 14
  líneas sin mercado.
- **Decisión:** SKU siempre a mayúsculas sin espacios; las 26 variantes se
  normalizan a `ES`; los 14 nulos pasan a `DESCONOCIDO`, **sin imputar**.
- **Reto:** 1 y 2.
- **Impacto:** sin la normalización de SKU se perderían 15 ventas en silencio al
  cruzar con el catálogo. Imputar los 14 mercados sería inventar dato por el 0,08 %.
- **Estado:** confirmado con el usuario.

### [2026-11-14] El SKU `EME999-BLA-M` se excluye del análisis
- **Contexto:** tiene 14 unidades de stock pero no existe en el catálogo y nunca
  se ha vendido.
- **Decisión:** se excluye (cruce `inner` con PRODUCTO) y se reporta con nombre y
  apellidos en las notas de calidad. Sin producto, color ni talla no se puede
  agregar por modelo ni calcular margen.
- **Reto:** 1 y 2.
- **Impacto:** 14 unidades de stock fuera del análisis. Es un aviso para almacén.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Las compras vencidas se marcan, no se descartan
- **Contexto:** 37 pedidos sin fecha real de llegada cuya fecha estimada ya pasó
  a la fecha de corte. Además, 427 de 555 entregas (77 %) llegaron tarde.
- **Decisión:** `clean.py` las marca con `esta_vencida` contra `FECHA_CORTE_DATOS`
  (no contra la semana de análisis, que es exclusiva del Reto 1). Qué hacer con
  ellas se decide en el Reto 2.
- **Reto:** 1 (se reporta) y 2 (se decide).
- **Impacto:** en el Reto 2, contarlas como stock en camino llevaría a reponer de
  menos para unidades que probablemente no lleguen.
- **Estado:** marcado; tratamiento pendiente de decidir en el Reto 2.

### [2026-11-14] `modelo_id` se construye con la referencia del SKU, no con el nombre
- **Contexto:** la regla 4 dice "modelo = producto + color". Agrupando por el
  **nombre comercial** aparecen 4 colisiones: productos distintos que comparten
  nombre y color. El caso más claro es `ECHO BOMBER OLIVE`, que es a la vez una
  chaqueta de **HOMBRE a 100 €** (ref. EME045, drop 2024-05) y una de **MUJER a
  140 €** (ref. EME076, drop 2024-03). También `NOVA JOGGER BROWN`,
  `RIOT OVERSIZE CREAM` y `VAPOR REGULAR BLACK`.
- **Opciones consideradas:** agrupar por nombre y aceptar la fusión. Descartada:
  creaba modelos inexistentes con dos secciones y dos precios, y contaminaba el
  sell-through y el margen de ambos.
- **Decisión:** `modelo_id` = **referencia del SKU + color** (`EME045-OLI`), que es
  el producto de verdad. Para mostrar, el nombre comercial; si dos modelos lo
  comparten, se desambigua añadiendo el drop.
- **Reto:** 1 y 2.
- **Impacto:** 119 → **123 modelos**. Sin esto, 4 modelos aparecerían fusionados en
  los rankings y en las alertas de stock.
- **Estado:** detectado al revisar los rankings; no lo vio el perfilado inicial.

### [2026-11-14] La ventana del forecast es de 4 semanas, elegida por backtesting
- **Contexto:** el negocio tiene una rampa estacional fuerte (de ~115 uds/semana en
  agosto a ~600 en octubre). Una ventana larga la persigue con retraso.
- **Decisión:** media móvil de **4 semanas**, excluyendo ventas a precio especial.
  Validado con backtesting de origen móvil sobre 13 cortes del último año:
  MAE 2,09 y sesgo +9,8 %, frente a MAE 2,05 y sesgo +20,1 % con 8 semanas. El
  error apenas cambia y el sesgo se reduce a la mitad.
- **Reto:** 1 (alertas de rotura) y 2 (reposición).
- **Impacto:** un sesgo ligeramente positivo es el lado correcto del error para
  reponer: cuesta menos tener stock de más que romper.
- **Estado:** validado con los datos.

### [2026-11-14] Un modelo está en rotura si le falta ALGUNA talla
- **Contexto:** agregando a modelo antes de comparar demanda y stock, la rotura
  desaparecía: ningún modelo rompía en conjunto, pero 43 SKUs sí.
- **Decisión:** la rotura se calcula a nivel de SKU y se agrega contando tallas
  afectadas. Un modelo con exceso de XL y cero de M está en rotura.
- **Reto:** 1 y 2.
- **Impacto:** de 0 modelos en rotura a **37 modelos / 43 tallas**.
- **Estado:** confirmado.

### [2026-11-14] El exceso de stock se prioriza por capital inmovilizado
- **Contexto:** con el umbral de cobertura (> 16 semanas, el doble del objetivo),
  **103 de 123 modelos** quedan marcados. Una lista de 103 no es accionable.
- **Decisión:** se mantiene el umbral para medir, pero la lista se ordena por
  **capital inmovilizado** = unidades por encima de la cobertura objetivo × coste.
- **Reto:** 1.
- **Impacto:** convierte una lista de 103 en un top accionable. Total:
  11.705 uds de exceso, **191.400 € a coste**.
- **Estado:** confirmado.

### [2026-11-14] La pregunta 2 se responde con el 0 % y con la estacionalidad
- **Contexto:** la semana analizada no tiene ni una venta a precio especial, y la
  del año pasado tampoco. Responder "0 %" a secas no aporta nada.
- **Decisión:** se responde que esta semana es 0 % **y** se muestra que el precio
  especial es estacional, concentrado en campañas (rebajas de enero, verano y
  Black Friday en noviembre de 2024). Se desglosa aparte la promoción `WELCOME10`,
  que sí está activa: 45 uds esta semana.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-14] El informe es un HTML autocontenido, no una aplicación
- **Contexto:** el entregable tiene que poder abrirlo dirección un lunes por la mañana.
- **Decisión:** un único fichero `.html` de ~5 MB con Plotly embebido, que se abre con
  doble clic. Sin servidor, sin `localhost`, sin conexión y sin nada que instalar.
  Se puede reenviar por correo tal cual.
- **Opciones consideradas:** un dashboard servido (Streamlit, Dash). Descartado para
  este reto: añade una dependencia operativa para un informe que se lee, no se opera.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-14] Paleta de un solo acento, validada con el validador de `dataviz`
- **Contexto:** dirección estética tipo Apple: sobrio, un único color de acento, y
  verde/rojo reservados a las variaciones.
- **Decisión:** acento `#0071e3` en claro y `#0a84ff` en oscuro. Los seis checks del
  validador pasan contra las dos superficies reales (`#fbfbfd` y `#161617`).
  La mayoría de los gráficos son de **una sola serie**, así que el color no codifica
  identidad. Donde hay dos series (curva de tallas, estacionalidad) se usa el patrón
  de énfasis: la serie de contexto en gris y la relevante en el acento, siempre con
  leyenda y etiquetas directas.
- **Nota sobre el verde y el rojo:** ningún par rojo/verde supera la separación para
  daltonismo, y este tampoco. Es aceptable porque **nunca van solos**: siempre llevan
  flecha ▲▼ y el número con signo, que es la codificación secundaria exigida.
- **Reto:** 1.
- **Estado:** validado con herramienta.

### [2026-11-14] La tabla de rotura muestra las cifras de las tallas afectadas
- **Contexto:** la primera versión mezclaba el stock del modelo entero con el déficit
  de las tallas en rotura, así que el lector no podía comprobar la resta.
- **Decisión:** se muestran `stock en esas tallas`, `en camino a esas tallas` y
  `demanda 4 sem` de las tallas afectadas, de modo que
  `déficit = demanda − stock − en camino` cuadra a la vista. El stock del modelo se
  mantiene en una columna aparte, precisamente porque es el número que engaña.
- **Reto:** 1.
- **Estado:** confirmado.

### [2026-11-16] La entrega es una web navegable por páginas, no un scroll continuo
- **Contexto:** con solo el Reto 1 el informe ya era un scroll muy largo, y los tres
  retos tienen que convivir en el mismo entregable.
- **Decisión:** menú lateral fijo con los apartados agrupados por reto, y un panel
  visible cada vez. Los tres retos son grupos del menú; **glosario, asunciones y
  decisiones quedan fuera de cualquier reto**, en un grupo "Referencia", porque valen
  para los tres por igual. Los retos 2 y 3 ya figuran en el menú marcados como
  pendientes: la estructura se ve completa desde el principio.
- **Detalles de implementación:** todos los paneles están en el DOM y solo uno es
  visible, así que sigue siendo un único fichero. La navegación usa el hash de la URL
  (`#stock`), de modo que se puede enlazar un apartado concreto y el botón «atrás» del
  navegador funciona. Un gráfico de Plotly dibujado dentro de un contenedor oculto no
  conoce su ancho, así que al mostrar un panel se redimensionan los suyos. Al imprimir
  se muestran todos los paneles, uno por página.
- **Reto:** transversal.
- **Estado:** confirmado con el usuario.
