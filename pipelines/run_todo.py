"""Genera de una vez todo lo que se entrega como fichero: Retos 1 y 3.

El Reto 2 no está aquí porque no se genera, se ejecuta: vive desplegado en
Cloud Run y se lanza solo cada día. Para reproducirlo en local está
`pipelines/run_reto2.py`.

El orden importa. El Reto 1 limpia los datos y calcula las métricas; el Reto 3
lee esas mismas tablas para sus cifras de partida, así que va después.

Uso:
    python pipelines/run_todo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_reto1  # noqa: E402
import run_reto3  # noqa: E402

from src import config  # noqa: E402


def main() -> None:
    """Lanza los dos pipelines en orden y resume dónde ha quedado todo."""
    arranque = time.time()

    print("━━ Reto 1 · Informe semanal ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    run_reto1.main()

    print("\n━━ Reto 3 · Hoja de ruta ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    run_reto3.main()

    informe = config.DIR_OUTPUT / "reto1" / "informe_semanal.html"
    print(f"\n━━ Listo en {time.time() - arranque:.0f} s ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Informe (Retos 1 y 3):  open {informe.relative_to(config.RAIZ_PROYECTO)}")
    print(f"  Hoja de ruta en texto:  docs/reto3_roadmap_ia.md")
    print(f"  Reto 2, desplegado:     {config.URL_SERVICIO_RETO2}")


if __name__ == "__main__":
    main()
