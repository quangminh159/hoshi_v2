#!/bin/bash
# Build script cho Render

# Hiển thị thông tin cấu trúc thư mục
echo "===== Thông tin thư mục ====="
pwd
ls -la

echo "===== Cài đặt các thư viện cần thiết trước ====="
pip install python-decouple==3.8
pip install dj-database-url==2.1.0

echo "===== Cài đặt các dependencies ====="
pip install -r requirements_render.txt

echo "===== Tạo thư mục static nếu không tồn tại ====="
mkdir -p static staticfiles media

echo "===== Thu thập static files ====="
python manage.py collectstatic --noinput || echo "Lỗi khi thu thập static files, nhưng vẫn tiếp tục..."

echo "===== Kiểm tra xem có thể kết nối với database ====="
python -c "
import os
import sys
import dj_database_url
import psycopg2

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('Không tìm thấy DATABASE_URL, bỏ qua kiểm tra kết nối database')
    sys.exit(0)

try:
    conn_info = dj_database_url.parse(db_url)
    conn = psycopg2.connect(
        dbname=conn_info['NAME'],
        user=conn_info['USER'],
        password=conn_info['PASSWORD'],
        host=conn_info['HOST'],
        port=conn_info['PORT']
    )
    conn.close()
    print('Kết nối database thành công')
except Exception as e:
    print(f'Lỗi khi kết nối database: {e}')
    print('Tiếp tục quá trình...')
"

echo "===== Áp dụng các migrations ====="
python manage.py migrate --noinput || echo "Lỗi khi migrate, nhưng vẫn tiếp tục..."

echo "===== Tạo liên kết symbolic từ module hoshi nếu cần ====="
if [ ! -d "hoshi" ]; then
    for dir in */; do
        if [ -f "${dir}settings.py" ]; then
            ln -sf "$dir" hoshi
            echo "Đã tạo liên kết symbolic đến $dir"
            break
        fi
    done
fi

echo "===== Cài đặt hoàn tất =====" 