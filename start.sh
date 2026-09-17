#!/bin/bash
set -e

echo 'Running migrations...'
if ! python manage.py migrate --noinput --fake-initial; then
    echo 'fake-initial failed, falling back to --fake...'
    python manage.py migrate --noinput --fake
fi

echo 'Collecting static files...'
python manage.py collectstatic --noinput

echo 'Starting gunicorn...'
exec gunicorn cobijo_vzla.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
