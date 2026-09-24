"""Generación de YouTube Shorts (9:16, 1080x1920, 15-60 s).

Características aplicadas automáticamente:
  - Gancho en los primeros 3 s: pregunta corta + imagen "misterio" desenfocada
    + texto enorme + sonido. La respuesta se revela al final (retención).
  - Ritmo rápido: voz ~12 % más rápida, pausas mínimas, efectos de rebote.
  - Texto grande en pantalla y barra de progreso superior.
  - Música más energética (procedural CC0 a 128 bpm) adecuada para niños.
  - Cierre con llamado a la acción («¡Sígueme para más!», «¡Dale like!»).
"""
from __future__ import annotations

from typing import Callable

from contenido_infantil import TEMAS, Tema
from generador_guion import CTA_SUGERIDOS, Guion, cta_en_idioma, generar_guion_short  # noqa: F401
from generador_imagenes import GestorImagenes
from produccion import ConfigProduccion, ResultadoVideo, producir_video

MODOS = {
    "ambos": ["largo", "short"],
    "solo_largo": ["largo"],
    "solo_short": ["short"],
}
NOMBRES_MODOS = {"ambos": "Video largo + Short", "solo_largo": "Solo video largo", "solo_short": "Solo Short"}
__all__ = ["CTA_SUGERIDOS", "cta_en_idioma", "MODOS", "NOMBRES_MODOS", "formatos_para", "guion_short",
           "generar_short", "short_desde_largo"]


def formatos_para(modo: str) -> list[str]:
    return MODOS.get(modo, MODOS["ambos"])


def guion_short(tema: Tema | str, idioma: str = "es", texto_cta: str = "") -> Guion:
    tema = TEMAS[tema] if isinstance(tema, str) else tema
    return generar_guion_short(tema, idioma, texto_cta)


def generar_short(tema: Tema | str, idioma: str, cfg: ConfigProduccion, numero: int | None = None,
                  gestor: GestorImagenes | None = None,
                  progreso: Callable[[float, str], None] | None = None) -> ResultadoVideo:
    return producir_video(tema, idioma, "short", cfg, numero=numero, gestor=gestor, progreso=progreso)


def short_desde_largo(largo: ResultadoVideo, cfg: ConfigProduccion, numero: int | None = None,
                      progreso: Callable[[float, str], None] | None = None) -> ResultadoVideo:
    """Crea el Short del mismo tema/idioma reutilizando las imágenes (caché) del video largo."""
    gestor = cfg.gestor_imagenes()
    return producir_video(largo.tema, largo.guion.idioma, "short", cfg, numero=numero, gestor=gestor,
                          progreso=progreso)
