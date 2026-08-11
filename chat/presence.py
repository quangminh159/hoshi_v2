'''Trạng thái of người dùng'''

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone

from chat.models import UserSetting


def get_user_presence(user):
    """Trạng thái online / lần hoạt động cuối của người dùng."""
    if not user:
        return {'is_online': False, 'last_seen': None}
    try:
        settings = UserSetting.objects.get(user=user)
    except UserSetting.DoesNotExist:
        return {'is_online': False, 'last_seen': None}

    return {
        'is_online': bool(settings.is_online),
        'last_seen': settings.last_seen,
    }


def _conn_key(user_id):
    return f'chat_presence_conn:{int(user_id)}'


def presence_connection_delta(user_id, delta):
    """Đếm số socket đang mở (inbox + chat). Trả về số kết nối còn lại."""
    if not user_id:
        return 0
    key = _conn_key(user_id)
    current = cache.get(key) or 0
    try:
        current = int(current)
    except (TypeError, ValueError):
        current = 0
    next_n = max(0, current + int(delta))
    if next_n:
        cache.set(key, next_n, timeout=60 * 60 * 36)
    else:
        cache.delete(key)
    return next_n


def set_user_presence(user, *, online, touch_last_seen=False):
    """
    Cập nhật DB presence.
    online=True → is_online True
    online=False → is_online False + last_seen=now
    touch_last_seen → cập nhật last_seen khi vẫn online (heartbeat)
    """
    if not user:
        return None
    settings, _ = UserSetting.objects.get_or_create(
        user=user,
        defaults={'username': getattr(user, 'username', '') or ''},
    )
    update_fields = []
    if online:
        if not settings.is_online:
            settings.is_online = True
            update_fields.append('is_online')
        if touch_last_seen:
            settings.last_seen = timezone.now()
            update_fields.append('last_seen')
    else:
        settings.is_online = False
        settings.last_seen = timezone.now()
        update_fields.extend(['is_online', 'last_seen'])

    if update_fields:
        settings.save(update_fields=list(dict.fromkeys(update_fields)))

    return {
        'is_online': bool(settings.is_online),
        'last_seen': settings.last_seen.isoformat() if settings.last_seen else None,
    }


def broadcast_user_presence(user_id, status, last_seen=None, extra_inbox_ids=None):
    """
    Gửi trạng thái tới:
    - group user_presence_{user_id} (người đang xem chat với user này)
    - inbox của các user trong extra_inbox_ids (ví dụ đối phương trong DM)
    """
    if not user_id:
        return
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    event = {
        'type': 'user_presence',
        'user_id': int(user_id),
        'status': status,
        'last_seen': last_seen,
    }
    try:
        async_to_sync(channel_layer.group_send)(
            f'user_presence_{int(user_id)}',
            event,
        )
    except Exception:
        pass

    for inbox_id in extra_inbox_ids or []:
        if not inbox_id or int(inbox_id) == int(user_id):
            continue
        try:
            async_to_sync(channel_layer.group_send)(
                f'chat_inbox_{int(inbox_id)}',
                {
                    'type': 'inbox_user_presence',
                    'user_id': int(user_id),
                    'status': status,
                    'last_seen': last_seen,
                },
            )
        except Exception:
            pass


def mark_user_online(user, *, notify_inbox_ids=None):
    """Tăng refcount + online + broadcast."""
    if not user:
        return None
    presence_connection_delta(user.id, 1)
    info = set_user_presence(user, online=True, touch_last_seen=True)
    broadcast_user_presence(
        user.id,
        'online',
        last_seen=info.get('last_seen') if info else None,
        extra_inbox_ids=notify_inbox_ids,
    )
    return info


def mark_user_offline(user, *, notify_inbox_ids=None, force=False):
    """
    Giảm refcount; chỉ offline khi hết socket (hoặc force=True).
    """
    if not user:
        return None
    remaining = 0 if force else presence_connection_delta(user.id, -1)
    if remaining > 0 and not force:
        # Vẫn còn tab/socket khác → giữ online, chỉ touch last_seen
        info = set_user_presence(user, online=True, touch_last_seen=True)
        return info

    info = set_user_presence(user, online=False)
    broadcast_user_presence(
        user.id,
        'offline',
        last_seen=info.get('last_seen') if info else None,
        extra_inbox_ids=notify_inbox_ids,
    )
    return info
