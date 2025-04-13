#!/bin/bash
# Build script cho Render

# Hiển thị thông tin cấu trúc thư mục
echo "===== Thông tin thư mục ====="
pwd
ls -la

echo "===== Cài đặt pip và setuptools mới nhất ====="
pip install --upgrade pip setuptools wheel

echo "===== Cài đặt các thư viện cần thiết trước ====="
pip install python-decouple==3.8
pip install dj-database-url==2.1.0
pip install python-dotenv==1.0.1
pip install django-two-factor-auth==1.16.0
pip install pyotp==2.9.0

# Cài đặt các thư viện crispy forms
echo "===== Cài đặt thư viện crispy forms ====="
pip install django-crispy-forms==2.1
pip install crispy-bootstrap5==2025.4

echo "===== Cài đặt các dependencies ====="
pip install -r requirements_render.txt

echo "===== Hiển thị thông tin về các packages đã cài đặt ====="
pip list | grep -i crispy
pip list | grep -i bootstrap
pip list | grep -i django
pip list | grep -i all
pip list | grep -i two-factor
pip list | grep -i pyotp

echo "===== Tạo thư mục static nếu không tồn tại ====="
mkdir -p static staticfiles media

echo "===== Kiểm tra cấu trúc và nội dung các tệp quan trọng ====="
echo "Kiểm tra settings_render.py:"
head -n 20 hoshi/settings_render.py

echo "Kiểm tra app.py:"
head -n 20 app.py

echo "===== Thu thập static files ====="
python manage.py collectstatic --noinput || echo "Lỗi khi thu thập static files, nhưng vẫn tiếp tục..."

echo "===== Kiểm tra xem có thể kết nối với database ====="
python -c "
import os
import sys
import dj_database_url

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('Không tìm thấy DATABASE_URL, bỏ qua kiểm tra kết nối database')
    sys.exit(0)

try:
    import psycopg2
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
except ImportError:
    print('Không thể import psycopg2, cài đặt...')
    pip install psycopg2-binary==2.9.9
    print('Đã cài đặt psycopg2-binary')
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

echo "===== Kiểm tra môi trường Python ====="
python --version
pip --version
which python

echo "===== Cài đặt hoàn tất ====="
echo "Quá trình build đã hoàn tất, ứng dụng sẵn sàng để chạy"

# Cài đặt các thư viện Python cần thiết
echo "Đang cài đặt các thư viện Python..."
pip install -r requirements.txt

# Cài đặt thư viện rich
echo "Đang cài đặt thư viện rich..."
pip install rich

# Tạo bảng dữ liệu Django
echo "Đang tạo bảng dữ liệu..."
python manage.py migrate

# Thu thập các file tĩnh
echo "Đang thu thập file tĩnh..."
python manage.py collectstatic --no-input

echo "Quá trình cài đặt đã hoàn tất!" 