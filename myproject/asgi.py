import os
import django

# Thiết lập biến môi trường
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Khởi tạo Django
django.setup()

# Bây giờ mới import các module phụ thuộc vào Django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

# Cấu hình ASGI application
application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
}) 