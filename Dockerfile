# Imagen del servicio de reposición (Reto 2).
#
# Lleva dentro el código y el Excel del caso: en el caso el dato es inmutable, así
# que hornearlo en la imagen hace el contenedor autosuficiente y el despliegue
# reproducible. En producción esto no se haría —el dato vendría del almacén
# analítico— y es la única diferencia real entre esta imagen y la que correría en
# la empresa.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Madrid

WORKDIR /app

# Las dependencias en una capa aparte: así un cambio en el código no obliga a
# reinstalarlas en cada despliegue.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY service/ ./service/
COPY docs/decisiones.md ./docs/decisiones.md
COPY data/raw/ ./data/raw/

# Cloud Run inyecta el puerto por entorno; 8080 es su valor por defecto.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn service.app:app --host 0.0.0.0 --port ${PORT} --workers 1
