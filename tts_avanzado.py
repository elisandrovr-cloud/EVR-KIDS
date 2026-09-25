"""Sistema de voz avanzado (Text-to-Speech) para narración infantil.

Motores:
  - edge      : edge-tts (gratuito, voces neuronales de Microsoft) ← por defecto
  - elevenlabs: ElevenLabs API (muy natural, de pago)
  - azure     : Azure Speech (SSML con estilos emocionales reales)
  - polly     : Amazon Polly (incluye voces infantiles: Ivy, Justin, Kevin)
  - gtts      : Google Translate TTS (gratuito, calidad básica)
  - prueba    : sin red; tonos sintéticos para probar el pipeline (no publicar)

Controles: idioma, género, edad, acento, velocidad (muy lenta/lenta/normal +
ajuste fino), tono (Hz), volumen relativo, pausa entre frases, estilo
emocional, vista previa y perfiles favoritos guardados en datos/perfiles_voz.json.
"""
from __future__ import annotations

import asyncio
import math
import os
import subprocess
import threading
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Callable
from xml.sax.saxutils import escape

import numpy as np
import requests

from config import ARCHIVO_PERFILES_VOZ, DIR_CACHE, env
from utilidades import cargar_audio, dividir_frases, exportar_audio, ffmpeg_exe, guardar_json, hash_corto, leer_json

# ---------------------------------------------------------------------------
# Catálogo de voces (curado para contenido infantil)
# edad: niño | joven | adulto. "tono_extra" simula voces infantiles/jóvenes.
# ---------------------------------------------------------------------------
CATALOGO_VOCES: list[dict] = [
    # ---- edge-tts / Azure (mismos nombres de voz) ----
    {"motor": "edge", "id": "es-MX-DaliaNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "México"},
    {"motor": "edge", "id": "es-MX-JorgeNeural", "idioma": "es", "genero": "masculino", "edad": "adulto", "acento": "México"},
    {"motor": "edge", "id": "es-ES-ElviraNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "España"},
    {"motor": "edge", "id": "es-ES-AlvaroNeural", "idioma": "es", "genero": "masculino", "edad": "adulto", "acento": "España"},
    {"motor": "edge", "id": "es-US-PalomaNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "EE. UU. (latino)"},
    {"motor": "edge", "id": "es-US-AlonsoNeural", "idioma": "es", "genero": "masculino", "edad": "adulto", "acento": "EE. UU. (latino)"},
    {"motor": "edge", "id": "es-CO-SalomeNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "Colombia"},
    {"motor": "edge", "id": "es-AR-ElenaNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "Argentina"},
    {"motor": "edge", "id": "es-MX-DaliaNeural", "idioma": "es", "genero": "femenino", "edad": "joven", "acento": "México",
     "tono_extra": 12, "nota": "joven (simulada subiendo el tono)"},
    {"motor": "edge", "id": "es-MX-DaliaNeural", "idioma": "es", "genero": "femenino", "edad": "niño", "acento": "México",
     "tono_extra": 28, "nota": "infantil (simulada subiendo el tono)"},
    {"motor": "edge", "id": "es-MX-JorgeNeural", "idioma": "es", "genero": "masculino", "edad": "niño", "acento": "México",
     "tono_extra": 35, "nota": "infantil (simulada subiendo el tono)"},
    {"motor": "edge", "id": "en-US-AnaNeural", "idioma": "en", "genero": "femenino", "edad": "niño", "acento": "EE. UU."},
    {"motor": "edge", "id": "en-GB-MaisieNeural", "idioma": "en", "genero": "femenino", "edad": "niño", "acento": "Reino Unido"},
    {"motor": "edge", "id": "en-US-JennyNeural", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "EE. UU."},
    {"motor": "edge", "id": "en-US-AriaNeural", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "EE. UU."},
    {"motor": "edge", "id": "en-US-GuyNeural", "idioma": "en", "genero": "masculino", "edad": "adulto", "acento": "EE. UU."},
    {"motor": "edge", "id": "en-GB-SoniaNeural", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "Reino Unido"},
    {"motor": "edge", "id": "en-GB-RyanNeural", "idioma": "en", "genero": "masculino", "edad": "adulto", "acento": "Reino Unido"},
    {"motor": "edge", "id": "en-AU-NatashaNeural", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "Australia"},
    {"motor": "edge", "id": "en-US-JennyNeural", "idioma": "en", "genero": "femenino", "edad": "joven", "acento": "EE. UU.",
     "tono_extra": 10, "nota": "joven (simulada subiendo el tono)"},
    # ---- Azure (estilos emocionales reales vía SSML) ----
    {"motor": "azure", "id": "es-MX-DaliaNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "México"},
    {"motor": "azure", "id": "es-MX-JorgeNeural", "idioma": "es", "genero": "masculino", "edad": "adulto", "acento": "México"},
    {"motor": "azure", "id": "es-ES-ElviraNeural", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "España"},
    {"motor": "azure", "id": "en-US-JennyNeural", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "EE. UU."},
    {"motor": "azure", "id": "en-US-AriaNeural", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "EE. UU."},
    {"motor": "azure", "id": "en-US-AnaNeural", "idioma": "en", "genero": "femenino", "edad": "niño", "acento": "EE. UU."},
    # ---- Amazon Polly (neural) ----
    {"motor": "polly", "id": "Mia", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "México"},
    {"motor": "polly", "id": "Lupe", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "EE. UU. (latino)"},
    {"motor": "polly", "id": "Pedro", "idioma": "es", "genero": "masculino", "edad": "adulto", "acento": "EE. UU. (latino)"},
    {"motor": "polly", "id": "Lucia", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "España"},
    {"motor": "polly", "id": "Ivy", "idioma": "en", "genero": "femenino", "edad": "niño", "acento": "EE. UU."},
    {"motor": "polly", "id": "Justin", "idioma": "en", "genero": "masculino", "edad": "niño", "acento": "EE. UU."},
    {"motor": "polly", "id": "Kevin", "idioma": "en", "genero": "masculino", "edad": "niño", "acento": "EE. UU."},
    {"motor": "polly", "id": "Joanna", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "EE. UU."},
    # ---- ElevenLabs (voces predefinidas multilingües; añade las tuyas por ID) ----
    {"motor": "elevenlabs", "id": "21m00Tcm4TlvDq8ikWAM", "nombre": "Rachel", "idioma": "multi", "genero": "femenino", "edad": "adulto", "acento": "multilingüe"},
    {"motor": "elevenlabs", "id": "EXAVITQu4vr4xnSDxMaL", "nombre": "Sarah", "idioma": "multi", "genero": "femenino", "edad": "joven", "acento": "multilingüe"},
    {"motor": "elevenlabs", "id": "TX3LPaxmHKxFdv7VOQHJ", "nombre": "Liam", "idioma": "multi", "genero": "masculino", "edad": "joven", "acento": "multilingüe"},
    # ---- gTTS (el acento se elige con el dominio) ----
    {"motor": "gtts", "id": "com.mx", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "México"},
    {"motor": "gtts", "id": "es", "idioma": "es", "genero": "femenino", "edad": "adulto", "acento": "España"},
    {"motor": "gtts", "id": "us", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "EE. UU."},
    {"motor": "gtts", "id": "co.uk", "idioma": "en", "genero": "femenino", "edad": "adulto", "acento": "Reino Unido"},
    # ---- prueba (offline) ----
    {"motor": "prueba", "id": "tono", "idioma": "multi", "genero": "neutro", "edad": "adulto", "acento": "—"},
]

MOTORES_TTS = {
    "edge": "edge-tts (gratis) ★ recomendado",
    "elevenlabs": "ElevenLabs",
    "azure": "Azure TTS (estilos emocionales)",
    "polly": "Amazon Polly (voces infantiles EN)",
    "gtts": "gTTS (Google, básico)",
    "prueba": "Prueba offline (sin voz real)",
}

VELOCIDADES = {"muy_lenta": -30, "lenta": -15, "normal": 0, "rapida": 12}
NOMBRES_VELOCIDAD = {"muy_lenta": "Muy lenta", "lenta": "Lenta", "normal": "Normal", "rapida": "Rápida (Shorts)"}

# Estilo emocional: ajustes de prosodia (todos los motores) + estilo nativo (Azure / ElevenLabs)
ESTILOS_EMOCION = {
    "neutral": {"tasa": 0, "tono": 0, "azure": None, "eleven_style": 0.0, "eleven_stab": 0.5},
    "alegre": {"tasa": 4, "tono": 6, "azure": "cheerful", "eleven_style": 0.45, "eleven_stab": 0.35},
    "entusiasta": {"tasa": 8, "tono": 10, "azure": "excited", "eleven_style": 0.7, "eleven_stab": 0.3},
    "calmado": {"tasa": -8, "tono": -3, "azure": "gentle", "eleven_style": 0.1, "eleven_stab": 0.7},
    "amable": {"tasa": 0, "tono": 3, "azure": "friendly", "eleven_style": 0.3, "eleven_stab": 0.5},
    "cuentacuentos": {"tasa": -5, "tono": 2, "azure": "narration-relaxed", "eleven_style": 0.35, "eleven_stab": 0.45},
}


@dataclass
class PerfilVoz:
    nombre: str = "Maestra alegre (ES)"
    motor: str = "edge"
    idioma: str = "es"
    voz: str = "es-MX-DaliaNeural"
    velocidad: str = "lenta"
    ajuste_velocidad: int = 0  # % adicional (-30 .. +30)
    tono_hz: int = 0  # -30 .. +40 Hz
    volumen_pct: int = 0  # volumen del motor (-50 .. +50 %)
    ganancia_db: float = 0.0  # ganancia posterior (volumen relativo)
    pausa_frases: float = 0.45  # segundos de silencio entre frases
    estilo: str = "alegre"
    tono_extra: int = 0  # para voces infantiles simuladas
    extra: dict = field(default_factory=dict)

    # -- valores efectivos --------------------------------------------------
    def tasa_total(self) -> int:
        return VELOCIDADES.get(self.velocidad, 0) + self.ajuste_velocidad + ESTILOS_EMOCION.get(self.estilo, {}).get("tasa", 0)

    def tono_total(self) -> int:
        return self.tono_hz + self.tono_extra + ESTILOS_EMOCION.get(self.estilo, {}).get("tono", 0)

    def variante(self, **cambios) -> "PerfilVoz":
        return replace(self, **cambios)

    def clave_cache(self, texto: str) -> str:
        return hash_corto(texto, self.motor, self.voz, self.tasa_total(), self.tono_total(), self.volumen_pct,
                          self.estilo, self.idioma, self.extra)

    def to_dict(self) -> dict:
        return asdict(self)


PERFILES_PREDEFINIDOS = [
    PerfilVoz("Maestra alegre (ES)", "edge", "es", "es-MX-DaliaNeural", "lenta", estilo="alegre"),
    PerfilVoz("Maestro amable (ES)", "edge", "es", "es-MX-JorgeNeural", "lenta", estilo="amable"),
    PerfilVoz("Niña (ES, simulada)", "edge", "es", "es-MX-DaliaNeural", "lenta", estilo="alegre", tono_extra=28),
    PerfilVoz("Cuento calmado (ES)", "edge", "es", "es-ES-ElviraNeural", "muy_lenta", estilo="calmado", pausa_frases=0.7),
    PerfilVoz("Teacher cheerful (EN)", "edge", "en", "en-US-JennyNeural", "lenta", estilo="alegre"),
    PerfilVoz("Kid voice (EN)", "edge", "en", "en-US-AnaNeural", "lenta", estilo="alegre"),
    PerfilVoz("Calm storyteller (EN)", "edge", "en", "en-GB-SoniaNeural", "muy_lenta", estilo="calmado", pausa_frases=0.7),
]


def perfil_por_defecto(idioma: str) -> PerfilVoz:
    return next(p for p in PERFILES_PREDEFINIDOS if p.idioma == idioma)


# ---------------------------------------------------------------------------
# Perfiles favoritos
# ---------------------------------------------------------------------------
def cargar_perfiles() -> dict[str, PerfilVoz]:
    perfiles = {p.nombre: p for p in PERFILES_PREDEFINIDOS}
    for d in leer_json(ARCHIVO_PERFILES_VOZ, []) or []:
        try:
            p = PerfilVoz(**d)
            perfiles[p.nombre] = p
        except TypeError:
            continue
    return perfiles


def guardar_perfil(perfil: PerfilVoz) -> None:
    datos = [d for d in (leer_json(ARCHIVO_PERFILES_VOZ, []) or []) if d.get("nombre") != perfil.nombre]
    datos.append(perfil.to_dict())
    guardar_json(ARCHIVO_PERFILES_VOZ, datos)


def eliminar_perfil(nombre: str) -> None:
    datos = [d for d in (leer_json(ARCHIVO_PERFILES_VOZ, []) or []) if d.get("nombre") != nombre]
    guardar_json(ARCHIVO_PERFILES_VOZ, datos)


def filtrar_voces(motor: str | None = None, idioma: str | None = None, genero: str | None = None,
                  edad: str | None = None, acento: str | None = None) -> list[dict]:
    res = []
    for v in CATALOGO_VOCES:
        if motor and v["motor"] != motor:
            continue
        if idioma and v["idioma"] not in (idioma, "multi"):
            continue
        if genero and genero != "todos" and v["genero"] != genero:
            continue
        if edad and edad != "todas" and v["edad"] != edad:
            continue
        if acento and acento != "todos" and v["acento"] != acento:
            continue
        res.append(v)
    return res


def etiqueta_voz(v: dict) -> str:
    nombre = v.get("nombre") or v["id"]
    nota = f" — {v['nota']}" if v.get("nota") else ""
    return f"{nombre} · {v['genero']} · {v['edad']} · {v['acento']}{nota}"


def listar_voces_edge(idioma: str | None = None) -> list[dict]:
    """Lista completa de voces de edge-tts (requiere internet)."""
    import edge_tts

    voces = _ejecutar_async(edge_tts.list_voices())
    out = []
    for v in voces:
        if idioma and not v["Locale"].lower().startswith(idioma):
            continue
        out.append({"motor": "edge", "id": v["ShortName"], "idioma": v["Locale"][:2],
                    "genero": "femenino" if v["Gender"] == "Female" else "masculino", "edad": "adulto",
                    "acento": v["Locale"]})
    return out


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _ejecutar_async(coro):
    """Ejecuta una corrutina aunque ya haya un event loop activo (p. ej. dentro de Streamlit)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    resultado: dict = {}

    def _hilo():
        try:
            resultado["v"] = asyncio.run(coro)
        except BaseException as e:  # noqa: BLE001
            resultado["e"] = e

    t = threading.Thread(target=_hilo)
    t.start()
    t.join()
    if "e" in resultado:
        raise resultado["e"]
    return resultado.get("v")


def ajustar_audio_ffmpeg(origen: Path, destino: Path, tasa_pct: int = 0, tono_hz: int = 0) -> Path:
    """Cambia velocidad (sin alterar el tono) y tono (≈ Hz -> semitonos) para motores sin prosodia nativa."""
    filtros = []
    if tono_hz:
        semitonos = tono_hz / 12.0  # aproximación: ~12 Hz ≈ 1 semitono en voz hablada
        factor = 2 ** (semitonos / 12)
        filtros += [f"asetrate=44100*{factor:.4f}", "aresample=44100", f"atempo={1 / factor:.4f}"]
    if tasa_pct:
        tempo = max(0.5, min(2.0, 1 + tasa_pct / 100))
        filtros.append(f"atempo={tempo:.4f}")
    if not filtros:
        if Path(origen) != Path(destino):
            Path(destino).write_bytes(Path(origen).read_bytes())
        return Path(destino)
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(origen), "-ar", "44100",
                    "-af", ",".join(filtros), str(destino)], check=True, capture_output=True)
    return Path(destino)


# ---------------------------------------------------------------------------
# Motores
# ---------------------------------------------------------------------------
def _edge(texto: str, p: PerfilVoz, destino: Path) -> Path:
    import edge_tts

    com = edge_tts.Communicate(texto, p.voz, rate=f"{p.tasa_total():+d}%", pitch=f"{p.tono_total():+d}Hz",
                               volume=f"{p.volumen_pct:+d}%")
    _ejecutar_async(com.save(str(destino)))
    if not destino.exists() or destino.stat().st_size < 200:
        raise RuntimeError("edge-tts no devolvió audio (¿sin conexión?)")
    return destino


def _azure(texto: str, p: PerfilVoz, destino: Path) -> Path:
    clave, region = env("AZURE_SPEECH_KEY"), env("AZURE_SPEECH_REGION", "eastus")
    if not clave:
        raise RuntimeError("Falta AZURE_SPEECH_KEY")
    estilo = ESTILOS_EMOCION.get(p.estilo, {}).get("azure")
    locale = "-".join(p.voz.split("-")[:2])
    prosodia = (f'<prosody rate="{p.tasa_total():+d}%" pitch="{p.tono_total():+d}Hz" '
                f'volume="{p.volumen_pct:+d}%">{escape(texto)}</prosody>')
    cuerpo = f'<mstts:express-as style="{estilo}">{prosodia}</mstts:express-as>' if estilo else prosodia
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{locale}">'
            f'<voice name="{p.voz}">{cuerpo}</voice></speak>')
    r = requests.post(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml.encode("utf-8"),
                      headers={"Ocp-Apim-Subscription-Key": clave, "Content-Type": "application/ssml+xml",
                               "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                               "User-Agent": "EVR-KIDS"}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Azure TTS error {r.status_code}: {r.text[:200]}")
    destino.write_bytes(r.content)
    return destino


def _elevenlabs(texto: str, p: PerfilVoz, destino: Path) -> Path:
    clave = env("ELEVENLABS_API_KEY")
    if not clave:
        raise RuntimeError("Falta ELEVENLABS_API_KEY")
    emo = ESTILOS_EMOCION.get(p.estilo, ESTILOS_EMOCION["neutral"])
    velocidad = max(0.7, min(1.2, 1 + p.tasa_total() / 100))
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{p.voz}",
                      params={"output_format": "mp3_44100_128"},
                      headers={"xi-api-key": clave, "Content-Type": "application/json"},
                      json={"text": texto, "model_id": env("ELEVENLABS_MODELO", "eleven_multilingual_v2"),
                            "language_code": p.idioma,
                            "voice_settings": {"stability": emo["eleven_stab"], "similarity_boost": 0.75,
                                               "style": emo["eleven_style"], "use_speaker_boost": True,
                                               "speed": round(velocidad, 2)}}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
    crudo = destino.with_suffix(".raw.mp3")
    crudo.write_bytes(r.content)
    ajustar_audio_ffmpeg(crudo, destino, 0, p.tono_total())  # ElevenLabs no tiene control de tono
    crudo.unlink(missing_ok=True)
    return destino


def _polly(texto: str, p: PerfilVoz, destino: Path) -> Path:
    import boto3

    cliente = boto3.client("polly", region_name=env("AWS_DEFAULT_REGION", "us-east-1"))
    ssml = f'<speak><prosody rate="{100 + p.tasa_total()}%" volume="{p.volumen_pct:+d}dB">{escape(texto)}</prosody></speak>'
    try:
        resp = cliente.synthesize_speech(Text=ssml, TextType="ssml", VoiceId=p.voz, Engine="neural", OutputFormat="mp3")
    except Exception:  # noqa: BLE001 - algunas voces solo existen en motor estándar
        resp = cliente.synthesize_speech(Text=ssml, TextType="ssml", VoiceId=p.voz, Engine="standard", OutputFormat="mp3")
    crudo = destino.with_suffix(".raw.mp3")
    crudo.write_bytes(resp["AudioStream"].read())
    ajustar_audio_ffmpeg(crudo, destino, 0, p.tono_total())  # Polly neural no admite pitch
    crudo.unlink(missing_ok=True)
    return destino


def _gtts(texto: str, p: PerfilVoz, destino: Path) -> Path:
    from gtts import gTTS

    crudo = destino.with_suffix(".raw.mp3")
    gTTS(texto, lang=p.idioma, tld=p.voz or "com", slow=p.velocidad == "muy_lenta").save(str(crudo))
    tasa = 0 if p.velocidad == "muy_lenta" else p.tasa_total()
    ajustar_audio_ffmpeg(crudo, destino, tasa, p.tono_total())
    crudo.unlink(missing_ok=True)
    return destino


def _prueba(texto: str, p: PerfilVoz, destino: Path) -> Path:
    """Audio sintético (tonos por sílaba) con duración realista. SOLO para pruebas."""
    sr = 44100
    silabas = max(1, sum(1 for c in texto.lower() if c in "aeiouáéíóú"))
    seg_por_silaba = 0.2 * (1 - p.tasa_total() / 100)
    base = 220 * 2 ** ((p.tono_total()) / 120)
    partes = []
    for i in range(silabas):
        n = int(sr * seg_por_silaba)
        t = np.arange(n) / sr
        f = base * (1 + 0.15 * math.sin(i))
        env_ = np.sin(np.pi * np.arange(n) / n) ** 0.5
        partes.append(0.35 * env_ * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)))
    audio = np.concatenate(partes)
    estereo = (np.stack([audio, audio], axis=1) * 32767).astype(np.int16)
    import wave

    wav = destino.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(estereo.tobytes())
    if wav != destino:
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav), str(destino)], check=True,
                       capture_output=True)
        wav.unlink(missing_ok=True)
    return destino


_MOTORES: dict[str, Callable[[str, PerfilVoz, Path], Path]] = {
    "edge": _edge, "azure": _azure, "elevenlabs": _elevenlabs, "polly": _polly, "gtts": _gtts, "prueba": _prueba,
}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
# Acentos de gTTS equivalentes a cada locale de edge/Azure (para el respaldo automático)
_TLD_GTTS = {"es-MX": "com.mx", "es-US": "com.mx", "es-CO": "com.mx", "es-AR": "com.mx", "es-ES": "es",
             "en-US": "us", "en-GB": "co.uk", "en-AU": "com.au"}


def _sintetizar_con_respaldo(texto: str, perfil: PerfilVoz, destino: Path) -> Path:
    """Usa el motor del perfil; si falla (red, cuota, servicio caído) recurre a gTTS.

    Desactívalo con EVR_TTS_RESPALDO=no. El motor "prueba" nunca usa respaldo.
    """
    try:
        return _MOTORES[perfil.motor](texto, perfil, destino)
    except Exception as e:  # noqa: BLE001
        if perfil.motor in ("gtts", "prueba") or env("EVR_TTS_RESPALDO", "si").lower() in ("no", "0", "false"):
            raise
        locale = "-".join(perfil.voz.split("-")[:2])
        respaldo = perfil.variante(motor="gtts", voz=_TLD_GTTS.get(locale, "com"), tono_extra=perfil.tono_extra)
        print(f"[tts] {perfil.motor} falló ({str(e)[:120]}); usando gTTS como respaldo")
        return _gtts(texto, respaldo, destino)


def sintetizar(texto: str, perfil: PerfilVoz, destino: Path | None = None, usar_cache: bool = True) -> Path:
    """Genera la narración (WAV) de un texto, con pausas entre frases y ganancia relativa."""
    from pydub import AudioSegment

    carpeta = DIR_CACHE / "tts"
    carpeta.mkdir(parents=True, exist_ok=True)
    clave = perfil.clave_cache(texto) + hash_corto(perfil.pausa_frases, perfil.ganancia_db)
    en_cache = carpeta / f"{clave}.wav"
    if not (usar_cache and en_cache.exists()):
        frases = dividir_frases(texto) or [texto]
        total = AudioSegment.silent(duration=0, frame_rate=44100)
        for i, frase in enumerate(frases):
            parcial = carpeta / f"{perfil.clave_cache(frase)}.mp3"
            if not (usar_cache and parcial.exists() and parcial.stat().st_size > 200):
                _sintetizar_con_respaldo(frase, perfil, parcial)
            seg = cargar_audio(parcial).set_frame_rate(44100).set_channels(2)
            seg = recortar_silencios_extremos(seg)
            if i:
                total += AudioSegment.silent(duration=int(perfil.pausa_frases * 1000), frame_rate=44100).set_channels(2)
            total += seg
        if perfil.ganancia_db:
            total = total.apply_gain(perfil.ganancia_db)
        exportar_audio(total, en_cache)
    if destino:
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(en_cache.read_bytes())
        return destino
    return en_cache


def recortar_silencios_extremos(seg, umbral_db: float = -50.0, margen_ms: int = 60):
    """Quita silencio al principio y al final (no toca las pausas internas)."""
    from pydub.silence import detect_leading_silence

    if len(seg) < 400:
        return seg
    ini = max(0, detect_leading_silence(seg, silence_threshold=umbral_db) - margen_ms)
    fin = max(0, detect_leading_silence(seg.reverse(), silence_threshold=umbral_db) - margen_ms)
    recortado = seg[ini:len(seg) - fin]
    return recortado if len(recortado) > 200 else seg


TEXTOS_PREVIEW = {
    "es": "¡Hola, amiguitos! Hoy vamos a aprender los colores. ¡Rojo! Repite conmigo: rojo. ¡Muy bien!",
    "en": "Hello, little friends! Today we are going to learn colors. Red! Say it with me: red. Great job!",
}


def vista_previa(perfil: PerfilVoz, texto: str | None = None) -> Path:
    return sintetizar(texto or TEXTOS_PREVIEW.get(perfil.idioma, TEXTOS_PREVIEW["es"]), perfil)


def duracion_audio(ruta: Path) -> float:
    import wave

    ruta = Path(ruta)
    if ruta.suffix.lower() == ".wav":
        with wave.open(str(ruta), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    return len(cargar_audio(ruta)) / 1000.0


def narrar_guion(guion, perfil: PerfilVoz, carpeta: Path,
                 progreso: Callable[[float, str], None] | None = None) -> list[Path]:
    """Genera un WAV por escena y fija las duraciones reales del guion.

    En las escenas de canción se usa una variante más enérgica de la voz; en
    los Shorts la voz va un poco más rápida.
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []
    duraciones: list[float] = []
    base = perfil
    if guion.formato == "short":
        base = perfil.variante(ajuste_velocidad=perfil.ajuste_velocidad + 12, pausa_frases=min(perfil.pausa_frases, 0.25))
    for i, esc in enumerate(guion.escenas):
        if progreso:
            progreso(i / len(guion.escenas), f"Voz {i + 1}/{len(guion.escenas)}")
        p = base
        if esc.seccion == "cancion":
            p = base.variante(estilo="entusiasta", ajuste_velocidad=base.ajuste_velocidad + 5)
        ruta = sintetizar(esc.narracion, p, carpeta / f"{esc.id}.wav")
        rutas.append(ruta)
        margen = 0.25 if guion.formato == "short" else 0.35
        duraciones.append(margen + duracion_audio(ruta) + esc.pausa_despues)
    guion.aplicar_duraciones(duraciones)
    if progreso:
        progreso(1.0, "Voz lista")
    return rutas


def configurar_certificados() -> None:
    """Si el sistema define un bundle de CA (proxies corporativos), úsalo también en aiohttp/edge-tts."""
    bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if bundle and Path(bundle).exists():
        os.environ.setdefault("SSL_CERT_FILE", bundle)


configurar_certificados()
