"""Gửi Web Push (điện thoại / trình duyệt) khi có thông báo mới."""

from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def vapid_configured() -> bool:
    return bool(
        getattr(settings, 'WEBPUSH_VAPID_PRIVATE_KEY', '')
        and getattr(settings, 'WEBPUSH_VAPID_PUBLIC_KEY', '')
    )


def send_web_push_for_notification(notification) -> int:
    """Gửi push tới mọi subscription của recipient. Trả về số máy gửi OK."""
    if not vapid_configured():
        return 0

    recipient = notification.recipient
    if not getattr(recipient, 'push_notifications', True):
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning('pywebpush chưa cài — bỏ qua web push')
        return 0

    from .models import WebPushSubscription

    subs = list(WebPushSubscription.objects.filter(user=recipient))
    if not subs:
        return 0

    link = notification.link or '/'
    payload = json.dumps({
        'title': 'Moora',
        'body': (notification.text or 'Bạn có thông báo mới')[:160],
        'url': link,
        'tag': f'notif-{notification.id}',
        'notification_id': notification.id,
    }, ensure_ascii=False)

    vapid_private = settings.WEBPUSH_VAPID_PRIVATE_KEY
    vapid_claims = {
        'sub': getattr(settings, 'WEBPUSH_VAPID_ADMIN_EMAIL', 'mailto:admin@moora.local'),
    }
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info=sub.as_subscription_info(),
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status in (404, 410):
                sub.delete()
            else:
                logger.warning('Web push failed user=%s: %s', recipient.id, exc)
        except Exception as exc:
            logger.warning('Web push error user=%s: %s', recipient.id, exc)
    return sent
