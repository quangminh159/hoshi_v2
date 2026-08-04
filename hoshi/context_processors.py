from notifications.models import Notification


def common_variables(request):
    context = {}

    if request.user.is_authenticated:
        notification_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:5]

        from chat.unread import get_unread_message_count
        unread_message_count = get_unread_message_count(request.user)

        context.update({
            'notification_count': notification_count,
            'notifications': notifications,
            'unread_message_count': unread_message_count,
        })

    return context
