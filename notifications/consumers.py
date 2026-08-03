import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        user = self.scope.get('user')

        if (
            not user
            or not getattr(user, 'is_authenticated', False)
            or str(user.id) != str(self.user_id)
        ):
            await self.close()
            return

        self.room_group_name = f'notifications_{self.user_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        room = getattr(self, 'room_group_name', None)
        if room:
            await self.channel_layer.group_discard(room, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')
        if message == 'ping':
            await self.send(text_data=json.dumps({'message': 'pong'}))

    async def notification_message(self, event):
        # Ưu tiên payload đã có sẵn từ signal
        notification_data = event.get('notification') or {}
        unread_count = event.get('unread_count')

        if not notification_data and event.get('notification_id'):
            notification_data = await self.get_notification_data(event['notification_id'])

        if unread_count is None:
            unread_count = await self.get_unread_count(self.user_id)

        await self.send(text_data=json.dumps({
            'message': event.get('message', 'new_notification'),
            'notification': notification_data,
            'unread_count': unread_count,
        }))

    @database_sync_to_async
    def get_notification_data(self, notification_id):
        try:
            notification = Notification.objects.select_related(
                'sender', 'message'
            ).get(id=notification_id)
            return {
                'id': notification.id,
                'notification_type': notification.notification_type,
                'text': notification.text,
                'created_at': notification.created_at.isoformat(),
                'is_read': notification.is_read,
                'sender_id': notification.sender_id,
                'sender_username': notification.sender.username,
                'sender_avatar': notification.sender.get_avatar_url(),
                'post_id': notification.post_id,
                'conversation_id': notification.conversation_id or (
                    notification.message.conversation_id
                    if notification.message_id and getattr(notification.message, 'conversation_id', None)
                    else None
                ),
                'link': notification.link,
            }
        except Notification.DoesNotExist:
            return {}

    @database_sync_to_async
    def get_unread_count(self, user_id):
        return Notification.objects.filter(recipient_id=user_id, is_read=False).count()
