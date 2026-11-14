# EME STUDIOS · Caso práctico AI Specialist

Resolución del caso práctico de selección para el puesto de **AI Specialist** en
EME STUDIOS (marca de moda). A partir de un Excel con actividad ficticia del
**1 de enero de 2024 al 9 de noviembre de 2025** (ventas, catálogo, stock y
compras) se entregan tres cosas:

| Reto | Peso | Qué es | Dónde está |
|------|------|--------|------------|
| **1 · Informe semanal de ventas y stock** | 40 % | El informe que la dirección abriría cada lunes: cómo fue la semana, cómo se reparte el negocio, qué modelos tiran y cuáles no, y qué roturas o excesos de stock hay que decidir. | `output/reto1/` |
| **2 · Propuesta automática de reposición** | 30 % | Proceso semanal que prevé la demanda por SKU, descuenta stock y compras en tránsito y propone qué reponer (lead time 6 semanas, cobertura objetivo 8 semanas). | `output/reto2/` · `docs/reto2_arquitectura_produccion.md` |
| **3 · Hoja de ruta de IA a 6 meses** | 30 % | Qué haría en los 6 primeros meses para que la IA ayude a Compras, Ventas, Planificación, Logística, Producto, Marketing y Atención al cliente. | `docs/reto3_roadmap_ia.md` · `output/reto3/` |

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
│   ├── forecast.py           # Demanda prevista por SKU (Reto 2)
│   ├── replenishment.py      # Cálculo de la propuesta de reposición (Reto 2)
│   └── report.py             # Generación del informe HTML (Reto 1)
├── pipelines/
│   ├── run_reto1.py          # clean → metrics → report
│   └── run_reto2.py          # clean → forecast → replenishment → export
├── notebooks/                # Exploración puntual · no es código de entrega
├── output/
│   ├── reto1/                # Informe semanal HTML
│   ├── reto2/                # Propuesta de reposición
│   └── reto3/                # Material de la hoja de ruta
└── docs/
    ├── enunciado/                        # Enunciado original del caso (PDF)
    ├── notas_calidad_datos.md            # Problemas encontrados en los datos y su tratamiento
    ├── decisiones.md                     # Log de decisiones y supuestos, con fecha
    ├── reto2_arquitectura_produccion.md  # Cómo funcionaría el proceso en producción
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

# Reto 1 · informe semanal → output/reto1/
python pipelines/run_reto1.py

# Reto 2 · propuesta de reposición → output/reto2/
python pipelines/run_reto2.py
```

Ambos pipelines parten siempre del Excel original y regeneran las tablas
intermedias, así que son idempotentes: se pueden relanzar sin efectos laterales.
