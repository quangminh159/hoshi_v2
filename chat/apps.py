from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Hệ thống nhắn tin'
    
    def ready(self):
        """Được gọi khi ứng dụng khởi động"""
        try:
            # Import signals để đăng ký các signal handlers
            import chat.signals
        except ImportError:
            pass