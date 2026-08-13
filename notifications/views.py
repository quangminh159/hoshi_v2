from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.utils.timesince import timesince
from .models import Notification

NOTIFICATIONS_PAGE_SIZE = 15

# Tabs kiểu Instagram: All / People you follow / Comments / Follows / Tags & mentions
NOTIFICATION_FILTERS = {
    'all': None,
    'following': 'following',
    'comments': ('comment', 'comment_reply'),
    'follows': ('follow', 'follow_request', 'follow_accepted'),
    'mentions': ('mention',),
}


def _activity_notifications(user):
    """Thông báo hoạt động — không gồm tin nhắn chat."""
    return (
        Notification.objects.filter(recipient=user)
        .exclude(notification_type='message')
        .select_related('sender')
    )


def _apply_notification_filter(qs, user, filter_key):
    key = (filter_key or 'all').strip().lower()
    if key not in NOTIFICATION_FILTERS:
        key = 'all'

    spec = NOTIFICATION_FILTERS[key]
    if key == 'following':
        following_ids = list(user.get_following_user_ids())
        if not following_ids:
            return qs.none(), key
        return qs.filter(sender_id__in=following_ids), key
    if isinstance(spec, tuple):
        return qs.filter(notification_type__in=spec), key
    return qs, key


def _attach_follow_back_flags(user, notifications):
    """Gắn cờ hiện nút Theo dõi lại cho thông báo follow."""
    items = list(notifications)
    sender_ids = {
        n.sender_id
        for n in items
        if n.notification_type == 'follow' and n.sender_id and n.sender_id != user.id
    }
    following_ids = set()
    pending_ids = set()
    if sender_ids:
        from accounts.models import UserFollowing, FollowRequest
        following_ids = set(
            UserFollowing.objects.filter(
                user=user, following_user_id__in=sender_ids
            ).values_list('following_user_id', flat=True)
        )
        pending_ids = set(
            FollowRequest.objects.filter(
                from_user=user,
                to_user_id__in=sender_ids,
            ).values_list('to_user_id', flat=True)
        )

    for n in items:
        if n.notification_type != 'follow' or not n.sender_id or n.sender_id == user.id:
            n.is_following_sender = False
            n.follow_request_pending = False
            n.show_follow_back = False
            continue
        n.is_following_sender = n.sender_id in following_ids
        n.follow_request_pending = n.sender_id in pending_ids
        n.show_follow_back = not n.is_following_sender and not n.follow_request_pending
        # Tránh hiển thị trùng "Moora Moora đã theo dõi bạn"
        raw = (n.text or '').strip()
        uname = n.sender.username if n.sender else ''
        if uname and raw.lower().startswith(uname.lower()):
            raw = raw[len(uname):].lstrip(' :,-')
        n.display_text = raw or 'đã theo dõi bạn'
    return items


def _serialize_notification(notification):
    sender = notification.sender
    data = {
        'id': notification.id,
        'notification_type': notification.notification_type,
        'text': (
            getattr(notification, 'display_text', None)
            or notification.text
            or ''
        ),
        'is_read': notification.is_read,
        'link': notification.link,
        'created_at': notification.created_at.isoformat(),
        'time_ago': timesince(notification.created_at),
        'sender': {
            'id': sender.id if sender else None,
            'username': sender.username if sender else '',
            'avatar_url': sender.get_avatar_url() if sender else '/static/img/default-avatar.png',
        },
        'show_follow_back': bool(getattr(notification, 'show_follow_back', False)),
        'is_following_sender': bool(getattr(notification, 'is_following_sender', False)),
        'follow_request_pending': bool(getattr(notification, 'follow_request_pending', False)),
    }
    return data



@login_required
def notification_list(request):
    filter_key = request.GET.get('filter', 'all')
    qs = _activity_notifications(request.user).order_by('-created_at')
    qs, filter_key = _apply_notification_filter(qs, request.user, filter_key)
    paginator = Paginator(qs, NOTIFICATIONS_PAGE_SIZE)
    page_obj = paginator.get_page(1)
    notifications = _attach_follow_back_flags(request.user, page_obj.object_list)

    context = {
        'notifications': notifications,
        'has_more': page_obj.has_next(),
        'next_page': 2 if page_obj.has_next() else None,
        'active_filter': filter_key,
    }
    return render(request, 'notifications/notifications.html', context)


@login_required
def api_notifications(request):
    """API phân trang cho cuộn vô hạn trang thông báo."""
    try:
        page_number = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page_number = 1

    filter_key = request.GET.get('filter', 'all')
    qs = _activity_notifications(request.user).order_by('-created_at')
    qs, filter_key = _apply_notification_filter(qs, request.user, filter_key)
    paginator = Paginator(qs, NOTIFICATIONS_PAGE_SIZE)

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({
            'notifications': [],
            'has_next': False,
            'next_page': None,
            'filter': filter_key,
        })

    notifications = _attach_follow_back_flags(request.user, page_obj.object_list)
    return JsonResponse({
        'notifications': [_serialize_notification(n) for n in notifications],
        'has_next': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'filter': filter_key,
    })


@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@login_required
def mark_all_as_read(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    filter_key = request.POST.get('filter') or request.GET.get('filter') or 'all'
    notifications = _activity_notifications(request.user).filter(is_read=False)
    notifications, filter_key = _apply_notification_filter(notifications, request.user, filter_key)

    count = notifications.count()
    notifications.update(is_read=True)

    return JsonResponse({
        'success': True,
        'count': count,
        'filter': filter_key,
    })


@login_required
def delete_notification(request, notification_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )
    notification.delete()

    return JsonResponse({'status': 'success'})


@login_required
def delete_all_notifications(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # filter=all (mặc định) → xóa hết; nếu đang ở tab khác → xóa theo tab đang xem
    filter_key = request.POST.get('filter') or request.GET.get('filter') or 'all'
    notifications = _activity_notifications(request.user)
    notifications, filter_key = _apply_notification_filter(notifications, request.user, filter_key)
    count = notifications.count()
    notifications.delete()

    return JsonResponse({
        'status': 'success',
        'count': count,
        'filter': filter_key,
    })


@login_required
def get_unread_count(request):
    """Lấy số lượng thông báo chưa đọc (không gồm tin nhắn chat)."""
    unread_count = _activity_notifications(request.user).filter(is_read=False).count()
    return JsonResponse({
        'unread_count': unread_count,
    })
