from channels.consumer import SyncConsumer, AsyncConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth.models import User
from chat.models import Message, Thread, UserSetting, Conversation, ConversationMessage, ConversationParticipant
from chat.message_utils import serialize_chat_message
import json
from rich.console import Console
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
import os
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

        other_id = await self.get_dm_other_user_id()
        self._presence_other_id = other_id

        # Theo dõi presence của đối phương (DM)
        if other_id:
            await self.channel_layer.group_add(
                f'user_presence_{other_id}',
                self.channel_name,
            )

        # Cập nhật trạng thái online + báo realtime
        await self.mark_self_online(notify_inbox_ids=[other_id] if other_id else None)

        # Thông báo trong phòng chat
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

        # Mở chat → đánh dấu đã đọc + báo realtime cho người gửi (Đã xem)
        read_ids = await self.mark_conversation_as_read()
        if read_ids:
            await self.broadcast_messages_read(read_ids)

        other_presence = await self.get_other_participant_presence()
        if other_presence and other_presence.get('user_id'):
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': other_presence['user_id'],
                'status': 'online' if other_presence['is_online'] else 'offline',
                'last_seen': other_presence.get('last_seen'),
            }))
    
    async def disconnect(self, close_code):
        other_id = getattr(self, '_presence_other_id', None)

        # Rời khỏi nhóm room
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        if other_id:
            await self.channel_layer.group_discard(
                f'user_presence_{other_id}',
                self.channel_name,
            )

        # Offline chỉ khi không còn socket khác (inbox/chat)
        info = await self.mark_self_offline(notify_inbox_ids=[other_id] if other_id else None)
        last_seen = (info or {}).get('last_seen')
        still_online = bool((info or {}).get('is_online'))

        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'status': 'online' if still_online else 'offline',
                    'last_seen': last_seen,
                }
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', '')
        
        if message_type == 'message':
            # Xử lý tin nhắn văn bản
            message_content = data.get('message', '').strip()
            reply_to = data.get('reply_to', None)
            
            if message_content:
                # Lưu tin nhắn vào database
                message = await self.save_message(message_content, reply_to)
                if not message:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Không thể gửi tin nhắn tới người nhận này.',
                    }))
                    return
                if message.get('error'):
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': message['error'],
                    }))
                    return
                payload = message['payload']
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': payload,
                    }
                )
                await self.notify_inboxes(payload)
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
                ok = await self.mark_message_as_read(message_id)
                
                if ok:
                    await self.broadcast_messages_read([message_id])
        elif message_type == 'delete_message':
            message_id = data.get('message_id')
            mode = (data.get('mode') or 'me').strip().lower()
            if mode not in ('me', 'everyone'):
                mode = 'me'

            if message_id:
                result = await self.delete_message(message_id, mode=mode)

                if not result or not result.get('ok'):
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': (result or {}).get('error') or 'Không thể xóa tin nhắn.',
                    }))
                elif result.get('scope') == 'me':
                    await self.send(text_data=json.dumps({
                        'type': 'message_deleted',
                        'message_id': message_id,
                        'deleted_by': self.user.id,
                        'scope': 'me',
                    }))
                else:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'message_deleted',
                            'message_id': message_id,
                            'deleted_by': self.user.id,
                            'scope': 'everyone',
                        }
                    )
        elif message_type in (
            'call_invite',
            'call_accept',
            'call_reject',
            'call_end',
            'call_busy',
            'call_offer',
            'call_answer',
            'call_ice',
            'call_mode',
        ):
            await self.handle_call_signal(message_type, data)
    
    async def handle_call_signal(self, signal_type, data):
        """Relay WebRTC call signaling for DM 1-1 only."""
        meta = await self.get_dm_call_meta()
        if not meta:
            await self.send(text_data=json.dumps({
                'type': 'call_error',
                'message': 'Chỉ hỗ trợ gọi trong chat 1-1.',
            }))
            return

        if meta.get('is_blocked'):
            await self.send(text_data=json.dumps({
                'type': 'call_error',
                'message': 'Không thể gọi vì một trong hai bên đã chặn.',
            }))
            return

        other_id = meta['other_user_id']
        from_user = {
            'id': self.user.id,
            'username': self.user.username,
            'avatar_url': meta['self_avatar'],
        }
        payload = {
            'type': 'call_event',
            'signal': signal_type,
            'conversation_id': int(self.conversation_id),
            'call_id': data.get('call_id'),
            'call_mode': data.get('call_mode') or 'voice',
            'from_user': from_user,
            'sdp': data.get('sdp'),
            'candidate': data.get('candidate'),
            'reason': data.get('reason'),
            'duration': data.get('duration'),
        }

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'call_event',
                'payload': payload,
                'exclude_user_id': self.user.id,
            },
        )

        # Reo chuông / trạng thái cuộc gọi qua inbox khi đang ngoài trang chat
        if signal_type in ('call_invite', 'call_accept', 'call_reject', 'call_end', 'call_busy'):
            await self.channel_layer.group_send(
                f'chat_inbox_{other_id}',
                {
                    'type': 'inbox_call',
                    'payload': payload,
                },
            )

        if signal_type == 'call_end' and data.get('write_system'):
            await self.write_call_system_message(data)

    async def call_event(self, event):
        if event.get('exclude_user_id') == getattr(self.user, 'id', None):
            return
        await self.send(text_data=json.dumps(event.get('payload') or {}))

    @database_sync_to_async
    def get_dm_call_meta(self):
        from chat.conversation_utils import users_are_blocked

        try:
            conversation = (
                Conversation.objects.prefetch_related('participants')
                .get(id=self.conversation_id)
            )
        except Conversation.DoesNotExist:
            return None
        if conversation.is_group:
            return None
        if not conversation.participants.filter(id=self.user.id).exists():
            return None
        other = conversation.get_other_participant(self.user)
        if not other:
            return None
        avatar = '/static/img/default-avatar.png'
        if hasattr(self.user, 'get_avatar_url'):
            avatar = self.user.get_avatar_url()
        return {
            'other_user_id': other.id,
            'other_username': other.username,
            'self_avatar': avatar,
            'is_blocked': users_are_blocked(self.user, other),
        }

    @database_sync_to_async
    def write_call_system_message(self, data):
        from chat.conversation_utils import create_system_message

        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            return None
        if conversation.is_group:
            return None

        mode = data.get('call_mode') or 'voice'
        reason = data.get('reason') or 'ended'
        duration = int(data.get('duration') or 0)
        label = 'Cuộc gọi video' if mode == 'video' else 'Cuộc gọi thoại'

        if reason in ('reject', 'timeout', 'missed', 'cancel', 'busy'):
            text = f'{label} nhỡ'
        elif duration > 0:
            mins = duration // 60
            secs = duration % 60
            text = f'{label} · {mins}:{secs:02d}'
        else:
            text = f'{label} đã kết thúc'

        return create_system_message(conversation, self.user, text)
    
    # Nhận tin nhắn từ room group và gửi đến WebSocket
    async def chat_message(self, event):
        message = event['message']
        
        # Gửi tin nhắn đến WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    async def message_request_accepted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_request_accepted',
            'conversation_id': event.get('conversation_id'),
            'accepted_by': event.get('accepted_by') or {},
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
        payload = {
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status'],
        }
        if event.get('last_seen'):
            payload['last_seen'] = event['last_seen']
        await self.send(text_data=json.dumps(payload))

    async def user_presence(self, event):
        """Presence từ group user_presence_{id} (đối phương online/offline ngoài phòng)."""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event.get('user_id'),
            'status': event.get('status'),
            'last_seen': event.get('last_seen'),
        }))
    
    # Xử lý sự kiện tin nhắn đã đọc
    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'read_by': event['read_by'],
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'message_ids': event.get('message_ids') or [],
            'read_by': event.get('read_by'),
        }))
    
    # Xử lý sự kiện tin nhắn đã bị xóa
    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
            'scope': event.get('scope') or 'everyone',
        }))
    
    # Database helper methods
    async def notify_inboxes(self, payload):
        """Đẩy tin nhắn tới inbox realtime của từng người trong cuộc trò chuyện."""
        rows = await self.get_inbox_targets()
        for row in rows:
            await self.channel_layer.group_send(
                f'chat_inbox_{row["user_id"]}',
                {
                    'type': 'inbox_message',
                    'conversation_id': int(self.conversation_id),
                    'message': payload,
                    'other_user': row.get('other_user'),
                    'conversation': row.get('conversation'),
                },
            )

    @database_sync_to_async
    def get_inbox_targets(self):
        from chat.conversation_utils import conversation_inbox_payload

        try:
            conversation = (
                Conversation.objects.prefetch_related('participants')
                .select_related('created_by')
                .get(id=self.conversation_id)
            )
        except Conversation.DoesNotExist:
            return []
        participants = list(conversation.participants.all())
        rows = []
        for participant in participants:
            other = next((u for u in participants if u.id != participant.id), None)
            other_payload = None
            if other and not conversation.is_group:
                other_payload = {
                    'id': other.id,
                    'username': other.username,
                    'avatar_url': other.get_avatar_url(),
                }
            rows.append({
                'user_id': participant.id,
                'other_user': other_payload,
                'conversation': conversation_inbox_payload(conversation, participant),
            })
        return rows

    @database_sync_to_async
    def get_participant_ids(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return list(conversation.participants.values_list('id', flat=True))
        except Conversation.DoesNotExist:
            return []

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
    def get_dm_other_user_id(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            return None
        if conversation.is_group:
            return None
        other = conversation.participants.exclude(id=self.user.id).first()
        return other.id if other else None

    @database_sync_to_async
    def mark_self_online(self, notify_inbox_ids=None):
        from chat.presence import mark_user_online
        return mark_user_online(self.user, notify_inbox_ids=notify_inbox_ids or [])

    @database_sync_to_async
    def mark_self_offline(self, notify_inbox_ids=None):
        from chat.presence import mark_user_offline
        return mark_user_offline(self.user, notify_inbox_ids=notify_inbox_ids or [])

    @database_sync_to_async
    def set_user_online(self, is_online):
        """Giữ tương thích cũ — ưu tiên dùng mark_self_online/offline."""
        from chat.presence import mark_user_offline, mark_user_online
        if is_online:
            info = mark_user_online(self.user)
            return (info or {}).get('last_seen')
        info = mark_user_offline(self.user, force=True)
        return (info or {}).get('last_seen')

    @database_sync_to_async
    def get_other_participant_presence(self):
        from chat.presence import get_user_presence

        conversation = Conversation.objects.get(id=self.conversation_id)
        if conversation.is_group:
            return {
                'user_id': None,
                'is_online': False,
                'last_seen': None,
                'is_group': True,
                'member_count': conversation.participants.count(),
            }
        other = conversation.participants.exclude(id=self.user.id).first()
        if not other:
            return None

        presence = get_user_presence(other)
        if getattr(other, 'hide_activity', False):
            presence = {
                'is_online': False,
                'last_seen': None,
                'hidden': True,
            }
        presence['user_id'] = other.id
        if presence.get('last_seen'):
            presence['last_seen'] = presence['last_seen'].isoformat()
        return presence
    
    @database_sync_to_async
    def get_conversation_messages(self):
        # Lấy 50 tin nhắn gần đây nhất (bỏ tin đã xóa phía mình)
        messages = ConversationMessage.objects.filter(
            conversation_id=self.conversation_id
        ).exclude(
            hidden_for=self.user
        ).select_related(
            'sender', 'reply_to', 'reply_to__sender',
            'shared_post', 'shared_post__author',
        ).prefetch_related('shared_post__media').order_by('-created_at')[:50]
        
        messages = list(messages)
        messages.reverse()
        
        return [serialize_chat_message(msg) for msg in messages]
    
    @database_sync_to_async
    def save_message(self, content, reply_to=None):
        from chat.conversation_utils import (
            accept_message_request,
            can_send_in_message_request,
            is_pending_message_request_for,
            unhide_conversation_participants,
        )

        conversation = Conversation.objects.get(id=self.conversation_id)

        if not conversation.is_group:
            other = conversation.get_other_participant(self.user)
            if is_pending_message_request_for(conversation, self.user):
                accept_message_request(conversation, self.user)
                conversation.refresh_from_db()
            elif other and not other.can_receive_message_from(self.user):
                if not (
                    conversation.is_message_request
                    and conversation.created_by_id == self.user.id
                ):
                    return None

        ok, err = can_send_in_message_request(conversation, self.user)
        if not ok:
            return {'error': err}

        reply_parent = None
        if reply_to and reply_to.get('id'):
            try:
                reply_parent = ConversationMessage.objects.select_related('sender').get(
                    id=reply_to['id'],
                    conversation_id=self.conversation_id,
                )
            except ConversationMessage.DoesNotExist:
                reply_parent = None

        # Tin mới → hiện lại cho người từng ẩn cuộc trò chuyện
        unhide_conversation_participants(conversation)

        message = ConversationMessage.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            text=content,
            reply_to=reply_parent,
        )

        message = ConversationMessage.objects.select_related(
            'sender', 'reply_to', 'reply_to__sender',
            'shared_post', 'shared_post__author',
        ).prefetch_related('shared_post__media').get(pk=message.pk)

        conversation.last_message_time = timezone.now()
        conversation.save()

        payload = serialize_chat_message(message)
        return {'payload': payload}
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        try:
            message = ConversationMessage.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
            )
            if self.user != message.sender and not message.is_read:
                message.is_read = True
                message.isread = True
                message.save(update_fields=['is_read', 'isread'])
                return True
            return False
        except ConversationMessage.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_conversation_as_read(self):
        from chat.unread import mark_conversation_messages_read
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            return []
        return mark_conversation_messages_read(conversation, self.user)

    async def broadcast_messages_read(self, message_ids):
        from asgiref.sync import sync_to_async
        from chat.conversation_utils import broadcast_messages_read

        await sync_to_async(broadcast_messages_read)(
            self.conversation_id,
            message_ids,
            self.user.id,
        )

    @database_sync_to_async
    def delete_message(self, message_id, mode='me'):
        """
        Xóa tin nhắn.
        mode='me' — chỉ ẩn phía người gửi yêu cầu.
        mode='everyone' — thu hồi cả hai bên (chỉ người gửi tin).
        """
        try:
            message = ConversationMessage.objects.select_related('sender', 'conversation').get(
                id=message_id,
                conversation_id=self.conversation_id,
            )
        except ConversationMessage.DoesNotExist:
            return {'ok': False, 'error': 'Không tìm thấy tin nhắn.'}

        if not message.conversation.participants.filter(id=self.user.id).exists():
            return {'ok': False, 'error': 'Không có quyền.'}

        if message.is_system:
            return {'ok': False, 'error': 'Không thể xóa tin hệ thống.'}

        if message.is_deleted_for_everyone:
            # Đã thu hồi — vẫn cho xóa phía mình
            if mode == 'me':
                message.hidden_for.add(self.user)
                return {'ok': True, 'scope': 'me'}
            return {'ok': False, 'error': 'Tin nhắn đã được thu hồi.'}

        if mode == 'everyone':
            if not message.sender_id or message.sender_id != self.user.id:
                return {'ok': False, 'error': 'Chỉ người gửi mới thu hồi được tin nhắn.'}
            message.clear_attachments()
            message.content = ''
            message.text = ''
            message.shared_post = None
            message.reply_to = None
            message.is_deleted_for_everyone = True
            message.deleted_for_everyone_at = timezone.now()
            message.save()
            return {'ok': True, 'scope': 'everyone'}

        # Xóa chỉ phía mình — cho phép với tin mình gửi (UI hiện tại)
        if not message.sender_id or message.sender_id != self.user.id:
            return {'ok': False, 'error': 'Chỉ có thể xóa tin nhắn của bạn.'}
        message.hidden_for.add(self.user)
        return {'ok': True, 'scope': 'me'}


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
        from chat.conversation_utils import get_or_create_direct_conversation
        return get_or_create_direct_conversation(user1, user2)
        
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

class ChatInboxConsumer(AsyncWebsocketConsumer):
    """Realtime inbox socket for conversation list page + global presence."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'chat_inbox_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Presence toàn site: mở app → online
        await self.mark_inbox_online()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if getattr(self, 'user', None) and self.user.is_authenticated:
            await self.mark_inbox_offline()

    @database_sync_to_async
    def mark_inbox_online(self):
        from chat.presence import mark_user_online
        return mark_user_online(self.user)

    @database_sync_to_async
    def mark_inbox_offline(self):
        from chat.presence import mark_user_offline
        return mark_user_offline(self.user)

    async def inbox_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'inbox_message',
            'conversation_id': event.get('conversation_id'),
            'message': event.get('message'),
            'other_user': event.get('other_user'),
            'conversation': event.get('conversation'),
        }))

    async def inbox_message_request_accepted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_request_accepted',
            'conversation_id': event.get('conversation_id'),
            'accepted_by': event.get('accepted_by') or {},
            'other_user': event.get('other_user'),
            'conversation': event.get('conversation'),
        }))

    async def inbox_messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'conversation_id': event.get('conversation_id'),
            'message_ids': event.get('message_ids') or [],
            'read_by': event.get('read_by'),
        }))

    async def inbox_user_presence(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event.get('user_id'),
            'status': event.get('status'),
            'last_seen': event.get('last_seen'),
        }))

    async def inbox_call(self, event):
        payload = event.get('payload') or {}
        await self.send(text_data=json.dumps(payload))
