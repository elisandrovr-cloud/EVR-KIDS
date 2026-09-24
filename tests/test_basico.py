"""Pruebas offline de EVR-KIDS (no necesitan internet ni claves).

    pytest -q                      # pruebas rápidas
    EVR_TEST_RENDER=1 pytest -q    # incluye el render completo de un Short (~1 min)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contenido_infantil import TEMAS, buscar_tema  # noqa: E402
from control_calidad import revisar_lenguaje  # noqa: E402
from generador_descripciones import _contar, calcular_timestamps, generar_metadatos  # noqa: E402
from generador_guion import VARIANTES, generar_guion  # noqa: E402
from generador_imagenes import GestorImagenes, optimizar_prompt  # noqa: E402
from generador_miniaturas import crear_miniatura, validar_miniatura  # noqa: E402
from generador_series import planificar_serie  # noqa: E402
from utilidades import imagen_valida  # noqa: E402


@pytest.mark.parametrize("clave", list(TEMAS))
def test_guiones_bilingues_misma_estructura(clave):
    for variante in VARIANTES:
        es = generar_guion(clave, "es", "largo", variante)
        en = generar_guion(clave, "en", "largo", variante)
        assert [e.imagen for e in es.escenas] == [e.imagen for e in en.escenas]
        assert [e.seccion for e in es.escenas] == [e.seccion for e in en.escenas]
    sh_es, sh_en = generar_guion(clave, "es", "short"), generar_guion(clave, "en", "short")
    assert [e.imagen for e in sh_es.escenas] == [e.imagen for e in sh_en.escenas]


@pytest.mark.parametrize("clave", list(TEMAS))
def test_estructura_y_duracion_estimada(clave):
    g = generar_guion(clave, "es", "largo")
    secciones = [e.seccion for e in g.escenas]
    assert secciones[0] == "intro" and secciones[-1] == "outro"
    assert "leccion" in secciones and "cancion" in secciones
    assert 120 <= g.duracion_estimada <= 300
    s = generar_guion(clave, "es", "short")
    assert s.escenas[0].seccion == "gancho" and s.escenas[-1].seccion == "cta"
    assert 15 <= s.duracion_estimada <= 60
    assert len(s.escenas[0].narracion.split()) <= 9  # gancho corto (≈3 s)


def test_buscar_tema_texto_libre():
    assert buscar_tema("animales de la granja").clave == "animales_granja"
    assert buscar_tema("números del 1 al 10").clave == "numeros_1_10"
    assert buscar_tema("aprender a decir hola y adiós").clave == "saludos"


def test_lenguaje_apto():
    for t in TEMAS:
        g = generar_guion(t, "es")
        assert revisar_lenguaje([e.narracion for e in g.escenas])[0]
    assert not revisar_lenguaje(["El monstruo tiene un cuchillo"])[0]


def test_prompt_optimizado():
    p, n = optimizar_prompt("a cute cow", "acuarela")
    assert "watercolor" in p and "no text" in p
    assert "scary" in n and "text" in n


def test_imagenes_procedurales_y_miniatura(tmp_path):
    g = generar_guion("formas", "es")
    gestor = GestorImagenes(motor="procedural", carpeta=tmp_path / "img")
    rutas = gestor.imagenes_para_guion(g)
    assert "portada" in rutas
    for r in rutas.values():
        assert imagen_valida(Path(r))[0]
        assert Path(r).with_suffix(".json").exists()  # metadatos de licencia
    mini = crear_miniatura(g.titulo, rutas["circulo"], tmp_path / "video", "es", "largo", [rutas["estrella"]])
    assert validar_miniatura(mini)[0]


def test_descripcion_y_timestamps():
    g = generar_guion("animales_granja", "es")
    g.aplicar_duraciones([e.duracion_est for e in g.escenas])
    m = generar_metadatos(g, "animales")
    assert 200 <= _contar(m.descripcion) <= 400
    assert len(m.titulo) <= 100
    ts = calcular_timestamps(g)
    assert ts[0][0] == "00:00" and len(ts) >= 3
    segs = [int(a[:2]) * 60 + int(a[3:]) for a, _ in ts]
    assert all(b - a >= 10 for a, b in zip(segs, segs[1:]))
    assert len(", ".join(m.tags)) <= 500
    s = generar_guion("animales_granja", "en", "short")
    s.aplicar_duraciones([e.duracion_est for e in s.escenas])
    assert "#shorts" in generar_metadatos(s).hashtags


def test_plan_serie_sin_repetidos():
    plan = planificar_serie("animales", 10)
    combinaciones = {(p.tema, p.variante) for p in plan}
    assert len(combinaciones) == 10


def test_musica_procedural(tmp_path):
    from musica_efectos import generar_musica, ruta_efecto

    ruta = generar_musica(12, "energica", 1, tmp_path / "m.wav")
    assert ruta.exists() and ruta.stat().st_size > 100_000
    assert ruta_efecto("pop").exists()


@pytest.mark.skipif(not os.getenv("EVR_TEST_RENDER"), reason="render lento: EVR_TEST_RENDER=1")
def test_render_short_completo(tmp_path):
    from config import Ajustes
    from produccion import ConfigProduccion, producir_video
    from tts_avanzado import PerfilVoz

    cfg = ConfigProduccion(ajustes=Ajustes(preset_x264="ultrafast"),
                           perfiles_voz={"es": PerfilVoz(motor="prueba", voz="tono")})
    r = producir_video("colores", "es", "short", cfg, carpeta_trabajo=tmp_path)
    assert r.informe.aprobado, r.informe.a_markdown()


def _llamar_wsgi(ruta: str, query: str = ""):
    from wsgiref.util import setup_testing_defaults

    import app as web

    entorno: dict = {}
    setup_testing_defaults(entorno)
    entorno.update(PATH_INFO=ruta, QUERY_STRING=query)
    estado: list[str] = []
    cuerpo = b"".join(web.app(entorno, lambda s, h: estado.append(s)))
    return estado[0], cuerpo.decode("utf-8")


def test_app_web_exporta_app_para_vercel():
    import app as web

    assert callable(web.app) and web.application is web.app
    estado, html = _llamar_wsgi("/", "tema=colores&idioma=en&formato=short")
    assert estado == "200 OK" and "What color" in html
    estado, cuerpo = _llamar_wsgi("/api/guion", "tema=animales_granja&idioma=es")
    assert estado == "200 OK" and '"timestamps"' in cuerpo
    assert _llamar_wsgi("/api/temas")[0] == "200 OK"
    assert _llamar_wsgi("/api/guion", "tema=inexistente")[0].startswith("400")
    assert _llamar_wsgi("/nada")[0].startswith("404")


def test_app_web_no_importa_dependencias_pesadas():
    import subprocess

    raiz = Path(__file__).resolve().parents[1]
    codigo = ("import sys, app; pesados = [m for m in ('numpy', 'PIL', 'streamlit', 'moviepy') "
              "if m in sys.modules]; assert not pesados, pesados")
    subprocess.run([sys.executable, "-S", "-c", codigo], cwd=raiz, check=True)
