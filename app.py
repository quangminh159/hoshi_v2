"""
Tệp tương thích với Render.
"""

import os

# Cấu hình môi trường trước khi import
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')

# Đảm bảo các package cần thiết được cài đặt
try:
    import dj_database_url
except ImportError:
    import sys
    print("dj-database-url không được tìm thấy, đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dj-database-url==2.1.0"])
    import dj_database_url

try:
    from decouple import config
except ImportError:
    import sys
    print("python-decouple không được tìm thấy, đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-decouple==3.8"])
    from decouple import config

# Import sau khi cài đặt package
from django.core.wsgi import get_wsgi_application

# Tạo ứng dụng WSGI
application = get_wsgi_application()
app = application  # Thêm alias app cho Render 