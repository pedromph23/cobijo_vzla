#!/bin/bash
set -e

# NOTA: Las migraciones se aplican manualmente desde local antes de pushear.
# Esto evita race conditions cuando gunicorn arranca múltiples workers.
# Para aplicar migraciones: `python manage.py migrate` en tu entorno local
# (que apunta a la misma base de datos en Supabase).

echo 'Collecting static files...'
python manage.py collectstatic --noinput

echo 'Starting gunicorn...'
exec gunicorn cobijo_vzla.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 100
