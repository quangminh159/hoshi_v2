FROM python:3.11-slim

WORKDIR /app

# Cài đặt các thư viện phụ thuộc hệ thống
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libmagic-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Sao chép requirements.txt trước để tận dụng cache
COPY requirements.txt /app/

# Cài đặt các thư viện Python
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Sao chép toàn bộ code
COPY . /app/

# Thu thập static files
RUN python manage.py collectstatic --noinput

# Cổng mặc định
EXPOSE 8000

# Lệnh chạy
CMD ["gunicorn", "wsgi_railway:application", "--bind", "0.0.0.0:8000"] 