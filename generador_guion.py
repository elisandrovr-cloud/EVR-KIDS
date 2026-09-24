"""Generador de guiones educativos infantiles (video largo y Short).

Estructura del video largo (2-5 min):
    intro animada -> lección principal (con repetición) -> repaso -> canción -> outro
Estructura del Short (15-60 s):
    gancho (0-3 s) -> contenido rápido -> llamado a la acción

Los guiones se generan con plantillas pedagógicas (repetición espaciada,
lenguaje positivo, frases cortas) a partir de la base bilingüe de
`contenido_infantil.py`, por lo que el mismo guion existe en español e
inglés con idéntica estructura (base del doblaje automático). Para temas
libres se puede usar Claude (Anthropic) para crear el vocabulario.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field

from config import env
from contenido_infantil import TEMAS, Elemento, Tema, buscar_tema, tema_personalizado
from utilidades import formato_tiempo

# Palabras por segundo aproximadas a velocidad "lenta" (para marcas de tiempo estimadas)
PALABRAS_POR_SEGUNDO = 2.1


@dataclass
class Escena:
    id: str
    seccion: str  # intro | leccion | repaso | cancion | outro | gancho | contenido | cta
    narracion: str
    texto_pantalla: str
    palabra: str = ""  # palabra clave grande en pantalla
    imagen: str = "portada"  # clave de imagen (elemento.clave o "portada")
    pausa_despues: float = 0.6  # silencio tras la narración (tiempo para que el niño repita)
    efecto: str = "zoom_in"  # zoom_in | zoom_out | pan_izq | pan_der | rebote | misterio
    sonido: str | None = None  # pop | ding | whoosh | aplauso
    capitulo: str = ""  # nombre del capítulo para los timestamps
    duracion_est: float = 0.0
    inicio_est: float = 0.0
    duracion: float = 0.0  # real (tras generar la voz)
    inicio: float = 0.0  # real

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Guion:
    tema_clave: str
    titulo: str
    idioma: str
    formato: str  # largo | short
    variante: str
    escenas: list[Escena] = field(default_factory=list)
    palabras_clave: list[str] = field(default_factory=list)
    elementos: list[dict] = field(default_factory=list)
    prompt_portada: str = ""

    # ------------------------------------------------------------------ tiempos
    def estimar_tiempos(self, factor_velocidad: float = 1.0) -> None:
        t = 0.0
        for e in self.escenas:
            palabras = max(1, len(e.narracion.split()))
            e.duracion_est = round(palabras / (PALABRAS_POR_SEGUNDO * factor_velocidad) + e.pausa_despues + 0.4, 2)
            e.inicio_est = round(t, 2)
            t += e.duracion_est

    @property
    def duracion_estimada(self) -> float:
        return sum(e.duracion_est for e in self.escenas)

    @property
    def duracion_real(self) -> float:
        return sum(e.duracion for e in self.escenas)

    def aplicar_duraciones(self, duraciones: list[float]) -> None:
        t = 0.0
        for e, d in zip(self.escenas, duraciones):
            e.duracion = round(d, 3)
            e.inicio = round(t, 3)
            t += d

    def capitulos(self, reales: bool = True) -> list[tuple[float, str]]:
        """Lista (inicio, nombre) de capítulos; agrupa escenas consecutivas."""
        caps: list[tuple[float, str]] = []
        for e in self.escenas:
            inicio = e.inicio if reales and self.duracion_real else e.inicio_est
            if not caps or caps[-1][1] != e.capitulo:
                caps.append((inicio, e.capitulo))
        return caps

    # ------------------------------------------------------------------ export
    def to_dict(self) -> dict:
        d = asdict(self)
        d["duracion_estimada"] = round(self.duracion_estimada, 1)
        d["duracion_real"] = round(self.duracion_real, 1)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Guion":
        escenas = [Escena(**e) for e in d.get("escenas", [])]
        campos = {k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "escenas"}
        return cls(escenas=escenas, **campos)

    def to_markdown(self) -> str:
        reales = self.duracion_real > 0
        dur = self.duracion_real if reales else self.duracion_estimada
        fmt = "Video largo (16:9)" if self.formato == "largo" else "YouTube Short (9:16)"
        lineas = [
            f"# Guion: {self.titulo}",
            "",
            f"- **Formato:** {fmt}",
            f"- **Idioma:** {self.idioma}",
            f"- **Variante:** {self.variante}",
            f"- **Duración {'real' if reales else 'estimada'}:** {formato_tiempo(dur)} ({dur:.0f} s)",
            "",
            "| Tiempo | Sección | Narración | Texto en pantalla | Imagen |",
            "|---|---|---|---|---|",
        ]
        for e in self.escenas:
            t = e.inicio if reales else e.inicio_est
            lineas.append(
                f"| [{formato_tiempo(t)}] | {e.seccion} | {e.narracion} | "
                f"**{e.palabra}** {e.texto_pantalla if e.texto_pantalla != e.narracion else ''} | {e.imagen} |"
            )
        return "\n".join(lineas) + "\n"

    def texto_completo(self) -> str:
        return "\n".join(e.narracion for e in self.escenas)


# ---------------------------------------------------------------------------
# Plantillas pedagógicas
# ---------------------------------------------------------------------------
FELICITACIONES = {
    "es": ["¡Muy bien!", "¡Excelente!", "¡Genial!", "¡Lo hiciste súper!", "¡Bravo!", "¡Qué bien!"],
    "en": ["Great job!", "Excellent!", "Awesome!", "Well done!", "Hooray!", "Very good!"],
}

T = {
    "es": {
        "hola": "¡Hola, amiguitos! ¡Bienvenidos!",
        "hoy": "Hoy vamos a aprender {titulo}. ¿Están listos? ¡Vamos!",
        "repite": "{W}. Repite conmigo: {w}.",
        "eco": "¡{W}! {bien}",
        "adivina": "¿Qué es esto? ¿Lo sabes?",
        "es_un": "¡Es {art} {w}!",
        "repaso": "¡Vamos a repasar! Di la palabra conmigo.",
        "otra_vez": "¡Otra vez! ¿Qué es esto?",
        "cancion": "¡Ahora, a cantar!",
        "coro": "¡Aprender es divertido, cantamos sin parar!",
        "coro2": "¡Aplaude conmigo, uno, dos y tres!",
        "fin1": "¡Lo hiciste muy bien! Hoy aprendimos {titulo}.",
        "fin2": "¡Adiós, amiguitos! ¡Hasta la próxima!",
        "cta": "¡Sígueme para aprender más! ¡Dale like!",
        "cta_pantalla": "¡SÍGUEME PARA MÁS!",
        "cap_intro": "Introducción", "cap_repaso": "Repaso", "cap_cancion": "Canción",
        "cap_outro": "Despedida", "cap_ronda": "¡Adivina!", "insignia_repaso": "¡A REPASAR!",
        "presenta": {
            "animal": "¡Mira! Es {art} {w}.", "objeto": "¡Mira! {Art_w}.",
            "color": "¡Este es el color {w}!", "numero": "¡Este es el número {w}!",
            "forma": "¡Mira! Es {art} {w}.", "emocion": "Esta carita está {w}.",
            "saludo": "Vamos a decir: {w}.",
        },
    },
    "en": {
        "hola": "Hello, little friends! Welcome!",
        "hoy": "Today we are going to learn {titulo}. Are you ready? Let's go!",
        "repite": "{W}. Say it with me: {w}.",
        "eco": "{W}! {bien}",
        "adivina": "What is this? Do you know?",
        "es_un": "It's {art} {w}!",
        "repaso": "Let's review! Say the word with me.",
        "otra_vez": "One more time! What is this?",
        "cancion": "Now, let's sing!",
        "coro": "Learning is so much fun, we sing and sing all day!",
        "coro2": "Clap with me, one, two, three!",
        "fin1": "You did a great job! Today we learned {titulo}.",
        "fin2": "Goodbye, little friends! See you next time!",
        "cta": "Follow me to learn more! Give it a like!",
        "cta_pantalla": "FOLLOW FOR MORE!",
        "cap_intro": "Intro", "cap_repaso": "Review", "cap_cancion": "Song",
        "cap_outro": "Goodbye", "cap_ronda": "Guess!", "insignia_repaso": "REVIEW TIME!",
        "presenta": {
            "animal": "Look! It's {art} {w}.", "objeto": "Look! {Art_w}.",
            "color": "This is the color {w}!", "numero": "This is the number {w}!",
            "forma": "Look! It's {art} {w}.", "emocion": "This face is {w}.",
            "saludo": "Let's say: {w}.",
        },
    },
}

CTA_SUGERIDOS = {
    "es": ["¡Sígueme para aprender más! ¡Dale like!", "¡Sígueme para más!", "¡Dale like si aprendiste!",
           "¡Pídele a un adulto que te ayude a ver más videos!"],
    "en": ["Follow me to learn more! Give it a like!", "Follow for more!", "Give it a like if you learned!",
           "Ask a grown-up to help you watch more videos!"],
}


def cta_en_idioma(cta: str, idioma: str) -> str:
    """Devuelve el CTA elegido o su equivalente en el idioma del video (las listas son paralelas)."""
    for lista in CTA_SUGERIDOS.values():
        if cta in lista:
            return CTA_SUGERIDOS[idioma][lista.index(cta)]
    return cta


EFECTOS = ["zoom_in", "pan_der", "zoom_out", "pan_izq"]
VARIANTES = ["nombres", "adivina", "canta"]


def _fmt(plantilla: str, el: Elemento | None, idioma: str, **extra) -> str:
    datos = dict(extra)
    if el is not None:
        w = el.palabra(idioma)
        art = el.articulo(idioma)
        datos.update(w=w, W=w[:1].upper() + w[1:], art=art,
                     Art_w=(f"{art} {w}".strip()[:1].upper() + f"{art} {w}".strip()[1:]))
    texto = plantilla.format(**datos)
    return " ".join(texto.replace(" .", ".").replace(" !", "!").split())


def _titulo_frase(tema: Tema, idioma: str) -> str:
    t = tema.titulo(idioma)
    return t[:1].lower() + t[1:] if idioma == "es" else t.lower()


def _elementos_para(tema: Tema, formato: str) -> list[Elemento]:
    items = list(tema.items)
    return items[:10] if formato == "largo" else items[:5]


def generar_guion_largo(tema: Tema, idioma: str = "es", variante: str = "nombres",
                        semilla: int = 7) -> Guion:
    rnd = random.Random(f"{tema.clave}-{variante}-{semilla}")  # igual en ambos idiomas
    tx = T[idioma]
    items = _elementos_para(tema, "largo")
    g = Guion(tema.clave, tema.titulo(idioma), idioma, "largo", variante,
              palabras_clave=list(tema.palabras_clave), elementos=[i.to_dict() for i in items],
              prompt_portada=f"{tema.titulo_en} for kids, " + ", ".join(i.en for i in items[:3]))
    n = 0

    def add(**kw) -> None:
        nonlocal n
        n += 1
        kw.setdefault("texto_pantalla", kw["narracion"])
        g.escenas.append(Escena(id=f"e{n:03d}", **kw))

    # 1) Intro
    # (la portada ya muestra el título, así que la intro no repite la insignia)
    add(seccion="intro", narracion=tx["hola"], palabra=tx["hola"].split("!")[0].upper() + "!", imagen="portada",
        efecto="rebote", sonido="ding", capitulo=tx["cap_intro"], pausa_despues=0.5)
    add(seccion="intro", narracion=_fmt(tx["hoy"], None, idioma, titulo=_titulo_frase(tema, idioma)),
        palabra="", imagen="portada", efecto="zoom_in", capitulo=tx["cap_intro"])

    # 2) Lección principal con repetición
    for k, el in enumerate(items):
        cap = el.palabra(idioma).capitalize()
        W = el.palabra(idioma).upper()
        efecto = EFECTOS[k % len(EFECTOS)]
        bien = rnd.randrange(len(FELICITACIONES[idioma]))
        if variante == "adivina":
            add(seccion="leccion", narracion=tx["adivina"], palabra="?", imagen=el.clave,
                efecto="misterio", sonido="ding", capitulo=cap, pausa_despues=1.8)
            add(seccion="leccion", narracion=_fmt(tx["es_un"], el, idioma), palabra=W, imagen=el.clave,
                efecto="rebote", sonido="pop", capitulo=cap)
        else:
            add(seccion="leccion", narracion=_fmt(tx["presenta"].get(tema.tipo, tx["presenta"]["objeto"]), el, idioma),
                palabra=W, imagen=el.clave, efecto=efecto, sonido="pop", capitulo=cap)
        add(seccion="leccion", narracion=_fmt(tx["repite"], el, idioma), palabra=W, imagen=el.clave,
            efecto=efecto, capitulo=cap, pausa_despues=1.8)
        add(seccion="leccion", narracion=el.extra(idioma), palabra=W, imagen=el.clave,
            efecto="zoom_in", capitulo=cap, pausa_despues=0.8)
        add(seccion="leccion", narracion=_fmt(tx["eco"], el, idioma, bien=FELICITACIONES[idioma][bien]),
            palabra=W, imagen=el.clave, efecto="rebote", sonido="aplauso", capitulo=cap, pausa_despues=0.9)

    # 3) Repaso rápido
    add(seccion="repaso", narracion=tx["repaso"], palabra=tx["insignia_repaso"], imagen="portada", efecto="zoom_in",
        sonido="whoosh", capitulo=tx["cap_repaso"])
    for el in items:
        w = el.palabra(idioma)
        add(seccion="repaso", narracion=f"{w[:1].upper() + w[1:]}.", palabra=w.upper(), imagen=el.clave,
            efecto="rebote", sonido="pop", capitulo=tx["cap_repaso"], pausa_despues=1.2)

    # 4) Canción (coro + cantinela con las palabras)
    add(seccion="cancion", narracion=tx["cancion"], palabra="♪ ♫ ♪", imagen="portada", efecto="rebote",
        sonido="ding", capitulo=tx["cap_cancion"], pausa_despues=0.4)
    add(seccion="cancion", narracion=tx["coro"], palabra="♪", imagen="portada", efecto="zoom_in",
        capitulo=tx["cap_cancion"], pausa_despues=0.4)
    for i in range(0, len(items), 2):
        par = items[i:i + 2]
        ab = "¡" if idioma == "es" else ""
        verso = " ".join(f"{ab}{p.palabra(idioma).capitalize()}, {p.palabra(idioma)}, {p.palabra(idioma)}!" for p in par)
        add(seccion="cancion", narracion=verso, palabra=" · ".join(p.palabra(idioma).upper() for p in par),
            imagen=par[0].clave, efecto="rebote", capitulo=tx["cap_cancion"], pausa_despues=0.4)
    add(seccion="cancion", narracion=tx["coro2"], palabra="★ ★ ★", imagen="portada", efecto="rebote",
        sonido="aplauso", capitulo=tx["cap_cancion"], pausa_despues=0.4)
    add(seccion="cancion", narracion=tx["coro"], palabra="♪", imagen="portada", efecto="zoom_out",
        capitulo=tx["cap_cancion"], pausa_despues=0.6)

    # 5) Ronda extra "¡Adivina!" si el video queda corto (mínimo 2 minutos).
    #    Depende solo del nº de elementos para que ES y EN tengan la misma estructura.
    if len(items) < 8:
        pos = next(i for i, e in enumerate(g.escenas) if e.seccion == "cancion")
        extra: list[Escena] = [Escena(id="", seccion="repaso", narracion=tx["otra_vez"], texto_pantalla=tx["otra_vez"],
                                      palabra="?", imagen="portada", efecto="zoom_in", sonido="whoosh",
                                      capitulo=tx["cap_ronda"])]
        for el in items:
            w = el.palabra(idioma)
            extra.append(Escena(id="", seccion="repaso", narracion=tx["adivina"], texto_pantalla="?",
                                palabra="?", imagen=el.clave, efecto="misterio", capitulo=tx["cap_ronda"],
                                pausa_despues=1.6))
            extra.append(Escena(id="", seccion="repaso", narracion=_fmt(tx["es_un"], el, idioma),
                                texto_pantalla=_fmt(tx["es_un"], el, idioma), palabra=w.upper(), imagen=el.clave,
                                efecto="rebote", sonido="aplauso", capitulo=tx["cap_ronda"], pausa_despues=0.8))
        g.escenas[pos:pos] = extra
        for i, e in enumerate(g.escenas, 1):
            e.id = f"e{i:03d}"
        n = len(g.escenas)

    # 6) Outro
    add(seccion="outro", narracion=_fmt(tx["fin1"], None, idioma, titulo=_titulo_frase(tema, idioma)),
        palabra="★ " + FELICITACIONES[idioma][0].upper().strip("¡!") + " ★", imagen="portada", efecto="zoom_in",
        sonido="aplauso", capitulo=tx["cap_outro"])
    add(seccion="outro", narracion=tx["fin2"], palabra="★ ★", imagen="portada", efecto="zoom_out",
        sonido="ding", capitulo=tx["cap_outro"], pausa_despues=1.5)

    if variante == "canta":  # más canción: repetir el bloque de versos
        versos = [e for e in g.escenas if e.seccion == "cancion" and e.imagen != "portada"]
        pos = max(i for i, e in enumerate(g.escenas) if e.seccion == "cancion") + 1
        g.escenas[pos:pos] = [Escena(**{**v.to_dict(), "id": ""}) for v in versos]
        for i, e in enumerate(g.escenas, 1):
            e.id = f"e{i:03d}"

    g.estimar_tiempos()
    return g


def generar_guion_short(tema: Tema, idioma: str = "es", texto_cta: str = "", semilla: int = 7) -> Guion:
    tx = T[idioma]
    rnd = random.Random(f"{tema.clave}-short-{semilla}")
    todos = list(tema.items)
    respuesta = next((i for i in todos if i.clave == tema.gancho_item), todos[0])
    resto = [i for i in todos if i is not respuesta]
    if tema.tipo == "numero":
        items = [i for i in todos if (i.cantidad or 0) <= (respuesta.cantidad or 5)][-5:]
        respuesta = items[-1]
    else:
        items = rnd.sample(resto, min(4, len(resto))) + [respuesta]  # la respuesta al final (retención)
    g = Guion(tema.clave, tema.titulo(idioma), idioma, "short", "short",
              palabras_clave=list(tema.palabras_clave), elementos=[i.to_dict() for i in items],
              prompt_portada=f"{tema.titulo_en} for kids")
    esc = g.escenas
    gancho = tema.gancho(idioma)
    # Gancho: la imagen de la respuesta aparece desenfocada ("misterio") y se revela al final
    esc.append(Escena("s001", "gancho", gancho, gancho.upper(), palabra="?", imagen=respuesta.clave,
                      pausa_despues=0.2, efecto="misterio", sonido="ding", capitulo="Gancho"))
    ab = "¡" if idioma == "es" else ""
    for el in items:
        w = el.palabra(idioma)
        narr = f"{ab}{w[:1].upper() + w[1:]}! {el.extra(idioma)}"
        esc.append(Escena(f"s{len(esc) + 1:03d}", "contenido", narr, w.upper(), palabra=w.upper(), imagen=el.clave,
                          pausa_despues=0.25, efecto="rebote" if len(esc) % 2 else "zoom_in", sonido="pop",
                          capitulo=w.capitalize()))
    # Mini repaso rápido: refuerza la memoria y alarga la retención
    lista = ", ".join(i.palabra(idioma) for i in items)
    repaso = f"{lista}. {FELICITACIONES[idioma][0]}"
    esc.append(Escena(f"s{len(esc) + 1:03d}", "contenido", repaso[:1].upper() + repaso[1:],
                      " · ".join(i.palabra(idioma).upper() for i in items), palabra=T[idioma]["insignia_repaso"],
                      imagen="portada", pausa_despues=0.3, efecto="zoom_in", sonido="whoosh",
                      capitulo=T[idioma]["cap_repaso"]))
    cta = cta_en_idioma(texto_cta, idioma) if texto_cta else tx["cta"]
    esc.append(Escena(f"s{len(esc) + 1:03d}", "cta", cta, tx["cta_pantalla"], palabra="♥",
                      imagen="portada", pausa_despues=0.8, efecto="rebote", sonido="aplauso", capitulo="CTA"))
    g.estimar_tiempos(factor_velocidad=1.25)
    return g


def generar_guion(tema: Tema | str, idioma: str = "es", formato: str = "largo", variante: str = "nombres",
                  texto_cta: str = "") -> Guion:
    """Punto de entrada: acepta un Tema o texto libre (se busca un tema predefinido)."""
    if isinstance(tema, str):
        encontrado = TEMAS.get(tema) or buscar_tema(tema)
        if encontrado is None:
            raise ValueError(
                f"No hay un tema predefinido para «{tema}». Usa tema_personalizado() con una lista de "
                "palabras o tema_con_claude() para generarlo con IA."
            )
        tema = encontrado
    if formato == "short":
        return generar_guion_short(tema, idioma, texto_cta)
    return generar_guion_largo(tema, idioma, variante)


# ---------------------------------------------------------------------------
# Doblaje de guiones editados a mano (traducción automática escena por escena)
# ---------------------------------------------------------------------------
def traducir_guion(guion: Guion, idioma_destino: str) -> Guion:
    """Traduce un guion manteniendo escenas, imágenes y estructura idénticas.

    Para temas de la base de datos es mejor regenerar con generar_guion(..., idioma)
    (traducción exacta, hecha por humanos). Esta función se usa para guiones editados.
    """
    from deep_translator import GoogleTranslator

    tr = GoogleTranslator(source=guion.idioma, target=idioma_destino)
    nuevo = Guion.from_dict(json.loads(json.dumps(guion.to_dict())))
    nuevo.idioma = idioma_destino
    nuevo.titulo = tr.translate(guion.titulo) or guion.titulo
    cache: dict[str, str] = {}

    def t(s: str) -> str:
        if not s.strip() or all(not c.isalpha() for c in s):
            return s
        if s not in cache:
            cache[s] = tr.translate(s) or s
        return cache[s]

    for e in nuevo.escenas:
        e.narracion = t(e.narracion)
        e.texto_pantalla = t(e.texto_pantalla)
        e.palabra = t(e.palabra).upper() if e.palabra else e.palabra
        e.capitulo = t(e.capitulo)
        e.duracion = e.inicio = 0.0
    nuevo.estimar_tiempos()
    return nuevo


# ---------------------------------------------------------------------------
# Temas libres con Claude (opcional)
# ---------------------------------------------------------------------------
_ESQUEMA_TEMA = {
    "type": "object",
    "properties": {
        "titulo_es": {"type": "string"},
        "titulo_en": {"type": "string"},
        "gancho_es": {"type": "string"},
        "gancho_en": {"type": "string"},
        "tipo": {"type": "string", "enum": ["animal", "objeto", "color", "numero", "forma", "emocion", "saludo"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clave": {"type": "string"},
                    "es": {"type": "string"},
                    "art_es": {"type": "string"},
                    "en": {"type": "string"},
                    "art_en": {"type": "string"},
                    "extra_es": {"type": "string"},
                    "extra_en": {"type": "string"},
                    "prompt": {"type": "string"},
                },
                "required": ["clave", "es", "art_es", "en", "art_en", "extra_es", "extra_en", "prompt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["titulo_es", "titulo_en", "gancho_es", "gancho_en", "tipo", "items"],
    "additionalProperties": False,
}

_SISTEMA_CLAUDE = """Eres un pedagogo experto en educación infantil temprana (2 a 5 años) y guionista \
de videos educativos para YouTube Kids. Diseñas vocabulario bilingüe (español/inglés) para un tema.

Reglas:
- Contenido 100% apropiado para niños pequeños: positivo, amable, sin miedo, violencia, peligro, \
marcas comerciales, personajes con copyright ni temas adultos.
- Palabras concretas, fáciles de pronunciar y de dibujar.
- art_es / art_en: artículo indefinido ("un", "una", "a", "an") o cadena vacía si no aplica.
- extra_es / extra_en: una frase de refuerzo de 3 a 8 palabras, simple y alegre.
- prompt: descripción visual breve EN INGLÉS de una ilustración infantil del elemento, sin texto.
- gancho: pregunta corta (máx. 8 palabras) que despierte curiosidad en los primeros 3 segundos.
- clave: identificador en minúsculas sin espacios ni acentos."""


def tema_con_claude(descripcion: str, n_elementos: int = 6) -> Tema:
    """Genera un Tema bilingüe para un tema libre usando Claude (requiere ANTHROPIC_API_KEY)."""
    import anthropic

    client = anthropic.Anthropic()
    respuesta = client.beta.messages.create(
        model=env("EVR_MODELO_CLAUDE", "claude-opus-5"),
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        thinking={"type": "adaptive"},
        system=_SISTEMA_CLAUDE,
        messages=[{
            "role": "user",
            "content": f"Tema del video: «{descripcion}». Crea exactamente {n_elementos} elementos.",
        }],
        output_config={"format": {"type": "json_schema", "schema": _ESQUEMA_TEMA}},
        extra_body={"fallbacks": "default"},
    )
    if respuesta.stop_reason == "refusal":
        raise RuntimeError("Claude rechazó generar este tema. Prueba con otra descripción.")
    texto = next(b.text for b in respuesta.content if b.type == "text")
    datos = json.loads(texto)
    from utilidades import slug

    items = [Elemento(**{**it, "clave": slug(it["clave"] or it["es"])}) for it in datos["items"]]
    return Tema(slug(datos["titulo_es"]), "personalizado", datos["tipo"], datos["titulo_es"], datos["titulo_en"],
                datos["gancho_es"], datos["gancho_en"], items, [descripcion.lower()])


def resolver_tema(texto: str, palabras: str = "", usar_claude: bool = False) -> Tema:
    """Convierte la entrada del usuario en un Tema.

    - texto coincide con un tema predefinido -> ese tema
    - `palabras` separadas por comas -> tema personalizado (traducción automática al inglés)
    - `usar_claude` -> vocabulario creado con Claude
    """
    if palabras.strip():
        lista = [p.strip() for p in palabras.replace(";", ",").split(",") if p.strip()]
        return tema_personalizado(texto or "Mi tema", lista)
    t = TEMAS.get(texto) or buscar_tema(texto)
    if t:
        return t
    if usar_claude and env("ANTHROPIC_API_KEY"):
        return tema_con_claude(texto)
    raise ValueError(
        f"«{texto}» no es un tema predefinido. Escribe una lista de palabras o activa Claude (ANTHROPIC_API_KEY)."
    )
