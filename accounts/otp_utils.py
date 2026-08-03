"""OTP helpers for verifying email / phone number changes."""
import logging
import random
import string

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 10 * 60
OTP_COOLDOWN_SECONDS = 60


def _cache_key(user_id, purpose):
    return f'contact_otp:{user_id}:{purpose}'


def _cooldown_key(user_id, purpose):
    return f'contact_otp_cooldown:{user_id}:{purpose}'


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def store_otp(user_id, purpose, code, payload):
    cache.set(
        _cache_key(user_id, purpose),
        {
            'code': code,
            'payload': payload,
            'created_at': timezone.now().isoformat(),
        },
        OTP_TTL_SECONDS,
    )
    cache.set(_cooldown_key(user_id, purpose), True, OTP_COOLDOWN_SECONDS)


def get_otp_record(user_id, purpose):
    return cache.get(_cache_key(user_id, purpose))


def clear_otp(user_id, purpose):
    cache.delete(_cache_key(user_id, purpose))
    cache.delete(_cooldown_key(user_id, purpose))


def is_in_cooldown(user_id, purpose):
    return bool(cache.get(_cooldown_key(user_id, purpose)))


def verify_otp(user_id, purpose, code):
    record = get_otp_record(user_id, purpose)
    if not record:
        return False, None, 'Mã xác thực đã hết hạn. Vui lòng gửi lại mã mới.'
    if str(record.get('code')) != str(code).strip():
        return False, None, 'Mã xác thực không chính xác.'
    payload = record.get('payload') or {}
    clear_otp(user_id, purpose)
    return True, payload, None


def send_email_otp(to_email, code, purpose_label):
    subject = f'[Hoshi] Mã xác thực {purpose_label}'
    message = (
        f'Mã xác thực {purpose_label} của bạn là: {code}\n\n'
        f'Mã có hiệu lực trong 10 phút. Nếu bạn không yêu cầu, hãy bỏ qua email này.'
    )
    html = (
        f'<p>Mã xác thực <strong>{purpose_label}</strong> của bạn là:</p>'
        f'<p style="font-size:28px;letter-spacing:6px;font-weight:bold">{code}</p>'
        f'<p>Mã có hiệu lực trong 10 phút. Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>'
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        html_message=html,
        fail_silently=False,
    )


def send_sms_otp(phone, code, purpose_label):
    """
    Send OTP SMS if Twilio (or compatible) credentials exist.
    Returns (ok: bool, detail: str).
    """
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '') or ''
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '') or ''
    from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '') or ''
    body = f'Hoshi: Ma xac thuc {purpose_label} la {code}. Hieu luc 10 phut.'

    if account_sid and auth_token and from_number:
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            client.messages.create(body=body, from_=from_number, to=str(phone))
            return True, 'sms'
        except Exception as exc:
            logger.exception('SMS OTP failed: %s', exc)
            return False, str(exc)

    # Development / no SMS provider: log clearly
    logger.warning('SMS OTP (no provider) to %s: %s — %s', phone, code, purpose_label)
    if settings.DEBUG:
        print(f'[Hoshi DEBUG SMS] To {phone}: {body}')
    return False, 'no_provider'


def deliver_contact_otp(user, channel, code, purpose_label):
    """
    Deliver OTP to the user's CURRENT contact.
    channel: 'email' | 'phone'
    Returns dict: {ok, method, message}
    """
    if channel == 'email':
        if not user.email:
            return {'ok': False, 'method': None, 'message': 'Tài khoản chưa có email để nhận mã.'}
        send_email_otp(user.email, code, purpose_label)
        return {
            'ok': True,
            'method': 'email',
            'message': f'Đã gửi mã xác thực đến email {user.email}.',
        }

    if channel == 'phone':
        if not user.phone_number:
            # First-time phone / missing phone: fall back to email
            if not user.email:
                return {
                    'ok': False,
                    'method': None,
                    'message': 'Không có số điện thoại hoặc email để gửi mã xác thực.',
                }
            send_email_otp(user.email, code, purpose_label)
            return {
                'ok': True,
                'method': 'email_fallback',
                'message': f'Chưa có SĐT cũ — đã gửi mã xác thực đến email {user.email}.',
            }

        sms_ok, sms_detail = send_sms_otp(user.phone_number, code, purpose_label)
        if sms_ok:
            return {
                'ok': True,
                'method': 'sms',
                'message': f'Đã gửi mã xác thực đến số {user.phone_number}.',
            }

        # Fallback: email copy when SMS unavailable
        if user.email:
            send_email_otp(user.email, code, purpose_label)
            debug_hint = f' (mã DEBUG: {code})' if settings.DEBUG else ''
            return {
                'ok': True,
                'method': 'email_fallback',
                'message': (
                    f'Không gửi được SMS tới {user.phone_number}. '
                    f'Đã gửi mã xác thực đổi SĐT về email {user.email}.{debug_hint}'
                ),
            }

        if settings.DEBUG:
            return {
                'ok': True,
                'method': 'debug',
                'message': f'[DEBUG] SMS chưa cấu hình. Mã xác thực: {code}',
            }

        return {
            'ok': False,
            'method': None,
            'message': 'Không thể gửi mã xác thực. Vui lòng thử lại sau hoặc liên hệ hỗ trợ.',
        }

    return {'ok': False, 'method': None, 'message': 'Kênh xác thực không hợp lệ.'}
