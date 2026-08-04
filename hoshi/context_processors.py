from notifications.models import Notification

# Tin nhắn dùng badge Chat riêng — không lẫn vào feed Thông báo
_EXCLUDE_FROM_ACTIVITY = ('message',)


def common_variables(request):
    context = {}

    if request.user.is_authenticated:
        activity_qs = Notification.objects.filter(
            recipient=request.user,
        ).exclude(
            notification_type__in=_EXCLUDE_FROM_ACTIVITY,
        )

        notification_count = activity_qs.filter(is_read=False).count()
        notifications = activity_qs.order_by('-created_at')[:5]

        from chat.unread import get_unread_message_count
        unread_message_count = get_unread_message_count(request.user)

        context.update({
            'notification_count': notification_count,
            'notifications': notifications,
            'unread_message_count': unread_message_count,
        })

    return context
