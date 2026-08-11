FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libmagic-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/staticfiles /app/media /app/static /app/logs

COPY requirements.txt /app/

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Build-time .env (chỉ để collectstatic — runtime ghi đè bằng env thật)
RUN printf '%s\n' \
    'DEBUG=True' \
    'SECRET_KEY=django-insecure-key-for-build-only' \
    'ALLOWED_HOSTS=localhost,127.0.0.1' \
    'DATABASE_URL=' \
    'REDIS_URL=' \
    > /app/.env

COPY . /app/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=hoshi.settings

# collectstatic với DEBUG=True (không bắt buộc Postgres/Redis lúc build)
RUN DEBUG=True SECRET_KEY=django-insecure-key-for-build-only \
    DATABASE_URL= REDIS_URL= \
    python manage.py collectstatic --noinput

EXPOSE 8000

# ASGI + WebSocket (chat). Runtime cần DATABASE_URL + REDIS_URL + DEBUG=False
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "hoshi.asgi:application"]
