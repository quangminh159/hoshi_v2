"""OTP helpers for verifying email / phone number changes and password reset."""
import logging
import secrets
import string

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 10 * 60
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
OTP_LOCKOUT_SECONDS = 15 * 60
OTP_IP_VERIFY_LIMIT = 30
OTP_IP_VERIFY_WINDOW = 15 * 60
OTP_IP_RESEND_LIMIT = 10
OTP_IP_RESEND_WINDOW = 15 * 60

PASSWORD_RESET_NEUTRAL_MESSAGE = (
    'Nếu số điện thoại này có trên Hoshi, bạn sẽ nhận được mã xác thực trong vài phút.'
)


def _cache_key(user_id, purpose):
    return f'contact_otp:{user_id}:{purpose}'


def _cooldown_key(user_id, purpose):
    return f'contact_otp_cooldown:{user_id}:{purpose}'


def _attempts_key(user_id, purpose):
    return f'contact_otp_attempts:{user_id}:{purpose}'


def _lockout_key(user_id, purpose):
    return f'contact_otp_lockout:{user_id}:{purpose}'


def generate_otp(length=6):
    alphabet = string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


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
    # New code resets failed attempts but not an active lockout window
    cache.delete(_attempts_key(user_id, purpose))


def get_otp_record(user_id, purpose):
    return cache.get(_cache_key(user_id, purpose))


def clear_otp(user_id, purpose):
    cache.delete(_cache_key(user_id, purpose))
    cache.delete(_cooldown_key(user_id, purpose))


def clear_otp_attempts(user_id, purpose):
    cache.delete(_attempts_key(user_id, purpose))
    cache.delete(_lockout_key(user_id, purpose))


def is_in_cooldown(user_id, purpose):
    return bool(cache.get(_cooldown_key(user_id, purpose)))


def is_otp_locked(user_id, purpose):
    return bool(cache.get(_lockout_key(user_id, purpose)))


def register_otp_failure(user_id, purpose):
    """
    Ghi nhận lần nhập OTP sai. Khóa tạm và hủy mã khi vượt ngưỡng.
    Returns (locked: bool, attempts: int).
    """
    if is_otp_locked(user_id, purpose):
        return True, OTP_MAX_ATTEMPTS

    key = _attempts_key(user_id, purpose)
    attempts = int(cache.get(key) or 0) + 1
    cache.set(key, attempts, OTP_TTL_SECONDS)

    if attempts >= OTP_MAX_ATTEMPTS:
        cache.set(_lockout_key(user_id, purpose), True, OTP_LOCKOUT_SECONDS)
        clear_otp(user_id, purpose)
        cache.delete(key)
        logger.warning(
            'OTP lockout purpose=%s user_id=%s after %s failed attempts',
            purpose,
            user_id,
            attempts,
        )
        return True, attempts
    return False, attempts


def verify_otp(user_id, purpose, code):
    if is_otp_locked(user_id, purpose):
        return False, None, (
            'Quá nhiều lần thử sai. Vui lòng thử lại sau khoảng 15 phút '
            'hoặc yêu cầu mã mới sau khi hết khóa.'
        )

    record = get_otp_record(user_id, purpose)
    if not record:
        return False, None, 'Mã xác thực đã hết hạn. Vui lòng gửi lại mã mới.'

    if str(record.get('code')) != str(code).strip():
        locked, attempts = register_otp_failure(user_id, purpose)
        if locked:
            return False, None, (
                'Quá nhiều lần thử sai. Mã hiện tại đã bị hủy. '
                'Vui lòng thử lại sau khoảng 15 phút.'
            )
        remaining = OTP_MAX_ATTEMPTS - attempts
        return False, None, f'Mã xác thực không chính xác. Còn {remaining} lần thử.'

    payload = record.get('payload') or {}
    clear_otp(user_id, purpose)
    clear_otp_attempts(user_id, purpose)
    return True, payload, None


def consume_ip_rate(ip, action, limit, window_seconds):
    """
    Đếm request theo IP. Returns (allowed: bool, retry_after_hint: str|None).
    """
    safe_ip = (ip or 'unknown').replace(':', '_')
    key = f'otp_ip_rate:{action}:{safe_ip}'
    count = int(cache.get(key) or 0) + 1
    if count == 1:
        cache.set(key, 1, window_seconds)
    else:
        cache.set(key, count, window_seconds)
    if count > limit:
        return False, 'Vui lòng thử lại sau vài phút.'
    return True, None


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'


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
    Never logs the OTP code.
    """
    account_sid = (getattr(settings, 'TWILIO_ACCOUNT_SID', '') or '').strip()
    auth_token = (getattr(settings, 'TWILIO_AUTH_TOKEN', '') or '').strip()
    from_number = (getattr(settings, 'TWILIO_FROM_NUMBER', '') or '').strip()

    # Bỏ qua placeholder / giá trị mẫu trong .env.example
    blob = f'{account_sid} {auth_token} {from_number}'.lower()
    if any(m in blob for m in ('your-twilio', 'xxxxxxxxxx', 'acxxxxxxxx', 'changeme')):
        account_sid = auth_token = from_number = ''

    purpose_ascii = (
        str(purpose_label)
        .encode('ascii', 'ignore')
        .decode('ascii')
        .strip()
        or 'OTP'
    )
    body = f'Hoshi: Ma xac thuc {purpose_ascii} la {code}. Hieu luc 10 phut.'

    if account_sid and auth_token and from_number:
        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            client.messages.create(body=body, from_=from_number, to=str(phone))
            return True, 'sms'
        except Exception:
            logger.exception('SMS OTP failed for phone ending %s', str(phone)[-4:])
            return False, 'provider_error'

    logger.warning(
        'SMS OTP skipped (no provider) phone_ending=%s purpose=%s',
        str(phone)[-4:],
        purpose_ascii,
    )
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
            'message': 'Đã gửi mã xác thực đến email hiện tại của bạn.',
        }

    if channel == 'phone':
        if not user.phone_number:
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
                'message': 'Chưa có SĐT cũ — đã gửi mã xác thực đến email hiện tại của bạn.',
            }

        sms_ok, _sms_detail = send_sms_otp(user.phone_number, code, purpose_label)
        if sms_ok:
            return {
                'ok': True,
                'method': 'sms',
                'message': 'Đã gửi mã xác thực đến số điện thoại hiện tại của bạn.',
            }

        if user.email:
            send_email_otp(user.email, code, purpose_label)
            return {
                'ok': True,
                'method': 'email_fallback',
                'message': (
                    'Không gửi được SMS. Đã gửi mã xác thực về email hiện tại của bạn.'
                ),
            }

        logger.error(
            'Unable to deliver contact OTP user_id=%s (no SMS provider, no email)',
            user.id,
        )
        return {
            'ok': False,
            'method': None,
            'message': 'Không thể gửi mã xác thực. Vui lòng thử lại sau hoặc liên hệ hỗ trợ.',
        }

    return {'ok': False, 'method': None, 'message': 'Kênh xác thực không hợp lệ.'}


def deliver_password_reset_otp(user, code):
    """
    Gửi OTP đặt lại mật khẩu ưu tiên SMS; fallback email khi chưa có Twilio.
    Message trả về luôn trung tính — không lộ email/SĐT/OTP.
    """
    purpose = 'đặt lại mật khẩu'
    delivered = False
    method = None

    if user.phone_number:
        sms_ok, _sms_detail = send_sms_otp(user.phone_number, code, 'dat lai mat khau')
        if sms_ok:
            delivered = True
            method = 'sms'

    if not delivered and user.email:
        send_email_otp(user.email, code, purpose)
        delivered = True
        method = 'email_fallback' if user.phone_number else 'email'

    if delivered:
        logger.info(
            'Password reset OTP delivered user_id=%s method=%s',
            user.id,
            method,
        )
        return {
            'ok': True,
            'method': method,
            'message': PASSWORD_RESET_NEUTRAL_MESSAGE,
        }

    logger.error(
        'Password reset OTP not delivered user_id=%s (no SMS provider, no email)',
        user.id,
    )
    # Vẫn trả message trung tính để tránh enumeration; OTP nằm trong cache
    # nhưng user không nhận được — họ có thể dùng email reset.
    return {
        'ok': False,
        'method': None,
        'message': PASSWORD_RESET_NEUTRAL_MESSAGE,
    }
