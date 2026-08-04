from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.utils.timesince import timesince
from .models import Notification

NOTIFICATIONS_PAGE_SIZE = 15


def _activity_notifications(user):
    """Thông báo hoạt động — không gồm tin nhắn chat."""
    return (
        Notification.objects.filter(recipient=user)
        .exclude(notification_type='message')
        .select_related('sender')
    )


def _serialize_notification(notification):
    sender = notification.sender
    return {
        'id': notification.id,
        'notification_type': notification.notification_type,
        'text': notification.text or '',
        'is_read': notification.is_read,
        'link': notification.link,
        'created_at': notification.created_at.isoformat(),
        'time_ago': timesince(notification.created_at),
        'sender': {
            'id': sender.id if sender else None,
            'username': sender.username if sender else '',
            'avatar_url': sender.get_avatar_url() if sender else '/static/img/default-avatar.png',
        },
    }


@login_required
def notification_list(request):
    qs = _activity_notifications(request.user).order_by('-created_at')
    paginator = Paginator(qs, NOTIFICATIONS_PAGE_SIZE)
    page_obj = paginator.get_page(1)

    context = {
        'notifications': page_obj,
        'has_more': page_obj.has_next(),
        'next_page': 2 if page_obj.has_next() else None,
    }
    return render(request, 'notifications/notifications.html', context)


@login_required
def api_notifications(request):
    """API phân trang cho cuộn vô hạn trang thông báo."""
    try:
        page_number = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page_number = 1

    qs = _activity_notifications(request.user).order_by('-created_at')
    paginator = Paginator(qs, NOTIFICATIONS_PAGE_SIZE)

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({
            'notifications': [],
            'has_next': False,
            'next_page': None,
        })

    return JsonResponse({
        'notifications': [_serialize_notification(n) for n in page_obj.object_list],
        'has_next': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
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

    notification_type = request.POST.get('type')
    notifications = _activity_notifications(request.user).filter(is_read=False)

    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)

    count = notifications.count()
    notifications.update(is_read=True)

    return JsonResponse({
        'success': True,
        'count': count,
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

    notification_type = request.POST.get('type')
    notifications = _activity_notifications(request.user)

    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)

    notifications.delete()

    return JsonResponse({'status': 'success'})


@login_required
def get_unread_count(request):
    """Lấy số lượng thông báo chưa đọc (không gồm tin nhắn chat)."""
    unread_count = _activity_notifications(request.user).filter(is_read=False).count()
    return JsonResponse({
        'unread_count': unread_count,
    })
