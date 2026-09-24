"""Música de fondo y efectos de sonido 100 % libres de derechos.

Fuentes:
  1. Música y efectos PROCEDURALES generados aquí (creación propia -> CC0).
     Siempre disponibles, sin internet y sin riesgo de Content ID.
  2. Freesound.org (API) filtrando SOLO licencia Creative Commons 0.
  3. Música propia subida por el usuario (Pixabay Music, YouTube Audio Library,
     composiciones propias...). Se guarda con un .json de licencia al lado.
"""
from __future__ import annotations

import math
import random
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import requests

from config import DIR_CACHE, DIR_EFECTOS, DIR_MUSICA, env
from utilidades import guardar_json, hash_corto, leer_json, slug

SR = 44100
EXTENSIONES_AUDIO = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}


@dataclass
class Pista:
    ruta: str
    titulo: str
    fuente: str
    licencia: str
    autor: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _guardar_wav(ruta: Path, audio: np.ndarray) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    pico = float(np.max(np.abs(audio))) or 1.0
    datos = (audio / pico * 0.89 * 32767).astype(np.int16)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(datos.tobytes())
    return ruta


# ---------------------------------------------------------------------------
# Sintetizador sencillo
# ---------------------------------------------------------------------------
def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _nota(freq: float, dur: float, timbre: str = "piano", vol: float = 1.0) -> np.ndarray:
    n = max(1, int(SR * dur))
    t = np.arange(n) / SR
    if timbre == "piano":  # piano de juguete / xilófono
        onda = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.12 * np.sin(6 * np.pi * freq * t)
        env = np.exp(-t * 5.5)
    elif timbre == "xilofono":
        onda = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 3.9 * t)
        env = np.exp(-t * 9)
    elif timbre == "bajo":
        onda = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)
        env = np.minimum(1, t * 40) * np.exp(-t * 2.5)
    else:  # pad suave
        onda = sum(np.sin(2 * np.pi * freq * (1 + d) * t) for d in (-0.003, 0, 0.003)) / 3
        env = np.minimum(1, t * 4) * np.minimum(1, (dur - t) * 4 + 0.01)
    ataque = np.minimum(1, t * 400)
    return (onda * env * ataque * vol).astype(np.float32)


def _bombo(dur=0.25) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    f = 110 * np.exp(-t * 18) + 45
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12)).astype(np.float32)


def _platillo(dur=0.07, rnd=None) -> np.ndarray:
    rnd = rnd or np.random.default_rng(1)
    n = int(SR * dur)
    ruido = rnd.standard_normal(n)
    ruido = np.diff(ruido, prepend=0)  # paso alto simple
    return (ruido * np.exp(-np.arange(n) / SR * 60) * 0.25).astype(np.float32)


def _palmada(rnd=None) -> np.ndarray:
    rnd = rnd or np.random.default_rng(2)
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    ruido = rnd.standard_normal(n)
    env = np.exp(-t * 35) + 0.5 * np.exp(-np.maximum(0, t - 0.01) * 40) * (t > 0.01)
    return (ruido * env * 0.35).astype(np.float32)


def _mezclar(buffer: np.ndarray, sonido: np.ndarray, inicio: float, pan: float = 0.0) -> None:
    i = int(inicio * SR)
    if i >= len(buffer):
        return
    s = sonido[: len(buffer) - i]
    izq, der = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buffer[i:i + len(s), 0] += s * izq
    buffer[i:i + len(s), 1] += s * der


PROGRESIONES = [[0, 7, 9, 5], [0, 5, 7, 0], [0, 9, 5, 7], [0, 5, 9, 7]]  # I-V-vi-IV etc. (semitonos)
TRIADAS = {0: [0, 4, 7], 7: [7, 11, 14], 9: [9, 12, 16], 5: [5, 9, 12], 2: [2, 5, 9]}
PENTATONICA = [0, 2, 4, 7, 9, 12, 14, 16]


def generar_musica(duracion: float, energia: str = "calma", semilla: int = 3, destino: Path | None = None) -> Path:
    """Compone una canción infantil instrumental (loop) y la guarda como WAV (CC0)."""
    bpm = {"calma": 96, "alegre": 112, "energica": 128}.get(energia, 104)
    clave = hash_corto("musica-v2", round(duracion), energia, semilla)
    destino = Path(destino or DIR_CACHE / "musica" / f"procedural_{energia}_{clave}.wav")
    if destino.exists():
        return destino
    rnd = random.Random(semilla)
    nrnd = np.random.default_rng(semilla)
    tonica = 60 + rnd.choice([0, 2, 5, 7])  # Do, Re, Fa o Sol mayor
    prog = rnd.choice(PROGRESIONES)
    negra = 60 / bpm
    compas = 4 * negra
    compases = 8
    loop = np.zeros((int(SR * compas * compases) + SR, 2), np.float32)

    # Motivo melódico de 2 compases que se repite con variaciones (memorable y repetitivo)
    motivo = []
    for _ in range(8):
        if rnd.random() < 0.18:
            motivo.append(None)
        else:
            motivo.append(rnd.choice(PENTATONICA[:6]))
    timbre = "xilofono" if energia == "energica" else "piano"
    for c in range(compases):
        grado = prog[c % 4]
        t0 = c * compas
        # Pad con el acorde
        for iv in TRIADAS[grado]:
            _mezclar(loop, _nota(_hz(tonica - 12 + iv), compas, "pad", 0.10), t0, pan=rnd.uniform(-0.3, 0.3))
        # Bajo
        for b in range(4 if energia != "calma" else 2):
            paso = negra if energia != "calma" else 2 * negra
            nota_bajo = tonica - 24 + grado + (7 if b % 2 and energia != "calma" else 0)
            _mezclar(loop, _nota(_hz(nota_bajo), paso * 0.95, "bajo", 0.35), t0 + b * paso)
        # Melodía en corcheas
        for k in range(8):
            nota = motivo[k] if c % 2 == 0 else (motivo[(k + 3) % 8] if rnd.random() < 0.5 else motivo[k])
            if nota is None or (energia == "calma" and k % 2):
                continue
            tri = TRIADAS[grado]
            if k in (0, 4):  # en tiempo fuerte, nota del acorde
                nota = rnd.choice(tri) % 12 + 12 * (nota // 12)
            _mezclar(loop, _nota(_hz(tonica + nota), negra * 0.9, timbre, 0.30), t0 + k * negra / 2, pan=0.15)
        # Percusión
        if energia != "calma":
            for b in range(4):
                if b % 2 == 0:
                    _mezclar(loop, _bombo() * 0.55, t0 + b * negra)
                else:
                    _mezclar(loop, _palmada(nrnd), t0 + b * negra, pan=-0.2)
                for h in range(2):
                    _mezclar(loop, _platillo(rnd=nrnd), t0 + b * negra + h * negra / 2, pan=0.3)
        else:
            _mezclar(loop, _platillo(0.12, nrnd) * 0.6, t0, pan=0.3)

    loop = loop[: int(SR * compas * compases)]
    reps = int(math.ceil(duracion / (compas * compases))) + 1
    pista = np.tile(loop, (reps, 1))[: int(SR * duracion)]
    fade = min(len(pista) // 4, int(SR * 1.5))
    rampa = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    pista[:fade] *= rampa
    pista[-fade:] *= rampa[::-1]
    _guardar_wav(destino, pista)
    guardar_json(destino.with_suffix(".json"), Pista(str(destino), f"EVR-KIDS {energia} #{semilla}",
                                                     "Generada por EVR-KIDS (procedural)",
                                                     "CC0 1.0 (creación propia, uso comercial libre)").to_dict())
    return destino


# ---------------------------------------------------------------------------
# Efectos de sonido
# ---------------------------------------------------------------------------
def _efecto(nombre: str) -> np.ndarray:
    rnd = np.random.default_rng(7)
    if nombre == "pop":
        t = np.arange(int(SR * 0.12)) / SR
        f = 300 + 900 * t / t[-1]
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30)
    if nombre == "ding":
        t = np.arange(int(SR * 0.9)) / SR
        return (np.sin(2 * np.pi * 1318.5 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t)
                + 0.3 * np.sin(2 * np.pi * 1975.5 * t)) * np.exp(-t * 5) * 0.6
    if nombre == "whoosh":
        n = int(SR * 0.5)
        t = np.arange(n) / SR
        ruido = rnd.standard_normal(n)
        # filtro paso bajo móvil
        salida = np.zeros(n)
        a_prev = 0.0
        for i in range(n):
            a = 0.02 + 0.3 * math.sin(math.pi * t[i] / t[-1])
            a_prev = a_prev + a * (ruido[i] - a_prev)
            salida[i] = a_prev
        return salida * np.sin(np.pi * t / t[-1]) * 1.5
    if nombre == "aplauso":
        total = np.zeros(int(SR * 1.2))
        for _ in range(28):
            i = int(rnd.uniform(0, 0.9) * SR)
            p = _palmada(rnd) * rnd.uniform(0.4, 1.0)
            total[i:i + len(p)] += p[: len(total) - i]
        t = np.arange(len(total)) / SR
        return total * np.minimum(1, (1.2 - t) * 3)
    raise ValueError(nombre)


EFECTOS_DISPONIBLES = ["pop", "ding", "whoosh", "aplauso"]


def ruta_efecto(nombre: str) -> Path | None:
    """Devuelve el efecto: primero uno subido por el usuario (assets/efectos/<nombre>.*), si no, el procedural."""
    if not nombre:
        return None
    for ext in EXTENSIONES_AUDIO:
        p = DIR_EFECTOS / f"{nombre}{ext}"
        if p.exists():
            return p
    destino = DIR_CACHE / "efectos" / f"{nombre}.wav"
    if not destino.exists():
        _guardar_wav(destino, _efecto(nombre).astype(np.float32))
    return destino


# ---------------------------------------------------------------------------
# Biblioteca, subida y Freesound
# ---------------------------------------------------------------------------
def listar_musica() -> list[Pista]:
    pistas = []
    if DIR_MUSICA.exists():
        for p in sorted(DIR_MUSICA.iterdir()):
            if p.suffix.lower() in EXTENSIONES_AUDIO:
                meta = leer_json(p.with_suffix(".json"), {}) or {}
                pistas.append(Pista(str(p), meta.get("titulo", p.stem), meta.get("fuente", "Subida por el usuario"),
                                    meta.get("licencia", "⚠️ sin declarar"), meta.get("autor", ""), meta.get("url", "")))
    return pistas


def guardar_musica_subida(nombre_archivo: str, contenido: bytes, licencia: str, fuente: str, autor: str = "",
                          url: str = "") -> Pista:
    DIR_MUSICA.mkdir(parents=True, exist_ok=True)
    ext = Path(nombre_archivo).suffix.lower() or ".mp3"
    destino = DIR_MUSICA / f"{slug(Path(nombre_archivo).stem)}{ext}"
    destino.write_bytes(contenido)
    pista = Pista(str(destino), Path(nombre_archivo).stem, fuente, licencia, autor, url)
    guardar_json(destino.with_suffix(".json"), {**pista.to_dict(), "titulo": pista.titulo})
    return pista


def buscar_freesound(consulta: str, max_resultados: int = 8, duracion_max: int = 240) -> list[dict]:
    """Busca en Freesound SOLO sonidos con licencia Creative Commons 0."""
    clave = env("FREESOUND_API_KEY")
    if not clave:
        raise RuntimeError("Falta FREESOUND_API_KEY")
    r = requests.get("https://freesound.org/apiv2/search/text/", params={
        "query": consulta, "token": clave, "page_size": max_resultados,
        "filter": f'license:"Creative Commons 0" duration:[1 TO {duracion_max}]',
        "fields": "id,name,username,license,url,previews,duration",
    }, timeout=60)
    r.raise_for_status()
    return r.json().get("results", [])


def descargar_freesound(resultado: dict, carpeta: Path = DIR_MUSICA) -> Pista:
    if "creativecommons.org/publicdomain/zero" not in resultado.get("license", "") and \
            "Creative Commons 0" not in resultado.get("license", ""):
        raise ValueError("Solo se permiten sonidos CC0")
    url = resultado["previews"]["preview-hq-mp3"]
    datos = requests.get(url, params={"token": env("FREESOUND_API_KEY")}, timeout=120).content
    destino = Path(carpeta) / f"freesound_{resultado['id']}_{slug(resultado['name'])[:40]}.mp3"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    pista = Pista(str(destino), resultado["name"], "Freesound.org", "CC0 1.0 (dominio público)",
                  resultado.get("username", ""), resultado.get("url", ""))
    guardar_json(destino.with_suffix(".json"), {**pista.to_dict(), "titulo": pista.titulo})
    return pista


def elegir_musica(formato: str, duracion: float, preferida: str | None = None, semilla: int = 3) -> Pista:
    """Pista de fondo para el video: la elegida por el usuario o una procedural (calma/energética)."""
    if preferida and Path(preferida).exists():
        meta = leer_json(Path(preferida).with_suffix(".json"), {}) or {}
        return Pista(preferida, meta.get("titulo", Path(preferida).stem), meta.get("fuente", "Usuario"),
                     meta.get("licencia", "⚠️ sin declarar"), meta.get("autor", ""), meta.get("url", ""))
    energia = "energica" if formato == "short" else "alegre"
    ruta = generar_musica(duracion + 2, energia, semilla)
    return Pista(str(ruta), f"EVR-KIDS {energia}", "Generada por EVR-KIDS (procedural)",
                 "CC0 1.0 (creación propia, uso comercial libre)")
