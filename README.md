# 🎈 EVR-KIDS — Generador automático de videos educativos infantiles para YouTube

Aplicación en Python con interfaz **Streamlit** que genera de forma automática videos educativos
para niños de **2 a 5 años** (vocabulario, primeras palabras, números, colores, animales, formas,
emociones…), listos para subir a YouTube como contenido **Made for Kids**:

- 🎞️ **Videos largos** 16:9 (1080p/720p, 30 fps, 2–5 min): intro animada → lección con repetición → repaso → canción → outro.
- 📱 **YouTube Shorts** 9:16 (1080×1920, 30 fps, 15–60 s): gancho en 3 s → contenido rápido → llamado a la acción.
- 🗣️ Voz TTS avanzada (edge-tts gratis, ElevenLabs, Azure, Polly, gTTS) con perfiles, vista previa y **doblaje ES ⇄ EN**.
- 🖼️ Imágenes con **Stable Diffusion** (local o nube), **stock libre** (Pixabay, Pexels, Unsplash, Wikimedia CC0) o **ilustraciones procedurales offline**.
- 🎵 Música y efectos **100 % libres**: composición procedural propia (CC0), Freesound CC0 o tu propia música con licencia.
- 🖼️ Miniaturas 1280×720, 📄 títulos + descripciones (200–400 palabras) + timestamps + tags + hashtags.
- 📚 **Series** completas (5, 10, 15… videos) con progreso en tiempo real.
- ✅ **Control de calidad** automático con informe ✓/✗, corrección automática o exportación forzada.

> Todo funciona **sin claves ni GPU** (modo offline: ilustraciones procedurales + música procedural + edge-tts).
> Las APIs de pago o la IA local solo mejoran el resultado.

---

## Índice

1. [Arquitectura](#1-arquitectura)
2. [Instalación paso a paso](#2-instalación-paso-a-paso)
3. [Configuración (.env)](#3-configuración-env)
4. [Uso de la interfaz (Streamlit)](#4-uso-de-la-interfaz-streamlit)
5. [Uso por línea de comandos](#5-uso-por-línea-de-comandos)
6. [Imágenes: IA (Stable Diffusion) y stock libre](#6-imágenes-ia-stable-diffusion-y-stock-libre)
7. [Voz avanzada (TTS)](#7-voz-avanzada-tts)
8. [Doblaje automático (español ⇄ inglés)](#8-doblaje-automático-español--inglés)
9. [Música y efectos de sonido](#9-música-y-efectos-de-sonido)
10. [YouTube Shorts](#10-youtube-shorts)
11. [Series de videos](#11-series-de-videos)
12. [Descripciones, timestamps y miniaturas](#12-descripciones-timestamps-y-miniaturas)
13. [Control de calidad](#13-control-de-calidad)
14. [Exportación y estructura de carpetas](#14-exportación-y-estructura-de-carpetas)
15. [EJEMPLO COMPLETO: serie de 5 videos + Shorts + inglés](#15-ejemplo-completo-serie-de-5-videos--shorts--inglés)
16. [Made for Kids, licencias y políticas de YouTube](#16-made-for-kids-licencias-y-políticas-de-youtube)
17. [Rendimiento y solución de problemas](#17-rendimiento-y-solución-de-problemas)
18. [Pruebas](#18-pruebas)
19. [Despliegue (Vercel, Docker, Render, Streamlit Cloud)](#19-despliegue-vercel-docker-render-streamlit-cloud)

---

## 1. Arquitectura

### Flujo de producción de un video

```
             ┌──────────────────────┐
  Tema ────▶ │ generador_guion.py   │  guion con escenas + marcas de tiempo (ES y EN, misma estructura)
             └─────────┬────────────┘
                       ▼
             ┌──────────────────────┐
             │ generador_imagenes.py│  IA / stock / procedural + metadatos de licencia (PNG + .json)
             └─────────┬────────────┘
                       ▼
             ┌──────────────────────┐
             │ tts_avanzado.py      │  un WAV por escena → duraciones REALES del guion
             └─────────┬────────────┘
                       ▼
             ┌──────────────────────┐
             │ musica_efectos.py    │  música CC0 (calma / energética) + efectos
             └─────────┬────────────┘
                       ▼
             ┌──────────────────────┐
             │ compositor_video.py  │  MoviePy + FFmpeg: zoom/paneo/rebote, subtítulos, mezcla, .srt
             └─────────┬────────────┘
                       ▼
   ┌───────────────────┼─────────────────────────┐
   ▼                   ▼                         ▼
generador_miniaturas  generador_descripciones   control_calidad.py
 (1280x720 .jpg)      (título, descripción,     (✓/✗: duración, audio, subtítulos,
                       timestamps, tags)          imágenes, miniatura, balance, formato)
                       ▼
             produccion.py → corregir() / exportar()  →  salida/<serie>/videos_largos|shorts/<idioma>/
```

`generador_series.py` repite este flujo para N temas × formatos × idiomas, y `generador_shorts.py`
configura la versión vertical.

### Módulos

| Archivo | Responsabilidad |
|---|---|
| `streamlit_app.py` | Interfaz Streamlit completa (crear video, series, laboratorio de voz, música, calidad, ayuda) |
| `app.py` | Versión web ligera (WSGI, solo librería estándar) para Vercel: guiones, descripciones y API |
| `cli.py` | Línea de comandos (`temas`, `guion`, `video`, `serie`, `voces`, `preview`) |
| `ejemplo_serie.py` | Ejemplo completo: 5 videos largos + Shorts + miniaturas + descripciones + inglés |
| `config.py` | Rutas, resoluciones, límites de duración, `.env`, aviso Made for Kids |
| `contenido_infantil.py` | Base bilingüe de 19 temas (palabra ES/EN, artículo, frase de refuerzo, prompt de imagen, emoji) |
| `generador_guion.py` | Guiones pedagógicos (largo / Short), variantes, timestamps, traducción, temas con Claude |
| `generador_imagenes.py` | Motores de imagen (diffusers, A1111, ComfyUI, Stability, Replicate, HF, Pixabay, Pexels, Unsplash, Wikimedia, procedural) |
| `tts_avanzado.py` | Motores TTS, catálogo de voces, prosodia, estilos, perfiles, vista previa |
| `musica_efectos.py` | Compositor procedural CC0, efectos, biblioteca, Freesound CC0, subida de música |
| `compositor_video.py` | Render de video, animaciones, subtítulos, mezcla de audio y `.srt` |
| `generador_miniaturas.py` | Miniaturas 1280×720 (JPG < 2 MB) |
| `generador_descripciones.py` | Título SEO, descripción 200–400 palabras, capítulos, tags, hashtags |
| `control_calidad.py` | Revisión automática antes de exportar |
| `produccion.py` | Pipeline de un video, corrección automática y exportación organizada |
| `generador_shorts.py` | Modos (solo largo / solo Short / ambos), CTA, Short desde un video largo |
| `generador_series.py` | Planificación y generación de series con progreso en tiempo real |
| `utilidades.py` | Fuentes, texto con borde, audio con FFmpeg, degradados, validación de imágenes |
| `tests/test_basico.py` | Pruebas offline |

### Diseño pedagógico de los guiones

- **Repetición espaciada**: cada palabra se presenta, se repite ("Repite conmigo…"), se refuerza con
  una frase y se celebra; luego vuelve en el repaso, en la ronda "¡Adivina!" y en la canción.
- **Pausas activas** (1,8 s) para que el niño repita en voz alta.
- **Lenguaje positivo**, frases de 3–8 palabras, felicitaciones variadas.
- Variantes para series: `nombres` (clásica), `adivina` (imagen desenfocada → revelación), `canta` (más canción).

---

## 2. Instalación paso a paso

### Requisitos

- **Python 3.10 o superior** (probado con 3.11).
- Conexión a internet para edge-tts (voz gratuita) y las APIs opcionales.
- FFmpeg: **no hace falta instalarlo**, se usa el binario incluido en `imageio-ffmpeg`.
- Opcional: GPU NVIDIA (≥ 8 GB VRAM) para Stable Diffusion local.

### Pasos

```bash
# 1) Clonar el proyecto
git clone https://github.com/elisandrovr-cloud/evr-kids.git
cd evr-kids

# 2) Crear y activar un entorno virtual
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3) Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4) Configuración (opcional: todo funciona sin claves)
cp .env.example .env        # Windows: copy .env.example .env

# 5) Arrancar la interfaz
streamlit run streamlit_app.py
```

Se abrirá `http://localhost:8501`.

### Fuente tipográfica infantil (recomendado)

La app usa DejaVu Sans Bold / Arial si no encuentra otra. Para un look más infantil descarga una
fuente redondeada con licencia **OFL** (uso comercial libre) y copia el `.ttf` en `assets/fuentes/`:

- [Fredoka](https://fonts.google.com/specimen/Fredoka) (recomendada), [Baloo 2](https://fonts.google.com/specimen/Baloo+2) o [Nunito](https://fonts.google.com/specimen/Nunito).

Para las ilustraciones offline con emojis se usa **Noto Color Emoji** (Apache-2.0) si está en el
sistema (en Linux: `sudo apt install fonts-noto-color-emoji`), o cualquier `*moji*.ttf` en `assets/fuentes/`.
Sin ella, las ilustraciones usan personajes geométricos con carita.

---

## 3. Configuración (.env)

Copia `.env.example` a `.env` y rellena solo lo que vayas a usar:

| Variable | Para qué |
|---|---|
| `ANTHROPIC_API_KEY`, `EVR_MODELO_CLAUDE` | Temas libres: Claude crea el vocabulario bilingüe (opcional) |
| `PIXABAY_API_KEY`, `PEXELS_API_KEY`, `UNSPLASH_ACCESS_KEY` | Imágenes de stock |
| `EVR_DIFFUSERS_MODELO`, `EVR_DIFFUSERS_DISPOSITIVO` | Stable Diffusion local |
| `A1111_URL` / `COMFYUI_URL`, `COMFYUI_CHECKPOINT` | Automatic1111 / ComfyUI |
| `STABILITY_API_KEY`, `REPLICATE_API_TOKEN`, `HF_API_TOKEN` | IA en la nube |
| `ELEVENLABS_API_KEY`, `AZURE_SPEECH_KEY`/`REGION`, `AWS_*` | Voces premium |
| `FREESOUND_API_KEY` | Buscar sonidos CC0 |
| `EVR_RESOLUCION`, `EVR_PRESET_X264` | Calidad/velocidad de render |

La pestaña lateral **🔑 Servicios configurados** muestra qué claves detecta la app.

---

## 4. Uso de la interfaz (Streamlit)

### 🎬 Crear video

1. **Tema**: elige uno de los 19 temas predefinidos, escribe un **tema personalizado** (título +
   palabras separadas por comas; se traducen solas al inglés) o describe un **tema libre para Claude**.
2. **Formato**: *Video largo + Short*, *Solo video largo* o *Solo Short*.
3. **Idiomas**: español, inglés o ambos (doblaje).
4. **1️⃣ Generar guion** → se muestran los guiones con marcas de tiempo. Puedes **editar** la
   narración y el texto en pantalla (y la versión en inglés se retraduce automáticamente).
5. **2️⃣ Generar imágenes** → galería con la licencia de cada imagen y botón 🔄 para regenerar una.
6. **3️⃣ Producir video(s)** → barra de progreso, video, miniatura, **informe de calidad ✓/✗**,
   título/descripción/tags listos para copiar.
7. **📦 Exportar** (si aprueba), **🛠️ Corregir** (automático) o **⚠️ Forzar exportación**.

### Otras pestañas

- **📚 Series**: categoría, número de videos (3–20), formatos, idiomas → progreso en tiempo real y árbol de carpetas.
- **🗣️ Voz**: filtros por motor/idioma/género/edad/acento, velocidad, tono, volumen, pausas, estilo emocional, **vista previa** y **perfiles favoritos**.
- **🎵 Música**: compone y escucha música procedural, sube tu música (con declaración de licencia), busca en Freesound CC0 y elige la pista para videos largos y Shorts.
- **✅ Control de calidad**: todos los informes generados.
- **Barra lateral**: resolución, motor de imágenes, estilo, volumen de música, efectos, velocidad de render y voces activas por idioma.

---

## 5. Uso por línea de comandos

```bash
python cli.py temas                                         # lista temas y categorías
python cli.py guion animales_granja --idioma es             # guion con marcas de tiempo
python cli.py guion colores --idioma en --formato short

python cli.py video colores --formato ambos --idiomas es en # largo + Short, español e inglés
python cli.py video "Los juguetes" --palabras "pelota, muñeca, bloques, tambor"
python cli.py video "los planetas" --claude                 # vocabulario con Claude
python cli.py video formas --motor-imagen diffusers --estilo 3d_suave --voz-es "Niña (ES, simulada)"

python cli.py serie animales -n 10 --formatos largo short --idiomas es en
python cli.py voces --idioma en --edad niño                 # catálogo de voces
python cli.py preview --perfil "Kid voice (EN)"             # vista previa en WAV
```

Opciones comunes: `--resolucion 1080p|720p`, `--estilo`, `--motor-imagen`, `--volumen-musica 0.18`,
`--musica ruta.mp3`, `--musica-short ruta.mp3`, `--voz-es/--voz-en "<perfil>"`,
`--motor-voz edge|gtts|azure|elevenlabs|polly`, `--cta "texto"`, `--preset ultrafast`, `--forzar`.

---

## 6. Imágenes: IA (Stable Diffusion) y stock libre

### Optimización automática del prompt

Cada elemento tiene un sujeto en inglés (p. ej. *"a happy cute cow in a green meadow"*). La app lo
convierte en un prompt infantil y añade un prompt negativo de seguridad:

```
a happy cute cow in a green meadow, cute cartoon style, bold clean outlines, flat vibrant colors,
kawaii, children's picture book illustration for toddlers, bright vivid saturated colors, simple clean
composition, single centered subject, friendly and happy, big expressive eyes, soft light, plain pastel
background, high quality, safe for kids, no text
NEGATIVO: text, letters, watermark, logo, scary, violent, blood, weapon, nsfw, deformed, ...
```

Estilos: `cartoon`, `acuarela`, `3d_suave`, `flat`, `crayon`, `papel`.

Las imágenes **no llevan texto** (salvo la portada), así sirven para cualquier idioma. Se guardan
en `cache/imagenes/<motor>_<estilo>/` con la licencia dentro del PNG (chunks iTXt: `Licencia`,
`Fuente`, `Autor`, `URL`, `Prompt`, `UsoComercial`) y en un `.json` al lado. Si un motor falla,
se usa la ilustración procedural como respaldo y se anota el aviso.

### A) Stable Diffusion local con `diffusers` (recomendado si tienes GPU)

```bash
# 1) PyTorch con CUDA (elige tu versión en https://pytorch.org/get-started/locally/)
pip install torch --index-url https://download.pytorch.org/whl/cu121
# 2) Librerías de Hugging Face
pip install diffusers transformers accelerate safetensors
```

`.env`:
```
EVR_DIFFUSERS_MODELO=stabilityai/stable-diffusion-xl-base-1.0
EVR_DIFFUSERS_DISPOSITIVO=auto   # cuda | mps (Apple Silicon) | cpu
EVR_DIFFUSERS_PASOS=30
```

- SDXL necesita ~8–10 GB de VRAM (1024×1024). Con menos VRAM usa
  `stable-diffusion-v1-5/stable-diffusion-v1-5` (4 GB).
- La primera ejecución descarga el modelo (~7 GB) a la caché de Hugging Face.
- En CPU funciona pero es muy lento (minutos por imagen).

| Modelo | Licencia | ¿Monetizable? |
|---|---|---|
| `stabilityai/stable-diffusion-xl-base-1.0` | CreativeML Open RAIL++-M | ✅ |
| `stable-diffusion-v1-5/stable-diffusion-v1-5` | CreativeML OpenRAIL-M | ✅ |
| `black-forest-labs/FLUX.1-schnell` | Apache-2.0 | ✅ |
| FLUX.1-dev, SDXL-Turbo, SD3 | licencias no comerciales / con límites | ⚠️ revisa antes |

### B) Automatic1111

1. Instala [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui).
2. Arráncalo con la API: `./webui.sh --api` (Windows: añade `--api` a `COMMANDLINE_ARGS` en `webui-user.bat`).
3. Carga un checkpoint con licencia comercial (p. ej. `sd_xl_base_1.0.safetensors`).
4. `.env`: `A1111_URL=http://127.0.0.1:7860` → en la app elige **IA · Automatic1111**.

### C) ComfyUI

1. Instala [ComfyUI](https://github.com/comfyanonymous/ComfyUI) y copia el checkpoint en `models/checkpoints/`.
2. Arráncalo (`python main.py`, puerto 8188).
3. `.env`: `COMFYUI_URL=http://127.0.0.1:8188` y `COMFYUI_CHECKPOINT=sd_xl_base_1.0.safetensors`.
   La app envía un workflow txt2img estándar (KSampler dpmpp_2m karras).

### D) Nube

| Motor | Variables | Notas |
|---|---|---|
| Stability AI | `STABILITY_API_KEY` | Stable Image Core; las salidas son del cliente (uso comercial) |
| Replicate | `REPLICATE_API_TOKEN`, `REPLICATE_MODELO` | Por defecto `black-forest-labs/flux-schnell` (Apache-2.0) |
| Hugging Face | `HF_API_TOKEN`, `HF_MODELO` | Inference API (router) |

### E) Stock libre

| Fuente | Licencia | Notas |
|---|---|---|
| Pixabay | Pixabay Content License | busca **ilustraciones** con `safesearch` |
| Pexels | Pexels License | fotos |
| Unsplash | Unsplash License | la app notifica la descarga como exige su API |
| Wikimedia Commons | **solo CC0 / dominio público** | filtra por `LicenseShortName` |
| `stock_auto` | — | prueba Pixabay → Pexels → Unsplash → Wikimedia |

### F) Procedural (offline)

Dibujos generados con Pillow: formas con carita, círculos de color, números con objetos para contar,
caritas de emociones y emojis a color para el resto. Creación propia → **CC0**.

---

## 7. Voz avanzada (TTS)

| Motor | Coste | Controles | Notas |
|---|---|---|---|
| **edge-tts** (por defecto) | gratis | velocidad, tono, volumen | voces neuronales de Microsoft, incl. infantiles EN (`en-US-AnaNeural`, `en-GB-MaisieNeural`) |
| Azure TTS | pago | + **estilos emocionales reales** (SSML `mstts:express-as`) | `cheerful`, `excited`, `gentle`, `friendly`, `narration-relaxed` |
| ElevenLabs | pago | velocidad, estilo, estabilidad (+ tono vía FFmpeg) | pega el ID de cualquier voz de tu cuenta |
| Amazon Polly | pago | velocidad, volumen (+ tono vía FFmpeg) | voces infantiles EN: Ivy, Justin, Kevin |
| gTTS | gratis | acento por dominio, lento (+ velocidad/tono vía FFmpeg) | calidad básica |
| prueba | — | — | tonos sintéticos, solo para tests offline (**no publicar**) |

### Controles

- **Idioma, género, edad (niño / joven / adulto) y acento** (México, España, EE. UU., Colombia, Argentina, Reino Unido, Australia…).
  Las voces "niño/joven" en español se **simulan** subiendo el tono de una voz adulta (edge-tts no tiene voces infantiles en español).
- **Velocidad**: muy lenta (−30 %), lenta (−15 %), normal, rápida (Shorts) + **ajuste fino** ±30 %.
- **Tono** (pitch) −30 a +40 Hz · **Volumen** del motor ±50 % · **Volumen relativo final** ±10 dB.
- **Pausa entre frases** (0–2 s): cada frase se sintetiza aparte y se unen con silencio.
- **Estilo emocional**: neutral, alegre, entusiasta, calmado, amable, cuentacuentos
  (Azure lo aplica de verdad; en los demás se simula con la prosodia).
- **Vista previa** antes de producir y **perfiles favoritos** (`datos/perfiles_voz.json`).
- En las escenas de **canción** la voz pasa automáticamente a "entusiasta"; en **Shorts** va un 12 % más rápida.
- Caché por frase en `cache/tts/`: regenerar o doblar un video no vuelve a llamar al motor.

Perfiles incluidos: *Maestra alegre (ES)*, *Maestro amable (ES)*, *Niña (ES, simulada)*,
*Cuento calmado (ES)*, *Teacher cheerful (EN)*, *Kid voice (EN)*, *Calm storyteller (EN)*.

---

## 8. Doblaje automático (español ⇄ inglés)

- Los 19 temas incluyen **traducciones humanas** de cada palabra y frase, por lo que la versión
  en inglés tiene **exactamente las mismas escenas, imágenes, música y estructura**. Solo cambian
  la voz, los subtítulos, el título de la portada y los timestamps (se recalculan con la duración real).
- Temas personalizados: las palabras se traducen con `deep-translator` (Google).
- Guiones editados a mano: el botón *Aplicar ediciones* re-traduce la versión inglesa escena a escena.
- Selecciona la voz de cada idioma en la barra lateral (*Español* / *English*).
- CLI: `--idiomas es en`; series: `idiomas=["es", "en"]`.

---

## 9. Música y efectos de sonido

- **Por defecto**: música **compuesta por la app** (progresiones I–V–vi–IV, melodía pentatónica,
  bajo, pad y percusión). "Alegre" (112 bpm) para videos largos y "energética" (128 bpm) para Shorts.
  Es creación propia → **CC0**, sin riesgo de reclamaciones de Content ID.
- **Efectos**: pop, ding, whoosh y aplausos procedurales. Para reemplazarlos pon `pop.wav`,
  `ding.mp3`… en `assets/efectos/`.
- **Música propia**: pestaña 🎵 → *Subir música propia* (hay que declarar fuente y confirmar los derechos)
  o copia archivos a `assets/musica/` con un `.json` de licencia al lado. Fuentes válidas:
  Pixabay Music, YouTube Audio Library (pistas sin atribución obligatoria), Freesound **CC0**, composiciones propias.
- **Freesound**: búsqueda filtrada `license:"Creative Commons 0"` (requiere `FREESOUND_API_KEY`).
- **Volumen relativo**: el deslizador *Volumen de la música* (0.18 ≈ 15 dB bajo la voz). La música
  sube +6 dB en la canción y baja −2 dB durante la lección (ducking). La voz se normaliza a −18 dBFS.

---

## 10. YouTube Shorts

Cada Short se genera automáticamente con:

| Requisito | Implementación |
|---|---|
| 9:16, 1080×1920, 30 fps | render vertical dedicado |
| 15–60 s | 5 elementos + mini-repaso + CTA (≈ 20–35 s) |
| **Gancho < 3 s** | pregunta corta ("¿Sabes qué animal hace ¡muuu!?") sobre la imagen de la respuesta **desenfocada**, texto enorme y "ding" desde el segundo 0; la respuesta se revela al final |
| Texto grande | insignia con la palabra + subtítulos grandes, barra de progreso superior |
| Ritmo rápido | voz +12 %, pausas mínimas, efectos de rebote y pop |
| Música energética | procedural 128 bpm |
| CTA | "¡Sígueme para aprender más! ¡Dale like!" (configurable) |

Modos: **solo Short**, **solo video largo** o **ambos** (interfaz, `cli.py video --formato`,
`generar_serie(formatos=[...])`). `generador_shorts.short_desde_largo()` crea el Short de un
video largo ya producido reutilizando sus imágenes.

---

## 11. Series de videos

```python
from config import Ajustes
from generador_series import generar_serie
from produccion import ConfigProduccion

serie = generar_serie("animales", n=10, cfg=ConfigProduccion(ajustes=Ajustes()),
                      formatos=["largo", "short"], idiomas=["es", "en"],
                      progreso=lambda ev: print(f"{ev.fraccion_total:.0%} {ev.mensaje}"))
```

- Categorías: `animales` (6 temas), `colores`, `numeros` (2), `formas`, `emociones`, `hablar` (3),
  `comida` (2), `vehiculos`, `cuerpo`, `naturaleza`, `mixta` (los 19).
- Si N es mayor que los temas disponibles, se rotan **variantes** (nombres → adivina → canta), por
  lo que una serie de 10 o 15 videos de animales no repite contenido idéntico.
- Cada video: guion, imágenes, miniatura, descripción, timestamps, subtítulos, informe de calidad.
- Si un video falla la serie continúa; los errores quedan en `resumen_serie.md` y `serie.json`.
- Los videos que no pasan el control de calidad se intentan **corregir automáticamente**; si aun así
  fallan, no se exportan (salvo `forzar_exportacion=True`).

---

## 12. Descripciones, timestamps y miniaturas

Por cada video se genera `<nombre>.md` con:

- **Título** optimizado (≤ 100 caracteres, emoji de la categoría, `#shorts` en Shorts).
- **Descripción** de 200–400 palabras: introducción, lista de lo que se aprende, método, consejos para
  padres, capítulos, nota de seguridad y hashtags.
- **Timestamps** reales (tras la voz), cumpliendo las reglas de YouTube: empiezan en `00:00`, ≥ 3
  capítulos y ≥ 10 s cada uno (los cortos se fusionan).
- **Tags** (≤ 500 caracteres) y **hashtags**; configuración recomendada de YouTube Studio.
- También `<nombre>_timestamps.txt`, `<nombre>_descripcion.txt` y `<nombre>.srt`.

**Miniatura** `<nombre>.jpg` (mismo nombre que el video): 1280×720, < 2 MB, fondo de rayos, imagen
principal grande con borde blanco y sombra, título corto con contorno grueso, sello "¡APRENDE!"/"SHORT!",
imágenes secundarias y etiqueta de idioma.

---

## 13. Control de calidad

Antes de exportar se genera `informe_calidad.md` / `.json`:

| Verificación | Criterio |
|---|---|
| Duración | largo 120–300 s · Short 15–60 s |
| Formato | 1920×1080 o 1280×720 (16:9) · 1080×1920 (9:16) · 30 fps |
| Fotogramas sin negro | 5 fotogramas muestreados con brillo y contraste |
| Pista de audio | presente y de la duración del video |
| Audio sin silencios largos | ningún silencio > 2,5 s en la mezcla |
| Narración continua | sin pausas de voz > 4,5 s (aviso) |
| Volumen general | −24 a −12 dBFS (aviso) |
| Balance voz/música | voz 8–30 dB por encima de la música |
| Subtítulos | un bloque `.srt` por escena + incrustados |
| Imágenes válidas | se abren, no negras ni planas |
| Miniatura | 1280×720 y < 2 MB |
| Gancho ≤ 3 s / CTA | solo Shorts (aviso) |
| Lenguaje apto | lista de palabras prohibidas para 2–5 años |

✓ = correcto · ✗ = bloquea la exportación · ⚠ = aviso. **Corregir** regenera imágenes, reajusta el
volumen de la música, re-renderiza y rehace la miniatura; **Forzar exportación** exporta igualmente y
deja `ATENCION_EXPORTACION_FORZADA.txt` en la carpeta.

---

## 14. Exportación y estructura de carpetas

```
salida/
└── serie-animales-para-ninos/
    ├── LEEME_MADE_FOR_KIDS.txt
    ├── resumen_serie.md          ← tabla de todos los videos y su calidad
    ├── serie.json / plan_serie.json
    ├── videos_largos/
    │   ├── es/
    │   │   └── 01_los-animales-de-la-granja_es/
    │   │       ├── 01_los-animales-de-la-granja_es.mp4
    │   │       ├── 01_los-animales-de-la-granja_es.jpg        ← miniatura (mismo nombre)
    │   │       ├── 01_los-animales-de-la-granja_es.md         ← título + descripción + timestamps + tags
    │   │       ├── 01_los-animales-de-la-granja_es.srt
    │   │       ├── 01_los-animales-de-la-granja_es_timestamps.txt
    │   │       ├── 01_los-animales-de-la-granja_es_descripcion.txt
    │   │       ├── guion.md
    │   │       ├── informe_calidad.md
    │   │       └── creditos.json                              ← licencia de cada imagen, música y voz
    │   └── en/ 01_farm-animals_en/ …
    └── shorts/
        ├── es/ 01_los-animales-de-la-granja_short_es/ …
        └── en/ 01_farm-animals_short_en/ …
```

Archivos intermedios (voces por escena, mezcla WAV, etc.) quedan en `trabajo/`; las cachés de
imágenes, voces y música en `cache/` (puedes borrarlas cuando quieras).

---

## 15. EJEMPLO COMPLETO: serie de 5 videos + Shorts + inglés

`ejemplo_serie.py` genera **20 archivos de video**: 5 videos largos de animales (granja, selva, mar,
mascotas, insectos) + sus 5 Shorts, en español **y** doblados al inglés, con miniaturas,
descripciones con timestamps, subtítulos e informes de calidad.

```bash
python ejemplo_serie.py                      # calidad final: 1080p, edge-tts
python ejemplo_serie.py --rapido             # 720p y preset ultrafast (prueba)
python ejemplo_serie.py --motor-imagen diffusers --estilo acuarela   # con Stable Diffusion
python ejemplo_serie.py --rapido --offline   # sin internet (voz de prueba, NO publicar)
```

El código esencial:

```python
from config import Ajustes
from generador_series import generar_serie
from produccion import ConfigProduccion
from tts_avanzado import PerfilVoz

cfg = ConfigProduccion(
    ajustes=Ajustes(resolucion="1080p", motor_imagen="procedural", estilo_imagen="cartoon",
                    volumen_musica=0.18),
    perfiles_voz={
        "es": PerfilVoz("Maestra alegre (ES)", "edge", "es", "es-MX-DaliaNeural", velocidad="lenta",
                        tono_hz=2, pausa_frases=0.5, estilo="alegre"),
        "en": PerfilVoz("Kid voice (EN)", "edge", "en", "en-US-AnaNeural", velocidad="lenta",
                        pausa_frases=0.5, estilo="alegre"),
    },
)
serie = generar_serie("animales", n=5, cfg=cfg, formatos=["largo", "short"], idiomas=["es", "en"],
                      nombre="Serie Animales para Niños")
print(serie.a_markdown())
```

Resultado (extracto de `resumen_serie.md`):

```
| # | Formato | Idioma | Título                                               | Duración | Calidad |
|---|---------|--------|------------------------------------------------------|----------|---------|
| 01| largo   | es     | Los animales de la granja 🐮 | Aprende a Hablar | ...  | 194 s    | ✓       |
| 01| largo   | en     | Farm animals 🐮 | Learn to Talk | Preschool ...        | 205 s    | ✓       |
| 01| short   | es     | Los animales de la granja en 30 segundos 🐮 #shorts  | 26 s     | ✓       |
| 01| short   | en     | Farm animals in 30 seconds 🐮 #shorts                | 27 s     | ✓       |
| 02| largo   | es     | Los animales de la selva 🐮 | ...                     | ...      | ✓       |
...
```

Extracto de una descripción generada (`01_los-animales-de-la-granja_es.md`):

```
⏱️ Capítulos:
00:00 Introducción y Vaca
00:24 Cerdito
00:38 Gallina
00:52 Caballo
01:05 Oveja
01:19 Pato
01:34 Repaso
01:53 ¡Adivina!
02:43 Canción
03:09 Despedida
```

Tiempos orientativos (CPU de 4 núcleos): video largo de 3 min ≈ 2,5 min a 720p (≈ 5 min a 1080p);
Short ≈ 50 s. La serie completa de 20 videos ≈ 35–60 min.

---

## 16. Made for Kids, licencias y políticas de YouTube

Cada carpeta exportada incluye `LEEME_MADE_FOR_KIDS.txt` y cada `.md` recuerda:

- Al subir, marca **"Sí, es contenido creado para niños"** (obligatorio por COPPA). Consecuencias:
  sin comentarios, sin anuncios personalizados, sin tarjetas/pantallas finales interactivas, sin
  notificaciones de campana ni miniplayer.
- **Categoría**: Educación. Sube el `.srt` como subtítulos.
- Los [principios de calidad para contenido infantil](https://support.google.com/youtube/answer/10774223)
  de YouTube premian contenido educativo, positivo y que fomente el juego y el aprendizaje, y penalizan
  el contenido "de baja calidad" (muy comercial, engañoso o que incita a comportamientos negativos).
  Recomendación: usa CTA dirigidos a los adultos (la app incluye *"¡Pídele a un adulto que te ayude a
  ver más videos!"*) y evita la producción masiva repetitiva: varía temas, voces y estilos.
- YouTube exige **declarar contenido sintético realista** (casilla "contenido alterado o sintético").
  Las ilustraciones de dibujos animados no suelen requerirlo, pero revisa la política vigente.

### Licencias de los recursos

| Recurso | Fuente | Licencia |
|---|---|---|
| Ilustraciones procedurales, música y efectos | generados por la app | CC0 (creación propia) |
| Emojis en ilustraciones | Noto Color Emoji | Apache-2.0 / OFL |
| Imágenes IA | modelos listados en §6 | OpenRAIL / Apache-2.0 (uso comercial) |
| Stock | Pixabay / Pexels / Unsplash | licencias de uso comercial sin atribución obligatoria |
| Wikimedia | solo CC0 / dominio público | — |
| Voces | edge-tts, Azure, ElevenLabs, Polly, gTTS | revisa los términos de cada servicio para uso comercial (ElevenLabs y Azure/Polly de pago lo permiten; edge-tts usa un servicio gratuito de Microsoft sin garantía de SLA) |

`creditos.json` registra fuente, autor, URL y licencia de cada recurso de cada video.

---

## 17. Rendimiento y solución de problemas

| Problema | Solución |
|---|---|
| El render es lento | usa `720p` y preset `ultrafast`/`veryfast` para pruebas; 1080p + `medium` para publicar |
| `edge-tts no devolvió audio` / error SSL | revisa la conexión; tras un proxy corporativo define `SSL_CERT_FILE` con el certificado raíz |
| Caracteres cuadrados en el texto | añade una fuente `.ttf` completa en `assets/fuentes/` |
| Las ilustraciones offline no muestran emojis | instala Noto Color Emoji o copia `NotoColorEmoji.ttf` a `assets/fuentes/` |
| `CUDA out of memory` con SDXL | usa SD 1.5 o `EVR_DIFFUSERS_DISPOSITIVO=cpu` |
| Balance voz/música ✗ | baja el deslizador de música o pulsa **🛠️ Corregir** |
| Duración ✗ en video largo | usa la variante *canta* o velocidad *muy lenta* (más largo), o menos elementos |
| Quiero regenerar todo | borra `cache/` (imágenes, voces, música) y `trabajo/` |
| pydub en Python 3.13 | `pip install audioop-lts` (ya incluido en requirements) |

---

## 18. Pruebas

```bash
pip install pytest
pytest -q                          # 47 pruebas offline (~5 s)
EVR_TEST_RENDER=1 pytest -q        # + render completo de un Short con control de calidad
```

---

## 19. Despliegue (Vercel, Docker, Render, Streamlit Cloud)

La aplicación tiene **dos puntos de entrada**:

| Archivo | Qué es | Dónde se despliega |
|---|---|---|
| `streamlit_app.py` | App **completa**: videos, Shorts, miniaturas, series, voz, música, control de calidad | Local, Docker, Render, Railway, Streamlit Community Cloud, Hugging Face Spaces |
| `app.py` | Web **ligera** (WSGI, solo librería estándar): guiones con timestamps, títulos, descripciones, tags y API JSON | **Vercel** (o cualquier servidor WSGI) |

### ¿Por qué no se puede renderizar video en Vercel?

Vercel ejecuta **funciones serverless**: tienen un tiempo máximo de ejecución, no mantienen el
servidor WebSocket que necesita Streamlit y limitan el tamaño del paquete (las dependencias de
video — Streamlit, MoviePy, FFmpeg, pandas… — ocupan ~470 MB). Por eso en Vercel se publica solo
la web ligera, y la producción de videos se hace en un servidor con CPU (Docker/Render) o en local.

> Si Vercel mostraba `Error: Found app.py but it does not export a top-level "app", "application",
> or "handler" variable`, era porque `app.py` contenía la interfaz Streamlit. Ahora la interfaz está en
> `streamlit_app.py` y `app.py` exporta la variable WSGI `app` que Vercel espera.

### Vercel (web ligera)

1. Importa el repositorio en Vercel (*Add New → Project*). **Framework Preset: Other**.
   No hace falta *Build Command* ni variables de entorno.
2. `vercel.json` enruta todas las rutas a `app.py` con el runtime `@vercel/python`.
3. `.vercelignore` excluye `requirements.txt` y los módulos de video, así Vercel no instala nada
   (el paquete pesa ~300 KB).
4. Rutas: `/` (formulario), `/api/temas`, `/api/guion?tema=colores&idioma=en&formato=short`,
   `/api/guion.md?...`, `/api/salud`.

Prueba local de la web ligera, sin instalar nada: `python app.py` → <http://localhost:8000>.

### Docker (app completa)

```bash
docker build -t evr-kids .
docker run -p 8501:8501 --env-file .env -v "$PWD/salida:/app/salida" evr-kids
# abre http://localhost:8501
```

### Render.com (app completa)

`render.yaml` ya está listo: *New → Blueprint* → selecciona el repositorio. Usa un plan con al
menos 2 GB de RAM (el render de video consume CPU y memoria). Las claves van en *Environment*.

### Streamlit Community Cloud (app completa)

*New app* → repositorio → **Main file path: `streamlit_app.py`**. `requirements.txt` y
`packages.txt` (fuentes) se instalan solos; las claves van en *Settings → Secrets* con el mismo
nombre que en `.env`. Ten en cuenta que los recursos gratuitos son limitados: usa 720p para renderizar.
