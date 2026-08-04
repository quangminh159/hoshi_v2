"""Helpers for private-account follow requests."""
from .models import FollowRequest, UserFollowing


def _clear_follow_request_notifications(from_user, to_user):
    from notifications.models import Notification

    Notification.objects.filter(
        recipient=to_user,
        sender=from_user,
        notification_type='follow_request',
    ).delete()


def create_follow_request(from_user, to_user):
    """Create or return existing pending request and notify target."""
    request_obj, created = FollowRequest.objects.get_or_create(
        from_user=from_user,
        to_user=to_user,
    )
    if created:
        _notify_follow_request(from_user, to_user)
    return request_obj, created


def _notify_follow_request(from_user, to_user):
    from notifications.models import Notification
    from notifications.signals import send_notification_to_websocket, _pref_enabled

    if not _pref_enabled(to_user, 'follow_notifications'):
        return

    notification = Notification.objects.create(
        recipient=to_user,
        sender=from_user,
        notification_type='follow_request',
        text=f'{from_user.username} đã gửi yêu cầu theo dõi bạn',
    )
    send_notification_to_websocket(notification)


def cancel_follow_request(from_user, to_user):
    deleted, _ = FollowRequest.objects.filter(
        from_user=from_user,
        to_user=to_user,
    ).delete()
    if deleted:
        _clear_follow_request_notifications(from_user, to_user)
    return deleted > 0


def accept_follow_request(to_user, from_user):
    """Target (to_user) accepts a request from from_user."""
    try:
        req = FollowRequest.objects.get(from_user=from_user, to_user=to_user)
    except FollowRequest.DoesNotExist:
        return None
    _clear_follow_request_notifications(from_user, to_user)
    return req.accept()


def reject_follow_request(to_user, from_user):
    try:
        req = FollowRequest.objects.get(from_user=from_user, to_user=to_user)
    except FollowRequest.DoesNotExist:
        return False
    _clear_follow_request_notifications(from_user, to_user)
    req.reject()
    return True


def accept_all_pending_for(user):
    """When account becomes public, convert pending requests into follows."""
    pending = list(FollowRequest.objects.filter(to_user=user).select_related('from_user'))
    for req in pending:
        from_user = req.from_user
        _clear_follow_request_notifications(from_user, user)
        UserFollowing.objects.get_or_create(user=from_user, following_user=user)
        req.delete()
    return len(pending)
