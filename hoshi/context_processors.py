from notifications.models import Notification

def common_variables(request):
    context = {}
    
    if request.user.is_authenticated:
        # Count unread notifications
        notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        # Get 5 most recent notifications
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
        
        context.update({
            'notification_count': notification_count,
            'notifications': notifications,
        })
    
    return context 