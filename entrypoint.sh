#!/bin/bash
set -euo pipefail

# If arguments are passed (e.g., celery worker), run them instead of uvicorn
if [ $# -gt 0 ]; then
    echo "Starting: $*"
    exec "$@"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting uvicorn ASGI server..."
exec uvicorn ase_project.asgi:application --host 0.0.0.0 --port 8000 --no-proxy-headers
