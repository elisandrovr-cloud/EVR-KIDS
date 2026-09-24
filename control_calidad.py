"""Control de calidad automático antes de exportar.

Verifica: duración según formato, audio completo (sin silencios largos),
subtítulos, imágenes válidas (ni rotas ni negras), miniatura, balance
voz/música, formato de video (16:9 o 9:16, 30 fps) y lenguaje apropiado.
Genera un informe con ✓ / ✗ y sugerencias de corrección.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from config import DURACION_LARGO, DURACION_SHORT, FPS
from generador_miniaturas import validar_miniatura
from utilidades import cargar_audio, formato_tiempo, imagen_valida

# Palabras que nunca deberían aparecer en contenido para niños de 2-5 años
PALABRAS_PROHIBIDAS = [
    "matar", "muerte", "muerto", "sangre", "arma", "pistola", "cuchillo", "odio", "estupido", "idiota", "tonto",
    "callate", "monstruo", "diablo", "infierno", "droga", "alcohol", "cerveza", "cigarro",
    "kill", "death", "dead", "blood", "weapon", "gun", "knife", "hate", "stupid", "idiot", "dumb", "shut up",
    "monster", "devil", "hell", "drug", "beer", "cigarette",
]


@dataclass
class Verificacion:
    nombre: str
    ok: bool
    detalle: str
    critico: bool = True
    correccion: str = ""  # acción automática disponible (clave) o sugerencia

    @property
    def icono(self) -> str:
        return "✓" if self.ok else ("✗" if self.critico else "⚠")


@dataclass
class InformeCalidad:
    video: str
    formato: str
    verificaciones: list[Verificacion] = field(default_factory=list)

    @property
    def aprobado(self) -> bool:
        return all(v.ok or not v.critico for v in self.verificaciones)

    @property
    def fallos(self) -> list[Verificacion]:
        return [v for v in self.verificaciones if not v.ok]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["aprobado"] = self.aprobado
        return d

    def a_markdown(self) -> str:
        estado = "✅ APROBADO" if self.aprobado else "❌ NO APROBADO"
        lineas = [f"# Informe de calidad — {estado}", "", f"- Video: `{Path(self.video).name}`",
                  f"- Formato: {self.formato}", "", "| | Verificación | Detalle | Corrección |", "|---|---|---|---|"]
        for v in self.verificaciones:
            lineas.append(f"| {v.icono} | {v.nombre} | {v.detalle} | {v.correccion if not v.ok else ''} |")
        return "\n".join(lineas) + "\n"


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def revisar_lenguaje(textos: list[str]) -> tuple[bool, str]:
    encontrados = set()
    for t in textos:
        tn = f" {re.sub(r'[^a-z ]', ' ', _norm(t))} "
        for p in PALABRAS_PROHIBIDAS:
            if f" {p} " in tn:
                encontrados.add(p)
    if encontrados:
        return False, "palabras no aptas: " + ", ".join(sorted(encontrados))
    return True, "lenguaje positivo y apto para 2-5 años"


def silencios_largos(ruta_audio: Path, min_ms: int, umbral_db: float = -45.0, ignorar_bordes_ms: int = 1200) -> list[tuple[int, int]]:
    from pydub.silence import detect_silence

    seg = cargar_audio(ruta_audio)
    res = detect_silence(seg, min_silence_len=min_ms, silence_thresh=umbral_db, seek_step=20)
    return [(a, b) for a, b in res if a > ignorar_bordes_ms and b < len(seg) - ignorar_bordes_ms]


def revisar_video(ruta_video: Path, guion, imagenes: dict[str, str], miniatura: Path | None,
                  ruta_srt: Path | None, ruta_mezcla: Path | None, estad_audio: dict | None) -> InformeCalidad:
    try:
        from moviepy import VideoFileClip
    except ImportError:  # MoviePy 1.x
        from moviepy.editor import VideoFileClip  # type: ignore

    formato = guion.formato
    inf = InformeCalidad(str(ruta_video), "YouTube Short (9:16)" if formato == "short" else "Video largo (16:9)")
    V = inf.verificaciones
    ruta_video = Path(ruta_video)
    if not ruta_video.exists():
        V.append(Verificacion("Archivo de video", False, "no existe", correccion="re-renderizar"))
        return inf

    clip = VideoFileClip(str(ruta_video))
    try:
        dur, (w, h), fps = clip.duration, clip.size, clip.fps
        # 1) Duración
        lo, hi = DURACION_SHORT if formato == "short" else DURACION_LARGO
        ok = lo <= dur <= hi
        sug = ("acortar: menos elementos o voz más rápida" if dur > hi else
               "alargar: variante «canta» o voz más lenta") if not ok else ""
        V.append(Verificacion("Duración", ok, f"{formato_tiempo(dur)} ({dur:.1f} s; rango {lo:.0f}-{hi:.0f} s)",
                              correccion=sug))
        # 2) Formato
        esperado = (9, 16) if formato == "short" else (16, 9)
        ok_ar = abs(w / h - esperado[0] / esperado[1]) < 0.01
        ok_fps = abs(fps - FPS) < 0.5
        tam_ok = (w, h) == (1080, 1920) if formato == "short" else (w, h) in ((1920, 1080), (1280, 720))
        V.append(Verificacion("Formato", ok_ar and ok_fps and tam_ok,
                              f"{w}x{h} ({'9:16' if h > w else '16:9'}) a {fps:.0f} fps", correccion="re-renderizar"))
        # 3) Fotogramas: ni negros ni vacíos (muestra 5 instantes)
        malos = []
        for t in np.linspace(1.0, max(1.0, dur - 1.2), 5):
            fr = clip.get_frame(float(t)).astype(np.float32)
            if fr.mean() < 15 or fr.std() < 4:
                malos.append(formato_tiempo(t))
        V.append(Verificacion("Fotogramas sin negro", not malos,
                              "5/5 fotogramas con contenido" if not malos else f"negros en {', '.join(malos)}",
                              correccion="regenerar imágenes"))
        # 4) Audio presente y completo
        tiene_audio = clip.audio is not None
        V.append(Verificacion("Pista de audio", tiene_audio,
                              f"AAC, {clip.audio.duration:.1f} s" if tiene_audio else "sin audio",
                              correccion="re-renderizar"))
    finally:
        clip.close()

    if ruta_mezcla and Path(ruta_mezcla).exists():
        huecos = silencios_largos(Path(ruta_mezcla), 2500)
        V.append(Verificacion("Audio sin silencios largos", not huecos,
                              "ningún silencio > 2,5 s" if not huecos else
                              f"{len(huecos)} silencio(s) > 2,5 s (p. ej. {formato_tiempo(huecos[0][0] / 1000)})",
                              correccion="subir música / revisar voz"))
        voz = Path(ruta_mezcla).with_name("pista_voz.wav")
        if voz.exists():
            huecos_voz = silencios_largos(voz, 4500)
            V.append(Verificacion("Narración continua", not huecos_voz,
                                  "sin pausas de voz > 4,5 s" if not huecos_voz else
                                  f"{len(huecos_voz)} pausa(s) de voz > 4,5 s", critico=False,
                                  correccion="reducir pausas entre frases"))
        mezcla_db = (estad_audio or {}).get("mezcla_dbfs")
        if mezcla_db is not None:
            V.append(Verificacion("Volumen general", -26 <= mezcla_db <= -10, f"{mezcla_db} dBFS (ideal -24 a -12)",
                                  critico=False, correccion="normalizar"))

    # 5) Balance voz / música
    if estad_audio and estad_audio.get("balance_db") is not None:
        b = estad_audio["balance_db"]
        ok = 8 <= b <= 30
        V.append(Verificacion("Balance voz/música", ok, f"voz {b:+.1f} dB sobre la música (ideal 8-30 dB)",
                              correccion="bajar música" if b < 8 else "subir música"))
    else:
        V.append(Verificacion("Balance voz/música", True, "sin música de fondo (solo voz)", critico=False))

    # 6) Subtítulos
    n_bloques = 0
    if ruta_srt and Path(ruta_srt).exists():
        n_bloques = len([b for b in Path(ruta_srt).read_text(encoding="utf-8").split("\n\n") if "-->" in b])
    vacios = [e.id for e in guion.escenas if not e.narracion.strip()]
    ok = n_bloques == len(guion.escenas) and not vacios
    V.append(Verificacion("Subtítulos", ok, f"{n_bloques} bloques .srt + incrustados en el video"
                          if ok else f"{n_bloques}/{len(guion.escenas)} bloques; vacíos: {vacios}",
                          correccion="regenerar subtítulos"))

    # 7) Imágenes
    malas = []
    for clave, ruta in imagenes.items():
        ok_img, det = imagen_valida(Path(ruta))
        if not ok_img:
            malas.append(f"{clave}: {det}")
    V.append(Verificacion("Imágenes válidas", not malas, f"{len(imagenes)} imágenes correctas" if not malas
                          else "; ".join(malas), correccion="regenerar imágenes"))

    # 8) Miniatura
    if miniatura:
        ok_m, det = validar_miniatura(miniatura)
        V.append(Verificacion("Miniatura", ok_m, det, correccion="regenerar miniatura"))
    else:
        V.append(Verificacion("Miniatura", False, "no generada", correccion="regenerar miniatura"))

    # 9) Estructura del Short: gancho en los primeros 3 s y llamado a la acción al final
    if formato == "short" and guion.escenas:
        g0 = guion.escenas[0]
        fin_gancho = g0.inicio + g0.duracion
        V.append(Verificacion("Gancho ≤ 3 s", g0.seccion == "gancho" and fin_gancho <= 3.6,
                              f"gancho «{g0.narracion}» termina en {fin_gancho:.1f} s",
                              critico=False, correccion="acortar la pregunta gancho"))
        V.append(Verificacion("Llamado a la acción", guion.escenas[-1].seccion == "cta",
                              f"«{guion.escenas[-1].narracion}»", critico=False, correccion="añadir CTA"))

    # 9) Lenguaje apropiado
    ok_l, det = revisar_lenguaje([e.narracion for e in guion.escenas] + [e.texto_pantalla for e in guion.escenas])
    V.append(Verificacion("Lenguaje apto (Made for Kids)", ok_l, det, correccion="editar guion"))
    return inf
