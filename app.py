"""EVR-KIDS · Punto de entrada web (WSGI) para Vercel y servidores serverless.

Vercel busca en `app.py` una variable global `app` (WSGI/ASGI). Esta versión web
es LIGERA (solo librería estándar): permite explorar los temas y generar guiones
con marcas de tiempo, títulos, descripciones y tags en español e inglés.

La producción de video (imágenes, voz, render con FFmpeg) necesita un servidor
con CPU y tiempo de ejecución largo; se hace con la interfaz Streamlit:
    streamlit run streamlit_app.py        (local, Docker, Render, Streamlit Cloud…)

Rutas:
    GET /                         página web con formulario
    GET /api/temas                lista de temas (JSON)
    GET /api/guion?tema=colores&idioma=es&formato=largo&variante=nombres   (JSON)
    GET /api/guion.md?...         guion en Markdown
    GET /api/salud                comprobación de estado

Ejecutar localmente sin dependencias:  python app.py   → http://localhost:8000
"""
from __future__ import annotations

import html
import json
from urllib.parse import parse_qs

from contenido_infantil import CATEGORIAS, NOMBRES_CATEGORIAS, TEMAS
from generador_descripciones import generar_metadatos
from generador_guion import VARIANTES, generar_guion

FORMATOS = ("largo", "short")
IDIOMAS = ("es", "en")
NOMBRES_VARIANTES = {"nombres": "Nombres y repetición", "adivina": "¡Adivina!", "canta": "Más canción"}


class ErrorPeticion(ValueError):
    pass


def _param(q: dict, nombre: str, defecto: str, validos) -> str:
    valor = (q.get(nombre) or [defecto])[0].strip()
    if valor not in validos:
        raise ErrorPeticion(f"Parámetro «{nombre}» no válido: {valor!r}. Opciones: {', '.join(validos)}")
    return valor


def construir_guion(q: dict) -> dict:
    """Genera el guion y sus metadatos (con tiempos estimados) a partir de la query string."""
    tema = _param(q, "tema", "animales_granja", TEMAS)
    idioma = _param(q, "idioma", "es", IDIOMAS)
    formato = _param(q, "formato", "largo", FORMATOS)
    variante = _param(q, "variante", "nombres", VARIANTES)
    g = generar_guion(tema, idioma, formato, variante)
    g.aplicar_duraciones([e.duracion_est for e in g.escenas])  # tiempos estimados
    meta = generar_metadatos(g, TEMAS[tema].categoria)
    return {"guion": g, "metadatos": meta}


def api_temas() -> list[dict]:
    return [{"clave": t.clave, "categoria": t.categoria, "titulo_es": t.titulo_es, "titulo_en": t.titulo_en,
             "elementos": [{"es": e.es, "en": e.en} for e in t.items]} for t in TEMAS.values()]


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
ESTILO = """
:root{--fondo:#fff8ec;--texto:#2b2340;--tarjeta:#ffffff;--acento:#ff595e;--azul:#1982c4;--suave:#6b6480;--borde:#f0e4cf}
@media (prefers-color-scheme:dark){:root{--fondo:#1d1a26;--texto:#f3eefc;--tarjeta:#282336;--suave:#b7afc9;--borde:#3a3350}}
*{box-sizing:border-box}body{margin:0;background:var(--fondo);color:var(--texto);
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:2.2rem;margin:.2em 0;color:var(--acento)}h2{margin-top:1.6em}
.sub{color:var(--azul);margin-top:0}.aviso{background:var(--tarjeta);border:2px solid var(--borde);
border-left:6px solid #ffca3a;border-radius:12px;padding:12px 16px;margin:16px 0}
form{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;align-items:end;
background:var(--tarjeta);border:2px solid var(--borde);border-radius:16px;padding:16px}
label{font-size:.85rem;color:var(--suave);display:flex;flex-direction:column;gap:4px}
select,button{font:inherit;padding:8px 10px;border-radius:10px;border:2px solid var(--borde);
background:var(--fondo);color:var(--texto)}button{background:var(--acento);color:#fff;border:0;font-weight:700;cursor:pointer}
.tabla{overflow-x:auto}table{border-collapse:collapse;width:100%;background:var(--tarjeta);border-radius:12px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid var(--borde);text-align:left;vertical-align:top}
th{font-size:.8rem;color:var(--suave);text-transform:uppercase}td.t{font-variant-numeric:tabular-nums;white-space:nowrap}
.pal{font-weight:800;color:var(--azul)}pre{white-space:pre-wrap;background:var(--tarjeta);border:2px solid var(--borde);
border-radius:12px;padding:12px;font-size:.9rem}a{color:var(--azul)}code{font-size:.9em}
"""


def _opciones(valores, seleccionado, etiqueta=lambda v: v) -> str:
    return "".join(f'<option value="{html.escape(v)}"{" selected" if v == seleccionado else ""}>'
                   f"{html.escape(etiqueta(v))}</option>" for v in valores)


def pagina(q: dict) -> str:
    error = ""
    datos = None
    try:
        datos = construir_guion(q)
    except ErrorPeticion as e:
        error = str(e)
    sel = {k: (q.get(k) or [d])[0] for k, d in
           (("tema", "animales_granja"), ("idioma", "es"), ("formato", "largo"), ("variante", "nombres"))}
    grupos = "".join(
        f'<optgroup label="{html.escape(NOMBRES_CATEGORIAS.get(cat, cat))}">'
        + _opciones(claves, sel["tema"], lambda c: f"{TEMAS[c].titulo_es} · {TEMAS[c].titulo_en}") + "</optgroup>"
        for cat, claves in CATEGORIAS.items() if cat != "mixta")
    formulario = f"""
<form method="get" action="/">
  <label>Tema<select name="tema">{grupos}</select></label>
  <label>Idioma<select name="idioma">{_opciones(IDIOMAS, sel["idioma"], {"es": "Español", "en": "English"}.get)}</select></label>
  <label>Formato<select name="formato">{_opciones(FORMATOS, sel["formato"], {"largo": "Video largo (16:9)", "short": "Short (9:16)"}.get)}</select></label>
  <label>Variante<select name="variante">{_opciones(VARIANTES, sel["variante"], NOMBRES_VARIANTES.get)}</select></label>
  <button type="submit">Generar guion</button>
</form>"""
    cuerpo = f'<p class="aviso">⚠️ {html.escape(error)}</p>' if error else ""
    if datos:
        g, m = datos["guion"], datos["metadatos"]
        filas = "".join(
            f'<tr><td class="t">{int(e.inicio // 60):02d}:{int(e.inicio % 60):02d}</td><td>{html.escape(e.seccion)}</td>'
            f'<td>{html.escape(e.narracion)}</td><td class="pal">{html.escape(e.palabra)}</td></tr>' for e in g.escenas)
        consulta = "&".join(f"{k}={v}" for k, v in sel.items())
        ts = "\n".join(f"{a} {b}" for a, b in m.timestamps) or "(los Shorts no usan capítulos)"
        cuerpo += f"""
<h2>{html.escape(g.titulo)} · {"Video largo" if g.formato == "largo" else "Short"} · {g.idioma.upper()}</h2>
<p>{len(g.escenas)} escenas · duración estimada {g.duracion_real:.0f} s ·
<a href="/api/guion.md?{consulta}">Markdown</a> · <a href="/api/guion?{consulta}">JSON</a></p>
<div class="tabla"><table><thead><tr><th>Tiempo</th><th>Sección</th><th>Narración</th><th>Pantalla</th></tr></thead>
<tbody>{filas}</tbody></table></div>
<h2>Título para YouTube</h2><pre>{html.escape(m.titulo)}</pre>
<h2>Descripción</h2><pre>{html.escape(m.descripcion)}</pre>
<h2>Timestamps (estimados)</h2><pre>{html.escape(ts)}</pre>
<h2>Tags</h2><pre>{html.escape(", ".join(m.tags))}</pre>"""
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>EVR-KIDS</title>
<style>{ESTILO}</style></head><body><main>
<h1>🎈 EVR-KIDS</h1>
<p class="sub">Guiones educativos para niños de 2 a 5 años · YouTube Made for Kids · Español / English</p>
<p class="aviso">Esta versión web genera <b>guiones, títulos, descripciones, timestamps y tags</b>.
La producción de <b>videos, Shorts, miniaturas y series</b> se ejecuta con la aplicación completa:
<code>streamlit run streamlit_app.py</code> (local, Docker, Render o Streamlit Cloud). Ver README.</p>
{formulario}{cuerpo}
<p class="sub" style="margin-top:32px">API: <code>/api/temas</code> · <code>/api/guion?tema=colores&amp;idioma=en&amp;formato=short</code></p>
</main></body></html>"""


# ---------------------------------------------------------------------------
# WSGI
# ---------------------------------------------------------------------------
def _responder(start_response, estado: str, cuerpo: str, tipo: str):
    datos = cuerpo.encode("utf-8")
    start_response(estado, [("Content-Type", f"{tipo}; charset=utf-8"), ("Content-Length", str(len(datos))),
                            ("Cache-Control", "public, max-age=300")])
    return [datos]


def app(environ, start_response):
    """Aplicación WSGI (variable `app` que exige Vercel)."""
    ruta = environ.get("PATH_INFO", "/") or "/"
    q = parse_qs(environ.get("QUERY_STRING", ""))
    if environ.get("REQUEST_METHOD", "GET") not in ("GET", "HEAD"):
        return _responder(start_response, "405 Method Not Allowed", '{"error": "solo GET"}', "application/json")
    try:
        if ruta in ("/", "/index.html"):
            return _responder(start_response, "200 OK", pagina(q), "text/html")
        if ruta == "/api/salud":
            return _responder(start_response, "200 OK", '{"estado": "ok"}', "application/json")
        if ruta == "/api/temas":
            return _responder(start_response, "200 OK", json.dumps(api_temas(), ensure_ascii=False), "application/json")
        if ruta == "/api/guion":
            d = construir_guion(q)
            cuerpo = {"guion": d["guion"].to_dict(), "metadatos": d["metadatos"].to_dict()}
            return _responder(start_response, "200 OK", json.dumps(cuerpo, ensure_ascii=False), "application/json")
        if ruta == "/api/guion.md":
            d = construir_guion(q)
            return _responder(start_response, "200 OK", d["guion"].to_markdown() + "\n" + d["metadatos"].a_markdown(),
                              "text/markdown")
    except ErrorPeticion as e:
        return _responder(start_response, "400 Bad Request", json.dumps({"error": str(e)}, ensure_ascii=False),
                          "application/json")
    return _responder(start_response, "404 Not Found", '{"error": "ruta no encontrada"}', "application/json")


application = app  # alias WSGI estándar

if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    print("EVR-KIDS web en http://localhost:8000  (Ctrl+C para salir)")
    make_server("", 8000, app).serve_forever()
