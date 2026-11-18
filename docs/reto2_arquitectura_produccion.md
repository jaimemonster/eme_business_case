# Reto 2 · Arquitectura en producción de la propuesta de reposición

Cómo funcionaría dentro de EME STUDIOS el proceso que aquí se ejecuta con
`pipelines/run_reto2.py` y que está desplegado en
<https://eme-reposicion-761842722633.europe-southwest1.run.app>.

> La versión navegable de este esquema vive en la pestaña **En producción** del
> propio servicio. Aquí queda la misma información en el repositorio, por si
> alguien la busca sin abrir la web. El montaje técnico concreto —proyecto, APIs,
> credenciales, comandos— está en [`reto2_infraestructura.md`](reto2_infraestructura.md).

---

## 1. Visión general

Reponer stock son siempre los mismos cinco pasos: el dato aparece, se limpia, se
calcula qué falta, se publica la propuesta y **una persona decide**. Lo que está
desplegado hoy es ese proceso completo; lo único que cambia en una empresa real
son los dos primeros pasos.

| Paso | Hoy (datos del caso) | En producción |
|------|----------------------|---------------|
| 1 · El dato | El Excel del caso, dentro del contenedor | ERP, tienda online y sistema de almacén |
| 2 · La limpieza | `src/clean.py` | Las mismas reglas, como tablas que consume toda la empresa |
| 3 · El cálculo | Cloud Run, mismo código | Cloud Run Job, mismo código |
| 4 · La publicación | Web + Google Sheet | Lo mismo, más el histórico de propuestas |
| 5 · La decisión | Compras aprueba en el Sheet | Igual, y lo aprobado vuelve al ERP como pedido |

Tres de los cinco pasos son ya hoy exactamente lo que serían en producción.

## 2. De dónde salen los datos

| Dato | Sistema de origen | Frecuencia | Responsable | El riesgo real |
|------|-------------------|------------|-------------|----------------|
| Ventas | ERP y tienda online | Diaria, de madrugada | Sistemas / e-commerce | Devoluciones que llegan tarde e inflan la demanda de la semana |
| Catálogo | Gestor de producto | Cuando cambia | Producto | SKUs nuevos sin coste o sin categoría: entran sin margen calculable |
| Stock | Sistema de almacén | Diaria, tras el cierre | Logística | Que el stock del sistema no sea el del estante; un inventario desfasado propone de menos |
| Compras | ERP · pedidos a proveedor | Diaria | Compras | Fechas de llegada sin confirmar, que es el problema que ya aparece en los datos del caso |

## 3. Cada cuánto se ejecuta

**Hoy**: cada día a las 00:00 (`Europe/Madrid`), disparado por Cloud Scheduler, que
es un servicio externo a la aplicación. El diario es para poder ver el proceso
ejecutándose varios días seguidos durante la evaluación.

**En producción**: **semanal, los lunes a las 06:00.** El pedido a proveedor es
semanal y así Compras tiene la propuesta al llegar a la oficina. Se le añadiría una
pasada diaria que no propone pedidos, solo vigila roturas inminentes y avisa.

El calendario de un lunes, de punta a punta:

| Hora | Qué pasa |
|------|----------|
| 02:00 | La ingesta copia ventas, stock y compras al almacén analítico |
| 02:30 | Controles de entrada: ¿están las cuatro tablas? ¿cuadra el volumen con la semana pasada? |
| 03:00 | Se aplican las reglas de negocio y quedan las tablas limpias |
| 06:00 | El reloj arranca el cálculo: previsión, resta de stock y tránsito, propuesta |
| 06:02 | Controles de salida: ¿la propuesta se parece a las de las 8 semanas anteriores? |
| 06:05 | Se publica en la web y en el Sheet, y se avisa por Slack |
| 08:30 | **Compras revisa y aprueba** |
| 10:00 | Lo aprobado pasa al ERP como pedido a proveedor |

## 4. Dónde interviene una persona

| Quién | Cuándo | Qué decide | Dónde |
|-------|--------|-----------|-------|
| **Compras** | Cada semana · obligatorio | Aprueba, ajusta o rechaza cada línea. **Sin aprobación no hay pedido.** | El Google Sheet, con columnas de estado y unidades aprobadas |
| **Planificación** | Cada trimestre | Plazo de entrega, cobertura objetivo y umbrales | Los parámetros del proceso |
| **Quien mantiene el dato** | Cuando salta un aviso | Atiende el fallo o la propuesta marcada como anómala | Alerta a Slack o correo |

El sistema **nunca emite un pedido por su cuenta**. Y lo que Compras cambia
respecto a lo propuesto se guarda: la diferencia entre lo que el modelo dijo y lo
que una persona decidió es la mejor señal disponible para mejorar el modelo.

## 5. Qué pasa si falla

| Fallo | Detección | Impacto | Plan de contingencia |
|-------|-----------|---------|----------------------|
| Falta una tabla de datos | Control de entrada, antes de calcular | No hay propuesta nueva | No se calcula nada. Aviso, y sigue visible la propuesta anterior con su fecha |
| El cálculo revienta | El reloj, tras 3 reintentos con espera creciente | No hay propuesta nueva | Alerta con el error. Nunca se publica una propuesta a medias |
| La propuesta sale disparatada | Comparación con las 8 semanas previas | Riesgo de pedido erróneo | Se publica marcada como «requiere revisión». Una propuesta rara casi siempre es un dato roto |
| No se puede escribir el Sheet | Error de la API de Google | Compras no la ve donde la espera | La propuesta sigue en la web y descargable en Excel: el entregable no depende de un solo canal |
| Compras no revisa | Nadie marcó nada en 48 h | No se pide nada | Recordatorio automático. **El silencio no es una aprobación** |

## 6. Controles de calidad

- **Antes de calcular**: están las cuatro tablas, el volumen de filas se parece al
  de la semana anterior, no hay SKUs vendidos que falten del catálogo, y las fechas
  de llegada de compras son coherentes.
- **Después de calcular**: el número de SKUs, las unidades y los euros están dentro
  del rango de las 8 semanas previas. Si no, se publica marcado.
- **Sobre la previsión**: el backtesting se vuelve a lanzar en cada ejecución y
  elige el método que gana. Si el método ganador cambia, queda registrado: es la
  señal de que el comportamiento del negocio se ha movido.

## 7. Evolución

Por orden de lo que antes se rompe:

1. **Plazo de entrega por proveedor**, medido de su histórico real, en lugar de las
   6 semanas iguales para todos. El dato ya existe: en el caso, el 77 % de las
   entregas llegó tarde.
2. **Acotar el horizonte al final de temporada.** Las 14 semanas del cálculo cruzan
   campaña de Navidad y rebajas de enero, con ritmos que se diferencian en seis
   veces. Comprar a coste completo para vender con descuento es caro.
3. **Productos sin histórico**: un modelo recién lanzado no tiene ventas de las que
   aprender y hoy sale con demanda cero. Hace falta estimarlo por analogía con
   modelos parecidos, que en una marca con drops frecuentes no es un caso raro.
4. **Guardar lo que Compras decide** y medir la diferencia con lo propuesto.
5. **Multi-almacén**: cuando haya stock en varios sitios, aparece una decisión nueva
   —mover entre almacenes antes que pedir al proveedor— que suele salir más barata.
