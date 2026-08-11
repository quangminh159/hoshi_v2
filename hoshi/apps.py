from django.apps import AppConfig


class HoshiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hoshi'
    verbose_name = 'Moora Core'

    def ready(self):
        from .admin_setup import configure_admin
        configure_admin()
