"""Pipeline del Reto 2: limpieza → forecast → reposición → export.

Genera la propuesta semanal de reposición por SKU para que el equipo de Compras
la revise y apruebe. Salida en `output/reto2/`.

Parte siempre del Excel original y regenera las tablas intermedias, así que es
idempotente: se puede relanzar sin efectos laterales. Es el mismo proceso que
ejecuta el servicio desplegado; aquí corre a mano para poder mirarlo.

Uso:
    python pipelines/run_reto2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, replenishment, storage  # noqa: E402
from src.clean import ejecutar_limpieza  # noqa: E402


def main() -> None:
    """Orquesta clean → forecast → replenishment → export."""
    semanas = replenishment.horizonte_semanas()

    print("1/3  Limpiando datos y aplicando las reglas de negocio…")
    tablas = ejecutar_limpieza()
    print(
        f"     {len(tablas['ventas']):,} líneas de venta · "
        f"{len(tablas['producto'])} SKUs · {len(tablas['compras'])} pedidos a proveedor"
    )

    print(f"2/3  Previendo demanda y calculando la necesidad a {semanas} semanas…")
    resultado = replenishment.generar_propuesta(tablas)
    for _, fila in resultado["resumen"].iterrows():
        print(f"     {fila['concepto']:.<32} {fila['valor']:,}")

    if not resultado["error_forecast"].empty:
        err = resultado["error_forecast"].iloc[0]
        print(
            f"     Error de la previsión: MAE {err['mae']} · sesgo {err['sesgo_pct']} % "
            f"({err['n_cortes']} cortes)"
        )

    print("3/3  Guardando tablas y exportando la propuesta…")
    for nombre in ("propuesta", "necesidad", "sin_rotacion", "compras_a_confirmar"):
        storage.guardar_tabla(resultado[nombre], f"reto2_{nombre}", config.DIR_PROCESSED)

    destino = config.DIR_OUTPUT / "reto2" / "propuesta_reposicion.xlsx"
    ruta = replenishment.exportar_propuesta(resultado, destino)

    print(f"\n✓ Propuesta lista: {ruta}")
    print(f"  ábrela con:  open {ruta.relative_to(config.RAIZ_PROYECTO)}")


if __name__ == "__main__":
    main()
