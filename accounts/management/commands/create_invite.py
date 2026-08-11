import secrets

from django.core.management.base import BaseCommand

from accounts.models import InviteCode


class Command(BaseCommand):
    help = 'Tạo mã mời closed beta (InviteCode)'

    def add_arguments(self, parser):
        parser.add_argument('-n', '--count', type=int, default=1, help='Số mã tạo')
        parser.add_argument('--uses', type=int, default=1, help='Số lượt dùng mỗi mã')
        parser.add_argument('--note', type=str, default='beta', help='Ghi chú')
        parser.add_argument('--prefix', type=str, default='MOORA', help='Tiền tố mã')

    def handle(self, *args, **options):
        created = []
        for _ in range(max(options['count'], 1)):
            code = f"{options['prefix']}-{secrets.token_hex(3).upper()}"
            obj = InviteCode.objects.create(
                code=code,
                max_uses=max(options['uses'], 1),
                note=options['note'],
            )
            created.append(obj.code)
        self.stdout.write(self.style.SUCCESS('Đã tạo mã mời:'))
        for c in created:
            self.stdout.write(f'  {c}')
