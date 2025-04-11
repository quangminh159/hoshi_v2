import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Conversation, Message, MessageRead, ConversationParticipant

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            # Từ chối kết nối nếu người dùng chưa đăng nhập
            await self.close()
            return
            
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        
        # Kiểm tra xem người dùng có quyền tham gia cuộc trò chuyện này không
        is_participant = await self.is_conversation_participant(self.conversation_id, self.user.id)
        if not is_participant:
            # Từ chối kết nối nếu người dùng không phải là thành viên
            await self.close()
            return
        
        # Tham gia group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        # Chấp nhận kết nối WebSocket
        await self.accept()
        
        # Cập nhật trạng thái online
        await self.update_user_status(True)
        
        # Gửi thông báo người dùng đang online
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'status': 'online',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Đánh dấu đã đọc tin nhắn cũ
        await self.mark_messages_as_read()
    
    async def disconnect(self, close_code):
        # Kiểm tra xem conversation_group_name có tồn tại không
        if not hasattr(self, 'conversation_group_name'):
            # Nếu không có thuộc tính này, có thể kết nối đã bị từ chối trước đó
            return
            
        # Cập nhật trạng thái offline
        await self.update_user_status(False)
        
        # Gửi thông báo người dùng offline
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'status': 'offline',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Rời khỏi nhóm
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Xử lý tin nhắn nhận được từ WebSocket
        """
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        print(f"Received message: {text_data_json}")  # Thêm log để debug
        
        if message_type == 'message':
            message_content = text_data_json['message']
            attachment_url = text_data_json.get('attachment_url', None)
            
            # Lưu tin nhắn vào CSDL
            message = await self.save_message(message_content, attachment_url)
            
            # Gửi tin nhắn đến tất cả người dùng trong nhóm
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'sender_id': self.user.id,
                        'sender_username': self.user.username,
                        'sender_avatar': self.user.get_avatar_url(),
                        'content': message_content,
                        'attachment_url': attachment_url,
                        'timestamp': message.created_at.isoformat(),
                        'is_read': False
                    }
                }
            )
        elif message_type == 'typing':
            # Gửi thông báo người dùng đang nhập tin nhắn
            is_typing = text_data_json.get('is_typing', False)
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'user_typing',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': is_typing
                }
            )
        elif message_type == 'read_receipt':
            # Đánh dấu tin nhắn đã đọc
            message_id = text_data_json['message_id']
            await self.mark_message_read(message_id)
            
            # Gửi thông báo tin nhắn đã đọc
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'user_id': self.user.id,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def chat_message(self, event):
        """
        Gửi tin nhắn đến WebSocket
        """
        message = event['message']
        
        # Kiểm tra nếu người dùng là người gửi thì đánh dấu đã đọc
        if message['sender_id'] == self.user.id:
            message['is_read'] = True
        
        # Gửi tin nhắn đến WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))
    
    async def user_typing(self, event):
        """
        Gửi thông báo người dùng đang nhập tin nhắn đến WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))
    
    async def message_read(self, event):
        """
        Gửi thông báo tin nhắn đã đọc
        """
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))
    
    async def user_status(self, event):
        """
        Gửi trạng thái người dùng đến WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def is_conversation_participant(self, conversation_id, user_id):
        """
        Kiểm tra xem người dùng có phải là thành viên của cuộc trò chuyện
        """
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            user_id=user_id,
            left_at__isnull=True
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content, attachment_url=None):
        """
        Lưu tin nhắn vào CSDL
        """
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            attachment=attachment_url
        )
        
        # Đánh dấu là đã đọc đối với người gửi
        MessageRead.objects.create(
            message=message,
            user=self.user
        )
        
        # Cập nhật thời gian cập nhật của cuộc trò chuyện
        conversation.updated_at = timezone.now()
        conversation.save()
        
        return message
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """
        Đánh dấu một tin nhắn đã đọc
        """
        message = Message.objects.get(id=message_id)
        MessageRead.objects.get_or_create(
            message=message,
            user=self.user
        )
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        """
        Đánh dấu tất cả tin nhắn chưa đọc trong cuộc trò chuyện là đã đọc
        """
        conversation = Conversation.objects.get(id=self.conversation_id)
        unread_messages = Message.objects.filter(
            conversation=conversation
        ).exclude(
            read_receipts__user=self.user
        )
        
        for message in unread_messages:
            MessageRead.objects.get_or_create(
                message=message,
                user=self.user
            )
    
    @database_sync_to_async
    def update_user_status(self, is_online):
        """
        Cập nhật trạng thái online/offline của người dùng
        """
        # Cập nhật trạng thái với Redis (nếu cần)
        # Ví dụ: sử dụng Django-Redis để lưu trạng thái
        pass 