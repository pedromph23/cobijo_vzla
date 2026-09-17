# Dockerfile
FROM python:3.12-slim

# Instala las dependencias del sistema, incluyendo GDAL y GEOS
RUN apt-get update && apt-get install -y \
    binutils \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los requirements e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto
COPY . .

# Recolecta los archivos estáticos
RUN python manage.py collectstatic --noinput

# Comando para iniciar la aplicación usando gunicorn
CMD ["gunicorn", "cobijo_vzla.wsgi:application", "--bind", "0.0.0.0:8000"]