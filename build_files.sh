#!/bin/bash
# Build script cho Render

echo "===== Cài đặt các dependencies ====="
pip install -r requirements_render.txt

echo "===== Cấu hình dj-database-url ====="
pip install dj-database-url==2.1.0

echo "===== Thu thập static files ====="
python manage.py collectstatic --noinput

echo "===== Áp dụng các migrations ====="
python manage.py migrate

echo "===== Cài đặt hoàn tất =====" 