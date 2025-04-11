import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.notification_group_name = f'notifications_{self.user.id}'
        
        # Tham gia vào nhóm thông báo
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Gửi thông báo chưa đọc khi kết nối
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        # Rời khỏi nhóm thông báo
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data.get('command')
        
        if command == 'mark_as_read':
            notification_id = data.get('notification_id')
            if notification_id:
                await self.mark_notification_as_read(notification_id)
            else:
                await self.mark_all_as_read()
            
            # Gửi lại số lượng thông báo chưa đọc
            unread_count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': unread_count
            }))
    
    async def notification_message(self, event):
        # Gửi thông báo đến WebSocket
        await self.send(text_data=json.dumps(event))
    
    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(recipient=self.user, is_read=False).count()
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=self.user)
            notification.mark_as_read()
        except Notification.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_all_as_read(self):
        Notification.objects.filter(recipient=self.user, is_read=False).update(is_read=True) 