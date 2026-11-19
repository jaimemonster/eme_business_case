# EME STUDIOS · Caso práctico AI Specialist

Resolución del caso práctico de selección para el puesto de **AI Specialist** en
EME STUDIOS (marca de moda). A partir de un Excel con actividad ficticia del
**1 de enero de 2024 al 9 de noviembre de 2025** (ventas, catálogo, stock y
compras) se entregan tres cosas:

| Reto | Peso | Qué es | Dónde está |
|------|------|--------|------------|
| **1 · Informe semanal de ventas y stock** | 40 % | El informe que la dirección abriría cada lunes: cómo fue la semana, cómo se reparte el negocio, qué modelos tiran y cuáles no, y qué roturas o excesos de stock hay que decidir. | `output/reto1/` |
| **2 · Propuesta automática de reposición** | 30 % | **Servicio desplegado** que cada día a las 00:00 prevé la demanda por SKU, descuenta stock y compras en tránsito y propone qué reponer (lead time 6 semanas, cobertura objetivo 8 semanas), dejando la propuesta en un Google Sheet que revisa Compras. | **[Servicio en marcha](https://eme-reposicion-761842722633.europe-southwest1.run.app)** · `service/` · `output/reto2/` |
| **3 · Hoja de ruta de IA a 6 meses** | 30 % | Doce iniciativas para los siete departamentos, priorizadas por impacto y esfuerzo sobre las cifras reales del caso, con calendario a seis meses, KPIs y plan de adopción. Vive como **cinco páginas del propio informe**. | `output/reto1/` (sección Reto 3) · `docs/reto3_roadmap_ia.md` · `output/reto3/` |

El enunciado original está en [`docs/enunciado/`](docs/enunciado/).
Las reglas de negocio, los parámetros y las definiciones de KPIs están en
[`CLAUDE.md`](CLAUDE.md).

---

## Estructura

```
.
├── CLAUDE.md                 # Reglas de negocio, parámetros, KPIs y convenciones
├── README.md
├── requirements.txt
├── data/
│   ├── raw/                  # Excel original · NUNCA se modifica
│   ├── interim/              # Tablas limpias (parquet) · generadas
│   └── processed/            # Tablas de métricas listas para informe · generadas
├── src/
│   ├── config.py             # Rutas, fechas de corte y parámetros de negocio
│   ├── storage.py            # Carga del Excel y guardado/lectura de tablas
│   ├── profiling.py          # Perfilado de calidad de datos
│   ├── clean.py              # Limpieza + reglas de negocio (único sitio donde se aplican)
│   ├── metrics.py            # KPIs del Reto 1
│   ├── forecast.py           # Previsión simple usada por el Reto 1 (rotura a 4 semanas)
│   ├── demand.py             # Motor de previsión del Reto 2 (14 semanas, por categoría)
│   ├── replenishment.py      # Cálculo de la propuesta de reposición (Reto 2)
│   └── report.py             # Generación del informe HTML (Reto 1)
├── service/                  # Servicio desplegado del Reto 2 (FastAPI → Cloud Run)
│   ├── app.py                # Rutas: la web y el trabajo que dispara el reloj
│   ├── vista.py              # Las cinco páginas
│   ├── sheets.py             # Escritura en Google Sheets, sin claves
│   └── decisiones.py         # Lee docs/decisiones.md para la página de trazabilidad
├── Dockerfile                # Imagen del servicio
├── pipelines/
│   ├── run_todo.py           # Retos 1 y 3 de una vez
│   ├── run_reto1.py          # clean → metrics → report
│   ├── run_reto2.py          # clean → forecast → replenishment → export
│   └── run_reto3.py          # roadmap → docs/reto3_roadmap_ia.md + output/reto3
├── notebooks/                # Exploración puntual · no es código de entrega
├── output/
│   ├── reto1/                # Informe semanal HTML
│   ├── reto2/                # Propuesta de reposición
│   └── reto3/                # Material de la hoja de ruta
└── docs/
    ├── enunciado/                        # Enunciado original del caso (PDF)
    ├── notas_calidad_datos.md            # Problemas encontrados en los datos y su tratamiento
    ├── decisiones.md                     # Log de decisiones y supuestos, con fecha
    ├── presentacion.md                   # Enlace al guion de 20 diapositivas (Google Slides)
    ├── reto2_arquitectura_produccion.md  # Cómo funcionaría el proceso en producción
    ├── reto2_infraestructura.md          # Montaje real del despliegue y problemas resueltos
    └── reto3_roadmap_ia.md               # Hoja de ruta de IA a 6 meses
```

`data/interim/` y `data/processed/` no se versionan: son reproducibles ejecutando
los pipelines.

---

## Puesta en marcha

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Coloca el fichero `EME_Caso_Practico_Datos.xlsx` en `data/raw/`.

## Ejecución

```bash
source .venv/bin/activate

# Retos 1 y 3 · el informe completo → output/reto1/ y docs/
python pipelines/run_todo.py
```

El Reto 2 no entra ahí porque no se genera, se ejecuta: está desplegado y se
lanza solo cada día. Para reproducirlo en local:

```bash
python pipelines/run_reto2.py   # propuesta de reposición → output/reto2/
```

### El servicio del Reto 2

Está **desplegado y ejecutándose solo**:
<https://eme-reposicion-761842722633.europe-southwest1.run.app>

Para levantarlo en local:

```bash
uvicorn service.app:app --reload     # http://127.0.0.1:8000
```

El despliegue y el reloj diario están documentados en
[`docs/reto2_infraestructura.md`](docs/reto2_infraestructura.md).

Ambos pipelines parten siempre del Excel original y regeneran las tablas
intermedias, así que son idempotentes: se pueden relanzar sin efectos laterales.
