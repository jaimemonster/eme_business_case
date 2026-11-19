# Reto 3 · Hoja de ruta de IA a 6 meses

> Generado por `pipelines/run_reto3.py` desde `src/roadmap.py`. No se edita a mano.
> La versión navegable está en el informe: `output/reto1/informe_semanal.html`,
> sección **Reto 3**.

## 0 · Dónde duele

- Margen de 12 meses: **557.595 €** sobre 779.379 € de facturación neta.
- Capital parado en exceso: **191.400 €** a coste (712.221 € a PVP), en 103 de 123 modelos.
- Cobertura global: **29,2 semanas** frente a las 8 de objetivo.
- Entregas de proveedor que llegan tarde: **72 %** (427 de 592), 5,8 días de media.
- Facturación fuera de España: **45 %**, en 6 países.
- Concentración: **15 modelos** (12 % del catálogo) hacen la mitad de la facturación.

De ahí el reparto: Compras y Planificación se llevan cinco iniciativas de doce, y Logística una.

## 1 · El método y las preguntas

La unidad de análisis es la tarea recurrente, y la evidencia es el fichero que produce.

| Paso | Qué se hace | Cómo |
| --- | --- | --- |
| **1. Inventariar** | Qué entrega cada equipo cada semana | El fichero, el mensaje o la decisión que sale de su mesa. |
| **2. Descomponer** | Cada entregable, en tareas con verbo | «Enséñame los tres últimos y hazlo delante de mí.» |
| **3. Puntuar** | Horas al año, dato disponible, coste del error | De aquí salen los dos ejes de la matriz. |
| **4. Decidir cuánto se automatiza** | Qué hace la máquina y qué firma una persona | Casi todo arranca con la máquina proponiendo y alguien aprobando. |

### El verbo de la tarea decide la tecnología

| Verbo | Qué es | Qué lo automatiza |
| --- | --- | --- |
| **Recoger** | Descargar, copiar, consolidar | Integración. Nada de IA. |
| **Calcular** | Aplicar una regla fija | Código determinista. Nada de IA. |
| **Juzgar** | Decidir con criterio | La persona. La IA propone y explica. |
| **Comunicar** | Escribir, responder, traducir | LLM. |

### Las seis preguntas comunes a todos los departamentos

1. **¿Qué entregas cada semana?** — Qué sale de su mesa.
2. **Enséñame los tres últimos.** — Las excepciones están en el fichero.
3. **¿De dónde sacas cada dato de ahí?** — Quién tiene la llave. Suele ser el bloqueante.
4. **¿Qué parte sigue una regla que podrías escribir?** — Separa lo que se automatiza de lo que se asiste.
5. **¿Qué pasa si sale mal y quién se entera?** — Decide el peldaño.
6. **¿Qué harías con ese tiempo?** — Si no hay respuesta, la iniciativa da igual.

### Las tres preguntas propias de cada departamento

| Departamento | Peso | Preguntas | Hipótesis que pone a prueba |
| --- | --- | --- | --- |
| Compras | Alto | · ¿Con qué plazo planificas: el del contrato o el real de cada proveedor?<br>· ¿Cómo decides la curva de tallas de un pedido? | Se planifica con 6 semanas fijas y el 72 % de las entregas llega tarde. |
| Planificación | Alto | · ¿Cómo decides cuántas unidades comprar de un modelo que todavía no existe?<br>· ¿Quién decide cuándo un modelo pasa a rebaja, y con qué criterio? | Nadie mira la cobertura por modelo. Hay 103 de 123 sobre el umbral. |
| Atención al cliente | Alto | · ¿Qué os preguntan, y en qué idioma?<br>· ¿Qué pasa con un mensaje que entra un sábado a las 21:00? | El motivo no se registra. Constan 7 devoluciones en 12 meses. |
| Producto | Medio | · ¿Cuánto pasa desde que llega la muestra hasta que el drop está publicado?<br>· ¿Quién escribe las descripciones, y en cuántos idiomas? | El contenido retrasa el lanzamiento del drop. |
| Marketing | Medio | · ¿Cómo eliges qué modelo empujar cada semana?<br>· ¿Miras el stock antes de lanzar una campaña? | La campaña se decide sin mirar el stock. |
| Ventas y dirección | Medio-alto | · ¿Qué miras el lunes por la mañana, y de dónde lo sacas?<br>· ¿Qué número te gustaría tener y no tienes? | El informe se monta a mano y llega con la semana empezada. |
| Logística | Bajo | · ¿Cuándo sabes de verdad que va a llegar un contenedor?<br>· ¿Cómo planificas el personal de una semana de recepción? | La fecha estimada del proveedor se trata como firme. |

## 2 · Las 12 iniciativas

**1.229 horas** de persona al año, **79.600 €** de ahorro recurrente y **35.300 €** de capital liberado una sola vez. Solo **6 de 12** llevan IA dentro del proceso.

Tipo **A**, la IA escribe el código y en producción corre lógica determinista. Tipo **B**, la IA está dentro del proceso.

| # | Dept. | Iniciativa | Tipo | Problema | h/año | € 1er año | Esf. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Compras | Reposición semanal automática | A | La propuesta se monta a mano cada semana. Hay 37 modelos que rompen en cuatro semanas, 249 unidades de déficit. | 312 | 7.800 € | 2 sem |
| 2 | Compras | Plazo real de cada proveedor | A | 427 de 592 entregas llegaron tarde, 5,8 días de media. Compras planifica con 6 semanas fijas para los cuatro. | 104 | 9.200 € | 1 sem |
| 3 | Compras | Repartir cada pedido por tallas | A | Los pedidos se reparten casi a partes iguales entre tallas. Sobran 1.959 unidades en XL y XXL y faltan 1.240 de la M. | — | 8.000 € | 2 sem |
| 4 | Planificación | Plan de liquidación del exceso | A | 103 de 123 modelos pasan el umbral de cobertura: 11.705 unidades y 191 k€ a coste, con 51 semanas de cobertura mediana. | — | 35.300 € | 3 sem |
| 5 | Planificación | Cuánto comprar de un modelo que aún no existe | A+B | Seis drops al año, diez modelos nuevos en cada uno. Sin ventas previas, la primera compra se decide a ojo. | — | 18.000 € | 5 sem |
| 6 | Atención al cliente | Agente de chat y voz multiidioma | B | El 45 % de la facturación viene de seis países fuera de España. Fuera de horario no contesta nadie. | 200 | 11.800 € | 4 sem |
| 7 | Atención al cliente | Por qué devuelven, y arreglar el tallaje | B | En 12 meses constan 7 devoluciones y ninguna trae motivo. La M se agota y la XXL se queda, sin saber si es demanda o patrón. | — | 6.500 € | 2 sem |
| 8 | Producto | Ficha de producto automática y multiidioma | B | 62 modelos nuevos al año para siete mercados. El contenido retrasa cada lanzamiento. | 93 | 5.300 € | 3 sem |
| 9 | Ventas y dirección | Preguntar a los datos en lenguaje natural | B | Cada pregunta nueva pasa por alguien que sepa cruzar tablas. Las que no son urgentes no llegan a preguntarse. | 156 | 3.900 € | 3 sem |
| 10 | Marketing | Qué promocionar esta semana, según el stock | A | 37 modelos a punto de romper y 103 con exceso. La campaña de la semana no mira ninguno de los dos. | 52 | 1.300 € | 1 sem |
| 11 | Ventas y dirección | Informe del lunes automático | A+B | El informe existe desde el Reto 1, pero se lanza a mano. | 208 | 5.200 € | 1 sem |
| 12 | Logística | Plan semanal de entradas al almacén | A | El almacén planifica con la fecha estimada del proveedor. Hay 37 pedidos vencidos sin confirmar. | 104 | 2.600 € | 2 sem |

### Detalle de cada iniciativa

#### 1 · Reposición semanal automática (Compras)

- **Qué pasa hoy**: La propuesta se monta a mano cada semana. Hay 37 modelos que rompen en cuatro semanas, 249 unidades de déficit.
- **Qué hace**: Prevé la demanda por SKU, descuenta stock y tránsito, y deja la propuesta en un Sheet que firma Compras. Ya está desplegada.
- **De dónde sale el número**: 6 h/semana × 52 × 25 €/h = 7.800 €/año. Aparte protege 10.500 € de margen (249 uds × 42,1 €).
- **Error que evita**: Comprar lo que ya sobra.
- **Peldaño 2**: Propone y alguien aprueba.
- **KPI**: Pedidos de compra que salen de la propuesta sin editar — de 0 % a 70 %.

#### 2 · Plazo real de cada proveedor (Compras)

- **Qué pasa hoy**: 427 de 592 entregas llegaron tarde, 5,8 días de media. Compras planifica con 6 semanas fijas para los cuatro.
- **Qué hace**: Mide el plazo que cumple de verdad cada proveedor y se lo pasa al motor de reposición. Avisa del pedido vencido sin confirmar.
- **De dónde sale el número**: 2 h/semana de seguimiento = 2.600 €. Más 6.600 €, el 65 % del déficit de 249 uds × 42,1 € de margen.
- **Error que evita**: Planificar con una fecha que falla tres de cada cuatro veces.
- **Peldaño 3**: Automático con excepciones.
- **KPI**: Entregas dentro de la fecha planificada — de 28 % a 60 %.

#### 3 · Repartir cada pedido por tallas (Compras)

- **Qué pasa hoy**: Los pedidos se reparten casi a partes iguales entre tallas. Sobran 1.959 unidades en XL y XXL y faltan 1.240 de la M.
- **Qué hace**: Calcula cuánto pesa cada talla en la venta real de esa categoría y reparte el pedido con esos pesos.
- **De dónde sale el número**: Evitar la mitad de las 2.017 uds que hoy sobran son 16.500 € que no se gastan. Se imputa la mitad al año.
- **Error que evita**: Comprar tallas que no se venden, drop tras drop.
- **Peldaño 2**: Propone y alguien aprueba.
- **KPI**: SKUs sin una sola venta en 6 meses — de 21 a menos de 10.

#### 4 · Plan de liquidación del exceso (Planificación)

- **Qué pasa hoy**: 103 de 123 modelos pasan el umbral de cobertura: 11.705 unidades y 191 k€ a coste, con 51 semanas de cobertura mediana.
- **Qué hace**: Ordena el exceso por capital parado y por lo que aún vende, y propone descuento y mercado sin bajar de un suelo de margen.
- **De dónde sale el número**: 1.756 uds (el 15 %) × (60,8 € de PVP − 40 % − 16,35 € de coste) = 35.300 €.
- **Error que evita**: Rebajar lo que ya se vendía solo.
- **Peldaño 2**: Propone y alguien aprueba.
- **KPI**: Cobertura global de stock — de 29,2 semanas a menos de 22.

#### 5 · Cuánto comprar de un modelo que aún no existe (Planificación)

- **Qué pasa hoy**: Seis drops al año, diez modelos nuevos en cada uno. Sin ventas previas, la primera compra se decide a ojo.
- **Qué hace**: Busca modelos parecidos en categoría, sección, precio y color entre los 123 con histórico, y usa su curva de venta como punto de partida.
- **De dónde sale el número**: 217 k€ de compra anual a coste. Un 8 % menos de error son 18.000 €.
- **Error que evita**: Fallar la primera compra de 62 modelos al año.
- **Peldaño 1**: Asistido.
- **KPI**: Desviación de la primera compra frente a la venta real — de sin medir a menos del 20 %.

#### 6 · Agente de chat y voz multiidioma (Atención al cliente)

- **Qué pasa hoy**: El 45 % de la facturación viene de seis países fuera de España. Fuera de horario no contesta nadie.
- **Qué hace**: Responde estado del pedido, disponibilidad y dudas de talla, tramita devoluciones y pasa a una persona con el contexto. Chat primero, voz después.
- **De dónde sale el número**: 3.566 contactos al año, 55 % resueltos, 6 min cada uno: 200 h = 5.000 €. Más 6.800 € de preventa recuperada.
- **Error que evita**: Perder la venta por no contestar un sábado en alemán.
- **Peldaño 3**: Automático con excepciones.
- **KPI**: Contactos resueltos sin intervención de una persona — de 0 % a 55 %.

#### 7 · Por qué devuelven, y arreglar el tallaje (Atención al cliente)

- **Qué pasa hoy**: En 12 meses constan 7 devoluciones y ninguna trae motivo. La M se agota y la XXL se queda, sin saber si es demanda o patrón.
- **Qué hace**: El agente etiqueta cada devolución con un motivo fijo (talla, calidad, envío, cambio de opinión). A los tres meses Producto los cruza con la venta por talla y corrige los patrones que fallan.
- **De dónde sale el número**: Sin línea base, la crea ella misma. Si el 1 % se devuelve por talla y se corrige la mitad: 119 × 75,87 € × 71,5 %.
- **Error que evita**: Repetir el patrón que genera la devolución.
- **Peldaño 2**: Propone y alguien aprueba.
- **KPI**: Devoluciones con motivo registrado — de ≈0 % a 90 %.

#### 8 · Ficha de producto automática y multiidioma (Producto)

- **Qué pasa hoy**: 62 modelos nuevos al año para siete mercados. El contenido retrasa cada lanzamiento.
- **Qué hace**: Del catálogo y la foto saca nombre, descripción, atributos, texto alternativo y SEO en seis idiomas. Producto revisa y publica.
- **De dónde sale el número**: 62 modelos × 6 idiomas × 15 min = 93 h = 2.325 €. Más 3.000 € por adelantar una semana cada drop.
- **Error que evita**: Publicar el drop tarde, o solo en español.
- **Peldaño 2**: Propone y alguien aprueba.
- **KPI**: Días desde la muestra hasta la ficha publicada — de sin medir a menos de 3.

#### 9 · Preguntar a los datos en lenguaje natural (Ventas y dirección)

- **Qué pasa hoy**: Cada pregunta nueva pasa por alguien que sepa cruzar tablas. Las que no son urgentes no llegan a preguntarse.
- **Qué hace**: «¿Cómo va la chaqueta en Francia?» se traduce a SQL sobre las tablas limpias. Enseña la consulta que ha escrito y devuelve el resultado. Solo lectura.
- **De dónde sale el número**: 3 h/semana de montar consultas a mano × 52 × 25 € = 3.900 €.
- **Error que evita**: Decidir con la única pregunta que a alguien le dio tiempo a contestar.
- **Peldaño 1**: Asistido.
- **KPI**: Preguntas respondidas sin pasar por una persona — de 0 % a 50 %.

#### 10 · Qué promocionar esta semana, según el stock (Marketing)

- **Qué pasa hoy**: 37 modelos a punto de romper y 103 con exceso. La campaña de la semana no mira ninguno de los dos.
- **Qué hace**: Lista semanal de qué empujar (exceso que aún vende) y qué dejar quieto (lo que va a romper). Es el canal de salida de la 4.
- **De dónde sale el número**: 1 h/semana × 52 × 25 € = 1.300 €. Los 35.300 € de la 4 no se cuentan aquí.
- **Error que evita**: Gastar en promocionar lo que ya no hay.
- **Peldaño 2**: Propone y alguien aprueba.
- **KPI**: Gasto de promoción sobre modelos con exceso — de sin medir a más del 60 %.

#### 11 · Informe del lunes automático (Ventas y dirección)

- **Qué pasa hoy**: El informe existe desde el Reto 1, pero se lanza a mano.
- **Qué hace**: Se genera los lunes a las 7:00 y manda un resumen con los tres cambios de la semana y lo que hay que decidir.
- **De dónde sale el número**: 4 h/semana de montar y revisar × 52 × 25 € = 5.200 €.
- **Error que evita**: Decidir el lunes con los números del lunes anterior.
- **Peldaño 4**: Automático.
- **KPI**: Lunes con el informe disponible antes de las 8:00 — de 0 % a 100 %.

#### 12 · Plan semanal de entradas al almacén (Logística)

- **Qué pasa hoy**: El almacén planifica con la fecha estimada del proveedor. Hay 37 pedidos vencidos sin confirmar.
- **Qué hace**: Calendario de lo que entra cada semana con la fecha corregida por el retraso real. Avisa si lo retrasado afecta a un modelo en rotura.
- **De dónde sale el número**: 2 h/semana de replanificación × 52 × 25 € = 2.600 €.
- **Error que evita**: Montar el turno de recepción para un camión que no llega.
- **Peldaño 3**: Automático con excepciones.
- **KPI**: Entradas con fecha fiable a 7 días vista — de sin medir a 85 %.

### Cimiento · Capa de validación del dato en la entrada

Valida cada fichero que entra (SKUs huérfanos, duplicados, tipos mezclados, fechas imposibles) y para el proceso antes de que el error llegue a un informe.

En el Reto 1 la limpieza se llevó media vuelta de trabajo: 25 líneas duplicadas, un SKU fuera del catálogo, mercados escritos de tres formas y descuentos imposibles.

## 3 · Matriz de impacto × esfuerzo

El eje de esfuerzo son **semanas hasta producción**. Dentro va conseguir el acceso al dato, acordar quién valida y las vueltas hasta que alguien lo usa. El gráfico está en el informe HTML.

| Cuadrante | Iniciativas |
| --- | --- |
| Hazlo ya — alto impacto, bajo esfuerzo | 1, 2, 3 |
| Proyecto con dueño — alto impacto, alto esfuerzo | 4, 5, 6 |
| Rápidas — bajo esfuerzo | 7, 10, 11, 12 |
| Justifícala por otra cosa — alto esfuerzo, poco € | 8, 9 |

## 4 · Calendario

| Mes | Foco | Iniciativas |
| --- | --- | --- |
| 1 | Cimientos y lo que ya está hecho | 1, 2, 11 |
| 2 | El dinero parado | 4, 8, 10 |
| 3 | Compras afinada y el agente en marcha | 3, 4, 6, 8, 12 |
| 4 | Atención al cliente completa | 5, 6, 7 |
| 5 | Lo nuevo, y preguntar a los datos | 5, 7, 9 |
| 6 | Cerrar el círculo del tallaje | 5, 7 |

### Tres victorias rápidas en los primeros 60 días

1. **Reposición semanal automática** — Pedidos de compra que salen de la propuesta sin editar: de 0 % a 70 %.
2. **Plan de liquidación del exceso** — Cobertura global de stock: de 29,2 semanas a menos de 22.
3. **Informe del lunes automático** — Lunes con el informe disponible antes de las 8:00: de 0 % a 100 %.

## 5 · Cómo se mide el éxito y cómo se consigue la adopción

Casi todas entran por el **peldaño 2**, el de proponer y que alguien apruebe. Se sube cuando el KPI lo permite.

| Peldaño | Qué significa | Cuándo |
| --- | --- | --- |
| **0** | Manual | Como está hoy |
| **1** | Asistido | Plantilla, buscador, borrador |
| **2** | Propone y alguien aprueba | La puerta de entrada |
| **3** | Automático con excepciones | Solo lo raro llega a una persona |
| **4** | Automático | Se mira el KPI |

### Un KPI por iniciativa

| # | Iniciativa | Cómo se mide | Hoy | A 6 meses |
| --- | --- | --- | --- | --- |
| 1 | Reposición semanal automática | Pedidos de compra que salen de la propuesta sin editar | 0 % | 70 % |
| 2 | Plazo real de cada proveedor | Entregas dentro de la fecha planificada | 28 % | 60 % |
| 3 | Repartir cada pedido por tallas | SKUs sin una sola venta en 6 meses | 21 | menos de 10 |
| 4 | Plan de liquidación del exceso | Cobertura global de stock | 29,2 semanas | menos de 22 |
| 5 | Cuánto comprar de un modelo que aún no existe | Desviación de la primera compra frente a la venta real | sin medir | menos del 20 % |
| 6 | Agente de chat y voz multiidioma | Contactos resueltos sin intervención de una persona | 0 % | 55 % |
| 7 | Por qué devuelven, y arreglar el tallaje | Devoluciones con motivo registrado | ≈0 % | 90 % |
| 8 | Ficha de producto automática y multiidioma | Días desde la muestra hasta la ficha publicada | sin medir | menos de 3 |
| 9 | Preguntar a los datos en lenguaje natural | Preguntas respondidas sin pasar por una persona | 0 % | 50 % |
| 10 | Qué promocionar esta semana, según el stock | Gasto de promoción sobre modelos con exceso | sin medir | más del 60 % |
| 11 | Informe del lunes automático | Lunes con el informe disponible antes de las 8:00 | 0 % | 100 % |
| 12 | Plan semanal de entradas al almacén | Entradas con fecha fiable a 7 días vista | sin medir | 85 % |

Por encima de las doce hay un KPI de la hoja de ruta entera: **cuántas siguen usándose tres meses después de entregarse**.

### Adopción

- **Un champion por departamento** — La persona que ya tenía ganas.
- **Una sesión al mes por área** — Sobre su trabajo de esa semana.
- **La herramienta vive donde ya trabajan** — Sheets, correo, chat.
- **Se sube de peldaño con el KPI** — Nada pasa a automático porque toque.

## 6 · Supuestos sobre los que se ha priorizado

| Supuesto | Valor | Origen | De dónde sale |
| --- | --- | --- | --- |
| **Coste hora interno** | 25 €/h | estimado | Perfil administrativo medio, coste empresa. |
| **Plantilla** | ≈14 personas | estimado | Compras 2 · Planificación 1 · Logística 3 · Producto 2 · Marketing 2 · Atención 2 · Dirección 2. |
| **Contactos de cliente** | 0,30 por pedido | estimado | ≈69 a la semana. El caso no trae datos de atención. |
| **Drops al año** | 6 | dato | 12 drops en 22 meses. |
| **Modelos nuevos por drop** | ≈10 | dato | 123 modelos en 12 drops. |
| **Margen medio por unidad** | 42,1 € | dato | 558 k€ sobre 13.260 unidades. |
| **Exceso de stock** | 11.705 uds · 191 k€ a coste | dato | 103 de 123 modelos sobre el umbral. |
| **Liquidación** | 40 % de descuento sobre el 15 % del exceso | estimado | Al 25 % el retorno sería de 58.900 €. |
| **Iniciativa 10** | Solo cuentan sus horas | regla | Los 35.300 € de liquidación ya están contados en la 4. |
| **Capital y ahorro** | Columnas distintas | regla | El capital se libera una vez. Las horas se ahorran cada año. |

Construir rápido con un agente traslada el riesgo al mantenimiento. La regla del repositorio lo cubre: todo en código, pipeline reproducible y decisiones fechadas.
