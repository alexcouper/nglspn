#!/bin/sh
set -e

echo "Running migrations..."
uv run python manage.py migrate --noinput

exec "$@"
