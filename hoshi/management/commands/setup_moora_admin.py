from django.core.management.base import BaseCommand

from hoshi.admin_setup import ensure_moora_theme


class Command(BaseCommand):
    help = 'Cấu hình theme Moora cho Django Admin (admin_interface)'

    def handle(self, *args, **options):
        ensure_moora_theme()
        self.stdout.write(self.style.SUCCESS('Đã áp dụng theme Moora cho Admin.'))
