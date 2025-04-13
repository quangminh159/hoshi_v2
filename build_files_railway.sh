#!/bin/bash

# Cài đặt dependencies
echo "Cài đặt dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Thu thập static files
echo "Thu thập static files..."
python manage.py collectstatic --noinput

# Thực hiện migrations
echo "Thực hiện migrations..."
python manage.py migrate

echo "Build hoàn tất!" 