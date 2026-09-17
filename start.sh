#!/bin/bash
set -e

echo "Ã°Å¸â€â€ž Running migrations..."
python manage.py migrate --noinput --fake-initial

echo "Ã°Å¸â€œÂ¦ Collecting static files..."
python manage.py collectstatic --noinput

echo "Ã°Å¸Å¡â‚¬ Starting gunicorn..."
exec gunicorn cobijo_vzla.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120