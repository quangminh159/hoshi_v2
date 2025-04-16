import os
import sys
import django

print("Loading config/asgi.py - forwarding to hoshi/asgi.py", file=sys.stderr)

# Thiết lập môi trường đúng
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

# Import application từ hoshi/asgi.py sau khi đã cấu hình Django
from hoshi.asgi import application 