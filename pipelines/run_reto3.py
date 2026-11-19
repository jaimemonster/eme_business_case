"""Pipeline del Reto 3: genera el documento de la hoja de ruta y sus exportaciones.

El contenido vive en `src/roadmap.py`. De ahí salen tres cosas, para que no
haya dos versiones que puedan contradecirse:

- las cinco páginas del informe HTML (las monta `run_reto1.py`),
- `docs/reto3_roadmap_ia.md`,
- las tablas sueltas de `output/reto3/`, por si hacen falta en una presentación.

Uso:
    python pipelines/run_reto3.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, roadmap  # noqa: E402


def main() -> None:
    """Escribe el markdown y los CSV. Necesita las tablas limpias del Reto 1."""
    print("1/2  Generando docs/reto3_roadmap_ia.md…")
    destino_md = config.DIR_DOCS / "reto3_roadmap_ia.md"
    destino_md.write_text(roadmap.documento_markdown(), encoding="utf-8")
    t = roadmap.totales()
    print(f"     12 iniciativas · {t['horas']:,} h/año · {t['euros_rec']:,} €/año recurrentes")

    print("2/2  Exportando las tablas a output/reto3…")
    salida = config.DIR_OUTPUT / "reto3"
    salida.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(roadmap.INICIATIVAS).to_csv(salida / "iniciativas.csv", index=False)
    pd.DataFrame(
        [{"concepto": c, "valor": v, "origen": o, "de_donde_sale": p}
         for c, v, p, o in roadmap.SUPUESTOS]
    ).to_csv(salida / "supuestos.csv", index=False)
    pd.DataFrame([roadmap.cifras_de_partida()]).T.rename(columns={0: "valor"}).to_csv(
        salida / "cifras_de_partida.csv")

    print(f"\n✓ Hoja de ruta lista: {destino_md.relative_to(config.RAIZ_PROYECTO)}")
    print(f"  Versión navegable: output/reto1/informe_semanal.html · sección Reto 3")


if __name__ == "__main__":
    main()
