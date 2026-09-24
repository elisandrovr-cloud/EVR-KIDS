"""Generación de series completas (5, 10, 15... videos) con Shorts y doblaje.

Ejemplo: "Serie de 10 videos de animales" -> 6 temas de animales x variantes
(nombres, adivina, canta). Cada video tiene su guion, imágenes, miniatura,
descripción y timestamps; opcionalmente su Short y su versión en inglés.

Estructura final:
    salida/<serie>/
        LEEME_MADE_FOR_KIDS.txt
        resumen_serie.md / serie.json
        videos_largos/es/01_.../   (mp4, jpg, md, srt, timestamps, guion, informe, créditos)
        videos_largos/en/01_.../
        shorts/es/01_..._short_es/
        shorts/en/01_..._short_en/
"""
from __future__ import annotations

import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from config import AVISO_MADE_FOR_KIDS, DIR_SALIDA, DIR_TRABAJO
from contenido_infantil import CATEGORIAS, NOMBRES_CATEGORIAS, TEMAS
from generador_guion import VARIANTES
from produccion import ConfigProduccion, corregir, escribir_aviso_made_for_kids, exportar, producir_video, resumen_resultado
from utilidades import guardar_json, slug


@dataclass
class PlanVideo:
    numero: int
    tema: str
    variante: str
    titulo_es: str
    titulo_en: str


@dataclass
class EventoProgreso:
    fraccion_total: float
    paso: int
    pasos_totales: int
    numero: int
    formato: str
    idioma: str
    mensaje: str
    fraccion_paso: float = 0.0


@dataclass
class ResultadoSerie:
    nombre: str
    carpeta: Path
    plan: list[PlanVideo]
    videos: list[dict] = field(default_factory=list)
    errores: list[dict] = field(default_factory=list)
    segundos: float = 0.0

    def a_markdown(self) -> str:
        lineas = [f"# Serie: {self.nombre}", "", f"- Videos planificados: {len(self.plan)}",
                  f"- Archivos generados: {len(self.videos)}", f"- Errores: {len(self.errores)}",
                  f"- Tiempo total: {self.segundos / 60:.1f} min", "", "## Videos", "",
                  "| # | Formato | Idioma | Título | Duración | Calidad | Carpeta |", "|---|---|---|---|---|---|---|"]
        for v in self.videos:
            calidad = "✓" if v["aprobado"] else "✗ " + ", ".join(v["fallos"])
            carpeta = Path(v["exportado_en"]).relative_to(self.carpeta) if v.get("exportado_en") else "(no exportado)"
            lineas.append(f"| {v['numero']:02d} | {v['formato']} | {v['idioma']} | {v['titulo']} | "
                          f"{v['duracion']:.0f} s | {calidad} | `{carpeta}` |")
        if self.errores:
            lineas += ["", "## Errores", ""] + [f"- #{e['numero']} {e['formato']} {e['idioma']}: {e['error']}"
                                                for e in self.errores]
        lineas += ["", "---", "", AVISO_MADE_FOR_KIDS]
        return "\n".join(lineas) + "\n"


def planificar_serie(categoria: str | list[str], n: int) -> list[PlanVideo]:
    """Reparte N videos entre los temas de la categoría, rotando variantes para no repetir."""
    temas = list(categoria) if isinstance(categoria, list) else CATEGORIAS.get(categoria, [])
    if not temas:
        raise ValueError(f"Categoría desconocida: {categoria}. Opciones: {', '.join(CATEGORIAS)}")
    plan = []
    for i in range(n):
        tema = TEMAS[temas[i % len(temas)]]
        variante = VARIANTES[(i // len(temas)) % len(VARIANTES)]
        plan.append(PlanVideo(i + 1, tema.clave, variante, tema.titulo_es, tema.titulo_en))
    return plan


def generar_serie(categoria: str | list[str], n: int, cfg: ConfigProduccion, formatos: list[str] | None = None,
                  idiomas: list[str] | None = None, nombre: str | None = None, exportar_auto: bool = True,
                  forzar_exportacion: bool = False, corregir_auto: bool = True,
                  progreso: Callable[[EventoProgreso], None] | None = None) -> ResultadoSerie:
    formatos = formatos or ["largo", "short"]
    idiomas = idiomas or ["es"]
    plan = planificar_serie(categoria, n)
    nombre_cat = NOMBRES_CATEGORIAS.get(categoria, "Personalizada") if isinstance(categoria, str) else "Personalizada"
    nombre = nombre or f"Serie {nombre_cat} ({n} videos)"
    raiz = DIR_SALIDA / slug(nombre)
    raiz.mkdir(parents=True, exist_ok=True)
    escribir_aviso_made_for_kids(raiz)
    res = ResultadoSerie(nombre, raiz, plan)
    guardar_json(raiz / "plan_serie.json", [asdict(p) for p in plan])
    gestor = cfg.gestor_imagenes()  # un solo gestor: las imágenes se reutilizan entre idiomas y formatos
    pasos = [(p, f, i) for p in plan for f in formatos for i in idiomas]
    t0 = time.time()

    for k, (p, formato, idioma) in enumerate(pasos):
        base = k / len(pasos)

        def sub(f: float, m: str, _k=k, _p=p, _f=formato, _i=idioma, _b=base) -> None:
            if progreso:
                progreso(EventoProgreso(_b + f / len(pasos), _k + 1, len(pasos), _p.numero, _f, _i, m, f))

        sub(0.0, f"Video {p.numero}/{n} · {formato} · {idioma}: {p.titulo_es}")
        try:
            cfg.variante = p.variante
            carpeta = DIR_TRABAJO / slug(nombre) / f"{p.numero:02d}_{formato}_{idioma}"
            r = producir_video(TEMAS[p.tema], idioma, formato, cfg, numero=p.numero, gestor=gestor,
                               progreso=sub, carpeta_trabajo=carpeta)
            if corregir_auto and r.informe and not r.informe.aprobado:
                sub(0.98, "Corrigiendo problemas de calidad")
                corregir(r, cfg)
            if exportar_auto and (r.informe.aprobado or forzar_exportacion):
                exportar(r, raiz, forzar=forzar_exportacion)
            res.videos.append({"numero": p.numero, **resumen_resultado(r)})
        except Exception as e:  # noqa: BLE001 - la serie continúa aunque un video falle
            res.errores.append({"numero": p.numero, "formato": formato, "idioma": idioma, "error": str(e),
                                "traza": traceback.format_exc()})
        res.segundos = time.time() - t0
        (raiz / "resumen_serie.md").write_text(res.a_markdown(), encoding="utf-8")
        guardar_json(raiz / "serie.json", {"nombre": nombre, "videos": res.videos, "errores": res.errores})

    if progreso:
        progreso(EventoProgreso(1.0, len(pasos), len(pasos), n, "", "", "Serie completada", 1.0))
    return res


def arbol_carpetas(raiz: Path, max_archivos: int = 400) -> str:
    """Representación en texto del árbol de carpetas de salida (para la interfaz)."""
    raiz = Path(raiz)
    lineas = [raiz.name + "/"]
    cuenta = 0

    def rec(d: Path, pref: str) -> None:
        nonlocal cuenta
        hijos = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, h in enumerate(hijos):
            cuenta += 1
            if cuenta > max_archivos:
                return
            ult = i == len(hijos) - 1
            lineas.append(f"{pref}{'└── ' if ult else '├── '}{h.name}{'/' if h.is_dir() else ''}")
            if h.is_dir():
                rec(h, pref + ("    " if ult else "│   "))

    if raiz.exists():
        rec(raiz, "")
    return "\n".join(lineas)
