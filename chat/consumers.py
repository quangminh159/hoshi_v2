import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message, MessageSeen

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send user join message
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'join',
                        'user': self.user.username,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Send user leave message
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'leave',
                        'user': self.user.username,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')

        if message_type == 'message':
            message = text_data_json['message']
            
            # Save message to database
            if self.user.is_authenticated:
                saved_message = await self.save_message(message)
                
                # Broadcast message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': saved_message.id,
                            'type': 'message',
                            'user': self.user.username,
                            'content': message,
                            'timestamp': saved_message.created_at.isoformat()
                        }
                    }
                )
        
        elif message_type == 'typing':
            # Broadcast typing status
            if self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_status',
                        'user': self.user.username,
                        'typing': text_data_json['typing']
                    }
                )
        
        elif message_type == 'seen':
            # Mark messages as seen
            if self.user.is_authenticated:
                message_id = text_data_json['message_id']
                await self.mark_message_seen(message_id)
                
                # Broadcast seen status
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_seen',
                        'message_id': message_id,
                        'user': self.user.username,
                        'timestamp': timezone.now().isoformat()
                    }
                )

    async def chat_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user'],
            'typing': event['typing']
        }))

    async def message_seen(self, event):
        # Send seen status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'seen',
            'message_id': event['message_id'],
            'user': event['user'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def save_message(self, content):
        room = ChatRoom.objects.get(id=self.room_id)
        message = Message.objects.create(
            room=room,
            sender=self.user,
            text=content
        )
        return message

    @database_sync_to_async
    def mark_message_seen(self, message_id):
        message = Message.objects.get(id=message_id)
        MessageSeen.objects.get_or_create(
            user=self.user,
            message=message
        ) 