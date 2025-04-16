from channels.consumer import SyncConsumer, AsyncConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth.models import User
from chat.models import Message, Thread, UserSetting, Conversation, ConversationMessage, ConversationParticipant
import json
from rich.console import Console
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
console = Console(style='bold green')

online_users = []

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Kiểm tra quyền truy cập vào cuộc trò chuyện
        conversation = await self.get_conversation()
        if not conversation or not await self.check_conversation_access(conversation):
            # Không có quyền truy cập vào cuộc trò chuyện này
            await self.close()
            return
            
        # Thêm người dùng vào nhóm
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Chấp nhận kết nối WebSocket
        await self.accept()
        
        # Cập nhật trạng thái online
        await self.set_user_online(True)
        
        # Thông báo cho tất cả người dùng trong cuộc trò chuyện biết người này online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'status': 'online',
            }
        )
        
        # Lấy lịch sử tin nhắn gần đây và gửi cho người dùng
        messages = await self.get_conversation_messages()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': messages
        }))
    
    async def disconnect(self, close_code):
        # Rời khỏi nhóm room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Cập nhật trạng thái offline
        await self.set_user_online(False)
        
        # Thông báo cho tất cả người dùng trong cuộc trò chuyện biết người này offline
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'status': 'offline',
            }
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', '')
        
        if message_type == 'message':
            # Xử lý tin nhắn văn bản
            message_content = data.get('message', '').strip()
            
            if message_content:
                # Lưu tin nhắn vào database
                message = await self.save_message(message_content)
                
                # Gửi tin nhắn đến nhóm
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': message['id'],
                            'content': message['content'],
                            'sender_id': self.user.id,
                            'sender_username': self.user.username,
                            'created_at': message['created_at'],
                            'has_attachment': message['has_attachment'],
                            'attachment_url': message['attachment_url'] if message['has_attachment'] else None,
                            'attachment_type': message['attachment_type'] if message['has_attachment'] else None,
                            'file_name': message['file_name'] if message['has_attachment'] else None,
                        }
                    }
                )
        elif message_type == 'typing':
            # Xử lý trạng thái đang nhập
            is_typing = data.get('is_typing', False)
            
            # Gửi trạng thái đang nhập đến nhóm
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': is_typing
                }
            )
        elif message_type == 'read':
            # Xử lý đánh dấu đã đọc
            message_id = data.get('message_id')
            
            if message_id:
                await self.mark_message_as_read(message_id)
                
                # Thông báo cho tất cả người dùng rằng tin nhắn đã được đọc
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_read',
                        'message_id': message_id,
                        'read_by': self.user.id
                    }
                )
    
    # Nhận tin nhắn từ room group và gửi đến WebSocket
    async def chat_message(self, event):
        message = event['message']
        
        # Gửi tin nhắn đến WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))
    
    # Xử lý sự kiện user đang nhập
    async def user_typing(self, event):
        # Gửi thông báo đến WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))
    
    # Xử lý sự kiện user thay đổi trạng thái online/offline
    async def user_status(self, event):
        # Gửi thông báo đến WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status']
        }))
    
    # Xử lý sự kiện tin nhắn đã đọc
    async def message_read(self, event):
        # Gửi thông báo đến WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'read_by': event['read_by']
        }))
    
    # Database helper methods
    @database_sync_to_async
    def get_conversation(self):
        try:
            return Conversation.objects.get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def check_conversation_access(self, conversation):
        # Kiểm tra xem người dùng có quyền truy cập vào cuộc trò chuyện không
        return conversation.participants.filter(id=self.user.id).exists()
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        try:
            user_setting = UserSetting.objects.get(user=self.user)
            user_setting.is_online = is_online
            user_setting.save()
            return True
        except UserSetting.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_conversation_messages(self):
        # Lấy 50 tin nhắn gần đây nhất
        messages = ConversationMessage.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-created_at')[:50]
        
        # Chuyển thành danh sách và đảo ngược để hiển thị theo thứ tự thời gian
        messages = list(messages)
        messages.reverse()
        
        # Chuyển đổi các tin nhắn thành định dạng JSON
        result = []
        for msg in messages:
            has_attachment = bool(msg.image or msg.video or msg.document)
            attachment_type = None
            attachment_url = None
            
            if msg.image:
                attachment_type = 'image'
                attachment_url = msg.image.url
            elif msg.video:
                attachment_type = 'video'
                attachment_url = msg.video.url
            elif msg.document:
                attachment_type = 'document'
                attachment_url = msg.document.url
            
            result.append({
                'id': msg.id,
                'content': msg.content,
                'sender_id': msg.sender.id,
                'sender_username': msg.sender.username,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
                'has_attachment': has_attachment,
                'attachment_type': attachment_type,
                'attachment_url': attachment_url,
                'file_name': msg.file_name,
            })
        
        return result
    
    @database_sync_to_async
    def save_message(self, content):
        # Lưu tin nhắn mới vào database
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = ConversationMessage.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            text=content
        )
        
        # Cập nhật thời gian tin nhắn cuối cùng
        conversation.last_message_time = timezone.now()
        conversation.save()
        
        # Trả về thông tin tin nhắn đã lưu
        has_attachment = bool(message.image or message.video or message.document)
        attachment_type = None
        attachment_url = None
        
        if message.image:
            attachment_type = 'image'
            attachment_url = message.image.url
        elif message.video:
            attachment_type = 'video'
            attachment_url = message.video.url
        elif message.document:
            attachment_type = 'document'
            attachment_url = message.document.url
            
        return {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'has_attachment': has_attachment,
            'attachment_type': attachment_type,
            'attachment_url': attachment_url,
            'file_name': message.file_name,
        }
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            message = ConversationMessage.objects.get(id=message_id)
            if self.user != message.sender:
                message.is_read = True
                message.isread = True
                message.save()
            return True
        except ConversationMessage.DoesNotExist:
            return False


class WebConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.me = self.scope['user']
        self.room_name = str(self.me.id)
        
        online_users.append(self.me.id)
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.send({
            'type': 'websocket.accept',
        })

        console.print(f'You are connected {self.room_name}')

    async def websocket_receive(self, event):
        event = json.loads(event['text'])
        # console.print(f'Received message: {event["type"]}')

        if event['type'] == 'message':
            # Xử lý cho cả Thread và Conversation
            msg = await self.send_msg(event)
            await self.send_users(msg, [self.me.id, self.them_user.id])
        elif event['type'] == 'online':
            msg = await self.send_online(event)
            console.print(online_users)
            await self.send_users(msg, [])
        elif event['type'] == 'read':
            # Xử lý đánh dấu đã đọc cho Thread
            if 'thread_id' in event:
                msg = await sync_to_async(Message.objects.get)(id=event['id'])
                msg.isread = True
                msg.is_read = True
                await sync_to_async(msg.save)()
                
                msg_thread = await sync_to_async(Thread.objects.get)(message=msg)
                await self.unread(msg_thread, int(event['user']), -1)
            # Xử lý đánh dấu đã đọc cho Conversation
            elif 'conversation_id' in event:
                msg = await sync_to_async(ConversationMessage.objects.get)(id=event['id'])
                await sync_to_async(msg.mark_as_read)(self.me)
        elif event['type'] == 'istyping':
            console.print(self.me, event)
            await self.send_istyping(event)

    async def websocket_message(self, event):
        await self.send(
            {
                'type': 'websocket.send',
                'text': event.get('text'),
            }
        )

    async def websocket_disconnect(self, event):
        console.print(f'[{self.channel_name}] - Disconnected')

        event = json.loads('''{
            "type": "online",
            "set": "false"
        }''')

        online_users.remove(self.me.id)
        msg = await self.send_online(event)
        await self.send_users(msg, [])

        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def send_msg(self, msg):
        them_id = msg['to']
        self.them_user = await sync_to_async(User.objects.get)(id=them_id)
        
        # Xử lý gửi tin nhắn cho mô hình Thread
        self.thread = await sync_to_async(Thread.objects.get_or_create_thread)(self.me, self.them_user)
        await self.store_message_thread(msg['message'])
        await self.unread(self.thread, self.me.id, 1)
        
        # Xử lý gửi tin nhắn cho mô hình Conversation
        # Tìm hoặc tạo cuộc trò chuyện
        conversation = await self.get_or_create_conversation(self.me, self.them_user)
        await self.store_message_conversation(conversation, msg['message'])

        await self.send_notifi([self.me.id, self.them_user.id])
        return json.dumps({
            'type': 'message',
            'sender': them_id,
        })

    @database_sync_to_async
    def store_message_thread(self, text):
        Message.objects.create(
            thread = self.thread,
            sender = self.scope['user'],
            text = text,
            content = text,
        )
        
    @database_sync_to_async
    def get_or_create_conversation(self, user1, user2):
        # Tìm cuộc trò chuyện hiện có
        conversations = Conversation.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        )
        
        if conversations.exists():
            return conversations.first()
        
        # Tạo cuộc trò chuyện mới
        conversation = Conversation.objects.create()
        ConversationParticipant.objects.create(conversation=conversation, user=user1)
        ConversationParticipant.objects.create(conversation=conversation, user=user2)
        return conversation
        
    @database_sync_to_async
    def store_message_conversation(self, conversation, content):
        ConversationMessage.objects.create(
            conversation = conversation,
            sender = self.scope['user'],
            content = content,
            text = content,
        )
        # Cập nhật thời gian tin nhắn cuối cùng
        from django.utils import timezone
        conversation.last_message_time = timezone.now()
        conversation.save()

    async def send_users(self, msg, users=[]):
        if not users: users = online_users

        for user in users:
            await self.channel_layer.group_send(
                str(user),
                {
                    'type': 'websocket.message',
                    'text': msg,
                },
            )

    async def send_online(self, event):
        user = self.scope['user']
        await self.store_is_online(user, event['set'])
        return json.dumps({
            'type': 'online',
            'set': event['set'],
            'user': user.id
        })

    async def store_is_online(self, user, value):
        if value == 'true': value = True
        else: value = False

        settings = await sync_to_async(UserSetting.objects.get)(id=user.id)
        settings.is_online = value
        await sync_to_async(settings.save)()
    
    async def send_notifi(self, users):
        console.print(f'NOTIFI {users}')

        for i in range(len(users)):
            text = json.dumps({
                'type': 'notifi',
                'user': users[i-1],
                'sender': users[0]
            })

            await self.channel_layer.group_send(
                str(users[i]),
                {
                    'type': 'websocket.message',
                    'text': text,
                },
            )

    async def unread(self, thread, user, plus):
        users = await sync_to_async(thread.users.first)()
        
        if(users.id != int(user)): 
            thread.unread_by_1 += plus
        else: 
            thread.unread_by_2 += plus
        
        await sync_to_async(thread.save)()

    async def send_istyping(self, event):
        text = json.dumps({
            'type': 'istyping',
            'set': event['set'],
        })

        await self.channel_layer.group_send(
            str(event['user']),
            {
                'type': 'websocket.message',
                'text': text,
            },
        )