# Dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Dar permisos al script
RUN chmod +x start.sh

EXPOSE 8000

# Ejecutar el script de arranque
CMD ["./start.sh"]