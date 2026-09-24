"""Funciones auxiliares compartidas: fuentes, texto, audio, colores, rutas."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import unicodedata
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Iterable

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # entorno web ligero (Vercel): solo se usan las funciones de texto
    np = Image = ImageDraw = ImageFilter = ImageFont = None  # type: ignore[assignment]

from config import DIR_FUENTES

# pydub avisa si no hay ffmpeg en el PATH; usamos el binario de imageio-ffmpeg
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")
warnings.filterwarnings("ignore", message="Couldn't find ffprobe or avprobe")

# Paleta infantil de colores vivos (RGB)
PALETA = [
    (255, 89, 94),    # rojo coral
    (255, 202, 58),   # amarillo sol
    (138, 201, 38),   # verde lima
    (25, 130, 196),   # azul
    (106, 76, 147),   # morado
    (255, 146, 76),   # naranja
    (255, 112, 166),  # rosa
    (0, 187, 189),    # turquesa
]


# ---------------------------------------------------------------------------
# Texto y rutas
# ---------------------------------------------------------------------------
def slug(texto: str, max_len: int = 60) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:max_len].strip("-") or "video"


def hash_corto(*partes) -> str:
    h = hashlib.sha1(json.dumps(partes, sort_keys=True, default=str).encode()).hexdigest()
    return h[:12]


def formato_tiempo(segundos: float, horas: bool = False) -> str:
    s = int(round(segundos))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if horas or h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def formato_srt(segundos: float) -> str:
    ms = int(round(segundos * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def guardar_json(ruta: Path, datos) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return ruta


def leer_json(ruta: Path, defecto=None):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defecto


def dividir_frases(texto: str) -> list[str]:
    """Divide un texto en frases para insertar pausas entre ellas."""
    partes = re.split(r"(?<=[.!?¡¿…])\s+", texto.strip())
    return [p.strip() for p in partes if p.strip()]


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------
_FUENTES_SISTEMA = [
    # Fuentes redondeadas/infantiles si el usuario las añade a assets/fuentes
    "Fredoka-Bold.ttf", "Fredoka-SemiBold.ttf", "Fredoka[wdth,wght].ttf",
    "BalooBhai2-ExtraBold.ttf", "Baloo2-ExtraBold.ttf", "Nunito-Black.ttf",
    "Nunito-ExtraBold.ttf", "ComicNeue-Bold.ttf",
    # Sistema (Linux / macOS / Windows)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/Library/Fonts/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/comicbd.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


@lru_cache(maxsize=1)
def ruta_fuente() -> str | None:
    # 1) cualquier .ttf/.otf que el usuario haya puesto en assets/fuentes
    if DIR_FUENTES.exists():
        propias = sorted(list(DIR_FUENTES.glob("*.ttf")) + list(DIR_FUENTES.glob("*.otf")))
        for p in propias:
            if any(k in p.name.lower() for k in ("bold", "black", "heavy", "wght")):
                return str(p)
        if propias:
            return str(propias[0])
    for nombre in _FUENTES_SISTEMA:
        p = Path(nombre)
        if not p.is_absolute():
            p = DIR_FUENTES / nombre
        if p.exists():
            return str(p)
    return None


@lru_cache(maxsize=64)
def fuente(tamano: int) -> ImageFont.FreeTypeFont:
    ruta = ruta_fuente()
    if ruta:
        f = ImageFont.truetype(ruta, tamano)
        if "wght" in ruta or "[" in Path(ruta).name:  # fuente variable: usar peso grueso
            try:
                f.set_variation_by_axes([700])
            except Exception:  # noqa: BLE001
                pass
        return f
    return ImageFont.load_default(size=tamano)


def envolver_texto(texto: str, fnt: ImageFont.FreeTypeFont, ancho_max: int) -> list[str]:
    palabras = texto.split()
    lineas: list[str] = []
    actual = ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if fnt.getlength(prueba) <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def ajustar_fuente(texto: str, ancho_max: int, alto_max: int, tam_max: int, tam_min: int = 18,
                   max_lineas: int = 3) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Busca el tamaño de fuente más grande que hace caber el texto."""
    tam = tam_max
    while tam >= tam_min:
        f = fuente(tam)
        lineas = envolver_texto(texto, f, ancho_max)
        alto = len(lineas) * int(tam * 1.18)
        if len(lineas) <= max_lineas and alto <= alto_max and all(f.getlength(l) <= ancho_max for l in lineas):
            return f, lineas
        tam = int(tam * 0.9)
    f = fuente(tam_min)
    return f, envolver_texto(texto, f, ancho_max)


def texto_con_borde(draw: ImageDraw.ImageDraw, xy, texto: str, fnt, relleno=(255, 255, 255),
                    borde=(40, 40, 60), grosor: int = 6, anchor: str = "mm") -> None:
    draw.text(xy, texto, font=fnt, fill=relleno, anchor=anchor, stroke_width=grosor, stroke_fill=borde)


def bloque_texto(texto: str, ancho: int, alto_max: int, tam_max: int, relleno=(255, 255, 255),
                 borde=(35, 35, 70), fondo=(0, 0, 0, 120), max_lineas: int = 3,
                 margen: int = 24) -> Image.Image:
    """Imagen RGBA con el texto grande, borde grueso y caja semitransparente."""
    fnt, lineas = ajustar_fuente(texto, ancho - 2 * margen, alto_max - 2 * margen, tam_max,
                                 max_lineas=max_lineas)
    alto_linea = int(fnt.size * 1.18)
    grosor = max(3, fnt.size // 12)
    ancho_txt = int(max(fnt.getlength(l) for l in lineas)) + 2 * grosor if lineas else 10
    w = min(ancho, ancho_txt + 2 * margen)
    h = alto_linea * len(lineas) + 2 * margen
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if fondo:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=min(40, h // 3), fill=fondo)
    y = margen + alto_linea // 2
    for linea in lineas:
        texto_con_borde(d, (w // 2, y), linea, fnt, relleno, borde, grosor)
        y += alto_linea
    return img


# ---------------------------------------------------------------------------
# Imagen
# ---------------------------------------------------------------------------
def degradado(tamano: tuple[int, int], c1, c2, vertical: bool = True) -> Image.Image:
    w, h = tamano
    n = h if vertical else w
    t = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    fila = (np.array(c1, np.float32)[None, :] * (1 - t) + np.array(c2, np.float32)[None, :] * t)
    if vertical:
        arr = np.repeat(fila[:, None, :], w, axis=1)
    else:
        arr = np.repeat(fila[None, :, :], h, axis=0)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def rayos_sol(tamano: tuple[int, int], c1, c2, n: int = 16, centro=None) -> Image.Image:
    """Fondo de rayos de sol (clásico de miniaturas infantiles)."""
    import math

    w, h = tamano
    img = Image.new("RGB", tamano, c1)
    d = ImageDraw.Draw(img)
    cx, cy = centro or (w // 2, h // 2)
    r = int(math.hypot(w, h))
    for i in range(n):
        if i % 2:
            continue
        a1 = 2 * math.pi * i / n
        a2 = 2 * math.pi * (i + 1) / n
        d.polygon([(cx, cy), (cx + r * math.cos(a1), cy + r * math.sin(a1)),
                   (cx + r * math.cos(a2), cy + r * math.sin(a2))], fill=c2)
    return img


def ajustar_cubrir(img: Image.Image, tamano: tuple[int, int]) -> Image.Image:
    """Redimensiona y recorta la imagen para cubrir el tamaño (object-fit: cover)."""
    w, h = tamano
    iw, ih = img.size
    escala = max(w / iw, h / ih)
    nueva = img.resize((max(1, int(iw * escala + 0.5)), max(1, int(ih * escala + 0.5))), Image.LANCZOS)
    x = (nueva.width - w) // 2
    y = (nueva.height - h) // 2
    return nueva.crop((x, y, x + w, y + h))


def ajustar_contener(img: Image.Image, tamano: tuple[int, int]) -> Image.Image:
    w, h = tamano
    iw, ih = img.size
    escala = min(w / iw, h / ih)
    return img.resize((max(1, int(iw * escala)), max(1, int(ih * escala))), Image.LANCZOS)


def fondo_desenfocado(img: Image.Image, tamano: tuple[int, int]) -> Image.Image:
    """Imagen contenida sobre una versión desenfocada de sí misma (para cambiar aspecto)."""
    base = ajustar_cubrir(img.convert("RGB"), tamano).filter(ImageFilter.GaussianBlur(40))
    base = Image.blend(base, Image.new("RGB", tamano, (255, 255, 255)), 0.15)
    frente = ajustar_contener(img.convert("RGB"), (int(tamano[0] * 0.96), int(tamano[1] * 0.96)))
    base.paste(frente, ((tamano[0] - frente.width) // 2, (tamano[1] - frente.height) // 2))
    return base


def imagen_valida(ruta: Path) -> tuple[bool, str]:
    """Comprueba que la imagen abre, no está negra/vacía y tiene contenido."""
    try:
        with Image.open(ruta) as im:
            im.verify()
        with Image.open(ruta) as im:
            arr = np.asarray(im.convert("L").resize((64, 64)), dtype=np.float32)
    except Exception as e:  # noqa: BLE001
        return False, f"no se puede abrir ({e})"
    media, desv = float(arr.mean()), float(arr.std())
    if media < 12:
        return False, f"imagen casi negra (brillo {media:.0f})"
    if desv < 3:
        return False, f"imagen plana sin contenido (desv {desv:.1f})"
    return True, f"ok (brillo {media:.0f}, contraste {desv:.0f})"


# ---------------------------------------------------------------------------
# Audio (FFmpeg de imageio-ffmpeg, sin depender de ffmpeg del sistema)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return "ffmpeg"


def a_wav(origen: Path, destino: Path | None = None, sr: int = 44100) -> Path:
    """Convierte cualquier audio (mp3, ogg, m4a...) a WAV estéreo con FFmpeg."""
    origen = Path(origen)
    if destino is None:
        destino = Path(tempfile.mkstemp(suffix=".wav")[1])
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(origen), "-ar", str(sr), "-ac", "2", str(destino)]
    subprocess.run(cmd, check=True, capture_output=True)
    return Path(destino)


def cargar_audio(ruta: Path):
    """Carga un audio como pydub.AudioSegment sin necesitar ffprobe."""
    from pydub import AudioSegment

    ruta = Path(ruta)
    if ruta.suffix.lower() == ".wav":
        try:
            return AudioSegment.from_wav(ruta)
        except Exception:  # noqa: BLE001 - WAV raro: reconvertir
            pass
    tmp = a_wav(ruta)
    try:
        seg = AudioSegment.from_wav(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    return seg


def exportar_audio(seg, ruta: Path) -> Path:
    """Exporta un AudioSegment. WAV no requiere FFmpeg; mp3 usa el binario de imageio."""
    from pydub import AudioSegment

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.suffix.lower() == ".wav":
        seg.export(ruta, format="wav")
    else:
        AudioSegment.converter = ffmpeg_exe()
        seg.export(ruta, format=ruta.suffix.lstrip(".") or "mp3")
    return ruta


def primeros(iterable: Iterable, n: int) -> list:
    out = []
    for x in iterable:
        if len(out) >= n:
            break
        out.append(x)
    return out
