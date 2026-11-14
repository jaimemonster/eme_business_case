"""Pipeline del Reto 1: limpieza → métricas → informe semanal HTML.

Ejecuta de punta a punta la generación del informe que la dirección abriría cada
lunes, a partir del Excel original. Salida en `output/reto1/`.

Uso:
    python pipelines/run_reto1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, report, storage  # noqa: E402
from src.clean import ejecutar_limpieza  # noqa: E402
from src.metrics import calcular_todas_las_metricas  # noqa: E402


def main() -> None:
    """Orquesta clean → metrics → report y deja el informe en output/reto1."""
    print("1/4  Limpiando datos y aplicando las reglas de negocio…")
    tablas = ejecutar_limpieza()
    print(f"     {len(tablas['ventas']):,} líneas de venta · {tablas['producto']['modelo_id'].nunique()} modelos")

    print("2/4  Calculando los KPIs del informe…")
    metricas = calcular_todas_las_metricas(tablas)
    print(f"     {len(metricas)} tablas de métricas en data/processed")

    print("3/4  Extrayendo los ejemplos de las decisiones desde los datos crudos…")
    ejemplos = report.recopilar_ejemplos_decisiones(storage.cargar_excel_crudo())

    print("4/4  Generando el informe HTML…")
    destino = config.DIR_OUTPUT / "reto1" / "informe_semanal.html"
    ruta = report.construir_informe(metricas, ejemplos, destino)
    print(f"\n✓ Informe listo: {ruta}")
    print(f"  {ruta.stat().st_size / 1_000_000:.1f} MB · ábrelo con:  open {ruta.relative_to(config.RAIZ_PROYECTO)}")


if __name__ == "__main__":
    main()
