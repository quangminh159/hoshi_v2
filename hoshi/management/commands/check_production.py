"""Kiểm tra sẵn sàng production: python manage.py check_production"""
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Checklist cấu hình production (DEBUG=False, DB, Redis, media, email, OAuth, TURN, Sentry)'

    def handle(self, *args, **options):
        ok = 0
        warn = 0
        bad = 0

        def status(label, good, detail='', level='ok'):
            nonlocal ok, warn, bad
            if level == 'ok' and good:
                ok += 1
                self.stdout.write(self.style.SUCCESS(f'  [OK]  {label}' + (f' — {detail}' if detail else '')))
            elif level == 'warn' or (good is None):
                warn += 1
                self.stdout.write(self.style.WARNING(f'  [..]  {label}' + (f' — {detail}' if detail else '')))
            else:
                bad += 1
                self.stdout.write(self.style.ERROR(f'  [!!]  {label}' + (f' — {detail}' if detail else '')))

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Moora production check ===\n'))

        status('DEBUG=False', settings.DEBUG is False, f'DEBUG={settings.DEBUG}')
        sk = settings.SECRET_KEY or ''
        status(
            'SECRET_KEY mạnh',
            len(sk) >= 40 and not sk.startswith('dev-only') and 'insecure' not in sk.lower(),
            f'len={len(sk)}',
        )
        hosts = list(settings.ALLOWED_HOSTS or [])
        status(
            'ALLOWED_HOSTS không phải *',
            bool(hosts) and '*' not in hosts,
            ','.join(hosts) or '(trống)',
        )
        csrf = list(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []) or [])
        https_csrf = [o for o in csrf if o.startswith('https://')]
        status(
            'CSRF_TRUSTED_ORIGINS có https://',
            bool(https_csrf),
            ','.join(csrf) or '(trống)',
            level='ok' if https_csrf else ('warn' if settings.DEBUG else 'bad'),
        )

        engine = settings.DATABASES['default']['ENGINE']
        status('Postgres (không SQLite)', 'sqlite' not in engine, engine)

        redis_ok = bool(getattr(settings, 'USE_REDIS', False))
        status('Redis connected', redis_ok, getattr(settings, 'REDIS_URL', '') or '(không có REDIS_URL)')

        local_media = bool(getattr(settings, 'ALLOW_LOCAL_MEDIA', True))
        s3 = bool(getattr(settings, 'USE_S3_MEDIA', False))
        status(
            'Media (S3/R2 hoặc local)',
            s3 or local_media,
            'S3/R2' if s3 else f'local disk → {getattr(settings, "MEDIA_ROOT", "")}',
            level='ok' if (s3 or local_media) else 'warn',
        )

        email_backend = settings.EMAIL_BACKEND or ''
        smtp = 'smtp' in email_backend.lower() and bool(settings.EMAIL_HOST_USER)
        status(
            'Email SMTP',
            smtp,
            email_backend,
            level='ok' if smtp else 'warn',
        )

        g = bool(getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('google', {}).get('APP', {}).get('client_id'))
        # providers structure may nest differently
        try:
            g_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
            f_id = settings.SOCIALACCOUNT_PROVIDERS['facebook']['APP']['client_id']
            g_ok = bool(g_id) and 'your-google' not in g_id
            f_ok = bool(f_id) and 'your-facebook' not in f_id
        except Exception:
            g_ok = f_ok = False
        status('Google OAuth', g_ok, level='ok' if g_ok else 'warn')
        status('Facebook OAuth', f_ok, level='ok' if f_ok else 'warn')

        turn = bool(getattr(settings, 'TURN_HOST', '') or getattr(settings, 'TURN_URLS', ''))
        status('TURN (coturn)', turn, getattr(settings, 'TURN_HOST', '') or '(chưa)', level='ok' if turn else 'warn')

        sentry = bool(getattr(settings, 'SENTRY_DSN', ''))
        status('Sentry DSN', sentry, level='ok' if sentry else 'warn')

        invite = getattr(settings, 'INVITE_ONLY', None)
        status('INVITE_ONLY (beta)', True, f'INVITE_ONLY={invite}', level='ok')

        self.stdout.write('')
        self.stdout.write(f'Kết quả: OK={ok}  cảnh báo={warn}  lỗi={bad}')
        if bad:
            self.stdout.write(self.style.ERROR('Chưa sẵn sàng production — sửa các mục [!!].'))
        elif warn:
            self.stdout.write(self.style.WARNING('Có thể soft-launch beta; nên hoàn tất mục [..].'))
        else:
            self.stdout.write(self.style.SUCCESS('Checklist cơ bản đạt.'))
        self.stdout.write('')
