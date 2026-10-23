from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Tạo MESSAGE_ENCRYPTION_KEY (Fernet) để dán vào .env — giữ bí mật, backup riêng.'

    def handle(self, *args, **options):
        key = Fernet.generate_key().decode('ascii')
        self.stdout.write(key)
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE(
            'Thêm vào .env:\nMESSAGE_ENCRYPTION_ENABLED=True\nMESSAGE_ENCRYPTION_KEY=' + key
        ))
        self.stdout.write(self.style.WARNING(
            'Đổi key sau khi đã mã hóa tin → không đọc lại được. Backup key an toàn.'
        ))
