"""
WSGI config for Render.
"""

import os
import sys

print("===== Khởi động WSGI cho Render =====")

# Đảm bảo thư mục hiện tại trong Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cấu hình môi trường trước khi import bất kỳ module nào
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')

try:
    # Đảm bảo các package cần thiết được cài đặt
    packages_to_check = [
        ('python-decouple', 'python-decouple==3.8'),
        ('dj-database-url', 'dj-database-url==2.1.0'),
        ('whitenoise', 'whitenoise==6.6.0'),
        ('crispy-bootstrap5', 'crispy-bootstrap5==2025.4'),
        ('django-crispy-forms', 'django-crispy-forms==2.1'),
        ('django-two-factor-auth', 'django-two-factor-auth==1.16.0'),
        ('pyotp', 'pyotp==2.9.0')
    ]
    
    for package_name, package_install in packages_to_check:
        try:
            __import__(package_name.replace('-', '_'))
            print(f"✓ {package_name} đã được cài đặt")
        except ImportError:
            print(f"Đang cài đặt {package_name}...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_install])
            print(f"✓ Đã cài đặt {package_name}")
    
    # Hiển thị thông tin môi trường
    print(f"Django Settings Module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"Thư mục hiện tại: {os.getcwd()}")
    
    # Import WSGI application
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    print("✓ WSGI application đã được khởi tạo thành công")
    
except Exception as e:
    print(f"Lỗi khi tạo WSGI application: {e}")
    import traceback
    traceback.print_exc()
    raise

# Thêm biến app để tương thích với Render
app = application 