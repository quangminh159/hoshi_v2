import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.asgi import get_asgi_application

# Chỉ sử dụng ứng dụng ASGI tiêu chuẩn của Django
application = get_asgi_application() 