FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    .cache/
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Corregir CRLF por si acaso + dar permisos
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]