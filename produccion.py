"""Pipeline de producción de UN video (largo o Short, en un idioma).

guion -> imágenes -> voz -> música -> video -> miniatura -> descripción
      -> control de calidad -> (corrección) -> exportación organizada
"""
from __future__ import annotations

import json
import shutil
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from config import AVISO_MADE_FOR_KIDS, DIR_SALIDA, DIR_TRABAJO, Ajustes
from compositor_video import ResultadoComposicion, componer_video
from contenido_infantil import TEMAS, Tema
from control_calidad import InformeCalidad, revisar_video
from generador_descripciones import Metadatos, generar_metadatos, guardar_metadatos
from generador_guion import Guion, generar_guion
from generador_imagenes import GestorImagenes
from generador_miniaturas import crear_miniatura
from musica_efectos import elegir_musica
from tts_avanzado import PerfilVoz, narrar_guion, perfil_por_defecto
from utilidades import guardar_json, slug

Progreso = Callable[[float, str], None]


@dataclass
class ConfigProduccion:
    ajustes: Ajustes = field(default_factory=Ajustes)
    perfiles_voz: dict[str, PerfilVoz] = field(default_factory=dict)  # idioma -> perfil
    musica_largo: str | None = None  # ruta a pista propia (None = procedural CC0)
    musica_short: str | None = None
    variante: str = "nombres"

    def perfil(self, idioma: str) -> PerfilVoz:
        return self.perfiles_voz.get(idioma) or perfil_por_defecto(idioma)

    def gestor_imagenes(self) -> GestorImagenes:
        return GestorImagenes(motor=self.ajustes.motor_imagen, estilo=self.ajustes.estilo_imagen)


@dataclass
class ResultadoVideo:
    guion: Guion
    tema: Tema
    carpeta: Path
    nombre: str
    imagenes: dict[str, str]
    composicion: ResultadoComposicion | None = None
    miniatura: Path | None = None
    metadatos: Metadatos | None = None
    informe: InformeCalidad | None = None
    creditos: list[dict] = field(default_factory=list)
    exportado_en: Path | None = None

    @property
    def video(self) -> Path | None:
        return self.composicion.video if self.composicion else None


def _sub(progreso: Progreso | None, a: float, b: float) -> Progreso | None:
    """Reescala un sub-progreso [0,1] al rango [a,b] del progreso total."""
    if not progreso:
        return None
    return lambda f, m: progreso(a + (b - a) * max(0.0, min(1.0, f)), m)


def nombre_archivo(guion: Guion, numero: int | None = None) -> str:
    pref = f"{numero:02d}_" if numero is not None else ""
    suf = "_short" if guion.formato == "short" else ""
    return f"{pref}{slug(guion.titulo, 50)}{suf}_{guion.idioma}"


def producir_video(tema: Tema | str, idioma: str, formato: str, cfg: ConfigProduccion, numero: int | None = None,
                   guion: Guion | None = None, gestor: GestorImagenes | None = None,
                   progreso: Progreso | None = None, carpeta_trabajo: Path | None = None) -> ResultadoVideo:
    """Produce un video completo en la carpeta de trabajo (sin exportar todavía)."""
    if isinstance(tema, str):
        from generador_guion import resolver_tema

        tema = resolver_tema(tema)
    if tema.clave not in TEMAS:  # temas personalizados/IA: registrarlos para imágenes y doblaje
        TEMAS[tema.clave] = tema
    p = progreso or (lambda f, m: None)
    p(0.0, "Generando guion")
    guion = guion or generar_guion(tema, idioma, formato, cfg.variante, cfg.ajustes.texto_cta)
    nombre = nombre_archivo(guion, numero)
    carpeta = Path(carpeta_trabajo or DIR_TRABAJO / nombre)
    carpeta.mkdir(parents=True, exist_ok=True)

    gestor = gestor or cfg.gestor_imagenes()
    imagenes = gestor.imagenes_para_guion(guion, tema, progreso=_sub(p, 0.02, 0.15))
    audios = narrar_guion(guion, cfg.perfil(idioma), carpeta / "voz", progreso=_sub(p, 0.15, 0.3))
    p(0.3, "Preparando música")
    preferida = cfg.musica_short if formato == "short" else cfg.musica_largo
    musica = elegir_musica(formato, guion.duracion_real, preferida, semilla=zlib.crc32(tema.clave.encode()) % 97)
    comp = componer_video(guion, imagenes, audios, carpeta / f"{nombre}.mp4", cfg.ajustes, musica,
                          progreso=_sub(p, 0.3, 0.92))
    res = ResultadoVideo(guion, tema, carpeta, nombre, imagenes, comp)
    res.creditos = list(gestor.creditos) + ([{"clave": "musica", **musica.to_dict()}] if musica else []) + [
        {"clave": "voz", "fuente": f"TTS {cfg.perfil(idioma).motor} ({cfg.perfil(idioma).voz})",
         "licencia": "Audio sintetizado: uso comercial según los términos del motor TTS elegido"}]
    p(0.93, "Creando miniatura")
    crear_miniatura_para(res)
    p(0.95, "Escribiendo descripción y timestamps")
    escribir_metadatos(res)
    p(0.97, "Control de calidad")
    revisar(res)
    p(1.0, "Listo" if res.informe and res.informe.aprobado else "Listo (con avisos de calidad)")
    return res


def crear_miniatura_para(res: ResultadoVideo) -> Path:
    g = res.guion
    claves = [e["clave"] for e in g.elementos if e["clave"] in res.imagenes]
    if g.formato == "short" and g.escenas and g.escenas[0].imagen in res.imagenes:
        principal = g.escenas[0].imagen  # la respuesta al gancho
    else:
        principal = claves[0] if claves else "portada"
    extras = [res.imagenes[c] for c in claves if c != principal][:2]
    res.miniatura = crear_miniatura(g.titulo, res.imagenes[principal], res.carpeta / res.nombre, g.idioma,
                                    g.formato, extras, semilla=len(g.titulo))
    return res.miniatura


def escribir_metadatos(res: ResultadoVideo) -> None:
    res.metadatos = generar_metadatos(res.guion, res.tema.categoria)
    guardar_metadatos(res.metadatos, res.carpeta / res.nombre)
    (res.carpeta / "guion.md").write_text(res.guion.to_markdown(), encoding="utf-8")
    guardar_json(res.carpeta / "guion.json", res.guion.to_dict())
    guardar_json(res.carpeta / "creditos.json", res.creditos)


def revisar(res: ResultadoVideo) -> InformeCalidad:
    c = res.composicion
    res.informe = revisar_video(c.video if c else res.carpeta / f"{res.nombre}.mp4", res.guion, res.imagenes,
                                res.miniatura, c.srt if c else None, c.audio if c else None,
                                c.estadisticas_audio if c else None)
    (res.carpeta / "informe_calidad.md").write_text(res.informe.a_markdown(), encoding="utf-8")
    guardar_json(res.carpeta / "informe_calidad.json", res.informe.to_dict())
    return res.informe


def corregir(res: ResultadoVideo, cfg: ConfigProduccion, progreso: Progreso | None = None) -> InformeCalidad:
    """Aplica correcciones automáticas para los fallos que las admiten y vuelve a revisar."""
    fallos = {v.nombre: v for v in (res.informe.fallos if res.informe else [])}
    rerender = False
    if "Imágenes válidas" in fallos or "Fotogramas sin negro" in fallos:
        gestor = GestorImagenes(motor="procedural", estilo=cfg.ajustes.estilo_imagen)
        res.imagenes = gestor.imagenes_para_guion(res.guion, res.tema, forzar=set(res.imagenes))
        rerender = True
    if "Balance voz/música" in fallos and res.composicion:
        b = res.composicion.estadisticas_audio.get("balance_db") or 15
        objetivo = 15.0  # dB de separación ideal
        cfg.ajustes.volumen_musica = max(0.02, min(1.0, cfg.ajustes.volumen_musica * 10 ** ((b - objetivo) / 20)))
        rerender = True
    if any(k in fallos for k in ("Formato", "Pista de audio", "Subtítulos", "Audio sin silencios largos")):
        rerender = True
    if rerender:
        audios = sorted((res.carpeta / "voz").glob("*.wav"))
        preferida = cfg.musica_short if res.guion.formato == "short" else cfg.musica_largo
        musica = elegir_musica(res.guion.formato, res.guion.duracion_real, preferida,
                               semilla=zlib.crc32(res.tema.clave.encode()) % 97)
        res.composicion = componer_video(res.guion, res.imagenes, audios, res.carpeta / f"{res.nombre}.mp4",
                                         cfg.ajustes, musica, progreso)
    if "Miniatura" in fallos or rerender:
        crear_miniatura_para(res)
    escribir_metadatos(res)
    return revisar(res)


def carpeta_exportacion(res: ResultadoVideo, raiz: Path) -> Path:
    tipo = "shorts" if res.guion.formato == "short" else "videos_largos"
    return Path(raiz) / tipo / res.guion.idioma / res.nombre


def exportar(res: ResultadoVideo, raiz: Path | None = None, forzar: bool = False) -> Path:
    """Copia video + miniatura + descripción + timestamps + srt a la carpeta final organizada."""
    if res.informe and not res.informe.aprobado and not forzar:
        raise RuntimeError("El video no pasó el control de calidad. Corrige o usa forzar=True.")
    raiz = Path(raiz or DIR_SALIDA / slug(res.tema.titulo_es))
    destino = carpeta_exportacion(res, raiz)
    destino.mkdir(parents=True, exist_ok=True)
    archivos = [res.carpeta / f"{res.nombre}{ext}" for ext in (".mp4", ".jpg", ".md", ".srt")]
    archivos += [res.carpeta / f"{res.nombre}_timestamps.txt", res.carpeta / f"{res.nombre}_descripcion.txt",
                 res.carpeta / "guion.md", res.carpeta / "informe_calidad.md", res.carpeta / "creditos.json"]
    for a in archivos:
        if a.exists():
            shutil.copy2(a, destino / a.name)
    if res.informe and not res.informe.aprobado:
        (destino / "ATENCION_EXPORTACION_FORZADA.txt").write_text(
            "Este video se exportó sin superar todas las verificaciones de calidad.\n\n" + res.informe.a_markdown(),
            encoding="utf-8")
    escribir_aviso_made_for_kids(raiz)
    res.exportado_en = destino
    # resumen por video: permite consolidar series generadas en paralelo (GitHub Actions)
    guardar_json(destino / "resumen.json", {"numero": _numero_de(res.nombre), **resumen_resultado(res),
                                            "exportado_en": str(destino.relative_to(raiz))})
    return destino


def _numero_de(nombre: str) -> int:
    pref = nombre.split("_", 1)[0]
    return int(pref) if pref.isdigit() else 0


def escribir_aviso_made_for_kids(raiz: Path) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "LEEME_MADE_FOR_KIDS.txt").write_text(AVISO_MADE_FOR_KIDS + "\n", encoding="utf-8")


def resumen_resultado(res: ResultadoVideo) -> dict:
    return {
        "nombre": res.nombre,
        "titulo": res.metadatos.titulo if res.metadatos else res.guion.titulo,
        "formato": res.guion.formato,
        "idioma": res.guion.idioma,
        "duracion": round(res.guion.duracion_real, 1),
        "aprobado": bool(res.informe and res.informe.aprobado),
        "fallos": [v.nombre for v in (res.informe.fallos if res.informe else [])],
        "video": str(res.video) if res.video else None,
        "exportado_en": str(res.exportado_en) if res.exportado_en else None,
    }


def cargar_json(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))

