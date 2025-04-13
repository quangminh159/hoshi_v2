#!/bin/bash

set -e

echo "=== Cài đặt pip ==="
python -m pip install --upgrade pip

echo "=== Cài đặt các thư viện Python ==="
# Cài từng thư viện một để phát hiện lỗi
while IFS= read -r line || [[ -n "$line" ]]; do
    # Bỏ qua dòng trống
    if [ -z "$line" ] || [[ "$line" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    echo "Cài đặt: $line"
    pip install "$line" || { echo "Lỗi khi cài $line"; exit 1; }
done < requirements.txt

echo "=== Tạo thư mục staticfiles ==="
mkdir -p staticfiles

echo "=== Thu thập static files ==="
python manage.py collectstatic --noinput

echo "=== Build hoàn tất! ===" 