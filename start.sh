#!/bin/bash
set -e

echo 'Running migrations...'
python manage.py migrate --noinput

echo 'Collecting static files...'
python manage.py collectstatic --noinput

echo 'Precalculating heatmap cache...'
python manage.py precalcular_heatmap || echo 'Heatmap preload skipped (OK)'

echo 'Starting gunicorn...'
exec gunicorn cobijo_vzla.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120