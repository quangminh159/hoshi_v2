from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification, WebPushSubscription
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        ).exclude(
            notification_type='message',
        )

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe_webpush(request):
    """Lưu subscription Web Push từ trình duyệt."""
    data = request.data.get('subscription') or request.data
    endpoint = (data.get('endpoint') or '').strip()
    keys = data.get('keys') or {}
    p256dh = (keys.get('p256dh') or '').strip()
    auth = (keys.get('auth') or '').strip()
    if not endpoint or not p256dh or not auth:
        return Response({'ok': False, 'error': 'subscription không hợp lệ'}, status=400)

    sub, _ = WebPushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'user': request.user,
            'p256dh': p256dh,
            'auth': auth,
            'user_agent': (request.META.get('HTTP_USER_AGENT') or '')[:255],
        },
    )
    return Response({'ok': True, 'id': sub.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unsubscribe_webpush(request):
    endpoint = (request.data.get('endpoint') or '').strip()
    if endpoint:
        WebPushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    else:
        WebPushSubscription.objects.filter(user=request.user).delete()
    return Response({'ok': True})
