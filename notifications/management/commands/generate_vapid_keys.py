"""Tạo VAPID keys cho Web Push."""

import base64

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Tạo WEBPUSH_VAPID_* để dán vào .env'

    def handle(self, *args, **options):
        try:
            from py_vapid import Vapid
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            self.stderr.write(self.style.ERROR('Cần: pip install pywebpush'))
            return

        v = Vapid()
        v.generate_keys()
        priv = v.private_pem()
        if isinstance(priv, bytes):
            priv = priv.decode('utf-8')
        raw_pub = v.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        pub_b64 = base64.urlsafe_b64encode(raw_pub).decode('ascii').rstrip('=')
        pem_one_line = priv.strip().replace('\n', '\\n')

        self.stdout.write(self.style.SUCCESS('Dán vào .env:'))
        self.stdout.write(f'WEBPUSH_VAPID_PUBLIC_KEY={pub_b64}')
        self.stdout.write(f'WEBPUSH_VAPID_PRIVATE_KEY={pem_one_line}')
        self.stdout.write('WEBPUSH_VAPID_ADMIN_EMAIL=mailto:admin@yourdomain.com')
        self.stdout.write(self.style.WARNING(
            'Backup private key. Mất key → phải subscribe lại trên mọi máy.'
        ))
