"""EJEMPLO COMPLETO: serie de 5 videos largos de animales + sus Shorts +
miniaturas + descripciones con timestamps + versión doblada al inglés.

Uso:
    python ejemplo_serie.py                 # calidad final (1080p, edge-tts)
    python ejemplo_serie.py --rapido        # prueba rápida (720p, preset ultrafast)
    python ejemplo_serie.py --rapido --offline   # sin internet (voz de prueba; NO publicar)
    python ejemplo_serie.py --motor-imagen diffusers --estilo acuarela   # imágenes con IA

Resultado (20 videos = 5 temas x 2 formatos x 2 idiomas):
    salida/serie-animales-para-ninos/
        LEEME_MADE_FOR_KIDS.txt
        resumen_serie.md
        videos_largos/es/01_los-animales-de-la-granja_es/...
        videos_largos/en/01_farm-animals_en/...
        shorts/es/01_los-animales-de-la-granja_short_es/...
        shorts/en/01_farm-animals_short_en/...
"""
from __future__ import annotations

import argparse
import time

from config import Ajustes, asegurar_carpetas
from generador_series import arbol_carpetas, generar_serie
from produccion import ConfigProduccion
from tts_avanzado import PerfilVoz


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rapido", action="store_true", help="720p + preset ultrafast (para probar)")
    ap.add_argument("--offline", action="store_true", help="Voz sintética de prueba (sin internet)")
    ap.add_argument("--motor-imagen", default="procedural",
                    help="procedural | diffusers | automatic1111 | comfyui | stability | replicate | huggingface | "
                         "pixabay | pexels | unsplash | wikimedia | stock_auto")
    ap.add_argument("--estilo", default="cartoon", help="cartoon | acuarela | 3d_suave | flat | crayon | papel")
    ap.add_argument("-n", type=int, default=5)
    a = ap.parse_args()
    asegurar_carpetas()

    ajustes = Ajustes(
        resolucion="720p" if a.rapido else "1080p",
        motor_imagen=a.motor_imagen,
        estilo_imagen=a.estilo,
        volumen_musica=0.18,  # música ~15 dB por debajo de la voz
    )
    if a.rapido:
        ajustes.preset_x264 = "ultrafast"

    # Voces: una maestra alegre en español y una voz infantil real en inglés (doblaje)
    voz_es = PerfilVoz("Maestra alegre (ES)", "edge", "es", "es-MX-DaliaNeural", velocidad="lenta",
                       tono_hz=2, pausa_frases=0.5, estilo="alegre")
    voz_en = PerfilVoz("Kid voice (EN)", "edge", "en", "en-US-AnaNeural", velocidad="lenta",
                       pausa_frases=0.5, estilo="alegre")
    if a.offline:
        voz_es = voz_es.variante(motor="prueba", voz="tono")
        voz_en = voz_en.variante(motor="prueba", voz="tono")

    cfg = ConfigProduccion(ajustes=ajustes, perfiles_voz={"es": voz_es, "en": voz_en})

    def progreso(ev) -> None:
        barra = "█" * int(ev.fraccion_total * 30) + "░" * (30 - int(ev.fraccion_total * 30))
        print(f"\r[{barra}] {ev.fraccion_total * 100:5.1f}%  paso {ev.paso}/{ev.pasos_totales}  "
              f"#{ev.numero} {ev.formato:<5} {ev.idioma}  {ev.mensaje[:40]:<40}", end="", flush=True)

    t0 = time.time()
    serie = generar_serie(
        categoria="animales",
        n=a.n,
        cfg=cfg,
        formatos=["largo", "short"],  # video largo + su Short
        idiomas=["es", "en"],         # español + doblaje al inglés (mismas imágenes y estructura)
        nombre="Serie Animales para Niños",
        progreso=progreso,
    )
    print(f"\n\nTerminado en {(time.time() - t0) / 60:.1f} min\n")
    print(serie.a_markdown())
    print(arbol_carpetas(serie.carpeta))


if __name__ == "__main__":
    main()
