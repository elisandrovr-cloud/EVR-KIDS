"""Títulos, descripciones largas (200-400 palabras), timestamps, tags y hashtags.

Los timestamps siguen las reglas de capítulos de YouTube: el primero es 00:00,
al menos 3 capítulos y cada uno de 10 segundos o más.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from config import AVISO_MADE_FOR_KIDS
from utilidades import formato_tiempo

TEXTOS = {
    "es": {
        "titulos_largo": [
            "{T} para Niños {E} | Aprende {t} Jugando | Video Educativo",
            "Aprende {t} {E} | Canción y Vocabulario para Niños Pequeños",
            "{T} {E} | Aprende a Hablar | Video Educativo para Bebés y Niños",
        ],
        "titulos_short": ["{T} en 30 segundos {E} #shorts", "¡Aprende {t} jugando! {E} #shorts", "Aprende {t} {E} #shorts"],
        "intro": [
            "¡Bienvenidos a un nuevo video educativo! Hoy aprendemos {t} de una forma divertida, "
            "con colores vivos, palabras sencillas y mucha repetición para que los más pequeños "
            "puedan escuchar, mirar y repetir cada palabra.",
        ],
        "aprenden": "En este video tu peque aprenderá:",
        "metodo": (
            "Este video está pensado para niños de 2 a 5 años. Usamos frases cortas, pausas para que el "
            "niño repita en voz alta, subtítulos grandes y una canción final que refuerza todo lo aprendido. "
            "La repetición ayuda a desarrollar el lenguaje, ampliar el vocabulario y ganar confianza al hablar."
        ),
        "consejos": (
            "Consejo para mamás, papás y maestros: vean el video juntos, hagan pausas, señalen la pantalla "
            "y celebren cada palabra que su hijo repita. ¡Aprender en compañía es mucho más divertido! "
            "Recomendamos sesiones cortas y tiempo de pantalla moderado según la edad."
        ),
        "short": (
            "¡Un minuto de aprendizaje divertido! Mira, escucha y repite las palabras con nosotros. "
            "Perfecto para niños pequeños que están aprendiendo a hablar."
        ),
        "capitulos": "⏱️ Capítulos:",
        "seguridad": (
            "Contenido 100 % apto para niños, sin anuncios engañosos, sin personajes con derechos de autor. "
            "Todas las imágenes, voces y música son originales, de dominio público o con licencia comercial."
        ),
        "cierre": "¡Gracias por aprender con nosotros! Hay un nuevo video cada semana. ✨",
        "extras": [
            "Sobre nuestro canal: creamos videos alegres para aprender primeras palabras, números, colores, formas, "
            "animales y emociones. Cada video repite las palabras varias veces con imágenes claras, porque así es "
            "como los niños pequeños aprenden mejor.",
            "¿Cómo usar este video? 1) Véanlo una vez completo. 2) Vuelvan a verlo y pausen después de cada palabra "
            "para que el niño la diga. 3) Busquen esos mismos objetos en casa o en un libro. ¡Así el aprendizaje "
            "salta de la pantalla a la vida real!",
        ],
        "tags_base": ["video educativo", "para niños", "aprender a hablar", "vocabulario infantil", "preescolar",
                      "niños pequeños", "educación infantil", "bebés", "aprende jugando", "español para niños"],
        "hashtags_base": ["#AprendeJugando", "#VideosEducativos", "#NiñosPequeños"],
    },
    "en": {
        "titulos_largo": [
            "{T} for Kids {E} | Learn {t} | Educational Video for Toddlers",
            "Learn {t} {E} | Song and First Words for Toddlers",
            "{T} {E} | Learn to Talk | Preschool Learning Video",
        ],
        "titulos_short": ["{T} in 30 seconds {E} #shorts", "Do you know {t}? {E} #shorts", "Learn {t} {E} #shorts"],
        "intro": [
            "Welcome to a new learning video! Today we learn {t} in a fun way, with bright colors, "
            "simple words and lots of repetition so little ones can listen, watch and repeat every word.",
        ],
        "aprenden": "In this video your little one will learn:",
        "metodo": (
            "This video is made for children ages 2 to 5. We use short sentences, pauses so your child can "
            "repeat out loud, big captions and a final song that reinforces everything. Repetition helps "
            "language development, grows vocabulary and builds confidence when speaking."
        ),
        "consejos": (
            "Tip for parents and teachers: watch together, pause the video, point at the screen and celebrate "
            "every word your child repeats. Learning together is so much more fun! We recommend short sessions "
            "and age-appropriate screen time."
        ),
        "short": (
            "One minute of fun learning! Watch, listen and repeat the words with us. "
            "Perfect for toddlers who are learning to talk."
        ),
        "capitulos": "⏱️ Chapters:",
        "seguridad": (
            "100% kid-safe content, no misleading ads, no copyrighted characters. All images, voices and music "
            "are original, public domain or commercially licensed."
        ),
        "cierre": "Thanks for learning with us! New videos every week. ✨",
        "extras": [
            "About our channel: we make cheerful videos to learn first words, numbers, colors, shapes, animals and "
            "feelings. Every video repeats the words several times with clear pictures, because that is how "
            "toddlers learn best.",
            "How to use this video: 1) Watch it once all the way through. 2) Watch again and pause after each word "
            "so your child can say it. 3) Find the same things at home or in a book. Learning jumps from the "
            "screen into real life!",
        ],
        "tags_base": ["educational video", "for kids", "learn to talk", "toddler learning", "preschool",
                      "first words", "kids vocabulary", "baby learning", "learning video", "english for kids"],
        "hashtags_base": ["#ToddlerLearning", "#KidsEducation", "#LearnToTalk"],
    },
}
EMOJIS_CATEGORIA = {
    "animales": "🐮", "colores": "🌈", "numeros": "🔢", "formas": "⭐", "emociones": "😊", "hablar": "🗣️",
    "comida": "🍎", "vehiculos": "🚗", "cuerpo": "👀", "naturaleza": "☀️", "personalizado": "✨",
}


@dataclass
class Metadatos:
    titulo: str
    descripcion: str
    timestamps: list[tuple[str, str]]
    tags: list[str]
    hashtags: list[str]
    idioma: str
    formato: str
    made_for_kids: bool = True
    categoria_youtube: str = "Education (27)"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def a_markdown(self) -> str:
        ts = "\n".join(f"{t} {n}" for t, n in self.timestamps)
        return (
            f"# {self.titulo}\n\n"
            f"## Título (copiar en YouTube)\n\n{self.titulo}\n\n"
            f"## Descripción (copiar en YouTube)\n\n```\n{self.descripcion}\n```\n\n"
            f"## Timestamps\n\n```\n{ts or '(los Shorts no usan capítulos)'}\n```\n\n"
            f"## Tags (separados por comas)\n\n```\n{', '.join(self.tags)}\n```\n\n"
            f"## Hashtags\n\n{' '.join(self.hashtags)}\n\n"
            f"## Configuración recomendada en YouTube Studio\n\n"
            f"- Audiencia: **Sí, es contenido creado para niños** (Made for Kids)\n"
            f"- Categoría: {self.categoria_youtube}\n"
            f"- Idioma del video: {self.idioma}\n"
            f"- Subtítulos: sube el archivo `.srt` que está junto al video\n\n"
            f"> {AVISO_MADE_FOR_KIDS.replace(chr(10), chr(10) + '> ')}\n"
        )

    def a_txt(self) -> str:
        return f"{self.titulo}\n\n{self.descripcion}\n\nTAGS: {', '.join(self.tags)}\n"


def calcular_timestamps(guion) -> list[tuple[str, str]]:
    """Capítulos reales (tras generar la voz), fusionando los de menos de 10 s."""
    if guion.formato == "short":
        return []
    caps = guion.capitulos(reales=True)
    fin = guion.duracion_real or guion.duracion_estimada
    fusion: list[list] = []
    for inicio, nombre in caps:
        if fusion and (inicio - fusion[-1][0]) < 10:
            if nombre and nombre not in fusion[-1][1]:
                fusion[-1][1] = f"{fusion[-1][1]} y {nombre}" if guion.idioma == "es" else f"{fusion[-1][1]} & {nombre}"
            continue
        fusion.append([inicio, nombre])
    if len(fusion) > 1 and fin - fusion[-1][0] < 10:  # el último también debe durar 10 s
        ult = fusion.pop()
        fusion[-1][1] = f"{fusion[-1][1]} / {ult[1]}"
    if fusion:
        fusion[0][0] = 0.0
    return [(formato_tiempo(i), n) for i, n in fusion]


def _contar(texto: str) -> int:
    return len([p for p in texto.split() if any(c.isalnum() for c in p)])


def generar_metadatos(guion, categoria: str = "", semilla: int = 0, extra_tags: list[str] | None = None) -> Metadatos:
    idioma = guion.idioma if guion.idioma in TEXTOS else "es"
    tx = TEXTOS[idioma]
    extra = "" if guion.variante in ("nombres", "short") else f"-{guion.variante}"
    rnd = random.Random(f"{guion.tema_clave}-{guion.formato}-{semilla}{extra}")
    emoji = EMOJIS_CATEGORIA.get(categoria, "✨")
    T = guion.titulo
    t = T[:1].lower() + T[1:] if idioma == "es" else T.lower()
    palabras = [e.get(idioma, e.get("es")) for e in guion.elementos]

    plantillas = tx["titulos_short"] if guion.formato == "short" else tx["titulos_largo"]
    titulo = rnd.choice(plantillas).format(T=T, t=t, E=emoji)
    if len(titulo) > 100:
        titulo = f"{T} {emoji} #shorts" if guion.formato == "short" else f"{T} {emoji} | {tx['tags_base'][0].title()}"
    titulo = titulo[:100]

    timestamps = calcular_timestamps(guion)
    lista = "\n".join(f"✅ {p.capitalize()}" for p in palabras)
    partes = [rnd.choice(tx["intro"]).format(t=t)]
    if guion.formato == "short":
        partes.append(tx["short"])
    partes += [f"{tx['aprenden']}\n{lista}", tx["metodo"], tx["consejos"]]
    if timestamps:
        partes.append(tx["capitulos"] + "\n" + "\n".join(f"{a} {b}" for a, b in timestamps))
    partes += [tx["seguridad"], tx["cierre"]]

    tags = []
    for x in [t, T] + palabras + list(guion.palabras_clave) + (extra_tags or []) + tx["tags_base"]:
        x = x.strip().lower()
        if x and x not in tags:
            tags.append(x)
    while len(", ".join(tags)) > 480:  # YouTube: máx. 500 caracteres en tags
        tags.pop()
    hashtags = []
    if guion.formato == "short":
        hashtags.append("#shorts")
    for p in [T] + palabras[:2]:
        h = "#" + "".join(w.capitalize() for w in p.replace("-", " ").split())
        if h not in hashtags:
            hashtags.append(h)
    hashtags += tx["hashtags_base"]
    hashtags = hashtags[:6]
    partes.append(" ".join(hashtags))
    descripcion = "\n\n".join(partes)

    # Ajustar a 200-400 palabras
    for extra in tx["extras"]:
        if _contar(descripcion) >= 200:
            break
        descripcion = descripcion.replace(tx["cierre"], extra + "\n\n" + tx["cierre"], 1)
    if _contar(descripcion) > 400:
        descripcion = descripcion.replace("\n\n" + tx["consejos"], "", 1)
    return Metadatos(titulo, descripcion, timestamps, tags, hashtags, idioma, guion.formato)


def guardar_metadatos(meta: Metadatos, ruta_base: Path) -> tuple[Path, Path]:
    """Guarda <nombre>.md (completo) y <nombre>_timestamps.txt junto al video."""
    ruta_base = Path(ruta_base)
    md = ruta_base.with_suffix(".md")
    md.write_text(meta.a_markdown(), encoding="utf-8")
    ts = ruta_base.with_name(ruta_base.stem + "_timestamps.txt")
    ts.write_text("\n".join(f"{a} {b}" for a, b in meta.timestamps) or "(Short: sin capítulos)", encoding="utf-8")
    ruta_base.with_name(ruta_base.stem + "_descripcion.txt").write_text(meta.a_txt(), encoding="utf-8")
    return md, ts
