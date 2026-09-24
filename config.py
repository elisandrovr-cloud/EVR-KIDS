"""Configuración global de EVR-KIDS.

Lee variables del archivo .env (ver .env.example) y expone constantes y
ajustes compartidos por todos los módulos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv es opcional en tiempo de ejecución
    pass

RAIZ = Path(__file__).resolve().parent


def env(nombre: str, defecto: str = "") -> str:
    """Devuelve una variable de entorno sin espacios (o el valor por defecto)."""
    valor = os.getenv(nombre, "")
    valor = valor.strip() if valor else ""
    return valor or defecto


def _ruta(nombre: str, defecto: str) -> Path:
    p = Path(env(nombre, defecto))
    return p if p.is_absolute() else RAIZ / p


DIR_SALIDA = _ruta("EVR_DIR_SALIDA", "salida")
DIR_TRABAJO = _ruta("EVR_DIR_TRABAJO", "trabajo")
DIR_CACHE = _ruta("EVR_DIR_CACHE", "cache")
DIR_ASSETS = RAIZ / "assets"
DIR_MUSICA = DIR_ASSETS / "musica"
DIR_EFECTOS = DIR_ASSETS / "efectos"
DIR_FUENTES = DIR_ASSETS / "fuentes"
DIR_DATOS = RAIZ / "datos"
ARCHIVO_PERFILES_VOZ = DIR_DATOS / "perfiles_voz.json"

FPS = 30

# Resoluciones de salida
RESOLUCIONES = {
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "short": (1080, 1920),
}
TAMANO_MINIATURA = (1280, 720)

# Límites de duración (segundos) según el formato
DURACION_LARGO = (120.0, 300.0)
DURACION_SHORT = (15.0, 60.0)

IDIOMAS = {"es": "Español", "en": "English"}

AVISO_MADE_FOR_KIDS = (
    "⚠️ CONTENIDO PARA NIÑOS (Made for Kids / COPPA)\n"
    "Al subir este video a YouTube marca: «Sí, es contenido creado para niños».\n"
    "Consecuencias: comentarios desactivados, sin anuncios personalizados, sin "
    "notificaciones de campana ni miniplayer, y sin tarjetas/pantallas finales "
    "interactivas. No lo marques como «no es para niños»: la FTC y YouTube pueden "
    "sancionar el etiquetado incorrecto.\n"
    "Todo el material (imágenes, voces, música y efectos) proviene de fuentes CC0, "
    "dominio público, generación propia o licencias que permiten el uso comercial. "
    "Revisa creditos.json antes de publicar."
)


@dataclass
class Ajustes:
    """Ajustes de producción que se pasan por todo el pipeline."""

    resolucion: str = field(default_factory=lambda: env("EVR_RESOLUCION", "1080p"))
    fps: int = FPS
    preset_x264: str = field(default_factory=lambda: env("EVR_PRESET_X264", "medium"))
    estilo_imagen: str = "cartoon"
    motor_imagen: str = "procedural"
    volumen_musica: float = 0.18  # relativo a la voz (0-1)
    usar_efectos: bool = True
    texto_cta: str = ""  # vacío = texto por defecto según idioma
    hilos: int = max(1, (os.cpu_count() or 2) - 1)

    def tamano(self, formato: str) -> tuple[int, int]:
        if formato == "short":
            return RESOLUCIONES["short"]
        return RESOLUCIONES.get(self.resolucion, RESOLUCIONES["1080p"])


def asegurar_carpetas() -> None:
    for d in (DIR_SALIDA, DIR_TRABAJO, DIR_CACHE, DIR_MUSICA, DIR_EFECTOS, DIR_FUENTES, DIR_DATOS):
        d.mkdir(parents=True, exist_ok=True)


def estado_claves() -> dict[str, bool]:
    """Indica qué servicios externos están configurados (para la UI)."""
    nombres = {
        "Claude (guiones IA)": "ANTHROPIC_API_KEY",
        "Pixabay": "PIXABAY_API_KEY",
        "Pexels": "PEXELS_API_KEY",
        "Unsplash": "UNSPLASH_ACCESS_KEY",
        "Stability AI": "STABILITY_API_KEY",
        "Replicate": "REPLICATE_API_TOKEN",
        "Hugging Face": "HF_API_TOKEN",
        "ElevenLabs": "ELEVENLABS_API_KEY",
        "Azure TTS": "AZURE_SPEECH_KEY",
        "Amazon Polly": "AWS_ACCESS_KEY_ID",
        "Freesound": "FREESOUND_API_KEY",
    }
    return {k: bool(env(v)) for k, v in nombres.items()}
