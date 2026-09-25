"""Lee las opciones de la serie (botón "Run workflow" o formulario de Issue) y las
escribe en GITHUB_OUTPUT para el resto del workflow. Solo usa la librería estándar."""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())
from contenido_infantil import CATEGORIAS, NOMBRES_CATEGORIAS  # noqa: E402
from utilidades import slug  # noqa: E402

ETIQUETAS = {  # encabezado del formulario de Issue -> clave
    "categoría": "categoria", "número de videos": "cantidad", "formatos": "formatos", "idiomas": "idiomas",
    "resolución": "resolucion", "nombre de la serie (opcional)": "nombre",
}
VALIDOS = {
    "categoria": set(CATEGORIAS), "formatos": {"largo short", "largo", "short"},
    "idiomas": {"es en", "es", "en"}, "resolucion": {"1080p", "720p"},
}


def leer_issue(cuerpo: str) -> dict:
    """Extrae los valores de un Issue creado con el formulario (secciones '### Etiqueta')."""
    datos = {}
    for bloque in re.split(r"^###\s+", cuerpo or "", flags=re.MULTILINE)[1:]:
        titulo, _, valor = bloque.partition("\n")
        clave = ETIQUETAS.get(titulo.strip().lower())
        valor = valor.strip()
        if clave and valor and valor != "_No response_":
            datos[clave] = valor
    return datos


def plan(entorno: dict) -> dict:
    datos = {"categoria": "animales", "cantidad": "5", "formatos": "largo short", "idiomas": "es en",
             "resolucion": "1080p", "nombre": "", "forzar": "false"}
    if entorno.get("GITHUB_EVENT_NAME") == "issues":
        datos.update(leer_issue(entorno.get("ISSUE_BODY", "")))
    else:
        for k in datos:
            v = entorno.get(f"IN_{k.upper()}", "")
            if v:
                datos[k] = v
    for k, validos in VALIDOS.items():
        if datos[k] not in validos:
            raise SystemExit(f"Valor no válido para {k}: {datos[k]!r}. Opciones: {sorted(validos)}")
    n = int(datos["cantidad"])
    if not 1 <= n <= 20:
        raise SystemExit("El número de videos debe estar entre 1 y 20")
    cat = datos["categoria"]
    datos["nombre"] = datos["nombre"].strip() or f"Serie {NOMBRES_CATEGORIAS.get(cat, cat)} ({n} videos)"
    datos["carpeta"] = slug(datos["nombre"])
    datos["numeros"] = json.dumps(list(range(1, n + 1)))
    datos["forzar"] = "--forzar" if datos["forzar"] == "true" else ""
    return datos


if __name__ == "__main__":
    resultado = plan(dict(os.environ))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        for k, v in resultado.items():
            f.write(f"{k}={v}\n")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
