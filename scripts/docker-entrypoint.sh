#!/bin/bash
set -e
mkdir -p /app/media /app/staticfiles /app/logs
# Migrate mỗi lần start (an toàn, idempotent)
python manage.py migrate --noinput
exec daphne -b 0.0.0.0 -p 8000 hoshi.asgi:application
