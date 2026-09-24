"""Ensamblaje de video con MoviePy + FFmpeg.

- Animaciones suaves: zoom (Ken Burns), paneo, rebote, destello entre escenas,
  aparición con "pop" de la palabra clave y burbujas flotantes.
- Subtítulos grandes y legibles (Pillow, sin depender de ImageMagick) + .srt.
- Mezcla de audio: voz + música (con volumen relativo y subida en la canción)
  + efectos de sonido.
- Salida: 16:9 (1920x1080 o 1280x720) o 9:16 (1080x1920), 30 fps, H.264/AAC.
"""
from __future__ import annotations

import bisect
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw

from config import Ajustes
from musica_efectos import Pista, ruta_efecto
from utilidades import (PALETA, ajustar_cubrir, bloque_texto, cargar_audio, exportar_audio, fondo_desenfocado,
                        formato_srt)

try:  # MoviePy 2.x
    from moviepy import AudioFileClip, VideoClip
except ImportError:  # MoviePy 1.x
    from moviepy.editor import AudioFileClip, VideoClip  # type: ignore

import proglog

MARGEN_INICIO = {"largo": 0.35, "short": 0.25}  # la voz empieza un poco después del corte


@dataclass
class ResultadoComposicion:
    video: Path
    srt: Path
    audio: Path
    duracion: float
    tamano: tuple[int, int]
    estadisticas_audio: dict = field(default_factory=dict)


class _LoggerProgreso(proglog.ProgressBarLogger):
    def __init__(self, callback: Callable[[float, str], None] | None):
        super().__init__()
        self.cb = callback
        self._ultimo = -1.0

    def bars_callback(self, bar, attr, value, old_value=None):
        if not self.cb or attr != "index":
            return
        total = self.bars[bar].get("total") or 0
        if total and bar in ("frame_index", "t"):
            f = value / total
            if f - self._ultimo >= 0.01 or f >= 1:
                self._ultimo = f
                self.cb(f, f"Renderizando video {int(f * 100)}%")


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
def mezclar_audio(guion, audios: list[Path], musica: Pista | None, volumen_musica: float, usar_efectos: bool,
                  destino: Path) -> dict:
    """Mezcla voz + música + efectos y devuelve estadísticas para el control de calidad."""
    from pydub import AudioSegment

    total_ms = int(math.ceil(guion.duracion_real * 1000)) + 200
    voz = AudioSegment.silent(duration=total_ms, frame_rate=44100).set_channels(2)
    sfx = AudioSegment.silent(duration=total_ms, frame_rate=44100).set_channels(2)
    margen = MARGEN_INICIO.get(guion.formato, 0.3)
    niveles_voz = []
    for esc, ruta in zip(guion.escenas, audios):
        seg = cargar_audio(ruta).set_frame_rate(44100).set_channels(2)
        if seg.dBFS != float("-inf"):
            niveles_voz.append(seg.dBFS)
        voz = voz.overlay(seg, position=int((esc.inicio + margen) * 1000))
        if usar_efectos and esc.sonido:
            ef = ruta_efecto(esc.sonido)
            if ef:
                efecto = cargar_audio(ef).set_frame_rate(44100).set_channels(2)
                efecto = efecto.apply_gain(-20 - efecto.dBFS) if efecto.dBFS != float("-inf") else efecto
                sfx = sfx.overlay(efecto, position=int(esc.inicio * 1000))

    # Normalizar la voz a ~ -18 dBFS de media (cómodo para YouTube)
    nivel_voz = float(np.mean(niveles_voz)) if niveles_voz else -20.0
    ajuste_voz = -18.0 - nivel_voz
    voz = voz.apply_gain(ajuste_voz)
    nivel_voz += ajuste_voz

    estad = {"voz_dbfs": round(nivel_voz, 1), "musica_dbfs": None, "balance_db": None,
             "musica": musica.to_dict() if musica else None}
    mezcla = voz.overlay(sfx)
    if musica and volumen_musica > 0:
        pista = cargar_audio(musica.ruta).set_frame_rate(44100).set_channels(2)
        while len(pista) < total_ms:
            pista += pista
        pista = pista[:total_ms]
        # volumen relativo: 1.0 = mismo nivel que la voz; 0.18 ≈ 15 dB por debajo
        separacion = -20 * math.log10(max(0.01, min(1.0, volumen_musica)))
        objetivo = nivel_voz - separacion
        pista = pista.apply_gain(objetivo - pista.dBFS)
        # Subir la música en la canción; bajarla un poco (ducking) en la lección
        trozos = []
        for esc in guion.escenas:
            a, b = int(esc.inicio * 1000), int((esc.inicio + esc.duracion) * 1000)
            t = pista[a:b]
            if esc.seccion == "cancion":
                t = t.apply_gain(+6)
            elif esc.seccion in ("leccion", "contenido"):
                t = t.apply_gain(-2)
            trozos.append(t)
        cola = pista[int(guion.duracion_real * 1000):]
        pista = sum(trozos[1:], trozos[0]) + cola if trozos else pista
        pista = pista.fade_in(800).fade_out(1500)
        estad["musica_dbfs"] = round(pista.dBFS, 1)
        estad["balance_db"] = round(nivel_voz - pista.dBFS, 1)
        mezcla = mezcla.overlay(pista)
    # Limitar picos
    if mezcla.max_dBFS > -1.0:
        mezcla = mezcla.apply_gain(-1.0 - mezcla.max_dBFS)
    exportar_audio(mezcla, destino)
    exportar_audio(voz, Path(destino).with_name("pista_voz.wav"))
    estad["mezcla_dbfs"] = round(mezcla.dBFS, 1)
    return estad


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------
@dataclass
class _EscenaRender:
    inicio: float
    duracion: float
    base: Image.Image
    efecto: str
    insignia: Image.Image | None
    subtitulo: Image.Image | None
    color: tuple[int, int, int]
    destello: bool
    burbujas: bool
    seccion: str


def _preparar_base(ruta: str, tam_base: tuple[int, int]) -> Image.Image:
    img = Image.open(ruta).convert("RGB")
    ar_img = img.width / img.height
    ar_out = tam_base[0] / tam_base[1]
    if abs(ar_img - ar_out) / ar_out < 0.12:
        return ajustar_cubrir(img, tam_base)
    return fondo_desenfocado(img, tam_base)


def _layout(W: int, H: int, vertical: bool) -> dict:
    if vertical:
        return {"insignia_y": int(H * 0.11), "insignia_h": int(H * 0.16), "insignia_tam": int(H * 0.062),
                "sub_y": int(H * 0.70), "sub_h": int(H * 0.18), "sub_tam": int(H * 0.048), "ancho": int(W * 0.92)}
    return {"insignia_y": int(H * 0.11), "insignia_h": int(H * 0.2), "insignia_tam": int(H * 0.11),
            "sub_y": int(H * 0.86), "sub_h": int(H * 0.22), "sub_tam": int(H * 0.068), "ancho": int(W * 0.9)}


def _preparar_escenas(guion, imagenes: dict[str, str], W: int, H: int) -> list[_EscenaRender]:
    vertical = H > W
    lay = _layout(W, H, vertical)
    tam_base = (int(W * 1.12), int(H * 1.12))
    cache_base: dict[str, Image.Image] = {}
    escenas: list[_EscenaRender] = []
    anterior = None
    colores = {}
    for i, esc in enumerate(guion.escenas):
        clave = esc.imagen if esc.imagen in imagenes else "portada"
        # Con motores IA existe también una "escena" ilustrada (sin texto) para intro/outro
        if clave == "portada" and "escena" in imagenes and esc.seccion in ("cancion", "repaso", "cta"):
            clave = "escena"
        if clave not in cache_base:
            cache_base[clave] = _preparar_base(imagenes[clave], tam_base)
        color = colores.setdefault(clave, PALETA[len(colores) % len(PALETA)])
        base = cache_base[clave]
        if esc.efecto == "misterio":  # imagen desenfocada: el niño tiene que adivinar
            from PIL import ImageFilter

            base = base.filter(ImageFilter.GaussianBlur(max(12, W // 40)))
        # Insignia con la palabra clave (gancho/cta: el texto de pantalla completo)
        texto_insignia = esc.texto_pantalla if esc.seccion in ("gancho", "cta") else esc.palabra
        insignia = None
        if texto_insignia:
            tam = lay["insignia_tam"] * (1.25 if esc.seccion == "gancho" else 1)
            insignia = bloque_texto(texto_insignia, lay["ancho"], int(lay["insignia_h"] * (1.6 if esc.seccion == "gancho" else 1)),
                                    int(tam), relleno=(255, 255, 255), borde=tuple(int(c * 0.45) for c in color),
                                    fondo=color + (235,), max_lineas=3 if esc.seccion in ("gancho", "cta") else 2)
        mostrar_sub = esc.seccion not in ("gancho",) and esc.narracion.strip() and esc.narracion != texto_insignia
        subtitulo = bloque_texto(esc.narracion, lay["ancho"], lay["sub_h"], lay["sub_tam"], relleno=(255, 255, 255),
                                 borde=(20, 20, 45), fondo=(0, 0, 0, 140), max_lineas=3) if mostrar_sub else None
        escenas.append(_EscenaRender(esc.inicio, esc.duracion, base, esc.efecto, insignia, subtitulo, color,
                                     destello=(clave != anterior and i > 0),
                                     burbujas=esc.seccion in ("intro", "cancion", "outro", "cta", "gancho"),
                                     seccion=esc.seccion))
        anterior = clave
    return escenas


def _suavizar(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def crear_funcion_cuadro(escenas: list[_EscenaRender], W: int, H: int, duracion_total: float, vertical: bool,
                         barra_progreso: bool = False) -> Callable[[float], np.ndarray]:
    inicios = [e.inicio for e in escenas]
    lay = _layout(W, H, vertical)
    rnd = random.Random(5)
    burbujas = [(rnd.random(), rnd.random(), rnd.uniform(10, 34), rnd.uniform(0.04, 0.12), rnd.choice(PALETA))
                for _ in range(16)]

    def cuadro(t: float) -> np.ndarray:
        i = max(0, bisect.bisect_right(inicios, t) - 1)
        e = escenas[i]
        u = t - e.inicio
        p = _suavizar(u / max(0.01, e.duracion))
        bw, bh = e.base.size
        # ---- movimiento de cámara ----
        if e.efecto == "zoom_in":
            z, ox, oy = 1.0 + 0.1 * p, 0.5, 0.5
        elif e.efecto == "zoom_out":
            z, ox, oy = 1.1 - 0.1 * p, 0.5, 0.5
        elif e.efecto == "pan_der":
            z, ox, oy = 1.05, 0.2 + 0.6 * p, 0.5
        elif e.efecto == "pan_izq":
            z, ox, oy = 1.05, 0.8 - 0.6 * p, 0.5
        elif e.efecto == "misterio":
            z, ox, oy = 1.0 + 0.04 * math.sin(u * 3), 0.5, 0.5
        else:  # rebote
            rebote = abs(math.sin(u * math.pi * 2.2)) * math.exp(-u * 2.5) * 0.05
            z, ox, oy = 1.02 + rebote + 0.03 * p, 0.5, 0.5 - rebote
        ww, hh = bw / (z * 1.0), bh / (z * 1.0)
        ww, hh = min(ww, bw), min(hh, bh)
        x0 = (bw - ww) * ox
        y0 = (bh - hh) * oy
        frame = e.base.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + ww, y0 + hh))
        d = ImageDraw.Draw(frame)
        # ---- burbujas flotantes ----
        if e.burbujas:
            for bx, by, br, vel, col in burbujas:
                yy = (by - vel * t) % 1.1 - 0.05
                xx = bx + 0.02 * math.sin(t * 2 + by * 10)
                r = br * (W / 1920 if not vertical else W / 1080)
                d.ellipse([xx * W - r, yy * H - r, xx * W + r, yy * H + r], outline=(255, 255, 255), width=3,
                          fill=col)
        # ---- insignia con "pop" ----
        if e.insignia is not None:
            s = 0.55 + 0.45 * _suavizar(u / 0.28) + 0.06 * math.sin(min(u, 0.6) / 0.6 * math.pi)
            ins = e.insignia
            if abs(s - 1) > 0.01:
                ins = ins.resize((max(1, int(ins.width * s)), max(1, int(ins.height * s))), Image.BILINEAR)
            if e.seccion in ("gancho", "cta"):
                centro_y = int(H * (0.3 if vertical else 0.4))
            else:
                centro_y = lay["insignia_y"] + e.insignia.height // 2 - int(H * 0.04)
            frame.paste(ins, (W // 2 - ins.width // 2, centro_y - ins.height // 2), ins)
        # ---- subtítulo ----
        if e.subtitulo is not None:
            sub = e.subtitulo
            alfa = _suavizar(u / 0.2)
            if alfa < 1:
                sub = sub.copy()
                sub.putalpha(sub.getchannel("A").point(lambda v: int(v * alfa)))
            frame.paste(sub, (W // 2 - sub.width // 2, lay["sub_y"] - sub.height // 2), sub)
        # ---- barra de progreso (Shorts) ----
        if barra_progreso:
            alto = max(8, H // 160)
            d.rectangle([0, 0, W, alto], fill=(255, 255, 255))
            d.rectangle([0, 0, int(W * t / max(0.1, duracion_total)), alto], fill=e.color)
        arr = np.asarray(frame, dtype=np.uint8)
        # ---- transiciones: destello blanco al cambiar de imagen, fundidos al inicio/fin ----
        factor, color = 0.0, 255.0
        if e.destello and u < 0.22:
            factor = (1 - u / 0.22) * 0.75
        if t < 0.4:
            factor, color = 1 - t / 0.4, 255.0
        if duracion_total - t < 0.8:
            factor, color = 1 - (duracion_total - t) / 0.8, 0.0
        if factor > 0.001:
            arr = (arr.astype(np.float32) * (1 - factor) + color * factor).astype(np.uint8)
        return arr

    return cuadro


def escribir_srt(guion, ruta: Path) -> Path:
    margen = MARGEN_INICIO.get(guion.formato, 0.3)
    bloques = []
    for n, esc in enumerate(guion.escenas, 1):
        ini = esc.inicio + margen
        fin = max(ini + 0.5, esc.inicio + esc.duracion - 0.1)
        bloques.append(f"{n}\n{formato_srt(ini)} --> {formato_srt(fin)}\n{esc.narracion}\n")
    Path(ruta).write_text("\n".join(bloques), encoding="utf-8")
    return Path(ruta)


def componer_video(guion, imagenes: dict[str, str], audios: list[Path], salida: Path, ajustes: Ajustes,
                   musica: Pista | None, progreso: Callable[[float, str], None] | None = None) -> ResultadoComposicion:
    """Renderiza el video final (MP4) con audio mezclado y subtítulos incrustados."""
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    W, H = ajustes.tamano(guion.formato)
    vertical = guion.formato == "short"
    if progreso:
        progreso(0.0, "Mezclando audio")
    ruta_audio = salida.with_name(salida.stem + "_mezcla.wav")
    estad = mezclar_audio(guion, audios, musica, ajustes.volumen_musica, ajustes.usar_efectos, ruta_audio)
    srt = escribir_srt(guion, salida.with_suffix(".srt"))

    if progreso:
        progreso(0.02, "Preparando escenas")
    escenas = _preparar_escenas(guion, imagenes, W, H)
    duracion = guion.duracion_real
    clip = VideoClip(crear_funcion_cuadro(escenas, W, H, duracion, vertical, barra_progreso=vertical),
                     duration=duracion)
    audio = AudioFileClip(str(ruta_audio))
    if audio.duration > duracion:
        audio = audio.subclipped(0, duracion) if hasattr(audio, "subclipped") else audio.subclip(0, duracion)
    clip = clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)
    logger = _LoggerProgreso(progreso) if progreso else None
    clip.write_videofile(str(salida), fps=ajustes.fps, codec="libx264", audio_codec="aac", audio_bitrate="192k",
                         preset=ajustes.preset_x264, threads=ajustes.hilos,
                         temp_audiofile=str(salida.with_name(salida.stem + "_tmp_audio.m4a")),
                         ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart", "-crf", "20"],
                         logger=logger)
    audio.close()
    clip.close()
    if progreso:
        progreso(1.0, "Video renderizado")
    return ResultadoComposicion(salida, srt, ruta_audio, duracion, (W, H), estad)


def fotograma(guion, imagenes: dict[str, str], ajustes: Ajustes, t: float) -> Image.Image:
    """Vista previa rápida de un fotograma (sin renderizar el video)."""
    W, H = ajustes.tamano(guion.formato)
    if not guion.duracion_real:
        guion.aplicar_duraciones([e.duracion_est for e in guion.escenas])
    escenas = _preparar_escenas(guion, imagenes, W, H)
    f = crear_funcion_cuadro(escenas, W, H, guion.duracion_real, H > W, barra_progreso=H > W)
    return Image.fromarray(f(t))
