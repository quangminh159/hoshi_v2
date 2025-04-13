"""
Tệp tương thích với Render.
"""

import os

# Cấu hình môi trường trước khi import bất kỳ thứ gì khác
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')

# Import sau khi cấu hình môi trường
from django.core.wsgi import get_wsgi_application

# Tạo ứng dụng WSGI
application = get_wsgi_application()
app = application  # Thêm alias app cho Render 