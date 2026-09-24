# EVR-KIDS · aplicación completa (Streamlit + render de video)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# Fuentes: DejaVu (texto) y Noto Color Emoji (ilustraciones offline)
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core fonts-noto-color-emoji ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

ENV PORT=8501
EXPOSE 8501
CMD streamlit run streamlit_app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
