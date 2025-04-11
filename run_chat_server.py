import os
import sys
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

def run_daphne():
    """Run the Daphne ASGI server"""
    print("Starting Daphne ASGI server...")
    
    # Thiết lập biến môi trường
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
    
    # Khởi tạo Django
    django.setup()
    
    # Import sau khi Django đã được khởi tạo
    from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
    from notifications.routing import websocket_urlpatterns as notification_websocket_urlpatterns
    
    # Thiết lập cổng mặc định
    port = os.environ.get('DAPHNE_PORT', '8002')
    host = '0.0.0.0'
    
    # Tạo ứng dụng ASGI
    application = ProtocolTypeRouter({
        'http': get_asgi_application(),
        'websocket': AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    chat_websocket_urlpatterns +
                    notification_websocket_urlpatterns
                )
            )
        ),
    })
    
    # Khởi động Daphne
    from daphne.server import Server
    from daphne.endpoints import build_endpoint_description_strings
    
    print(f"Running Daphne server on {host}:{port}")
    
    server = Server(
        application=application,
        endpoints=build_endpoint_description_strings(host=host, port=int(port)),
        signal_handlers=True,
    )
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nDaphne server stopped.")
    except Exception as e:
        print(f"Error running Daphne: {e}")
        
if __name__ == "__main__":
    run_daphne() 