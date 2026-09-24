"""Interfaz de línea de comandos de EVR-KIDS.

Ejemplos:
    python cli.py temas
    python cli.py guion animales_granja --idioma es --formato largo
    python cli.py video colores --formato ambos --idiomas es en
    python cli.py serie animales -n 5 --formatos largo short --idiomas es en
    python cli.py voces --idioma es --edad niño
    python cli.py preview --perfil "Maestra alegre (ES)"
"""
from __future__ import annotations

import argparse
import sys

from typing import TYPE_CHECKING

from config import Ajustes, asegurar_carpetas
from contenido_infantil import CATEGORIAS, TEMAS

if TYPE_CHECKING:
    from produccion import ConfigProduccion


def _cfg(a) -> "ConfigProduccion":
    from produccion import ConfigProduccion
    from tts_avanzado import cargar_perfiles

    perfiles = cargar_perfiles()
    ajustes = Ajustes(resolucion=a.resolucion, estilo_imagen=a.estilo, motor_imagen=a.motor_imagen,
                      volumen_musica=a.volumen_musica, texto_cta=a.cta or "")
    if a.preset:
        ajustes.preset_x264 = a.preset
    pv = {}
    for idioma, nombre in (("es", a.voz_es), ("en", a.voz_en)):
        if nombre:
            if nombre not in perfiles:
                sys.exit(f"Perfil de voz desconocido: {nombre}. Usa: {', '.join(perfiles)}")
            pv[idioma] = perfiles[nombre]
    if a.motor_voz:
        from tts_avanzado import perfil_por_defecto

        for idioma in ("es", "en"):
            base = pv.get(idioma) or perfil_por_defecto(idioma)
            pv[idioma] = base.variante(motor=a.motor_voz, voz="tono" if a.motor_voz == "prueba" else base.voz)
    return ConfigProduccion(ajustes=ajustes, perfiles_voz=pv, musica_largo=a.musica, musica_short=a.musica_short)


def _progreso(f: float, m: str) -> None:
    barra = "█" * int(f * 30) + "░" * (30 - int(f * 30))
    print(f"\r[{barra}] {f * 100:5.1f}%  {m[:60]:<60}", end="", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="EVR-KIDS: videos educativos infantiles para YouTube")
    sub = ap.add_subparsers(dest="cmd", required=True)

    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--resolucion", default="1080p", choices=["1080p", "720p"])
    comunes.add_argument("--estilo", default="cartoon")
    comunes.add_argument("--motor-imagen", default="procedural")
    comunes.add_argument("--volumen-musica", type=float, default=0.18)
    comunes.add_argument("--musica", help="Pista propia (libre de derechos) para videos largos")
    comunes.add_argument("--musica-short", help="Pista propia para Shorts")
    comunes.add_argument("--voz-es", help="Nombre del perfil de voz en español")
    comunes.add_argument("--voz-en", help="Nombre del perfil de voz en inglés")
    comunes.add_argument("--motor-voz", help="Forzar motor TTS (edge, gtts, azure, elevenlabs, polly, prueba)")
    comunes.add_argument("--cta", help="Texto del llamado a la acción de los Shorts")
    comunes.add_argument("--preset", help="Preset x264 (ultrafast ... slow)")
    comunes.add_argument("--forzar", action="store_true", help="Exportar aunque falle el control de calidad")

    sub.add_parser("temas", help="Lista temas y categorías")

    g = sub.add_parser("guion", help="Muestra el guion con marcas de tiempo")
    g.add_argument("tema")
    g.add_argument("--idioma", default="es")
    g.add_argument("--formato", default="largo", choices=["largo", "short"])
    g.add_argument("--variante", default="nombres")

    v = sub.add_parser("video", parents=[comunes], help="Genera un video (largo, short o ambos)")
    v.add_argument("tema", help="Clave o texto del tema (ej. 'colores', 'animales de la granja')")
    v.add_argument("--palabras", default="", help="Tema personalizado: palabras separadas por comas")
    v.add_argument("--claude", action="store_true", help="Crear el vocabulario con Claude (ANTHROPIC_API_KEY)")
    v.add_argument("--formato", default="ambos", choices=["largo", "short", "ambos"])
    v.add_argument("--idiomas", nargs="+", default=["es"])
    v.add_argument("--variante", default="nombres")

    s = sub.add_parser("serie", parents=[comunes], help="Genera una serie completa")
    s.add_argument("categoria", help=f"Categoría: {', '.join(CATEGORIAS)}")
    s.add_argument("-n", type=int, default=5)
    s.add_argument("--formatos", nargs="+", default=["largo", "short"])
    s.add_argument("--idiomas", nargs="+", default=["es"])
    s.add_argument("--nombre")

    vz = sub.add_parser("voces", help="Lista voces del catálogo")
    vz.add_argument("--motor")
    vz.add_argument("--idioma")
    vz.add_argument("--genero")
    vz.add_argument("--edad")

    pv = sub.add_parser("preview", help="Genera una vista previa de voz (WAV)")
    pv.add_argument("--perfil", default="Maestra alegre (ES)")
    pv.add_argument("--texto")

    a = ap.parse_args(argv)
    asegurar_carpetas()

    if a.cmd == "temas":
        for cat, claves in CATEGORIAS.items():
            if cat == "mixta":
                continue
            print(f"\n[{cat}]")
            for c in claves:
                t = TEMAS[c]
                print(f"  {c:<20} {t.titulo_es} / {t.titulo_en}  ({len(t.items)} elementos)")
        return 0

    if a.cmd == "guion":
        from generador_guion import generar_guion

        print(generar_guion(a.tema, a.idioma, a.formato, a.variante).to_markdown())
        return 0

    if a.cmd == "voces":
        from tts_avanzado import etiqueta_voz, filtrar_voces

        for vv in filtrar_voces(a.motor, a.idioma, a.genero, a.edad):
            print(f"{vv['motor']:<11} {vv['id']:<24} {etiqueta_voz(vv)}")
        return 0

    if a.cmd == "preview":
        from tts_avanzado import cargar_perfiles, vista_previa

        ruta = vista_previa(cargar_perfiles()[a.perfil], a.texto)
        print(f"Vista previa: {ruta}")
        return 0

    cfg = _cfg(a)
    if a.cmd == "video":
        from generador_guion import resolver_tema
        from generador_shorts import formatos_para
        from produccion import corregir, exportar, producir_video

        cfg.variante = a.variante
        tema = resolver_tema(a.tema, a.palabras, a.claude)
        formatos = formatos_para({"ambos": "ambos", "largo": "solo_largo", "short": "solo_short"}[a.formato])
        gestor = cfg.gestor_imagenes()
        for idioma in a.idiomas:
            for formato in formatos:
                print(f"\n▶ {tema.titulo(idioma)} · {formato} · {idioma}")
                r = producir_video(tema, idioma, formato, cfg, numero=1, gestor=gestor, progreso=_progreso)
                print()
                if not r.informe.aprobado:
                    print("  Corrigiendo…")
                    corregir(r, cfg)
                print(r.informe.a_markdown())
                if r.informe.aprobado or a.forzar:
                    print("  Exportado en:", exportar(r, forzar=a.forzar))
                else:
                    print(f"  ✗ No exportado (usa --forzar). Trabajo en: {r.carpeta}")
        return 0

    if a.cmd == "serie":
        from generador_series import arbol_carpetas, generar_serie

        def prog(ev):
            _progreso(ev.fraccion_total, f"[{ev.paso}/{ev.pasos_totales}] {ev.mensaje}")

        r = generar_serie(a.categoria, a.n, cfg, a.formatos, a.idiomas, a.nombre, forzar_exportacion=a.forzar,
                          progreso=prog)
        print("\n\n" + r.a_markdown())
        print(arbol_carpetas(r.carpeta))
        return 0 if not r.errores else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
