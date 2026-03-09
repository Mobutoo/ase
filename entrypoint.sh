#!/bin/bash
set -euo pipefail

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

# If arguments are passed (e.g., celery worker), run them instead of daphne
if [ $# -gt 0 ]; then
    echo "Starting: $*"
    exec "$@"
fi

echo "Starting daphne ASGI server..."
exec daphne -b 0.0.0.0 -p 8000 ase_project.asgi:application
