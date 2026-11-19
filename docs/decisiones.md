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

### [2026-11-16] La variación interanual va en un panel propio, no en un segundo eje
- **Contexto:** hace falta ver el YoY en el gráfico de evolución, junto a las dos
  series (este año y el anterior).
- **Opciones consideradas:** un segundo eje vertical con el porcentaje sobre las
  mismas líneas. **Descartada**: la alineación entre dos escalas es arbitraria, así
  que un gráfico de doble eje inventa correlaciones que no están en el dato.
- **Decisión:** dos paneles con el mismo eje de tiempo. Arriba las dos series en su
  unidad; abajo la variación interanual en barras, con su propio eje en porcentaje.
  Además, el tooltip de la línea de este año incluye la variación, que es la pregunta
  que uno se hace justo al comparar las dos series.
- **Color:** verde para subidas y rojo para bajadas, siempre con el signo delante para
  que el color no sea el único portador. La muestra de la leyenda va partida en dos
  colores, que es lo honesto para una serie que cambia de color según el signo.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] El precio especial se apila sobre el precio completo
- **Contexto:** el gráfico de estacionalidad dibujaba el total en gris y el precio
  especial superpuesto en azul, con la misma anchura. Dos barras del mismo ancho
  superpuestas se leen como **dos series independientes**, y no lo son: el azul
  estaba contenido en el gris.
- **Decisión:** barras apiladas, con el tramo a precio completo abajo y el especial
  encima. Los dos trozos suman el total del mes, que es la relación real. La serie
  pasa a ser «a precio completo», no «total», para que no quepa la duda, y el
  tooltip muestra además el total.
- **Reto:** 1.
- **Impacto:** no cambia ninguna cifra, solo cómo se leen. Evita interpretar el
  gris como «ventas distintas de las rebajadas» cuando en realidad las incluía.
- **Estado:** detectado por el usuario al leer el gráfico.

### [2026-11-16] Los ejes de los gráficos usan separadores españoles
- **Contexto:** Plotly formatea en inglés por defecto y los ejes ponían
  «40,000 €» donde el resto del informe pone «40.000 €».
- **Decisión:** `separators=",."` en la plantilla de gráficos: coma decimal y punto
  para los miles, igual que el texto y las tablas.
- **Reto:** transversal.
- **Estado:** confirmado.

### [2026-11-16] Las marcas del eje temporal se desplazan seis horas
- **Contexto:** el tooltip del gráfico de evolución ponía «sep» como encabezado en
  lugar de la semana. No era un error de datos: cuando el punto señalado coincide
  **exactamente** con una marca del eje, Plotly usa la etiqueta de la marca como
  encabezado en vez del formato de hover. Las marcas son inicios de mes y las
  semanas empiezan en lunes, así que la semana del 1 de septiembre de 2025 caía
  justo encima. Lo mismo pasaba en el gráfico mensual, donde el encabezado perdía
  el año («ago» sin saber de cuál de los dos).
- **Decisión:** desplazar las marcas del eje seis horas. Sobre un eje de 26 semanas
  el desplazamiento es imperceptible y el encabezado pasa a usar el formato de hover:
  «Semana del 01/09/2025» y «08/2025».
- **Reto:** 1.
- **Impacto:** ninguna cifra cambia. Es legibilidad del tooltip.
- **Estado:** detectado por el usuario.

### [2026-11-16] Las series de venta incluyen el precio especial; la demanda prevista no
- **Contexto:** dos criterios opuestos conviven en el informe y no se deducía mirando.
- **Decisión:** los KPIs, la evolución semanal y los desgloses son **venta total**,
  con el precio especial dentro: la pregunta del enunciado es cuánto se vendió, no
  cuánto se vendió a tarifa. El reparto entre completo y especial se analiza aparte,
  en la pregunta 2. En cambio la **demanda prevista lo excluye**, porque una
  liquidación no es demanda recurrente e inflaría la previsión de un producto que ya
  no se vende a tarifa.
- **Comprobación:** en la ventana del gráfico el precio especial es el 11,4 % de las
  unidades este año y el 11,3 % el anterior, así que la comparación interanual es
  homogénea. Se calcula con el dato y se imprime en el informe, no se afirma a mano.
- **Reto:** 1 y 2.
- **Estado:** confirmado; se hace explícito en el gráfico y en Asunciones a raíz de
  la pregunta del usuario.

### [2026-11-16] El precio especial queda fuera de todo el análisis comercial
- **Contexto:** hasta ahora las series de venta lo incluían y solo el forecast lo
  excluía. Dos criterios opuestos en el mismo informe.
- **Decisión:** se unifica **excluyéndolo de todo**: KPIs, evolución semanal,
  desgloses, rankings, concentración, curva de tallas, previsión y alertas de stock
  usan `metrics.solo_tarifa`. El precio especial se analiza aparte, en la pregunta 2,
  que es donde el enunciado lo pide. El filtro vive en **una sola función** y el
  orquestador decide qué tabla recibe cada métrica.
- **Motivo:** el precio especial es liquidación de campaña. Mezclarlo hace que una
  semana de rebajas parezca una buena semana de venta y la vuelve incomparable con
  una semana normal.
- **Excepción declarada: el sell-through sí lo incluye.** Mide salida física de
  almacén, no resultado comercial: una unidad rebajada salió del almacén igual que
  una vendida a tarifa, y el denominador usa el stock actual, que ya refleja esa
  salida. Excluirla daría un sell-through artificialmente bajo e incoherente consigo
  mismo. Lo mismo para el sell-through por drop.
- **Impacto medido:** las tres semanas de la comparativa **no cambian** (ninguna tuvo
  ventas a precio especial). Sí cambian las nueve semanas de campaña de julio y
  agosto, que caen a la mitad: la meseta de verano era rebajas, no venta ordinaria.
  Sobre el histórico completo: 19.727 → 17.867 unidades y margen del 71,5 % al 72,6 %.
- **Reto:** 1 y 2.
- **Estado:** confirmado con el usuario.

### [2026-11-16] El descuento del cupón se resta una sola vez, en la facturación
- **Contexto:** el nombre «a precio completo» inducía a pensar que la facturación se
  registra a tarifa y el descuento se descuenta después, en el margen.
- **Aclaración:** no es así. `facturacion_neta = unidades × PVP − descuento` ya va
  neta de **todos** los descuentos de la línea, el cupón incluido, y el margen se
  calcula sobre esa cifra. El descuento no se resta dos veces. El efecto del cupón se
  ve en el margen **porcentual**, que baja porque la facturación cae y el coste no.
- **Medido en la semana:** las líneas con cupón dejan un **70,8 %** de margen frente
  al **73,0 %** de las que no lo llevan. El cupón deja de ingresar **333 €** sobre
  34.826 € de facturación.
- **Decisión:** se añade al informe la columna «descuento dado» por mercado y la
  comparación de márgenes, para poder ponerle precio al cupón. Y se aclara que
  «a precio completo» es una etiqueta de canal —todo lo que no es liquidación— e
  incluye las ventas con cupón.
- **Reto:** 1.
- **Estado:** aclarado a raíz de la pregunta del usuario; no cambia ningún cálculo.

### [2026-11-16] «Precio medio por unidad» pasa a llamarse «facturación por unidad»
- **Contexto:** el nombre sugería precio de venta, y no lo es: se calcula como
  `facturación neta ÷ unidades`, así que ya va neto de descuentos y además mezcla
  el reparto de producto. Un cambio en esa cifra puede no tener nada que ver con los
  precios.
- **Decisión:** renombrarlo a **facturación por unidad** y acompañarlo de la
  descomposición entre efecto precio y efecto mezcla, recalculando el periodo actual
  con el reparto por categoría del periodo de referencia.
- **Hallazgo:** el +11,6 % interanual **no es subida de precios**. Con la mezcla de
  2024 la cifra habría *bajado* un 5,5 %. Lo que ha cambiado es qué se vende: la
  chaqueta pasa del 10,8 % al 29,7 % de las unidades y es la categoría más cara
  (116 € de media frente a 32 € de una camiseta). Es noviembre.
- **Reto:** 1.
- **Estado:** aclarado a raíz de la pregunta del usuario.

### [2026-11-16] El peso del cupón se muestra con sus dos bases
- **Contexto:** la columna «Con WELCOME10» iba junto a una columna de unidades, y se
  leía como «este porcentaje de las unidades». Era **sobre facturación**. En España,
  8,6 % de la facturación frente a 7,7 % de las unidades; en Alemania la brecha es
  mayor: 14,4 % frente al 17,0 %.
- **Motivo de la diferencia:** el cupón no se reparte igual entre producto caro y
  barato, así que el peso en euros y en unidades no coincide.
- **Decisión:** la tabla muestra las unidades con cupón en bruto y el porcentaje
  etiquetado explícitamente como «% fact. con cupón». Se descarta añadir también el
  porcentaje sobre unidades: con las dos cifras al lado se deduce, y la tabla ya no
  cabía en el ancho de la página.
- **Cómo se calcula el descuento:** no se recalcula. Es la columna `Descuento (€)`
  del dato original, sumada sobre las líneas con cupón. Son exactamente el 10 % del
  importe de tarifa de esas líneas.
- **Reto:** 1.
- **Estado:** aclarado a raíz de la pregunta del usuario.

### [2026-11-16] Los rankings de modelos van por media de 4 semanas, no por la semana suelta
- **Contexto:** el ranking ordenaba por las unidades de la semana analizada. Con 509
  unidades repartidas entre 123 modelos, el décimo y el trigésimo se diferencian en
  dos unidades: un buen modelo con una mala semana caía a la cola.
- **Decisión:** se ordena por **media de las últimas 4 semanas**, la misma ventana
  que usa la previsión de demanda, de modo que las dos cifras del informe son
  consistentes. La columna de la semana se mantiene al lado: es un informe semanal y
  conviene ver quién se sale de su propio ritmo (`UNIFORM JOGGER OLIVE` promedia 10,8
  y esta semana vendió 5).
- **Efecto colateral útil:** la tabla de «modelos con stock y sin ninguna venta» pasa
  de 14 modelos a **1**. En una semana no vender es normal; en cuatro, no.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] El ranking de modelos se ordena por ritmo reciente, con el año como contexto
- **Contexto:** la pregunta 3 pide «los 10 modelos que más y que menos venden». Había
  tres candidatos para medirlo y se compararon con los datos.
- **Descartado, la semana suelta:** con 509 unidades repartidas entre 123 modelos, el
  décimo y el trigésimo se diferencian en dos unidades.
- **Descartado, el acumulado del año:** penaliza sistemáticamente a los drops
  recientes. **28 de los 123 modelos llevan ocho semanas o menos a la venta y ninguno
  puede entrar en el top 10 del año.** El modelo que más vende ahora mismo,
  `NOVA BOMBER BROWN` con 27 uds/semana, lleva 5 semanas y en el acumulado sería el
  **25.º**. En una marca que lanza seis drops al año, ordenar por acumulado es ordenar
  por antigüedad.
- **Decisión:** ordenar por el **ritmo de las últimas 4 semanas**, la misma ventana
  que la previsión de demanda. El año entra como **contexto**, no como orden: unidades
  acumuladas y un índice «ritmo actual ÷ ritmo medio del modelo en el año», que es lo
  que de verdad responde si un modelo tira o se desinfla.
- **Salvaguarda:** el índice solo se calcula con ocho o más semanas a la venta. Por
  debajo, la media del año y el ritmo reciente son casi el mismo dato y el índice
  daría ×1 sin significar nada; esos modelos se marcan como «nuevo».
- **Lo que destapa:** `NEON CREWNECK NAVY` es top 10 del año y va a ×0,63;
  `BLAZE BOMBER GREY MELANGE` lleva 70 uds en el año y va a ×0,12. Vendieron, ya no.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] El top de modelos se ofrece con dos lecturas, y la semana es la de entrada
- **Contexto:** el informe es semanal y lo más vendido de la semana tiene que estar sí
  o sí. Ordenar solo por ritmo lo escondía.
- **Decisión:** el top lleva un selector con dos vistas pre-renderizadas, **«Esta
  semana»** por defecto y «Ritmo · últimas 4 semanas» a un clic. Las dos muestran las
  mismas columnas, así que se comparan sin esfuerzo.
- **Coste real de la duda:** ninguno. Los dos top 10 **coinciden en nueve de diez**;
  la única diferencia es `RIOT OVERSIZE BROWN` (semana) frente a `UNIFORM JOGGER
  OLIVE` (ritmo). Discutíamos un puesto.
- **La cola se queda solo por ritmo:** esta semana hay **28 modelos empatados a una
  unidad**, así que un «bottom 10» semanal sería un recorte arbitrario de ese empate.
  Se dice en la propia tabla.
- **Implementación:** dos tablas en el DOM y un selector que alterna cuál se ve. No se
  reordena en el cliente: el orden lo decide Python, que es donde está el criterio.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] Se descarta el índice de ritmo: una tabla, ordenada por la semana
- **Contexto:** el ranking llegó a tener dos pestañas (semana / ritmo de 4 semanas) y
  una columna «ritmo vs. su año» con un multiplicador. El usuario no lo entendía.
- **Decisión:** se elimina. Una sola tabla, **ordenada por las unidades de la
  semana**, que es lo que un informe semanal tiene que responder. El contexto pasa a
  ser tres cifras que se leen sin explicación: la **semana anterior**, lo vendido
  **en el año** y el stock, además del sell-through que pide el enunciado.
- **Criterio general:** si una columna hay que explicarla en una nota, la columna no
  sirve en un informe que se lee en cinco minutos un lunes. Prefiero cuatro cifras
  literales a un índice que resume bien y se entiende mal.
- **Lo que se pierde y no importa:** el índice detectaba modelos desinflándose
  (`NEON CREWNECK NAVY` a ×0,63). Comparando «esta semana» con «semana anterior» y
  con «en el año» se ve lo mismo sin aprender nada nuevo.
- **La cola:** sigue habiendo muchos empates a una unidad, así que entre ellos ordena
  lo vendido en el año. Ahora saca modelos con sell-through del 7 %, que es la señal
  que importa.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] «Más allá del enunciado» se reduce a tres hallazgos, uno por gráfico
- **Contexto:** la sección tenía cinco insights, cada uno con gráfico **y** tabla
  diciendo lo mismo, más varios párrafos.
- **Se eliminan dos por duplicados:** el origen del crecimiento interanual ya está
  desglosado en la pregunta 1 y la concentración del catálogo en la pregunta 3.
  Repetirlos alargaba sin añadir.
- **Se eliminan las tablas:** si el gráfico ya lo dice, la tabla sobra. Queda una
  frase de conclusión, un gráfico y una nota con la acción.
- **Curva de tallas:** de dos series de porcentajes a **una sola de desvío**, con el
  cero en medio. Antes había que restar mentalmente «30,1 % de demanda» menos
  «22,6 % de stock»; ahora la resta está hecha y se lee «faltan 1.240 M».
  Un solo color: ni sobrar ni faltar es bueno, así que verde y rojo mentirían.
- **Proveedores:** la etiqueta de cada barra pasa a llevar también el retraso medio
  en días, que es el número accionable.
- **Drops:** etiquetas del eje en dos líneas en vez de giradas 45°.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] Revisión de coherencia del Reto 1
Repaso sistemático de lo entregado frente a lo que pide el enunciado. Los hallazgos
y lo que se hizo con cada uno:

1. **Faltaba responder literalmente a «qué parte se vendió a precio especial».**
   Al excluir el precio especial de todo el análisis, el informe dejó de decir cuánto
   pesa. Se añade una tabla en la pregunta 2 con la semana, el año en curso y el
   histórico: 0 % esta semana, **10,1 % de las unidades y 6,2 % de la facturación en
   2025**. La diferencia entre ambos porcentajes es el propio descuento.
2. **Dos de las cuatro páginas de respuesta no tenían ningún gráfico**, y el enunciado
   dice que valorará que el informe sea lo más visual posible. Se añade un gráfico de
   barras a la pregunta 3 (top 10 de la semana) y otro a la pregunta 4 (capital parado).
   Ahora todas las páginas de respuesta tienen al menos uno.
3. **Métricas calculadas y nunca mostradas:** `resumen_semanal` y `sin_rotacion`. La
   primera se sustituye por la tabla del punto 1; la segunda se elimina. `rotura_por_sku`
   se conserva aunque no se muestre: es el detalle por talla que respalda la tabla por
   modelo.
4. **Ficheros huérfanos en `data/processed`:** quedaban parquets de métricas ya
   eliminadas del código. El pipeline vacía el directorio antes de escribir.
5. **Cifras escritas a mano que podían quedarse obsoletas:** «37 modelos» y «123
   modelos y 579 SKUs» pasan a calcularse del dato.
6. **`notas_calidad_datos.md` decía 119 modelos** cuando el informe dice 123. La
   documentación contradecía al entregable; corregido.

**Comprobado y correcto:** las cuatro preguntas y sus piezas obligatorias están; el
hero cuadra con los tres desgloses al céntimo; el stock de la pregunta 3 coincide con
el de la 4 y con la tabla limpia; `demanda − stock − en camino = déficit` en las 37
filas de rotura; `stock − demanda × 8 = uds sobrantes` y `× coste = capital parado`;
el cuadre de limpieza 18.292 = 17.708 + 559 + 25; y los descuentos citados en el texto
(100 % regalo, 40 % especial, 10 % cupón) salen del dato.

### [2026-11-16] El gráfico de la pregunta 3 pasa a ser un mapa del catálogo
- **Contexto:** se había añadido un gráfico de barras del top 10 para que la página no
  fuese solo tablas. Decía exactamente lo mismo que la tabla de al lado.
- **Decisión:** sustituirlo por un **mapa de dispersión** con los 123 modelos: unidades
  de la semana en el eje X, sell-through en el Y, y el **tamaño del punto igual al
  stock** que queda. Es lo único que las tablas no pueden enseñar: dónde está cada
  modelo respecto al resto. Un top 10 ordenado no dice si el décimo está cerca del
  primero o del montón.
- **Lo que destapa:** **17 modelos** caen en la esquina de poca venta y poca rotación,
  con **1.920 unidades** inmovilizadas entre todos. Al escalar el punto por stock, los
  problemas pesan visualmente: un punto grande abajo a la izquierda es mucho producto
  parado que además no se vende.
- **Color:** acento para el catálogo y rojo para esa esquina. Es énfasis, no identidad,
  y la línea del umbral más la nota dicen lo mismo que el color.
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-16] El gráfico de la pregunta 4 pasa a ser la composición del stock
- **Contexto:** el gráfico de barras del capital parado repetía la primera columna de
  la tabla de al lado. Mismo problema que en la pregunta 3.
- **Decisión:** sustituirlo por el **reparto de los 123 modelos entre los cuatro
  estados posibles** de stock, con las unidades de cada grupo.
- **Lo que destapa, y es el hallazgo de la página:** rotura y exceso no son opuestos.
  **28 de los 37 modelos en rotura están también en exceso**: una talla a cero y otra
  con stock para meses, 3.417 unidades entre todos. Es la demostración numérica de
  que el problema no es cuánto stock hay sino cómo está repartido, que hasta ahora
  solo se afirmaba.
- **Tarjetas del encabezado:** las etiquetas eran demasiado escuetas para números que
  no se explican solos. «semanas de cobertura» pasa a «semanas que aguanta ese stock
  al ritmo de venta previsto, sin reponer nada; EME quiere tener 8», y «modelos en
  rotura» a «modelos a los que les faltará alguna talla dentro de 4 semanas».
- **Reto:** 1.
- **Estado:** confirmado con el usuario.

### [2026-11-17] La previsión del Reto 2 se hace por categoría y se reparte a SKU
- **Contexto:** a nivel de SKU la demanda semanal es ruido: 0,79 uds de media, el
  62 % de las semanas a cero y un ruido relativo de 1,90. A nivel de sección ×
  categoría son 21,47 uds/semana, 6,4 % de ceros y ruido 0,96.
- **Opciones consideradas:** un modelo por SKU (descartado: no hay datos por serie,
  mediana de 34 semanas de vida) y un modelo global que prediga directamente el
  SKU (descartado tras medir, ver más abajo).
- **Decisión:** se predice el **nivel** por sección × categoría y se **reparta** a
  SKU en dos pasos: share del modelo dentro de su categoría (estable, r = 0,77) y
  curva de tallas encogida hacia la de su categoría.
- **Evidencia:** regalando al método el total de categoría REAL (oráculo), sobre 4
  cortes: el método anterior daba MAE 3,72 y sesgo absoluto 44,1 %; con el total
  correcto, 3,14 y 7,9 %. **Casi todo el error era de nivel, no de reparto.**
  Refinar el reparto con encogimiento solo mejora de 3,14 a 3,06 (2 %).
- **Clave:** sí
- **Reto:** 2.
- **Impacto:** todo el esfuerzo de modelado va al nivel; el reparto se mantiene
  deliberadamente simple. Arregla además la curva de tallas que el Reto 1 dejó
  marcada como pendiente.
- **Estado:** validado con los datos.

### [2026-11-17] Las semanas con el producto agotado no cuentan como demanda cero
- **Contexto:** una semana sin ventas puede ser "nadie lo quería" o "estaba
  agotado", y en los datos las dos se ven igual: un cero. Contarlas juntas castiga
  a los productos que se agotan porque funcionan bien.
- **Decisión:** `clean.reconstruir_stock_semanal` reconstruye el stock semana a
  semana caminando hacia atrás desde la foto de cierre
  (`stock(t-1) = stock(t) − entradas(t) + salidas(t)`), **contando los regalos a
  influencers como salida** porque vacían el almacén aunque no sean venta. La
  demanda se calcula solo sobre las semanas con producto disponible.
- **Evidencia:** acotado a la vida comercial de cada SKU, el 4,9 % de las semanas
  sin venta eran roturas, en 45 SKUs de 579. La reconstrucción cuadra en el 97,5 %
  de las semanas; donde sale negativa se marca como no fiable.
- **Clave:** sí
- **Reto:** 2.
- **Impacto:** modesto en el agregado, grande en los 45 SKUs afectados.
- **Estado:** validado con los datos. Limitación: el Excel no recoge devoluciones,
  mermas ni ajustes de inventario, de ahí el 2,5 % que no cuadra.

### [2026-11-17] El método de previsión se elige por backtesting, no por criterio
- **Contexto:** hay cuatro candidatos razonables y ninguna razón a priori para
  preferir uno.
- **Decisión:** se comparan los cuatro con validación de origen móvil —entrenando
  solo con datos anteriores a cada corte— y se usa el que gana. La tabla viaja
  hasta el entregable.
- **Evidencia (12 cortes, horizonte 14 semanas):**

  | método | MAE | sesgo absoluto |
  |--------|-----|----------------|
  | modelo entrenado | **6,02** | **24,9 %** |
  | media móvil plana | 6,36 | 37,9 % |
  | media móvil estacional | 6,37 | 38,3 % |
  | mismas semanas del año anterior | 6,91 | 38,0 % |

- **Clave:** sí
- **Reto:** 2.
- **Impacto:** se usa el modelo entrenado. Si en una ejecución futura dejara de
  ganar, el pipeline cambiaría de método solo.
- **Estado:** validado con los datos.

### [2026-11-17] El error se mide en valor absoluto, no con signo
- **Contexto:** `forecast.evaluar_forecast` promediaba el sesgo con signo. A 14
  semanas los sesgos por corte son −62 %, −56 %, +11 %, +27 %, +46 %, +52 %, +70 %
  y +103 %: promediados dan +23,7 %, y desplazando los cortes tres semanas dan
  +6,4 %. El número no medía nada.
- **Decisión:** se reporta el **sesgo absoluto** como métrica principal, junto al
  MAE. El sesgo con signo se mantiene como dato secundario, porque sí dice hacia
  qué lado se tiende a fallar.
- **Reto:** 2.
- **Impacto:** el método anterior pasa de parecer un +23,7 % a ser un 44,1 % de
  error real sobre el total.
- **Estado:** confirmado.

### [2026-11-17] La necesidad se calcula a 14 semanas (6 de plazo + 8 de cobertura)
- **Contexto:** el pedido que se lanza hoy llega en 6 semanas y debe durar 8, así
  que responde de la demanda de las próximas 14.
- **Decisión:** `necesidad = demanda(14 semanas) − stock disponible − compras que
  llegan dentro de esas 14 semanas`, con suelo en cero y redondeo al alza.
- **Advertencia registrada:** esas 14 semanas **cruzan dos realidades comerciales
  distintas**. Con la fecha de corte del caso van del 16-nov al 15-feb: siete
  semanas de campaña de Navidad (191–314 uds/semana el año pasado) y siete de
  enero-febrero a una sexta parte del ritmo (34–60). Además, las últimas caen en
  rebajas: comprar a coste completo para vender con descuento es un error caro.
  En producción el horizonte debería acotarse al final de la temporada comercial.
- **Clave:** sí
- **Reto:** 2.
- **Impacto:** proyectar plano sobre esa ventana daba 7.606 uds frente a las 3.109
  reales del año anterior. Era el origen del sobrepedido.
- **Estado:** parámetro del enunciado, respetado. La acotación por temporada queda
  propuesta, no aplicada.

### [2026-11-17] Las compras vencidas sin confirmar no cuentan como stock en camino
- **Contexto:** 37 pedidos sin fecha real cuya estimada ya pasó. El Reto 1 los
  marcó y dejó la decisión para el Reto 2.
- **Decisión:** no cuentan como stock en camino, y salen en una pestaña propia para
  que Compras las reclame al proveedor. Es el mismo criterio que
  `metrics.alertas_stock`, para que las dos cifras puedan mirarse juntas.
- **Clave:** sí
- **Reto:** 2.
- **Impacto:** contarlas llevaría a reponer de menos para unidades que
  probablemente no estén.
- **Estado:** confirmado.

### [2026-11-17] No se inventa lote mínimo de proveedor, y los SKUs parados no se reponen
- **Decisión:** `UNIDADES_MINIMAS = 1` queda como parámetro configurable: el lote
  mínimo no está en los datos y no se simula. Los SKUs sin ventas recientes no se
  reponen, pero **no desaparecen**: salen en la pestaña "Sin rotación" ordenados
  por capital inmovilizado, porque son candidatos a rebaja o fin de vida y esa
  decisión también es de Compras.
- **Clave:** sí
- **Reto:** 2.
- **Estado:** confirmado.

### [2026-11-17] El Reto 1 conserva su método de previsión
- **Contexto:** el nuevo motor (`demand.py`) es mejor, pero el Reto 1 ya está
  entregado y sus alertas de rotura usan `forecast.py` a 4 semanas, horizonte en el
  que el problema del sesgo es mucho menor.
- **Decisión:** no se tocan las cifras del Reto 1. `forecast.py` se mantiene para el
  Reto 1 y `demand.py` es el motor del Reto 2.
- **Reto:** 1 y 2.
- **Impacto:** evita cambiar en silencio cifras ya presentadas. Queda como mejora
  pendiente unificar los dos retos bajo el motor nuevo.
- **Estado:** confirmado con el usuario.

### [2026-11-17] El servicio se despliega en Cloud Run con un reloj diario
- **Contexto:** el enunciado pide un proceso automático y un esquema de producción.
- **Decisión:** el proceso corre como servicio en Cloud Run, disparado por Cloud
  Scheduler **cada día a las 00:00 (Europe/Madrid)**, y escribe la propuesta en un
  Google Sheet fijo. En producción la frecuencia natural sería semanal, los lunes
  a primera hora; el diario es para poder verlo funcionar durante la evaluación.
- **Credenciales:** no existe ninguna clave descargada. El servicio corre *como* su
  cuenta de servicio y en local se usa impersonación. Detalle en
  `docs/reto2_infraestructura.md`.
- **Reto:** 2.
- **Estado:** confirmado.

### [2026-11-18] El stock parado se detecta por ventas observadas, no por demanda prevista
- **Contexto:** al pasar la previsión a jerárquica (se predice la categoría y se
  reparte), **ningún SKU tiene ya demanda prevista cero**: hasta un producto parado
  recibe una fracción del total de su categoría. La lista de "sin rotación", que se
  definía como demanda prevista cero, se quedó vacía de golpe.
- **Decisión:** el stock parado se identifica con las **unidades realmente vendidas**
  en las últimas 13 semanas (columna `uds_recientes`), no con la previsión.
- **Reto:** 2.
- **Impacto:** recupera la detección de **41 SKUs con 1.000 uds y 19.276 € de capital
  inmovilizado**, que con la definición anterior habrían desaparecido del entregable.
- **Estado:** confirmado. Es un efecto secundario del cambio de método que no estaba
  previsto y que solo se vio al revisar la salida.

### [2026-11-18] El entregable se reduce a tres pestañas y once columnas
- **Contexto:** la primera versión sacaba seis pestañas y diecinueve columnas. Un
  entregable así no se revisa: se cierra.
- **Decisión:** tres pestañas —**Propuesta** (sobre lo que hay que actuar),
  **Revisar** (lo que necesita una persona pero no es un pedido) y **Cómo se ha
  calculado**— más el histórico de ejecuciones que escribe el servicio. La propuesta
  pasa de 19 a 11 columnas.
- **Reto:** 2.
- **Impacto:** las tablas completas siguen en `data/processed/` para auditar; lo que
  se recorta es el entregable, no el cálculo.
- **Estado:** confirmado con el usuario.

### [2026-11-18] El Reto 3 son cinco páginas del mismo informe, no un documento aparte
- **Contexto:** el menú lateral del informe ya reservaba un hueco al Reto 3 marcado
  como «pendiente». La hoja de ruta podía entregarse como documento suelto o como
  parte de la web que ya existe.
- **Opciones consideradas:** (a) un HTML independiente en `output/reto3/`, que
  obligaría a duplicar el sistema de diseño y a abrir dos ficheros en la defensa;
  (b) solo el markdown de `docs/`, que no permite ni matriz ni calendario visuales.
- **Decisión:** el Reto 3 se integra como **cinco páginas** del informe, con el mismo
  `design.py`, la misma navegación y la misma paleta. Una sola entrega con los tres
  retos. El markdown de `docs/reto3_roadmap_ia.md` se **genera** desde las mismas
  estructuras de datos (`src/roadmap.py`), nunca se escribe a mano.
- **Reto:** 3.
- **Impacto:** `src/report.py` monta ahora 13 páginas; `pipelines/run_reto3.py`
  regenera el documento y los CSV de `output/reto3/`.
- **Estado:** decidido.

### [2026-11-18] Cada iniciativa declara si la IA construye o si la IA ejecuta
- **Contexto:** «hoja de ruta de IA» se lee por defecto como «meter un LLM en cada
  proceso». En una marca de este tamaño la mayor parte del valor no está ahí.
- **Decisión:** las iniciativas se etiquetan con **tipo A** (la IA escribe el código;
  en producción corre lógica determinista y auditable), **tipo B** (la IA está dentro
  del proceso: lenguaje, voz o modelo) y **tipo C** (la IA en manos del propio equipo,
  que es la palanca de adopción y no compite en la matriz). De las doce, **solo cinco
  son B**.
- **Por qué importa:** es lo que evita el error caro de poner un modelo de lenguaje
  donde basta una resta, y es lo que explica que quepan doce iniciativas en seis meses
  y no tres.
- **Reto:** 3.
- **Impacto:** la tabla de iniciativas y la forma de los puntos de la matriz
  (círculo = A, rombo = B).
- **Estado:** decidido.

### [2026-11-18] El esfuerzo se mide en semanas hasta producción, no en desarrollo
- **Contexto:** si el código lo escribe un agente, medir el esfuerzo en semanas de
  programar deja de tener sentido y desordena toda la priorización.
- **Decisión:** el eje de esfuerzo de la matriz son **semanas hasta estar en
  producción**, e incluyen conseguir el acceso al dato, acordar quién valida el
  resultado y las vueltas con el usuario hasta que lo usa de verdad.
- **Consecuencia poco intuitiva:** el agente de atención al cliente (iniciativa 6)
  sale caro no por su complejidad técnica, sino porque necesita conectar pedidos y
  seguimiento de envíos; y queda fuera de las victorias rápidas por eso.
- **Reto:** 3.
- **Impacto:** el eje X de la matriz y el orden del calendario.
- **Estado:** decidido.

### [2026-11-18] El impacto separa ahorro recurrente de capital liberado una sola vez
- **Contexto:** la iniciativa con más euros detrás (liquidar el exceso) libera capital
  una vez; el resto ahorra horas y errores todos los años. Sumarlo todo en una cifra
  habría dado un número grande y falso.
- **Decisión:** dos columnas separadas, **75.700 €/año recurrentes** y **35.300 € de
  capital liberado una vez**, y nunca se suman. Además, dos iniciativas (la 7 y la 10)
  se declaran **habilitadoras** y no se les imputa euro propio, porque su retorno ya
  está contado en la 9 y en la 4 respectivamente.
- **Reto:** 3.
- **Impacto:** las tarjetas de cabecera de la página de iniciativas y el eje Y de la
  matriz, que usa euros del primer año.
- **Estado:** decidido.

### [2026-11-18] Las cifras de la hoja de ruta se recalculan desde las tablas del Reto 1
- **Contexto:** la primera versión leía `reto2_propuesta.parquet` y `reto2_sin_rotacion.parquet`,
  y el informe dejaba de generarse si no se había ejecutado antes el pipeline del Reto 2.
- **Decisión:** `roadmap.cifras_de_partida()` solo usa `data/interim` y las métricas del
  Reto 1. El stock muerto se redefine como **SKUs con existencias y ninguna venta en los
  últimos 12 meses** (21 SKUs, 9.969 €), y la venta en riesgo pasa a **margen en riesgo**
  (249 uds de déficit × 42,1 € de margen medio ≈ 10.500 €).
- **Reto:** 3.
- **Impacto:** las cifras de las iniciativas 1 y 3. `python pipelines/run_reto1.py` vuelve
  a bastar por sí solo para generar el informe completo.
- **Estado:** corregido y verificado.

### [2026-11-18] Pasada de estilo sobre los tres retos: menos texto y voz propia
- **Contexto:** el texto de los tres entregables se leía como escrito por un modelo.
  Se revisó con `copy-tells.md` y `copy-voice.md` de la skill `taste-skill`
  (github.com/leonxlnx/taste-skill), que cataloga los tics que delatan a un modelo.
- **Qué se encontró:** contrastes «no X, sino Y» y «X, no Y» en cada sección; dos puntos
  reveladores («el problema es la fecha, no ellos»); frases de cierre con efecto («Una
  herramienta que se abandona cuenta como no entregada»); adjetivos sobre el propio texto
  («incómodo a propósito», «conservador»); y párrafos que hablaban del informe en vez de
  hablar del negocio («Plegadas. Dentro está…», «conviene enseñar…»).
- **Decisión:** se reescribe la prosa de los tres retos con una voz fija: frases de 8 a 16
  palabras, el dato como sujeto, sin cierres de efecto y sin que el texto se describa a sí
  mismo. Las notas de más de 50 palabras se recortan a la mitad.
- **Reto:** transversal.
- **Impacto:** el informe pasa de 9.869 a 8.600 palabras sin perder ninguna cifra ni ninguna
  decisión. Afecta a `src/report.py`, `src/roadmap.py` y `service/vista.py`.
- **Estado:** aplicado.

### [2026-11-19] La página de decisiones del Reto 2 muestra solo seis
- **Contexto:** la página listaba las 13 decisiones del log que tocan al Reto 2, incluidas
  las de formato del entregable y la del estilo del texto. Nadie las lee.
- **Decisión:** se marcan en `docs/decisiones.md` con un campo `Clave: sí` las seis sin las
  que no se entienden las cifras de la propuesta, y la página filtra por ese campo. El log
  completo sigue en el fichero.
- **Reto:** 2.
- **Impacto:** la página pasa de 13 entradas a 6. Ninguna cifra cambia.
- **Estado:** aplicado.

### [2026-11-19] El método del Reto 2 abre con un año de venta y de stock
- **Contexto:** la página explicaba el modelo sin enseñar nunca la serie sobre la que trabaja.
- **Decisión:** se añade un gráfico de dos paneles que comparten el eje de tiempo: unidades en
  almacén arriba, venta semanal abajo, 52 semanas observadas y 14 previstas. Dos paneles y no
  dos ejes en el mismo marco, porque el stock se mueve entre 13.000 y 16.000 unidades y la
  venta entre 150 y 500. El stock previsto es el que quedaría sin reponer nada.
- **Reto:** 2.
- **Impacto:** ninguna cifra nueva. Hace visible que la venta sube y baja con la temporada
  mientras el almacén apenas se mueve: en 14 semanas bajaría 3.613 uds, de 16.283 a 12.670.
- **Estado:** aplicado.

### [2026-11-19] El Reto 3 pasa a 12 iniciativas con text-to-SQL, y pierde una por fusión
- **Contexto:** la captura del motivo de devolución y la revisión del tallaje eran dos
  iniciativas, y la segunda no se entendía sin la primera. Faltaba además la vía más directa
  para que cualquiera use los datos.
- **Decisión:** se fusionan en una sola («Por qué devuelven, y arreglar el tallaje») y entra
  **Preguntar a los datos en lenguaje natural**: traduce la pregunta a SQL sobre las tablas
  limpias, enseña la consulta y devuelve la tabla. Entra por el peldaño 1, siempre con el SQL
  a la vista, porque un text-to-SQL que responde sin que nadie mire la consulta es peligroso.
- **Reto:** 3.
- **Impacto:** siguen siendo 12 iniciativas. Las que llevan IA dentro pasan de 5 a 6, las horas
  de 1.073 a 1.229 y el ahorro recurrente de 75.700 € a 79.600 €.
- **Estado:** aplicado.

### [2026-11-19] El gráfico de venta y stock se mueve a la propuesta, con selector por modelo
- **Contexto:** estaba en `/metodo`, que es la página que explica el cálculo. Compras entra
  por la propuesta y no llega a verlo, y además el total del catálogo no le dice qué hacer
  con una línea concreta.
- **Decisión:** pasa a `/`, encima de la tabla, con un selector de los 50 modelos que
  aparecen en la propuesta. La curva de un modelo **hereda la forma estacional de su
  categoría** —que es donde el modelo tiene señal— escalada por el peso del modelo dentro de
  ella: el mismo reparto que usa la propuesta, no una segunda estimación.
- **Opciones consideradas:** entrenar un modelo por cada uno de los 123 modelos, descartado
  por lo mismo que no se entrena por SKU (25 % de semanas a cero a nivel de modelo); y
  redibujar en JavaScript, descartado porque obligaría a duplicar en JS el código del gráfico.
- **Cómo funciona:** las 51 series se calculan una sola vez con la propuesta y viajan en una
  tabla con `modelo_id`. El selector solo cambia la query (`/?modelo=EME073-NAV`), así que la
  página se rehace en milisegundos y el enlace de un modelo se puede compartir.
- **Reto:** 2.
- **Impacto:** ninguna cifra cambia. `demand.generar_prevision` devuelve ahora también la
  curva por categoría, sin entrenar dos veces.
- **Estado:** aplicado.

### [2026-11-19] Nueve modelos al banco de pruebas: gana el gradient boosting con pérdida de Poisson
- **Contexto:** la comparativa en vivo tenía tres baselines y un solo modelo de verdad. Con
  esos cuatro candidatos no se puede afirmar que el elegido sea bueno, solo que gana a tres
  reglas sencillas.
- **Evidencia:** mismo backtesting (12 cortes, paso 4, origen móvil, 14 semanas de horizonte)
  sobre nueve modelos además de los tres baselines. `notebooks/banco_modelos.py`:

  | Modelo | MAE | \|sesgo\| |
  |--------|-----|---------|
  | **gradient boosting, pérdida de Poisson** | **5,87** | **21,0 %** |
  | gradient boosting, árboles llanos | 5,97 | 23,1 % |
  | gradient boosting, pérdida cuadrática (el que había) | 6,02 | 24,9 % |
  | gradient boosting, árboles hondos | 6,09 | 24,5 % |
  | gradient boosting clásico de sklearn | 6,15 | 27,1 % |
  | media móvil | 6,36 | 37,9 % |
  | extra trees | 6,37 | 30,3 % |
  | bosque aleatorio | 6,73 | 34,2 % |
  | regresión Ridge | 8,13 | 62,4 % |
  | regresión de Poisson lineal | 8,63 | 64,6 % |

- **Decisión:** el modelo pasa a entrenarse con **pérdida de Poisson**. Es la pérdida que
  corresponde al objetivo: unidades vendidas son conteos no negativos cuya varianza crece con
  la media, y la pérdida cuadrática asume lo contrario.
- **Lo que enseña la tabla:** los lineales son los peores con diferencia, así que la relación
  entre ritmo reciente, estacionalidad y semanas vista no es lineal. Y los árboles hondos
  pierden contra los llanos: con ~5.000 filas y menos de dos ciclos anuales, más capacidad es
  memorizar, no aprender.
- **Por qué solo cuatro candidatos en vivo:** cada modelo añade ~12 s al arranque del servicio.
  La web compara los cuatro que importan; el banco completo se reproduce con el script.
- **Reto:** 2.
- **Clave:** sí
- **Impacto:** MAE de 6,02 a **5,87** y sesgo del 24,9 % al **21,0 %**. Cambian las unidades
  propuestas de cada SKU.
- **Estado:** medido y aplicado.

### [2026-11-19] El gráfico enseña el efecto del pedido, no solo la previsión
- **Contexto:** el gráfico dibujaba la venta y el stock previstos, pero no se veía qué cambia
  por aprobar la propuesta, que es la decisión que tiene delante quien lo mira.
- **Decisión:** el panel de stock lleva dos futuros. En gris, lo que quedaría **sin reponer
  nada**. En azul, **con el pedido propuesto**, que entra en el almacén seis semanas después de
  firmarlo. El escalón de la línea azul son las unidades que se piden.
- **Además:** cada línea lleva su etiqueta pegada al final en vez de una leyenda aparte, y el
  corte entre lo observado y lo previsto va rotulado. El selector de modelo filtra también la
  tabla de abajo.
- **Reto:** 2.
- **Impacto:** ninguna cifra nueva. En `BLAZE PUFFER GREY MELANGE`, sin pedido el stock llega a
  cero a mitad de diciembre; con el pedido, aguanta el horizonte.
- **Estado:** aplicado.

### [2026-11-19] CORRECCIÓN: la proyección de stock ignoraba las compras ya pedidas
- **Contexto:** el gráfico de la propuesta dibujaba el almacén bajando de 16.283 a 12.670
  unidades en 14 semanas. Era falso.
- **Qué pasaba:** la proyección restaba la demanda prevista pero **no sumaba las compras que
  ya están pedidas y llegan dentro del horizonte**: 131 pedidos, **9.427 unidades** repartidas
  en las siete semanas siguientes al corte.
- **Decisión:** la proyección suma las llegadas en su semana. La línea «si no pido nada» pasa
  a significar lo que de verdad significa: sin pedir **nada más**. Las llegadas se dibujan
  además como barras bajo la línea, porque era lo que no se veía.
- **Impacto:** el almacén no se vacía, **crece un 36 %**: de 16.283 a 22.211 unidades. Es el
  argumento más fuerte del caso y estaba invertido. Las 347 unidades de la propuesta son el
  3,7 % de lo que ya viene, y van dirigidas a los SKUs que rompen.
- **Reto:** 2.
- **Clave:** sí
- **Estado:** corregido.

### [2026-11-19] La venta del gráfico se parte en precio completo y precio especial
- **Contexto:** el panel de venta se titulaba «unidades vendidas por semana» y dibujaba solo
  la venta a precio completo, que es la que alimenta la previsión. En la semana de Black
  Friday la línea baja, y leído así parece que se vendió menos.
- **Evidencia:** semana del 25 de noviembre de 2024: **291 unidades en total, 191 a precio
  completo y 100 a precio especial**. Las tres semanas anteriores fueron 351, 314 y 308. El
  volumen no sube en Black Friday: lo que cambia es el precio.
- **Decisión:** el panel se titula «unidades vendidas a precio completo» y lleva debajo, en
  área gris, lo vendido a precio especial. Así la caída de la línea en campaña se explica sola.
- **Reto:** 2.
- **Estado:** aplicado.
