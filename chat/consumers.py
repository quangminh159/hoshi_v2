import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message, MessageRead, MessageReaction

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

        # Kiểm tra quyền truy cập phòng chat
        if self.user.is_authenticated:
            has_access = await self.has_room_access()
            if not has_access:
                await self.close()
                return

            # Gửi thông báo có người tham gia
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_join',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Gửi thông báo có người rời đi
        if self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')

        if message_type == 'message':
            content = text_data_json.get('content', '')
            media_url = text_data_json.get('media', None)
            media_type = text_data_json.get('media_type', 'text')
            replied_to_id = text_data_json.get('replied_to', None)
            
            # Lưu tin nhắn vào cơ sở dữ liệu
            if self.user.is_authenticated and content:
                saved_message = await self.save_message(content, media_url, media_type, replied_to_id)
                
                # Gửi tin nhắn tới tất cả người dùng trong phòng
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': saved_message.id,
                            'content': saved_message.content,
                            'sender_id': self.user.id,
                            'sender': self.user.username,
                            'created_at': saved_message.created_at.isoformat(),
                            'media': saved_message.media.url if saved_message.media else None,
                            'media_type': saved_message.media_type,
                            'will_vanish': await self.is_vanish_mode(),
                            'replied_to': {
                                'id': saved_message.replied_to.id,
                                'content': saved_message.replied_to.content,
                                'sender': saved_message.replied_to.sender.username
                            } if saved_message.replied_to else None
                        }
                    }
                )
        
        elif message_type == 'typing':
            # Trạng thái đang nhập
            is_typing = text_data_json.get('is_typing', False)
            if self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_status',
                        'user_id': self.user.id,
                        'username': self.user.username,
                        'is_typing': is_typing
                    }
                )
        
        elif message_type == 'seen':
            # Đánh dấu tin nhắn đã đọc
            if self.user.is_authenticated:
                message_id = text_data_json.get('message_id')
                if message_id:
                    await self.mark_message_seen(message_id)
                    
                    # Gửi trạng thái đã đọc
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'message_seen',
                            'message_id': message_id,
                            'user_id': self.user.id,
                            'username': self.user.username,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
        
        elif message_type == 'reaction':
            # Thêm/xóa reaction
            if self.user.is_authenticated:
                message_id = text_data_json.get('message_id')
                reaction = text_data_json.get('reaction', 'like')
                
                if message_id:
                    result = await self.toggle_reaction(message_id, reaction)
                    
                    # Gửi thông tin về reaction
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'message_reaction',
                            'message_id': message_id,
                            'user_id': self.user.id,
                            'username': self.user.username,
                            'reaction': reaction,
                            'action': result['action'],
                            'reactions': result['reactions']
                        }
                    )
        
        elif message_type == 'delete':
            # Xóa tin nhắn
            if self.user.is_authenticated:
                message_id = text_data_json.get('message_id')
                
                if message_id:
                    result = await self.delete_message(message_id)
                    
                    if result['success']:
                        # Gửi thông báo xóa tin nhắn
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'message_deleted',
                                'message_id': message_id,
                                'user_id': self.user.id
                            }
                        )

    async def chat_message(self, event):
        # Gửi tin nhắn tới WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    async def typing_status(self, event):
        # Gửi trạng thái đang nhập
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def message_seen(self, event):
        # Gửi trạng thái đã đọc
        await self.send(text_data=json.dumps({
            'type': 'seen',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))
    
    async def message_reaction(self, event):
        # Gửi thông tin reaction
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'reaction': event['reaction'],
            'action': event['action'],
            'reactions': event['reactions']
        }))
    
    async def message_deleted(self, event):
        # Gửi thông báo tin nhắn đã xóa
        await self.send(text_data=json.dumps({
            'type': 'deleted',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))
    
    async def user_join(self, event):
        # Gửi thông báo có người tham gia
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))
    
    async def user_leave(self, event):
        # Gửi thông báo có người rời đi
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def has_room_access(self):
        try:
            ChatRoom.objects.get(
                id=self.room_id,
                participants=self.user,
                chatroomparticipant__is_accepted=True
            )
            return True
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def is_vanish_mode(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.is_vanish_mode
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, media_url=None, media_type='text', replied_to_id=None):
        room = ChatRoom.objects.get(id=self.room_id)
        
        replied_to = None
        if replied_to_id:
            try:
                replied_to = Message.objects.get(id=replied_to_id, room=room)
            except Message.DoesNotExist:
                pass
        
        message = Message.objects.create(
            room=room,
            sender=self.user,
            content=content,
            media_type=media_type,
            replied_to=replied_to
        )
        
        # Nếu có media_url, cần tải nó và lưu vào model
        # Đây chỉ là code mẫu và cần được triển khai đầy đủ
        if media_url:
            # Implement tải và lưu media
            pass
            
        return message

    @database_sync_to_async
    def mark_message_seen(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            
            # Chỉ đánh dấu là đã đọc nếu người đọc không phải người gửi
            if message.sender.id != self.user.id:
                MessageRead.objects.get_or_create(
                    message=message,
                    user=self.user
                )
                
                # Nếu tất cả người tham gia đã đọc, đánh dấu tin nhắn là đã đọc
                participants_count = message.room.participants.count() - 1  # Trừ người gửi
                read_count = MessageRead.objects.filter(message=message).count()
                
                if read_count >= participants_count:
                    message.is_read = True
                    message.save()
                
                # Vanish mode: tin nhắn sẽ biến mất sau khi đọc
                if message.room.is_vanish_mode:
                    message.is_vanished = True
                    message.save()
                
                return True
        except Message.DoesNotExist:
            pass
        
        return False
    
    @database_sync_to_async
    def toggle_reaction(self, message_id, reaction_type):
        try:
            message = Message.objects.get(id=message_id)
            
            # Kiểm tra xem đã có reaction chưa
            existing_reaction = MessageReaction.objects.filter(
                message=message,
                user=self.user
            ).first()
            
            action = ''
            if existing_reaction:
                # Nếu chọn cùng một reaction, xóa nó
                if existing_reaction.reaction == reaction_type:
                    existing_reaction.delete()
                    action = 'removed'
                else:
                    # Nếu chọn reaction khác, cập nhật
                    existing_reaction.reaction = reaction_type
                    existing_reaction.save()
                    action = 'updated'
            else:
                # Tạo reaction mới
                MessageReaction.objects.create(
                    message=message,
                    user=self.user,
                    reaction=reaction_type
                )
                action = 'added'
            
            # Lấy tất cả reactions
            reactions = MessageReaction.objects.filter(message=message)
            reaction_data = [
                {
                    'id': r.id,
                    'user_id': r.user.id,
                    'username': r.user.username,
                    'reaction': r.reaction,
                    'emoji': dict(MessageReaction.REACTION_TYPES).get(r.reaction, '❤️')
                }
                for r in reactions
            ]
            
            return {
                'action': action,
                'reactions': reaction_data
            }
            
        except Message.DoesNotExist:
            return {
                'action': 'error',
                'reactions': []
            }
    
    @database_sync_to_async
    def delete_message(self, message_id):
        try:
            # Chỉ cho phép xóa tin nhắn của chính mình
            message = Message.objects.get(id=message_id, sender=self.user)
            message.is_deleted = True
            message.content = "Tin nhắn này đã bị xóa"
            message.save()
            
            return {
                'success': True
            }
        except Message.DoesNotExist:
            return {
                'success': False
            } 