"""
Mã hóa nội dung tin nhắn khi lưu DB (AES / Fernet).

- Prefixed `enc:v1:` để phân biệt plaintext cũ.
- Key: MESSAGE_ENCRYPTION_KEY (khuyến nghị) hoặc derive từ SECRET_KEY.
- Đây là encryption-at-rest: server vẫn giải mã được khi user hợp lệ đọc.
  (E2EE kiểu Signal là bước sau, phức tạp hơn nhiều.)
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

ENC_PREFIX = 'enc:v1:'


class MessageCryptoError(Exception):
    pass


def is_encryption_enabled() -> bool:
    return bool(getattr(settings, 'MESSAGE_ENCRYPTION_ENABLED', True))


def is_encrypted_value(value) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


@lru_cache(maxsize=1)
def _fernet():
    from cryptography.fernet import Fernet

    raw = (getattr(settings, 'MESSAGE_ENCRYPTION_KEY', '') or '').strip()
    if raw:
        try:
            decoded = base64.urlsafe_b64decode(raw)
            if len(decoded) == 32:
                return Fernet(raw.encode('ascii'))
        except Exception:
            pass
        raw_key = hashlib.sha256(raw.encode('utf-8')).digest()
    else:
        secret = (getattr(settings, 'SECRET_KEY', '') or '').encode('utf-8')
        raw_key = hashlib.sha256(b'moora-msg-v1:' + secret).digest()
    return Fernet(base64.urlsafe_b64encode(raw_key))


def clear_fernet_cache():
    _fernet.cache_clear()


def encrypt_message_field(value):
    """Mã hóa chuỗi; giữ nguyên None/'' và giá trị đã mã hóa."""
    if value is None or value == '':
        return value
    text = str(value)
    if is_encrypted_value(text):
        return text
    if not is_encryption_enabled():
        return text
    try:
        token = _fernet().encrypt(text.encode('utf-8')).decode('ascii')
        return ENC_PREFIX + token
    except Exception as exc:
        logger.error('encrypt_message_field failed: %s', type(exc).__name__)
        raise MessageCryptoError('Không mã hóa được tin nhắn') from exc


def decrypt_message_field(value):
    """Giải mã nếu có prefix; plaintext cũ trả về nguyên."""
    if value is None or value == '':
        return value
    text = str(value)
    if not is_encrypted_value(text):
        return text
    token = text[len(ENC_PREFIX) :]
    try:
        return _fernet().decrypt(token.encode('ascii')).decode('utf-8')
    except Exception as exc:
        logger.error('decrypt_message_field failed: %s', type(exc).__name__)
        # Không crash cả app nếu key lệch — hiện placeholder
        return '[Không đọc được tin nhắn đã mã hóa]'


def prepare_fields_for_storage(content, text):
    """
    Đồng bộ content/text rồi mã hóa một lần (cùng ciphertext).
    Trả về (content, text) sẵn sàng ghi DB.
    """
    plain_c = decrypt_message_field(content) if content else ''
    plain_t = decrypt_message_field(text) if text else ''
    plain = plain_c or plain_t or ''
    if plain == '':
        synced = content or text or None
        if synced == '':
            synced = None
        return synced, synced

    # Giữ ciphertext cũ nếu plaintext không đổi
    for raw in (content, text):
        if is_encrypted_value(raw) and decrypt_message_field(raw) == plain:
            return raw, raw

    enc = encrypt_message_field(plain)
    return enc, enc


def redact_for_log(value, max_len: int = 0) -> str:
    """Không bao giờ log plaintext tin nhắn."""
    if not value:
        return ''
    if is_encrypted_value(value):
        return '[encrypted]'
    return '[redacted]'
