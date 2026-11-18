"""Lector del log de decisiones.

Responsabilidad: leer `docs/decisiones.md` y devolver las entradas que afectan a
un reto concreto, ya estructuradas.

Por qué existe: CLAUDE.md exige que la sección de trazabilidad de cada entregable
se **construya a partir de `decisiones.md`**, no se escriba a mano. Si se
escribiera a mano, a la tercera revisión el entregable y el log dirían cosas
distintas y nadie sabría cuál es la verdad.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from src import config

CAMPOS = (
    "contexto", "opciones consideradas", "decision", "evidencia",
    "advertencia registrada", "credenciales", "reto", "impacto", "estado",
)


@dataclass
class Decision:
    """Una entrada del log, ya troceada en sus campos."""

    fecha: str
    titulo: str
    campos: Dict[str, str] = field(default_factory=dict)
    retos: List[str] = field(default_factory=list)

    @property
    def resumen(self) -> str:
        """La frase que se enseña plegada: qué se decidió."""
        return self.campos.get("decision") or self.campos.get("contexto", "")


def _clave(etiqueta: str) -> str:
    """Normaliza el nombre de un campo: 'Opciones consideradas' -> 'opciones consideradas'."""
    etiqueta = etiqueta.strip().lower()
    for acento, llano in (("ó", "o"), ("í", "i"), ("á", "a"), ("é", "e"), ("ú", "u")):
        etiqueta = etiqueta.replace(acento, llano)
    return etiqueta


def leer(ruta: Path | None = None) -> List[Decision]:
    """Todas las decisiones del log, en orden de aparición."""
    ruta = ruta or config.DIR_DOCS / "decisiones.md"
    texto = ruta.read_text(encoding="utf-8")

    # El fichero empieza con una plantilla de ejemplo dentro de un bloque de
    # código; se corta por el encabezado real para no parsearla como decisión.
    if "## Decisiones" in texto:
        texto = texto.split("## Decisiones", 1)[1]

    decisiones: List[Decision] = []
    bloques = re.split(r"\n### ", texto)
    for bloque in bloques[1:]:
        lineas = bloque.strip().split("\n")
        cabecera = lineas[0]
        m = re.match(r"\[(\d{4}-\d{2}-\d{2})\]\s*(.+)", cabecera)
        if not m:
            continue
        dec = Decision(fecha=m.group(1), titulo=m.group(2).strip())

        actual = None
        for linea in lineas[1:]:
            campo = re.match(r"-\s+\*\*(.+?):\*\*\s*(.*)", linea)
            if campo:
                actual = _clave(campo.group(1))
                dec.campos[actual] = campo.group(2).strip()
            elif actual and linea.strip():
                dec.campos[actual] += "\n" + linea.strip()

        reto = dec.campos.get("reto", "")
        dec.retos = re.findall(r"\d|transversal", reto.lower())
        decisiones.append(dec)
    return decisiones


def del_reto(numero: str, ruta: Path | None = None) -> List[Decision]:
    """Las decisiones que afectan a un reto, más las transversales.

    Se incluyen las transversales a propósito: una decisión de limpieza que afecta
    a los tres retos también explica las cifras de éste.
    """
    return [
        d for d in leer(ruta)
        if numero in d.retos or "transversal" in d.retos
    ]
