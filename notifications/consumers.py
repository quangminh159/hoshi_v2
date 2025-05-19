import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'notifications_{self.user_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

        # Process any client-side messages if needed
        if message == 'ping':
            await self.send(text_data=json.dumps({
                'message': 'pong'
            }))

    # Receive message from room group
    async def notification_message(self, event):
        message = event['message']
        notification_id = event.get('notification_id')
        
        # If we have a notification ID, fetch details
        notification_data = {}
        if notification_id:
            notification_data = await self.get_notification_data(notification_id)
            
        # Get unread count
        unread_count = await self.get_unread_count(self.user_id)
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'notification': notification_data,
            'unread_count': unread_count
        }))

    @database_sync_to_async
    def get_notification_data(self, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id)
            
            # Build detailed notification data
            return {
                'id': notification.id,
                'notification_type': notification.notification_type,
                'text': notification.text,
                'created_at': notification.created_at.isoformat(),
                'is_read': notification.is_read,
                'sender_id': notification.sender.id,
                'sender_username': notification.sender.username,
                'sender_avatar': notification.sender.get_avatar_url(),
                'link': notification.link
            }
        except Notification.DoesNotExist:
            return {}

    @database_sync_to_async
    def get_unread_count(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            return Notification.objects.filter(recipient=user, is_read=False).count()
        except User.DoesNotExist:
            return 0 