"""Miniaturas llamativas estilo infantil (1280x720, JPG < 2 MB, requisito de YouTube).

Fondo de rayos de colores, imagen principal grande con borde blanco y sombra,
texto grueso con contorno y mini imágenes secundarias.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from config import TAMANO_MINIATURA
from utilidades import PALETA, ajustar_contener, ajustar_cubrir, ajustar_fuente, rayos_sol, texto_con_borde

ETIQUETAS = {
    "es": {"largo": "¡APRENDE!", "short": "¡SHORT!"},
    "en": {"largo": "LEARN!", "short": "SHORT!"},
}
ARTICULOS = r"^(los|las|el|la|mis|mi|the|my)\s+"


def titulo_corto(titulo: str, max_palabras: int = 4) -> str:
    t = re.sub(ARTICULOS, "", titulo.strip(), flags=re.IGNORECASE)
    palabras = t.split()
    return " ".join(palabras[:max_palabras]).upper()


def _tarjeta(img: Image.Image, lado: int, borde: int = 16, radio: int = 48, circular: bool = False) -> Image.Image:
    img = ajustar_cubrir(img.convert("RGB"), (lado, lado))
    mascara = Image.new("L", (lado, lado), 0)
    d = ImageDraw.Draw(mascara)
    if circular:
        d.ellipse([0, 0, lado - 1, lado - 1], fill=255)
    else:
        d.rounded_rectangle([0, 0, lado - 1, lado - 1], radius=radio, fill=255)
    total = lado + 2 * borde
    tarjeta = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    fondo = Image.new("L", (total, total), 0)
    df = ImageDraw.Draw(fondo)
    if circular:
        df.ellipse([0, 0, total - 1, total - 1], fill=255)
    else:
        df.rounded_rectangle([0, 0, total - 1, total - 1], radius=radio + borde, fill=255)
    tarjeta.paste((255, 255, 255, 255), (0, 0), fondo)
    tarjeta.paste(img, (borde, borde), mascara)
    return tarjeta


def _sombra(capa: Image.Image, desplazamiento=(12, 16), desenfoque=18, opacidad=110) -> Image.Image:
    alfa = capa.getchannel("A").point(lambda v: opacidad if v else 0)
    sombra = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    sombra.putalpha(alfa)
    sombra = sombra.filter(ImageFilter.GaussianBlur(desenfoque))
    lienzo = Image.new("RGBA", (capa.width + 60, capa.height + 60), (0, 0, 0, 0))
    lienzo.alpha_composite(sombra, (30 + desplazamiento[0], 30 + desplazamiento[1]))
    lienzo.alpha_composite(capa, (30, 30))
    return lienzo


def crear_miniatura(titulo: str, imagen_principal: str | Path, destino: str | Path, idioma: str = "es",
                    formato: str = "largo", imagenes_extra: list[str] | None = None, semilla: int = 0,
                    etiqueta: str | None = None) -> Path:
    W, H = TAMANO_MINIATURA
    rnd = random.Random(f"{titulo}-{semilla}")
    c1, c2, c3 = rnd.sample(PALETA, 3)
    claro = tuple(int(c + (255 - c) * 0.35) for c in c1)
    lienzo = rayos_sol((W, H), c1, claro, n=22, centro=(int(W * 0.72), int(H * 0.5))).convert("RGBA")

    # Imagen principal (derecha), ligeramente girada
    principal = Image.open(imagen_principal)
    tarjeta = _tarjeta(principal, int(H * 0.74), borde=18)
    tarjeta = tarjeta.rotate(-5, resample=Image.BICUBIC, expand=True)
    tarjeta = _sombra(tarjeta)
    lienzo.alpha_composite(tarjeta, (W - tarjeta.width + 10, (H - tarjeta.height) // 2 + 10))

    # Imágenes secundarias (círculos abajo a la izquierda)
    for i, ruta in enumerate((imagenes_extra or [])[:2]):
        try:
            mini = _sombra(_tarjeta(Image.open(ruta), 150, borde=10, circular=True), (6, 8), 10, 90)
            lienzo.alpha_composite(mini, (40 + i * 175, H - mini.height - 5))
        except OSError:
            continue

    # Texto principal (izquierda), palabras alternando colores
    d = ImageDraw.Draw(lienzo)
    texto = titulo_corto(titulo)
    ancho_txt = int(W * 0.56)
    fnt, lineas = ajustar_fuente(texto, ancho_txt, int(H * 0.56), 150, tam_min=48, max_lineas=3)
    alto = int(fnt.size * 1.08)
    y = int(H * 0.36) - alto * (len(lineas) - 1) // 2
    colores = [(255, 236, 60), (255, 255, 255)]
    for i, linea in enumerate(lineas):
        texto_con_borde(d, (int(W * 0.05), y), linea, fnt, relleno=colores[i % 2], borde=(35, 25, 80),
                        grosor=max(8, fnt.size // 9), anchor="lm")
        y += alto

    # Etiqueta tipo sello
    sello = etiqueta or ETIQUETAS.get(idioma, ETIQUETAS["es"])[formato]
    fs, _ = ajustar_fuente(sello, 330, 80, 64, max_lineas=1)
    sw, sh = int(fs.getlength(sello)) + 70, int(fs.size * 1.5)
    placa = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    dp = ImageDraw.Draw(placa)
    dp.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sh // 2, fill=c2 + (255,), outline=(255, 255, 255), width=6)
    texto_con_borde(dp, (sw // 2, sh // 2), sello, fs, relleno=(255, 255, 255), borde=(30, 30, 60), grosor=5)
    placa = placa.rotate(6, resample=Image.BICUBIC, expand=True)
    y_sello = min(H - placa.height - (170 if imagenes_extra else 30), y - alto // 2 + 10)
    lienzo.alpha_composite(placa, (int(W * 0.05), max(int(H * 0.62), y_sello)))

    # Idioma
    fi, _ = ajustar_fuente(idioma.upper(), 90, 50, 44, max_lineas=1)
    d.rounded_rectangle([W - 110, 20, W - 20, 80], radius=18, fill=c3, outline=(255, 255, 255), width=4)
    texto_con_borde(d, (W - 65, 50), idioma.upper(), fi, grosor=3)

    destino = Path(destino).with_suffix(".jpg")
    destino.parent.mkdir(parents=True, exist_ok=True)
    final = lienzo.convert("RGB")
    calidad = 92
    while True:
        final.save(destino, "JPEG", quality=calidad, optimize=True, progressive=True)
        if destino.stat().st_size < 2_000_000 or calidad <= 60:
            break
        calidad -= 8
    return destino


def miniatura_vertical(imagen: str | Path, titulo: str, destino: str | Path) -> Path:
    """Portada vertical 1080x1920 para Shorts (opcional, para redes)."""
    W, H = 1080, 1920
    base = ajustar_cubrir(Image.open(imagen).convert("RGB"), (W, H)).filter(ImageFilter.GaussianBlur(30))
    frente = ajustar_contener(Image.open(imagen).convert("RGB"), (int(W * 0.9), int(W * 0.9)))
    base.paste(ImageOps.expand(frente, 12, (255, 255, 255)), ((W - frente.width) // 2 - 12, int(H * 0.3)))
    d = ImageDraw.Draw(base)
    fnt, lineas = ajustar_fuente(titulo_corto(titulo), int(W * 0.9), int(H * 0.2), 140, max_lineas=3)
    y = int(H * 0.15)
    for l in lineas:
        texto_con_borde(d, (W // 2, y), l, fnt, relleno=(255, 236, 60), borde=(35, 25, 80), grosor=10)
        y += int(fnt.size * 1.1)
    destino = Path(destino).with_suffix(".jpg")
    base.save(destino, "JPEG", quality=90)
    return destino


def validar_miniatura(ruta: str | Path) -> tuple[bool, str]:
    ruta = Path(ruta)
    if not ruta.exists():
        return False, "no existe"
    try:
        with Image.open(ruta) as im:
            tam = im.size
    except OSError as e:
        return False, f"no se puede abrir: {e}"
    peso = ruta.stat().st_size
    if tam != TAMANO_MINIATURA:
        return False, f"tamaño {tam[0]}x{tam[1]} (se esperaba 1280x720)"
    if peso >= 2_000_000:
        return False, f"pesa {peso / 1e6:.1f} MB (máx. 2 MB)"
    return True, f"1280x720, {peso / 1024:.0f} KB"
