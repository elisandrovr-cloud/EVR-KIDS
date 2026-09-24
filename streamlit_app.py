"""EVR-KIDS · Interfaz gráfica (Streamlit).

Ejecutar:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (AVISO_MADE_FOR_KIDS, DIR_SALIDA, DIR_TRABAJO, IDIOMAS, Ajustes, asegurar_carpetas,
                    estado_claves)
from contenido_infantil import CATEGORIAS, NOMBRES_CATEGORIAS, TEMAS

st.set_page_config(page_title="EVR-KIDS · Videos educativos", page_icon="🎈", layout="wide")
asegurar_carpetas()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem;}
    .evr-titulo {font-size: 2.2rem; font-weight: 800; color: #ff595e; margin-bottom: 0;}
    .evr-sub {color: #1982c4; margin-top: 0;}
    .ok {color: #2e9e44; font-weight: 700;} .ko {color: #d62828; font-weight: 700;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<p class="evr-titulo">🎈 EVR-KIDS</p>', unsafe_allow_html=True)
st.markdown('<p class="evr-sub">Videos educativos para niños de 2 a 5 años · YouTube (Made for Kids) · '
            'Largos 16:9 + Shorts 9:16 · Español / English</p>', unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("guiones", {})
ss.setdefault("resultados", {})
ss.setdefault("imagenes", {})
ss.setdefault("editado", False)

# ---------------------------------------------------------------------------
# Barra lateral: ajustes globales
# ---------------------------------------------------------------------------
from generador_imagenes import ESTILOS, NOMBRES_ESTILOS, NOMBRES_MOTORES  # noqa: E402
from tts_avanzado import (ESTILOS_EMOCION, MOTORES_TTS, NOMBRES_VELOCIDAD, PerfilVoz, cargar_perfiles,  # noqa: E402
                          eliminar_perfil, etiqueta_voz, filtrar_voces, guardar_perfil, vista_previa)

with st.sidebar:
    st.header("⚙️ Ajustes de producción")
    resolucion = st.selectbox("Resolución (video largo)", ["1080p", "720p"], help="Los Shorts siempre son 1080x1920")
    motor_imagen = st.selectbox("Imágenes", list(NOMBRES_MOTORES), format_func=NOMBRES_MOTORES.get,
                                help="Si un motor falla se usa la ilustración procedural (CC0) como respaldo")
    estilo = st.selectbox("Estilo visual", list(ESTILOS), format_func=NOMBRES_ESTILOS.get)
    volumen_musica = st.slider("Volumen de la música (relativo a la voz)", 0.0, 0.6, 0.18, 0.01,
                               help="0.18 ≈ música 15 dB por debajo de la voz")
    usar_efectos = st.checkbox("Efectos de sonido (pop, ding, aplausos)", True)
    preset = st.selectbox("Velocidad de render", ["ultrafast", "veryfast", "medium", "slow"], index=2,
                          help="ultrafast = rápido pero archivo más grande; slow = mejor compresión")
    st.divider()
    perfiles = cargar_perfiles()
    st.subheader("🗣️ Voces activas")
    nombres_perfiles = list(perfiles)
    perfil_es = st.selectbox("Español", [n for n in nombres_perfiles if perfiles[n].idioma == "es"] or nombres_perfiles)
    perfil_en = st.selectbox("English", [n for n in nombres_perfiles if perfiles[n].idioma == "en"] or nombres_perfiles)
    st.divider()
    with st.expander("🔑 Servicios configurados (.env)"):
        for nombre, ok in estado_claves().items():
            st.write(("✅ " if ok else "▫️ ") + nombre)
        st.caption("edge-tts, ilustraciones y música procedurales no necesitan claves.")


def ajustes_actuales() -> Ajustes:
    return Ajustes(resolucion=resolucion, estilo_imagen=estilo, motor_imagen=motor_imagen,
                   volumen_musica=volumen_musica, usar_efectos=usar_efectos, preset_x264=preset,
                   texto_cta=ss.get("cta", ""))


def config_actual():
    from produccion import ConfigProduccion

    return ConfigProduccion(ajustes=ajustes_actuales(),
                            perfiles_voz={"es": perfiles[perfil_es], "en": perfiles[perfil_en]},
                            musica_largo=ss.get("musica_largo"), musica_short=ss.get("musica_short"),
                            variante=ss.get("variante", "nombres"))


def mostrar_informe(informe) -> None:
    filas = [{"": v.icono, "Verificación": v.nombre, "Detalle": v.detalle,
              "Corrección": "" if v.ok else v.correccion} for v in informe.verificaciones]
    if informe.aprobado:
        st.success("✅ Control de calidad APROBADO")
    else:
        st.error("❌ El video no superó el control de calidad")
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


tab_video, tab_serie, tab_voz, tab_musica, tab_calidad, tab_ayuda = st.tabs(
    ["🎬 Crear video", "📚 Series", "🗣️ Voz", "🎵 Música", "✅ Control de calidad", "ℹ️ Ayuda"])

# ---------------------------------------------------------------------------
# 1) Crear video
# ---------------------------------------------------------------------------
with tab_video:
    from generador_guion import VARIANTES, Guion, generar_guion, resolver_tema, traducir_guion
    from generador_shorts import CTA_SUGERIDOS, NOMBRES_MODOS, cta_en_idioma, formatos_para

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        opciones = ["__personalizado__", "__claude__"] + list(TEMAS)
        etiquetas = {"__personalizado__": "✏️ Tema personalizado (lista de palabras)",
                     "__claude__": "🤖 Tema libre con Claude (IA)"}
        clave = st.selectbox("Tema", opciones, index=2,
                             format_func=lambda k: etiquetas.get(k) or f"{TEMAS[k].titulo_es} · {TEMAS[k].titulo_en}")
        texto_tema, palabras = "", ""
        if clave == "__personalizado__":
            texto_tema = st.text_input("Título del tema", "Los juguetes")
            palabras = st.text_input("Palabras (separadas por comas)", "pelota, muñeca, bloques, tambor, cometa")
        elif clave == "__claude__":
            texto_tema = st.text_input("Describe el tema", "aprender a decir hola y adiós")
            st.caption("Requiere ANTHROPIC_API_KEY. Claude crea el vocabulario bilingüe; la app arma el guion.")
    with c2:
        modo = st.radio("Formato", list(NOMBRES_MODOS), format_func=NOMBRES_MODOS.get)
        ss.variante = st.selectbox("Variante (video largo)", VARIANTES,
                                   format_func={"nombres": "Nombres y repetición", "adivina": "¡Adivina!",
                                                "canta": "Más canción"}.get)
    with c3:
        idiomas = st.multiselect("Idiomas (doblaje)", list(IDIOMAS), default=["es"], format_func=IDIOMAS.get)
        ss.cta = st.selectbox("Llamado a la acción (Shorts)", CTA_SUGERIDOS["es"] + CTA_SUGERIDOS["en"],
                              help="YouTube recomienda que los CTA de contenido infantil se dirijan a los adultos")

    if st.button("1️⃣ Generar guion", type="primary"):
        try:
            if clave == "__personalizado__":
                tema = resolver_tema(texto_tema, palabras)
            elif clave == "__claude__":
                tema = resolver_tema(texto_tema, usar_claude=True)
            else:
                tema = TEMAS[clave]
            TEMAS.setdefault(tema.clave, tema)
            ss.tema = tema
            ss.guiones = {(i, f): generar_guion(tema, i, f, ss.variante, cta_en_idioma(ss.cta, i))
                          for i in idiomas for f in formatos_para(modo)}
            ss.resultados, ss.imagenes, ss.editado = {}, {}, False
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

    if ss.guiones:
        st.subheader("📝 Guiones")
        pestañas = st.tabs([f"{'🎞️ Largo' if f == 'largo' else '📱 Short'} · {i.upper()}" for (i, f) in ss.guiones])
        for pest, ((i, f), g) in zip(pestañas, list(ss.guiones.items())):
            with pest:
                st.caption(f"Duración estimada: {g.duracion_estimada:.0f} s · {len(g.escenas)} escenas")
                df = pd.DataFrame([{"t": f"{int(e.inicio_est // 60):02d}:{int(e.inicio_est % 60):02d}",
                                    "sección": e.seccion, "narración": e.narracion, "pantalla": e.palabra,
                                    "imagen": e.imagen} for e in g.escenas])
                editado = st.data_editor(df, hide_index=True, width="stretch", key=f"ed_{i}_{f}",
                                         disabled=["t", "sección", "imagen"], height=320)
                if st.button("💾 Aplicar ediciones", key=f"ap_{i}_{f}"):
                    for e, (_, fila) in zip(g.escenas, editado.iterrows()):
                        e.narracion, e.palabra = fila["narración"], fila["pantalla"]
                        e.texto_pantalla = e.narracion if e.seccion not in ("gancho", "cta") else e.texto_pantalla
                    g.estimar_tiempos()
                    ss.editado = True
                    if i == "es" and "en" in idiomas:
                        ss.guiones[("en", f)] = traducir_guion(g, "en")
                        st.info("Versión en inglés actualizada con traducción automática (mismas escenas e imágenes).")
                    st.success("Ediciones guardadas")
                with st.expander("Ver guion con marcas de tiempo (Markdown)"):
                    st.markdown(g.to_markdown())
                    st.download_button("⬇️ Descargar guion", g.to_markdown(), f"guion_{g.tema_clave}_{f}_{i}.md",
                                       key=f"dl_{i}_{f}")

        st.subheader("🖼️ Imágenes")
        if st.button("2️⃣ Generar imágenes"):
            from generador_imagenes import GestorImagenes

            gestor = GestorImagenes(motor=motor_imagen, estilo=estilo)
            barra = st.progress(0.0, "Generando imágenes…")
            for (i, f), g in ss.guiones.items():
                ss.imagenes.update({(i, k): v for k, v in gestor.imagenes_para_guion(
                    g, ss.tema, progreso=lambda x, m: barra.progress(x, m)).items()})
            barra.empty()
            ss.creditos_img = gestor.creditos
        if ss.imagenes:
            claves_img = sorted({k for (_, k) in ss.imagenes})
            cols = st.columns(6)
            for n, k in enumerate(claves_img):
                ruta = next(v for (i, kk), v in ss.imagenes.items() if kk == k)
                with cols[n % 6]:
                    st.image(ruta, caption=k, width="stretch")
                    meta = Path(ruta).with_suffix(".json")
                    if meta.exists():
                        st.caption("📄 " + json.loads(meta.read_text(encoding="utf-8")).get("licencia", "")[:60])
                    if st.button("🔄", key=f"re_{k}", help="Regenerar esta imagen con otra semilla"):
                        from generador_imagenes import GestorImagenes

                        gestor = GestorImagenes(motor=motor_imagen, estilo=estilo)
                        el = next((e for e in ss.tema.items if e.clave == k), None)
                        semilla = int(ss.get(f"sem_{k}", 42)) + 1
                        ss[f"sem_{k}"] = semilla
                        if el:
                            nueva = gestor.obtener(k, el.prompt, el.es, el, ss.tema.tipo, semilla=semilla, forzar=True)
                            for kk in list(ss.imagenes):
                                if kk[1] == k:
                                    ss.imagenes[kk] = nueva.ruta
                            st.rerun()

        st.subheader("🎬 Producción")
        if st.button("3️⃣ Producir video(s)", type="primary"):
            from generador_imagenes import GestorImagenes
            from produccion import producir_video

            cfg = config_actual()
            gestor = GestorImagenes(motor=motor_imagen, estilo=estilo)
            for (i, f), g in ss.guiones.items():
                barra = st.progress(0.0, f"{g.titulo} · {f} · {i}")
                try:
                    guion = Guion.from_dict(g.to_dict())
                    ss.resultados[(i, f)] = producir_video(
                        ss.tema, i, f, cfg, numero=1, guion=guion, gestor=gestor,
                        progreso=lambda x, m, b=barra, t=f"{f}·{i}": b.progress(min(1.0, x), f"{t}: {m}"))
                except Exception as e:  # noqa: BLE001
                    st.exception(e)
                barra.empty()

        for (i, f), r in ss.resultados.items():
            st.markdown(f"### {'🎞️ Video largo' if f == 'largo' else '📱 Short'} · {IDIOMAS[i]}")
            cv, ci = st.columns([3, 2] if f == "largo" else [1, 2])
            with cv:
                if r.video and Path(r.video).exists():
                    st.video(str(r.video))
                if r.miniatura:
                    st.image(str(r.miniatura), caption="Miniatura 1280x720")
            with ci:
                mostrar_informe(r.informe)
                b1, b2, b3 = st.columns(3)
                if b1.button("🛠️ Corregir", key=f"co_{i}_{f}", disabled=r.informe.aprobado):
                    from produccion import corregir

                    with st.spinner("Aplicando correcciones automáticas…"):
                        corregir(r, config_actual())
                    st.rerun()
                if b2.button("📦 Exportar", key=f"ex_{i}_{f}", disabled=not r.informe.aprobado, type="primary"):
                    from produccion import exportar

                    st.success(f"Exportado en `{exportar(r)}`")
                if b3.button("⚠️ Forzar exportación", key=f"fx_{i}_{f}", disabled=r.informe.aprobado):
                    from produccion import exportar

                    st.warning(f"Exportado (forzado) en `{exportar(r, forzar=True)}`")
                if r.metadatos:
                    with st.expander("📄 Título, descripción, timestamps y tags"):
                        st.text_input("Título", r.metadatos.titulo, key=f"ti_{i}_{f}")
                        st.text_area("Descripción", r.metadatos.descripcion, height=260, key=f"de_{i}_{f}")
                        st.text_area("Tags", ", ".join(r.metadatos.tags), key=f"ta_{i}_{f}")
            st.info("👶 Marca este video como **«Sí, es contenido creado para niños»** al subirlo.")

# ---------------------------------------------------------------------------
# 2) Series
# ---------------------------------------------------------------------------
with tab_serie:
    from generador_series import arbol_carpetas, generar_serie, planificar_serie
    from generador_shorts import NOMBRES_MODOS, formatos_para

    c1, c2, c3 = st.columns(3)
    with c1:
        categoria = st.selectbox("Categoría", list(CATEGORIAS), format_func=lambda c: NOMBRES_CATEGORIAS.get(c, c))
        n = st.select_slider("Número de videos", [3, 5, 10, 15, 20], value=5)
    with c2:
        modo_s = st.radio("Formatos", list(NOMBRES_MODOS), format_func=NOMBRES_MODOS.get, key="modo_serie")
        idiomas_s = st.multiselect("Idiomas", list(IDIOMAS), default=["es", "en"], format_func=IDIOMAS.get,
                                   key="idi_serie")
    with c3:
        nombre_s = st.text_input("Nombre de la serie", f"Serie {NOMBRES_CATEGORIAS.get(categoria, categoria)}")
        forzar_s = st.checkbox("Exportar aunque falle el control de calidad", False)
    plan = planificar_serie(categoria, n)
    total = n * len(formatos_para(modo_s)) * max(1, len(idiomas_s))
    st.caption(f"Se generarán **{total} videos** ({n} temas × {len(formatos_para(modo_s))} formato(s) × "
               f"{len(idiomas_s)} idioma(s)).")
    st.dataframe(pd.DataFrame([{"#": p.numero, "Tema": p.titulo_es, "Theme": p.titulo_en, "Variante": p.variante}
                               for p in plan]), hide_index=True, width="stretch")
    if st.button("🚀 Generar serie completa", type="primary", disabled=not idiomas_s):
        barra = st.progress(0.0, "Iniciando…")
        estado = st.empty()
        registro: list[str] = []

        def prog(ev) -> None:
            barra.progress(min(1.0, ev.fraccion_total),
                           f"Paso {ev.paso}/{ev.pasos_totales} · #{ev.numero} {ev.formato} {ev.idioma} · {ev.mensaje}")
            if ev.fraccion_paso == 0.0 and ev.mensaje:
                registro.append(f"▶ {ev.mensaje}")
                estado.code("\n".join(registro[-12:]))

        res = generar_serie(categoria, n, config_actual(), formatos_para(modo_s), idiomas_s, nombre_s,
                            forzar_exportacion=forzar_s, progreso=prog)
        barra.progress(1.0, "¡Serie completada!")
        ss.serie = res
    if ss.get("serie"):
        res = ss.serie
        st.success(f"Serie «{res.nombre}» en `{res.carpeta}` · {len(res.videos)} videos · {len(res.errores)} errores")
        st.dataframe(pd.DataFrame([{"#": v["numero"], "Formato": v["formato"], "Idioma": v["idioma"],
                                    "Título": v["titulo"], "Duración (s)": v["duracion"],
                                    "Calidad": "✓" if v["aprobado"] else "✗ " + ", ".join(v["fallos"])}
                                   for v in res.videos]), hide_index=True, width="stretch")
        for e in res.errores:
            st.error(f"#{e['numero']} {e['formato']} {e['idioma']}: {e['error']}")
        with st.expander("📁 Carpetas generadas"):
            st.code(arbol_carpetas(res.carpeta))

# ---------------------------------------------------------------------------
# 3) Voz
# ---------------------------------------------------------------------------
with tab_voz:
    st.markdown("Configura la voz, escucha una **vista previa** y guárdala como **perfil favorito**. "
                "Los perfiles guardados aparecen en la barra lateral para producir videos y series.")
    c1, c2 = st.columns(2)
    with c1:
        motor = st.selectbox("Motor TTS", list(MOTORES_TTS), format_func=MOTORES_TTS.get)
        idioma_v = st.selectbox("Idioma", list(IDIOMAS), format_func=IDIOMAS.get, key="idioma_voz")
        f1, f2, f3 = st.columns(3)
        genero = f1.selectbox("Género", ["todos", "femenino", "masculino"])
        edad = f2.selectbox("Edad", ["todas", "niño", "joven", "adulto"])
        acentos = sorted({v["acento"] for v in filtrar_voces(motor, idioma_v)})
        acento = f3.selectbox("Acento", ["todos"] + acentos)
        voces = filtrar_voces(motor, idioma_v, genero, edad, acento)
        if not voces:
            st.warning("No hay voces con esos filtros en el catálogo.")
            voces = filtrar_voces(motor, idioma_v)
        voz_sel = st.selectbox("Voz", range(len(voces)), format_func=lambda k: etiqueta_voz(voces[k]))
        voz_id = st.text_input("ID de voz (puedes pegar otra, p. ej. de ElevenLabs)", voces[voz_sel]["id"])
    with c2:
        velocidad = st.select_slider("Velocidad", list(NOMBRES_VELOCIDAD), value="lenta",
                                     format_func=NOMBRES_VELOCIDAD.get)
        ajuste = st.slider("Ajuste fino de velocidad (%)", -30, 30, 0)
        tono = st.slider("Tono / pitch (Hz)", -30, 40, 0)
        volumen = st.slider("Volumen del motor (%)", -50, 50, 0)
        ganancia = st.slider("Volumen relativo final (dB)", -10.0, 10.0, 0.0, 0.5)
        pausa = st.slider("Pausa entre frases (s)", 0.0, 2.0, 0.45, 0.05)
        emocion = st.selectbox("Estilo emocional", list(ESTILOS_EMOCION),
                               help="Azure aplica estilos reales (SSML); otros motores lo simulan con la prosodia")
    perfil = PerfilVoz(nombre="", motor=motor, idioma=idioma_v, voz=voz_id, velocidad=velocidad,
                       ajuste_velocidad=ajuste, tono_hz=tono, volumen_pct=volumen, ganancia_db=ganancia,
                       pausa_frases=pausa, estilo=emocion, tono_extra=voces[voz_sel].get("tono_extra", 0))
    texto_prev = st.text_area("Texto de prueba", "")
    cp1, cp2, cp3 = st.columns([1, 2, 1])
    if cp1.button("▶️ Vista previa", type="primary"):
        try:
            with st.spinner("Sintetizando…"):
                ss.preview = str(vista_previa(perfil, texto_prev or None))
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo generar la voz: {e}")
    if ss.get("preview"):
        cp2.audio(ss.preview)
    nombre_perfil = st.text_input("Nombre del perfil", f"Mi voz ({idioma_v.upper()})")
    if st.button("💾 Guardar perfil favorito"):
        guardar_perfil(perfil.variante(nombre=nombre_perfil))
        st.success(f"Perfil «{nombre_perfil}» guardado. Selecciónalo en la barra lateral.")
    with st.expander("⭐ Perfiles guardados"):
        for nombre_p, p in cargar_perfiles().items():
            a, b = st.columns([5, 1])
            a.write(f"**{nombre_p}** · {p.motor} · {p.voz} · {NOMBRES_VELOCIDAD.get(p.velocidad)} · {p.estilo}")
            if b.button("🗑️", key=f"del_{nombre_p}"):
                eliminar_perfil(nombre_p)
                st.rerun()

# ---------------------------------------------------------------------------
# 4) Música
# ---------------------------------------------------------------------------
with tab_musica:
    from musica_efectos import (EFECTOS_DISPONIBLES, buscar_freesound, descargar_freesound, generar_musica,
                                guardar_musica_subida, listar_musica, ruta_efecto)

    st.markdown("Solo se admite música **CC0, dominio público o con licencia comercial explícita**. "
                "Por defecto se compone música original (procedural, CC0) para cada video.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎼 Música procedural (CC0)")
        energia = st.selectbox("Energía", ["calma", "alegre", "energica"], index=1)
        semilla_m = st.number_input("Variación (semilla)", 0, 999, 3)
        if st.button("Componer y escuchar"):
            ss.musica_prev = str(generar_musica(40, energia, int(semilla_m)))
        if ss.get("musica_prev"):
            st.audio(ss.musica_prev)
        st.subheader("🔔 Efectos")
        for ef in EFECTOS_DISPONIBLES:
            st.caption(ef)
            st.audio(str(ruta_efecto(ef)))
    with c2:
        st.subheader("⬆️ Subir música propia")
        archivo = st.file_uploader("Archivo de audio", type=["mp3", "wav", "ogg", "m4a"])
        fuente = st.selectbox("Fuente", ["Pixabay Music (Pixabay Content License)", "YouTube Audio Library",
                                         "Freesound (CC0)", "Composición propia", "Otra con licencia comercial"])
        autor = st.text_input("Autor (opcional)")
        confirmo = st.checkbox("Confirmo que tengo derecho a usar esta música comercialmente en YouTube")
        if st.button("Guardar en la biblioteca", disabled=not (archivo and confirmo)):
            guardar_musica_subida(archivo.name, archivo.getvalue(), fuente, fuente, autor)
            st.success("Guardada")
        st.subheader("🔎 Freesound (solo CC0)")
        q = st.text_input("Buscar", "happy kids ukulele")
        if st.button("Buscar en Freesound"):
            try:
                ss.fs = buscar_freesound(q)
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
        for r in ss.get("fs", []):
            a, b = st.columns([4, 1])
            a.write(f"**{r['name']}** · {r.get('username')} · {r.get('duration', 0):.0f} s")
            a.audio(r["previews"]["preview-lq-mp3"])
            if b.button("⬇️", key=f"fs_{r['id']}"):
                descargar_freesound(r)
                st.success("Descargada a la biblioteca")
    st.subheader("📚 Biblioteca")
    pistas = listar_musica()
    opciones_m = [None] + [p.ruta for p in pistas]
    etiqueta_m = {None: "🎼 Procedural automática (CC0)"} | {p.ruta: f"{p.titulo} · {p.licencia}" for p in pistas}
    ss.musica_largo = st.selectbox("Música para videos largos", opciones_m, format_func=etiqueta_m.get)
    ss.musica_short = st.selectbox("Música para Shorts", opciones_m, format_func=etiqueta_m.get)
    for p in pistas:
        st.caption(f"{p.titulo} — {p.fuente} — {p.licencia}")
        st.audio(p.ruta)

# ---------------------------------------------------------------------------
# 5) Control de calidad
# ---------------------------------------------------------------------------
with tab_calidad:
    st.markdown("Informes de calidad de todos los videos producidos (carpeta de trabajo).")
    informes = sorted(DIR_TRABAJO.rglob("informe_calidad.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not informes:
        st.info("Todavía no hay videos producidos.")
    for ruta in informes[:60]:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        icono = "✅" if datos.get("aprobado") else "❌"
        with st.expander(f"{icono} {Path(datos['video']).name} · {datos['formato']}"):
            st.dataframe(pd.DataFrame([{"": ("✓" if v["ok"] else ("✗" if v["critico"] else "⚠")),
                                        "Verificación": v["nombre"], "Detalle": v["detalle"],
                                        "Corrección": "" if v["ok"] else v["correccion"]}
                                       for v in datos["verificaciones"]]), hide_index=True,
                         width="stretch")
            st.caption(str(ruta.parent))

# ---------------------------------------------------------------------------
# 6) Ayuda
# ---------------------------------------------------------------------------
with tab_ayuda:
    st.warning(AVISO_MADE_FOR_KIDS)
    st.markdown(f"""
**Flujo:** 1) guion → 2) imágenes → 3) producir → control de calidad → exportar.

**Salida:** `{DIR_SALIDA}` → `videos_largos/<idioma>/` y `shorts/<idioma>/`, cada video con
`.mp4`, miniatura `.jpg` (mismo nombre), descripción `.md`, `_timestamps.txt`, subtítulos `.srt`,
guion, informe de calidad y `creditos.json` con la licencia de cada recurso.

**Licencias:** ilustraciones y música procedurales = creación propia (CC0). Stock: Pixabay/Pexels/Unsplash
(uso comercial permitido), Wikimedia solo CC0/dominio público. IA: usa modelos con licencia comercial
(SDXL / SD 1.5 OpenRAIL, FLUX.1-schnell Apache-2.0).

Consulta el **README.md** para la instalación de Stable Diffusion, las voces avanzadas y el doblaje.
""")
