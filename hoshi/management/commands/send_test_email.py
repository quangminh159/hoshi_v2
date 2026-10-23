"""Gửi email thử: python manage.py send_test_email you@email.com"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Gửi 1 email test qua SMTP hiện tại (EMAIL_* trong .env)'

    def add_arguments(self, parser):
        parser.add_argument('to', type=str, help='Email nhận')

    def handle(self, *args, **options):
        to = options['to']
        if not to or '@' not in to:
            raise CommandError('Cần email hợp lệ')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER
        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'From: {from_email} → To: {to}')
        try:
            n = send_mail(
                subject='[Moora] Test email SMTP',
                message='Nếu nhận được mail này thì SMTP production đã OK.',
                from_email=from_email,
                recipient_list=[to],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f'Gửi thất bại: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f'Đã gửi ({n}). Kiểm tra hộp thư / spam.'))
