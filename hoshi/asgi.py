"""
ASGI config for hoshi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
import sys

print("Loading ASGI application from hoshi/asgi.py", file=sys.stderr)

# Thiết lập môi trường TRƯỚC KHI import bất kỳ thứ gì khác
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')

# Sau khi cài đặt môi trường, chúng ta mới import các module khác
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Khởi tạo ứng dụng Django
django_asgi_app = get_asgi_application()

# Chỉ import các module routing sau khi đã cấu hình Django
import chat.routing
import notifications.routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns +
                notifications.routing.websocket_urlpatterns
            )
        )
    ),
})
