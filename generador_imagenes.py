"""Generación y búsqueda de imágenes libres de derechos para videos infantiles.

Modos:
  A) Búsqueda de imágenes libres: Pixabay, Pexels, Unsplash, Wikimedia Commons
     (en Wikimedia solo se aceptan archivos CC0 o de dominio público).
  B) Generación con IA (preferido): Stable Diffusion local (diffusers),
     Automatic1111, ComfyUI, Stability AI, Replicate o Hugging Face.
  C) Ilustración procedural (offline, sin claves): dibujos sencillos generados
     con Pillow. Siempre disponible y se usa como respaldo si falla otro motor.

Cada imagen se guarda con sus metadatos de licencia dentro del PNG (chunks
tEXt) y en un archivo .json paralelo, para poder auditar los créditos.
"""
from __future__ import annotations

import base64
import io
import json
import math
import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import requests
from PIL import Image, ImageDraw, ImageFilter
from PIL.PngImagePlugin import PngInfo

from config import DIR_CACHE, env
from contenido_infantil import Elemento
from utilidades import (PALETA, ajustar_fuente, fuente, hash_corto, imagen_valida,
                        rayos_sol, texto_con_borde)

TAMANO_BASE = (1024, 1024)
TIMEOUT = 90
AGENTE = "EVR-KIDS/1.0 (educational kids video generator; contact: see README)"

# ---------------------------------------------------------------------------
# Estilos y optimización de prompts
# ---------------------------------------------------------------------------
ESTILOS = {
    "cartoon": "cute cartoon style, bold clean outlines, flat vibrant colors, kawaii",
    "acuarela": "soft watercolor children's book illustration, gentle textures, pastel and bright colors",
    "3d_suave": "soft 3D render, claymation style, rounded shapes, pixar-like cute character, soft studio lighting",
    "flat": "flat design vector illustration, simple geometric shapes, minimalist, vibrant palette",
    "crayon": "crayon drawing style, hand drawn by a friendly illustrator, colorful, playful",
    "papel": "paper cut-out collage style, layered colorful paper, craft look",
}
NOMBRES_ESTILOS = {
    "cartoon": "Cartoon", "acuarela": "Acuarela", "3d_suave": "3D suave", "flat": "Flat design",
    "crayon": "Crayón", "papel": "Papel recortado",
}

NEGATIVO = (
    "text, letters, words, numbers, typography, watermark, signature, logo, brand, "
    "scary, creepy, horror, violent, blood, weapon, angry teeth, dark, gloomy, "
    "nsfw, nude, adult content, realistic photo, deformed, disfigured, extra limbs, "
    "extra fingers, mutated, ugly, low quality, blurry, jpeg artifacts, cluttered background"
)


def optimizar_prompt(sujeto: str, estilo: str = "cartoon") -> tuple[str, str]:
    """Convierte un sujeto simple en un prompt optimizado para ilustración infantil."""
    base = ESTILOS.get(estilo, ESTILOS["cartoon"])
    prompt = (
        f"{sujeto}, {base}, children's picture book illustration for toddlers, "
        "bright vivid saturated colors, simple clean composition, single centered subject, "
        "friendly and happy, big expressive eyes, soft light, plain pastel background, "
        "high quality, safe for kids, no text"
    )
    return prompt, NEGATIVO


# ---------------------------------------------------------------------------
# Licencias
# ---------------------------------------------------------------------------
LICENCIAS_MODELOS = {
    "stabilityai/stable-diffusion-xl-base-1.0": "CreativeML Open RAIL++-M (uso comercial permitido)",
    "stable-diffusion-v1-5/stable-diffusion-v1-5": "CreativeML OpenRAIL-M (uso comercial permitido)",
    "runwayml/stable-diffusion-v1-5": "CreativeML OpenRAIL-M (uso comercial permitido)",
    "stabilityai/stable-diffusion-2-1": "CreativeML Open RAIL++-M (uso comercial permitido)",
    "black-forest-labs/FLUX.1-schnell": "Apache-2.0 (uso comercial permitido)",
    "black-forest-labs/flux-schnell": "Apache-2.0 (uso comercial permitido)",
}


@dataclass
class ResultadoImagen:
    ruta: str
    fuente: str
    licencia: str
    autor: str = ""
    url: str = ""
    prompt: str = ""
    uso_comercial: bool = True
    aviso: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def guardar_con_metadatos(img: Image.Image, ruta: Path, meta: ResultadoImagen) -> ResultadoImagen:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    info = PngInfo()
    for k, v in {
        "Licencia": meta.licencia, "Fuente": meta.fuente, "Autor": meta.autor, "URL": meta.url,
        "Prompt": meta.prompt, "UsoComercial": "si" if meta.uso_comercial else "no",
        "Software": "EVR-KIDS",
    }.items():
        info.add_itxt(k, str(v or ""))
    img.convert("RGB").save(ruta, "PNG", pnginfo=info, optimize=True)
    meta.ruta = str(ruta)
    ruta.with_suffix(".json").write_text(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def _descargar(url: str, headers: dict | None = None) -> Image.Image:
    r = requests.get(url, headers={"User-Agent": AGENTE, **(headers or {})}, timeout=TIMEOUT)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


# ---------------------------------------------------------------------------
# C) Ilustración procedural (offline)
# ---------------------------------------------------------------------------
def _cara(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, expresion: str = "feliz", color_ojos=(40, 40, 60)) -> None:
    """Dibuja una carita simple (ojos + boca) centrada en (cx, cy) con radio r."""
    ox, oy, ro = int(r * 0.35), int(r * 0.15), max(4, int(r * 0.12))
    if expresion == "cansado" or expresion == "tranquilo":
        for s in (-1, 1):
            d.arc([cx + s * ox - ro, cy - oy - ro // 2, cx + s * ox + ro, cy - oy + ro], 200, 340,
                  fill=color_ojos, width=max(3, ro // 2))
    else:
        esc = 1.5 if expresion == "sorprendido" else 1.0
        for s in (-1, 1):
            rr = int(ro * esc)
            d.ellipse([cx + s * ox - rr, cy - oy - rr, cx + s * ox + rr, cy - oy + rr], fill=color_ojos)
            d.ellipse([cx + s * ox - rr // 3 + rr // 3, cy - oy - rr // 2, cx + s * ox + rr // 3, cy - oy],
                      fill=(255, 255, 255))
    if expresion == "enojado":
        for s in (-1, 1):
            d.line([cx + s * (ox + ro), cy - oy - int(ro * 2.2), cx + s * (ox - ro), cy - oy - int(ro * 1.4)],
                   fill=color_ojos, width=max(3, ro // 2))
    # mejillas
    for s in (-1, 1):
        d.ellipse([cx + s * int(r * 0.55) - ro, cy + int(r * 0.1) - ro // 2, cx + s * int(r * 0.55) + ro,
                   cy + int(r * 0.1) + ro // 2], fill=(255, 150, 170))
    bw = max(3, ro // 2)
    my = cy + int(r * 0.25)
    mw = int(r * 0.35)
    if expresion in ("feliz", "tranquilo"):
        d.arc([cx - mw, my - mw // 2, cx + mw, my + mw // 2], 20, 160, fill=color_ojos, width=bw)
    elif expresion == "triste":
        d.arc([cx - mw, my, cx + mw, my + mw], 200, 340, fill=color_ojos, width=bw)
    elif expresion == "sorprendido":
        d.ellipse([cx - mw // 3, my - mw // 4, cx + mw // 3, my + mw // 2], fill=color_ojos)
    elif expresion == "cansado":
        d.ellipse([cx - mw // 4, my - mw // 6, cx + mw // 4, my + mw // 3], fill=color_ojos)
    else:  # enojado / neutro
        d.line([cx - mw // 2, my + mw // 6, cx + mw // 2, my + mw // 6], fill=color_ojos, width=bw)


def _poligono_forma(forma: str, cx: int, cy: int, r: int) -> list[tuple[float, float]] | None:
    if forma == "triangulo":
        return [(cx, cy - r), (cx + r * 0.95, cy + r * 0.75), (cx - r * 0.95, cy + r * 0.75)]
    if forma == "estrella":
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        return pts
    if forma == "corazon":
        pts = []
        for i in range(100):
            t = 2 * math.pi * i / 100
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((cx + x * r / 17, cy - y * r / 17))
        return pts
    return None


_RUTAS_EMOJI = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "C:/Windows/Fonts/seguiemj.ttf",
]


def dibujar_emoji(emoji: str, lado: int) -> Image.Image | None:
    """Renderiza un emoji a color (RGBA, lado x lado) si hay una fuente de emoji en el sistema."""
    from PIL import ImageFont

    from config import DIR_FUENTES

    candidatos = [str(p) for p in DIR_FUENTES.glob("*moji*.ttf")] + _RUTAS_EMOJI
    for ruta in candidatos:
        if not Path(ruta).exists():
            continue
        for tam in (109, 137, 160, 96, 64):  # las fuentes bitmap (CBDT) solo aceptan tamaños fijos
            try:
                f = ImageFont.truetype(ruta, tam)
                lienzo = Image.new("RGBA", (tam * 3, tam * 3), (0, 0, 0, 0))
                ImageDraw.Draw(lienzo).text((tam // 2, tam // 2), emoji, font=f, embedded_color=True)
                caja = lienzo.getbbox()
                if not caja:
                    continue
                recorte = lienzo.crop(caja)
                escala = lado / max(recorte.size)
                return recorte.resize((max(1, int(recorte.width * escala)), max(1, int(recorte.height * escala))),
                                      Image.LANCZOS)
            except Exception:  # noqa: BLE001
                continue
    return None


def ilustracion_procedural(sujeto: str, palabra: str = "", elemento: Elemento | None = None,
                           tipo: str = "", tamano=TAMANO_BASE, semilla: int = 0, titulo: str = "") -> Image.Image:
    """Dibuja una ilustración infantil simple sin necesidad de IA ni internet."""
    rnd = random.Random(f"{sujeto}-{palabra}-{semilla}")
    w, h = tamano
    c1, c2 = rnd.sample(PALETA, 2)
    claro = tuple(int(c + (255 - c) * 0.75) for c in c1)
    img = rayos_sol(tamano, claro, tuple(int(c + (255 - c) * 0.6) for c in c1), n=20)
    d = ImageDraw.Draw(img)
    # confeti
    for _ in range(40):
        x, y, r = rnd.randrange(w), rnd.randrange(h), rnd.randrange(6, 16)
        d.ellipse([x - r, y - r, x + r, y + r], fill=rnd.choice(PALETA))
    cx, cy, R = w // 2, int(h * 0.46), int(min(w, h) * 0.3)
    sombra = Image.new("RGBA", tamano, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse([cx - R, cy + R * 0.95, cx + R, cy + R * 1.15], fill=(0, 0, 0, 60))
    img.paste(sombra.filter(ImageFilter.GaussianBlur(12)), (0, 0), sombra.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(img)
    color = (elemento.color if elemento and elemento.color else c2)
    borde = tuple(max(0, int(c * 0.6)) for c in color)

    if titulo:  # portada del tema
        d.rounded_rectangle([int(w * 0.08), int(h * 0.3), int(w * 0.92), int(h * 0.7)], radius=60,
                            fill=(255, 255, 255), outline=c2, width=14)
        f, lineas = ajustar_fuente(titulo.upper(), int(w * 0.76), int(h * 0.34), 150, max_lineas=3)
        alto = int(f.size * 1.15)
        y0 = h // 2 - alto * (len(lineas) - 1) // 2
        for i, l in enumerate(lineas):
            oscuro = tuple(int(c * 0.7) for c in c2)
            texto_con_borde(d, (w // 2, y0 + i * alto), l, f, relleno=oscuro, borde=(255, 255, 255), grosor=4)
        for i in range(5):  # estrellas decorativas
            sx, sy = int(w * (0.12 + 0.19 * i)), int(h * (0.18 if i % 2 else 0.82))
            d.polygon(_poligono_forma("estrella", sx, sy, 50), fill=PALETA[i % len(PALETA)], outline=(255, 255, 255))
        return img

    forma = elemento.forma if elemento else None
    if tipo == "forma" and forma:
        pol = _poligono_forma(forma, cx, cy, R)
        if forma == "circulo":
            d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=color, outline=borde, width=12)
        elif forma == "cuadrado":
            d.rounded_rectangle([cx - R * 0.85, cy - R * 0.85, cx + R * 0.85, cy + R * 0.85], radius=30, fill=color,
                                outline=borde, width=12)
        elif forma == "rectangulo":
            d.rounded_rectangle([cx - R * 1.2, cy - R * 0.7, cx + R * 1.2, cy + R * 0.7], radius=30, fill=color,
                                outline=borde, width=12)
        elif pol:
            d.polygon(pol, fill=color, outline=borde, width=12)
        _cara(d, cx, cy + (R // 5 if forma == "triangulo" else 0), int(R * 0.6))
    elif tipo == "color":
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=color, outline=(255, 255, 255), width=16)
        for i in range(6):  # gotitas de pintura
            a = i * math.pi / 3 + 0.3
            px, py = cx + int(R * 1.25 * math.cos(a)), cy + int(R * 1.25 * math.sin(a))
            d.ellipse([px - 30, py - 30, px + 30, py + 30], fill=color, outline=(255, 255, 255), width=6)
        _cara(d, cx, cy, int(R * 0.7))
    elif tipo == "numero" and elemento and elemento.cantidad:
        n = elemento.cantidad
        cols = min(5, n)
        filas = math.ceil(n / cols)
        rr = int(min(w * 0.8 / cols, h * 0.28 / filas) * 0.42)
        from contenido_infantil import _OBJ_EMOJI

        emo = next((e for k, e in _OBJ_EMOJI.items() if k in elemento.extra_es.lower()), None)
        dib = dibujar_emoji(emo, int(rr * 2)) if emo else None
        for i in range(n):
            fx = cx + int((i % cols - (cols - 1) / 2) * rr * 2.3)
            fy = int(h * 0.72) + int((i // cols - (filas - 1) / 2) * rr * 2.3)
            if dib is not None:
                img.paste(dib, (fx - dib.width // 2, fy - dib.height // 2), dib)
            else:
                d.polygon(_poligono_forma("estrella", fx, fy, rr), fill=PALETA[i % len(PALETA)],
                          outline=(255, 255, 255))
        f = fuente(int(h * 0.42))
        texto_con_borde(d, (cx, int(h * 0.33)), str(n), f, relleno=color if elemento.color else c2,
                        borde=(255, 255, 255), grosor=14)
    elif tipo == "emocion" and elemento:
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 214, 90), outline=(230, 160, 40), width=12)
        _cara(d, cx, cy, R, expresion=elemento.clave)
    else:
        # Tarjeta genérica: emoji grande a color (sin texto, válido para cualquier idioma)
        from contenido_infantil import EMOJIS

        emo = EMOJIS.get(elemento.clave) if elemento else None
        dibujo = dibujar_emoji(emo, int(R * 1.9)) if emo else None
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 255, 255), outline=color, width=18)
        if dibujo is not None:
            img.paste(dibujo, (cx - dibujo.width // 2, cy - dibujo.height // 2), dibujo)
        else:  # sin fuente de emoji: personaje-burbuja sonriente del color del tema
            d.ellipse([cx - int(R * 0.8), cy - int(R * 0.8), cx + int(R * 0.8), cy + int(R * 0.8)], fill=color)
            _cara(d, cx, cy, int(R * 0.7))
    return img


# ---------------------------------------------------------------------------
# A) Búsqueda de imágenes libres
# ---------------------------------------------------------------------------
def buscar_pixabay(consulta: str) -> tuple[Image.Image, ResultadoImagen]:
    clave = env("PIXABAY_API_KEY")
    if not clave:
        raise RuntimeError("Falta PIXABAY_API_KEY")
    r = requests.get("https://pixabay.com/api/", params={
        "key": clave, "q": consulta[:100], "image_type": "illustration", "safesearch": "true",
        "per_page": 10, "order": "popular",
    }, timeout=TIMEOUT)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    if not hits:
        raise RuntimeError(f"Pixabay sin resultados para «{consulta}»")
    hit = hits[0]
    img = _descargar(hit["largeImageURL"])
    return img, ResultadoImagen("", "Pixabay", "Pixabay Content License (uso comercial, sin atribución obligatoria)",
                                hit.get("user", ""), hit.get("pageURL", ""), consulta)


def buscar_pexels(consulta: str) -> tuple[Image.Image, ResultadoImagen]:
    clave = env("PEXELS_API_KEY")
    if not clave:
        raise RuntimeError("Falta PEXELS_API_KEY")
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": clave},
                     params={"query": consulta[:100], "per_page": 5, "orientation": "landscape"}, timeout=TIMEOUT)
    r.raise_for_status()
    fotos = r.json().get("photos", [])
    if not fotos:
        raise RuntimeError(f"Pexels sin resultados para «{consulta}»")
    f = fotos[0]
    img = _descargar(f["src"]["large2x"])
    return img, ResultadoImagen("", "Pexels", "Pexels License (uso comercial, sin atribución obligatoria)",
                                f.get("photographer", ""), f.get("url", ""), consulta)


def buscar_unsplash(consulta: str) -> tuple[Image.Image, ResultadoImagen]:
    clave = env("UNSPLASH_ACCESS_KEY")
    if not clave:
        raise RuntimeError("Falta UNSPLASH_ACCESS_KEY")
    r = requests.get("https://api.unsplash.com/search/photos", params={
        "query": consulta[:100], "per_page": 5, "content_filter": "high", "client_id": clave,
    }, timeout=TIMEOUT)
    r.raise_for_status()
    res = r.json().get("results", [])
    if not res:
        raise RuntimeError(f"Unsplash sin resultados para «{consulta}»")
    foto = res[0]
    # Las directrices de la API de Unsplash exigen notificar la descarga
    try:
        requests.get(foto["links"]["download_location"], params={"client_id": clave}, timeout=20)
    except requests.RequestException:
        pass
    img = _descargar(foto["urls"]["regular"])
    autor = foto.get("user", {}).get("name", "")
    return img, ResultadoImagen("", "Unsplash", "Unsplash License (uso comercial permitido)", autor,
                                foto.get("links", {}).get("html", ""), consulta)


def buscar_wikimedia(consulta: str) -> tuple[Image.Image, ResultadoImagen]:
    """Wikimedia Commons: SOLO acepta CC0 o dominio público."""
    r = requests.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{consulta} filetype:bitmap", "gsrlimit": 20, "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 1280,
    }, headers={"User-Agent": AGENTE}, timeout=TIMEOUT)
    r.raise_for_status()
    paginas = r.json().get("query", {}).get("pages", {})
    for pag in sorted(paginas.values(), key=lambda p: p.get("index", 0)):
        info = (pag.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        lic_n = lic.lower()
        if "cc0" in lic_n or "public domain" in lic_n or lic_n.startswith("pd"):
            url = info.get("thumburl") or info.get("url")
            img = _descargar(url)
            autor = meta.get("Artist", {}).get("value", "")
            return img, ResultadoImagen("", "Wikimedia Commons", lic, autor[:200], info.get("descriptionurl", ""),
                                        consulta)
    raise RuntimeError(f"Wikimedia sin resultados CC0/dominio público para «{consulta}»")


# ---------------------------------------------------------------------------
# B) Generación con IA
# ---------------------------------------------------------------------------
_PIPELINE_DIFFUSERS = None


def generar_diffusers(prompt: str, negativo: str, semilla: int, tamano=TAMANO_BASE) -> tuple[Image.Image, ResultadoImagen]:
    global _PIPELINE_DIFFUSERS
    import torch
    from diffusers import AutoPipelineForText2Image

    modelo = env("EVR_DIFFUSERS_MODELO", "stabilityai/stable-diffusion-xl-base-1.0")
    disp = env("EVR_DIFFUSERS_DISPOSITIVO", "auto")
    if disp == "auto":
        disp = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    if _PIPELINE_DIFFUSERS is None or getattr(_PIPELINE_DIFFUSERS, "_evr_modelo", "") != modelo:
        dtype = torch.float16 if disp in ("cuda", "mps") else torch.float32
        kw = {"torch_dtype": dtype}
        if disp == "cuda":
            kw["variant"] = "fp16"
        try:
            pipe = AutoPipelineForText2Image.from_pretrained(modelo, use_safetensors=True, **kw)
        except Exception:  # noqa: BLE001 - el modelo puede no tener variante fp16
            kw.pop("variant", None)
            pipe = AutoPipelineForText2Image.from_pretrained(modelo, **kw)
        pipe = pipe.to(disp)
        if disp == "cuda":
            try:
                pipe.enable_attention_slicing()
            except Exception:  # noqa: BLE001
                pass
        pipe._evr_modelo = modelo
        _PIPELINE_DIFFUSERS = pipe
    gen = __import__("torch").Generator(device="cpu").manual_seed(semilla)
    pasos = int(env("EVR_DIFFUSERS_PASOS", "30"))
    guia = float(env("EVR_DIFFUSERS_GUIA", "7.0"))
    salida = _PIPELINE_DIFFUSERS(prompt=prompt, negative_prompt=negativo, num_inference_steps=pasos,
                                 guidance_scale=guia, width=tamano[0], height=tamano[1], generator=gen)
    img = salida.images[0]
    lic = LICENCIAS_MODELOS.get(modelo, f"Revisa la licencia de {modelo} antes de monetizar")
    return img, ResultadoImagen("", f"Stable Diffusion local ({modelo})", lic, "Generada por IA", "", prompt)


def generar_automatic1111(prompt: str, negativo: str, semilla: int, tamano=TAMANO_BASE):
    url = env("A1111_URL", "http://127.0.0.1:7860").rstrip("/")
    r = requests.post(f"{url}/sdapi/v1/txt2img", json={
        "prompt": prompt, "negative_prompt": negativo, "width": tamano[0], "height": tamano[1],
        "steps": int(env("EVR_DIFFUSERS_PASOS", "30")), "cfg_scale": 7, "seed": semilla,
        "sampler_name": "DPM++ 2M",
    }, timeout=600)
    r.raise_for_status()
    img = Image.open(io.BytesIO(base64.b64decode(r.json()["images"][0].split(",", 1)[-1]))).convert("RGB")
    return img, ResultadoImagen("", "Automatic1111 (Stable Diffusion local)",
                                "Según el checkpoint cargado (usa SDXL/SD1.5 con licencia OpenRAIL: uso comercial)",
                                "Generada por IA", url, prompt)


def _workflow_comfy(prompt: str, negativo: str, semilla: int, tamano) -> dict:
    return {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": semilla, "steps": int(env("EVR_DIFFUSERS_PASOS", "30")), "cfg": 7.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": env("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": tamano[0], "height": tamano[1], "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negativo, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "evr_kids", "images": ["8", 0]}},
    }


def generar_comfyui(prompt: str, negativo: str, semilla: int, tamano=TAMANO_BASE):
    url = env("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    r = requests.post(f"{url}/prompt", json={"prompt": _workflow_comfy(prompt, negativo, semilla, tamano),
                                            "client_id": str(uuid.uuid4())}, timeout=60)
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    limite = time.time() + 600
    while time.time() < limite:
        h = requests.get(f"{url}/history/{pid}", timeout=30).json()
        if pid in h and h[pid].get("outputs"):
            for salida in h[pid]["outputs"].values():
                for im in salida.get("images", []):
                    v = requests.get(f"{url}/view", params={"filename": im["filename"], "subfolder": im["subfolder"],
                                                            "type": im["type"]}, timeout=60)
                    v.raise_for_status()
                    img = Image.open(io.BytesIO(v.content)).convert("RGB")
                    return img, ResultadoImagen("", "ComfyUI (Stable Diffusion local)",
                                                "Según el checkpoint cargado (SDXL/SD1.5 OpenRAIL: uso comercial)",
                                                "Generada por IA", url, prompt)
        time.sleep(1.5)
    raise TimeoutError("ComfyUI no devolvió la imagen a tiempo")


def generar_stability(prompt: str, negativo: str, semilla: int, tamano=TAMANO_BASE):
    clave = env("STABILITY_API_KEY")
    if not clave:
        raise RuntimeError("Falta STABILITY_API_KEY")
    r = requests.post("https://api.stability.ai/v2beta/stable-image/generate/core",
                      headers={"authorization": f"Bearer {clave}", "accept": "image/*"},
                      files={"none": ""},
                      data={"prompt": prompt, "negative_prompt": negativo, "aspect_ratio": "1:1",
                            "output_format": "png", "seed": semilla}, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"Stability AI error {r.status_code}: {r.text[:200]}")
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    return img, ResultadoImagen("", "Stability AI API (Stable Image Core)",
                                "Términos de Stability AI: el cliente puede usar comercialmente las salidas",
                                "Generada por IA", "https://stability.ai", prompt)


def generar_replicate(prompt: str, negativo: str, semilla: int, tamano=TAMANO_BASE):
    token = env("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("Falta REPLICATE_API_TOKEN")
    modelo = env("REPLICATE_MODELO", "black-forest-labs/flux-schnell")
    cab = {"Authorization": f"Bearer {token}", "Prefer": "wait", "Content-Type": "application/json"}
    entrada = {"prompt": prompt, "aspect_ratio": "1:1", "output_format": "png", "seed": semilla}
    if "flux" not in modelo:
        entrada["negative_prompt"] = negativo
    r = requests.post(f"https://api.replicate.com/v1/models/{modelo}/predictions", headers=cab,
                      json={"input": entrada}, timeout=TIMEOUT)
    r.raise_for_status()
    pred = r.json()
    limite = time.time() + 300
    while pred.get("status") not in ("succeeded", "failed", "canceled") and time.time() < limite:
        time.sleep(2)
        pred = requests.get(pred["urls"]["get"], headers=cab, timeout=60).json()
    if pred.get("status") != "succeeded":
        raise RuntimeError(f"Replicate: {pred.get('status')} {pred.get('error')}")
    salida = pred["output"]
    url = salida[0] if isinstance(salida, list) else salida
    img = _descargar(url)
    lic = LICENCIAS_MODELOS.get(modelo, f"Revisa la licencia de {modelo} en replicate.com antes de monetizar")
    return img, ResultadoImagen("", f"Replicate ({modelo})", lic, "Generada por IA", url, prompt)


def generar_huggingface(prompt: str, negativo: str, semilla: int, tamano=TAMANO_BASE):
    token = env("HF_API_TOKEN")
    if not token:
        raise RuntimeError("Falta HF_API_TOKEN")
    modelo = env("HF_MODELO", "stabilityai/stable-diffusion-xl-base-1.0")
    r = requests.post(f"https://router.huggingface.co/hf-inference/models/{modelo}",
                      headers={"Authorization": f"Bearer {token}", "Accept": "image/png"},
                      json={"inputs": prompt, "parameters": {"negative_prompt": negativo, "seed": semilla}},
                      timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Hugging Face error {r.status_code}: {r.text[:200]}")
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    lic = LICENCIAS_MODELOS.get(modelo, f"Revisa la licencia de {modelo} antes de monetizar")
    return img, ResultadoImagen("", f"Hugging Face Inference ({modelo})", lic, "Generada por IA",
                                f"https://huggingface.co/{modelo}", prompt)


MOTORES_IA: dict[str, Callable] = {
    "diffusers": generar_diffusers,
    "automatic1111": generar_automatic1111,
    "comfyui": generar_comfyui,
    "stability": generar_stability,
    "replicate": generar_replicate,
    "huggingface": generar_huggingface,
}
MOTORES_STOCK: dict[str, Callable] = {
    "pixabay": buscar_pixabay,
    "pexels": buscar_pexels,
    "unsplash": buscar_unsplash,
    "wikimedia": buscar_wikimedia,
}
NOMBRES_MOTORES = {
    "procedural": "Ilustración procedural (offline, CC0)",
    "diffusers": "IA · Stable Diffusion local (diffusers)",
    "automatic1111": "IA · Automatic1111 (local)",
    "comfyui": "IA · ComfyUI (local)",
    "stability": "IA · Stability AI (nube)",
    "replicate": "IA · Replicate (nube)",
    "huggingface": "IA · Hugging Face Inference (nube)",
    "pixabay": "Stock · Pixabay",
    "pexels": "Stock · Pexels",
    "unsplash": "Stock · Unsplash",
    "wikimedia": "Stock · Wikimedia Commons (CC0/PD)",
    "stock_auto": "Stock · automático (Pixabay → Pexels → Unsplash → Wikimedia)",
}


# ---------------------------------------------------------------------------
# Gestor principal
# ---------------------------------------------------------------------------
@dataclass
class GestorImagenes:
    motor: str = "procedural"
    estilo: str = "cartoon"
    carpeta: Path = field(default_factory=lambda: DIR_CACHE / "imagenes")
    respaldo_procedural: bool = True
    creditos: list[dict] = field(default_factory=list)

    def _ruta(self, clave: str, sujeto: str, semilla: int) -> Path:
        return Path(self.carpeta) / f"{self.motor}_{self.estilo}" / f"{clave}_{hash_corto(sujeto, semilla)}.png"

    def obtener(self, clave: str, sujeto: str, palabra: str = "", elemento: Elemento | None = None,
                tipo: str = "", titulo: str = "", semilla: int = 42, forzar: bool = False) -> ResultadoImagen:
        """Devuelve (y cachea) la imagen para `clave`. Si el motor falla usa la ilustración procedural."""
        ruta = self._ruta(clave, sujeto + titulo, semilla)
        if ruta.exists() and not forzar and imagen_valida(ruta)[0]:
            meta = json.loads(ruta.with_suffix(".json").read_text(encoding="utf-8")) if ruta.with_suffix(".json").exists() else {}
            res = ResultadoImagen(**{**{"ruta": str(ruta), "fuente": "caché", "licencia": "?"}, **meta})
            self._acreditar(clave, res)
            return res

        aviso = ""
        img = meta = None
        prompt, negativo = optimizar_prompt(sujeto, self.estilo)
        if self.motor in MOTORES_IA and not titulo:
            for intento in range(2):
                try:
                    img, meta = MOTORES_IA[self.motor](prompt, negativo, semilla + intento)
                    tmp = io.BytesIO()
                    img.save(tmp, "PNG")
                    probe = ruta.with_suffix(".tmp.png")
                    probe.parent.mkdir(parents=True, exist_ok=True)
                    probe.write_bytes(tmp.getvalue())
                    ok, det = imagen_valida(probe)
                    probe.unlink(missing_ok=True)
                    if ok:
                        break
                    aviso = f"imagen IA descartada: {det}"
                    img = None
                except Exception as e:  # noqa: BLE001
                    aviso = f"{self.motor} falló: {e}"
                    img = None
                    break
        elif (self.motor in MOTORES_STOCK or self.motor == "stock_auto") and not titulo:
            fuentes = list(MOTORES_STOCK) if self.motor == "stock_auto" else [self.motor]
            consulta = sujeto.replace("a cute ", "").replace("cute ", "")
            for nombre in fuentes:
                try:
                    img, meta = MOTORES_STOCK[nombre](consulta)
                    break
                except Exception as e:  # noqa: BLE001
                    aviso = f"{nombre}: {e}"
                    img = None
        if img is None:
            if self.motor != "procedural" and not titulo and not self.respaldo_procedural:
                raise RuntimeError(aviso or "No se pudo obtener la imagen")
            img = ilustracion_procedural(sujeto, palabra, elemento, tipo, semilla=semilla, titulo=titulo)
            meta = ResultadoImagen("", "EVR-KIDS ilustración procedural",
                                   "CC0 1.0 (creación propia, uso comercial libre)", "EVR-KIDS", "", sujeto,
                                   aviso=aviso)
        res = guardar_con_metadatos(img, ruta, meta)
        self._acreditar(clave, res)
        return res

    def _acreditar(self, clave: str, res: ResultadoImagen) -> None:
        self.creditos = [c for c in self.creditos if c.get("clave") != clave]
        self.creditos.append({"clave": clave, **res.to_dict()})

    def imagenes_para_guion(self, guion, tema=None, progreso: Callable[[float, str], None] | None = None,
                            forzar: set[str] | None = None) -> dict[str, str]:
        """Genera todas las imágenes necesarias para un guion. Devuelve {clave_imagen: ruta}."""
        from contenido_infantil import TEMAS

        tema = tema or TEMAS.get(guion.tema_clave)
        elementos = {e["clave"]: Elemento(**e) for e in guion.elementos}
        claves = []
        for esc in guion.escenas:
            if esc.imagen not in claves:
                claves.append(esc.imagen)
        rutas: dict[str, str] = {}
        tipo = tema.tipo if tema else ""
        for i, clave in enumerate(claves):
            if progreso:
                progreso(i / max(1, len(claves)), f"Imagen {i + 1}/{len(claves)}: {clave}")
            fz = bool(forzar and clave in forzar)
            if clave == "portada":
                titulo = tema.titulo(guion.idioma) if tema else guion.titulo
                # La portada lleva el título (en el idioma del video), por eso es procedural;
                # con motores IA se genera además una escena ilustrada sin texto.
                res = self.obtener(f"portada_{tema.clave if tema else guion.tema_clave}_{guion.idioma}",
                                   guion.prompt_portada or guion.titulo, titulo=titulo, tipo=tipo, forzar=fz)
                rutas["portada"] = res.ruta
                if self.motor != "procedural":
                    fondo = self.obtener("escena_" + (tema.clave if tema else guion.tema_clave),
                                         f"a happy scene with {guion.prompt_portada}", forzar=fz)
                    rutas["escena"] = fondo.ruta
                continue
            el = elementos.get(clave)
            sujeto = el.prompt if el else clave
            palabra = el.es if el else clave
            res = self.obtener(clave, sujeto, palabra=palabra, elemento=el, tipo=tipo, forzar=fz)
            rutas[clave] = res.ruta
        if progreso:
            progreso(1.0, "Imágenes listas")
        return rutas
