from django.core.management.base import BaseCommand
from django.db import transaction

from chat.crypto import (
    encrypt_message_field,
    is_encrypted_value,
    is_encryption_enabled,
)
from chat.models import ConversationMessage, Message


class Command(BaseCommand):
    help = 'Mã hóa tin nhắn plaintext cũ trong DB (idempotent — bỏ qua tin đã enc:v1:).'

    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=200, help='Số tin mỗi batch')
        parser.add_argument('--dry-run', action='store_true', help='Chỉ đếm, không ghi')

    def handle(self, *args, **options):
        if not is_encryption_enabled():
            self.stderr.write(self.style.ERROR('MESSAGE_ENCRYPTION_ENABLED=False — dừng.'))
            return

        batch = max(1, options['batch'])
        dry = options['dry_run']
        total = 0

        for model, label in (
            (ConversationMessage, 'ConversationMessage'),
            (Message, 'Message'),
        ):
            # Đọc raw từ DB: dùng iterator + values để tránh from_db decrypt rồi tưởng là plain
            qs = model.objects.all().order_by('pk').values_list('pk', 'content', 'text')
            pending = []
            for pk, content, text in qs.iterator(chunk_size=batch):
                need_c = bool(content) and not is_encrypted_value(content)
                need_t = bool(text) and not is_encrypted_value(text)
                if not need_c and not need_t:
                    continue
                plain = (content if need_c else '') or (text if need_t else '') or ''
                if not plain:
                    continue
                enc = encrypt_message_field(plain)
                pending.append((pk, enc))
                if len(pending) >= batch:
                    total += self._flush(model, pending, dry, label)
                    pending = []
            if pending:
                total += self._flush(model, pending, dry, label)

        if dry:
            self.stdout.write(self.style.WARNING(f'Dry-run: sẽ mã hóa ~{total} tin.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Đã mã hóa {total} tin nhắn.'))

    def _flush(self, model, pending, dry, label):
        n = len(pending)
        if dry:
            self.stdout.write(f'[dry] {label}: {n}')
            return n
        with transaction.atomic():
            for pk, enc in pending:
                # update() bypass save()/from_db — ghi ciphertext thẳng
                model.objects.filter(pk=pk).update(content=enc, text=enc)
        self.stdout.write(f'{label}: +{n}')
        return n
