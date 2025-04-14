FROM python:3.11-slim

WORKDIR /app

# Cài đặt các thư viện phụ thuộc hệ thống
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libmagic-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục static và media
RUN mkdir -p /app/staticfiles /app/media /app/static /app/logs

# Sao chép requirements.txt trước để tận dụng cache
COPY requirements.txt /app/

# Cài đặt các thư viện Python
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Tạo tệp .env rỗng mặc định để tránh lỗi khi collectstatic
RUN echo "DEBUG=False" > /app/.env && \
    echo "SECRET_KEY=django-insecure-key-for-build-only" >> /app/.env && \
    echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> /app/.env

# Sao chép toàn bộ code
COPY . /app/

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False
ENV SECRET_KEY=django-insecure-key-for-build-only
ENV DATABASE_URL=""

# Thu thập static files
RUN python manage.py collectstatic --noinput

# Cổng mặc định
EXPOSE 8000

# Lệnh chạy
CMD ["gunicorn", "wsgi_railway:application", "--bind", "0.0.0.0:8000"]