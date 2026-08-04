"""Tiện ích cuộc trò chuyện — tạo DM, gửi tin, broadcast."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from accounts.models import UserBlock
from chat.message_utils import serialize_chat_message
from chat.models import Conversation, ConversationMessage, ConversationParticipant


def users_are_blocked(user_a, user_b):
    if not user_a or not user_b:
        return True
    return UserBlock.objects.filter(
        blocker=user_a, blocked=user_b
    ).exists() or UserBlock.objects.filter(
        blocker=user_b, blocked=user_a
    ).exists()


def get_or_create_direct_conversation(user, recipient):
    """Tìm hoặc tạo cuộc trò chuyện 1-1 giữa hai người dùng."""
    conversation = Conversation.objects.filter(
        participants=user
    ).filter(
        participants=recipient
    ).first()

    if conversation:
        return conversation

    conversation = Conversation.objects.create()
    ConversationParticipant.objects.create(conversation=conversation, user=user)
    ConversationParticipant.objects.create(conversation=conversation, user=recipient)
    return conversation


def send_conversation_message(user, conversation, content='', shared_post=None):
    """Tạo tin nhắn, cập nhật conversation và broadcast qua WebSocket."""
    message = ConversationMessage.objects.create(
        conversation=conversation,
        sender=user,
        content=(content or '').strip(),
        shared_post=shared_post,
    )
    message = ConversationMessage.objects.select_related(
        'sender', 'reply_to', 'reply_to__sender', 'shared_post', 'shared_post__author'
    ).prefetch_related('shared_post__media').get(pk=message.pk)

    conversation.last_message_time = timezone.now()
    conversation.save(update_fields=['last_message_time'])

    payload = serialize_chat_message(message, user)
    broadcast_chat_message(conversation.id, payload)
    return message, payload


def broadcast_chat_message(conversation_id, message_data):
    """Gửi tin nhắn realtime tới phòng chat + inbox của từng người tham gia."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {'type': 'chat_message', 'message': message_data},
        )
    except Exception:
        pass

    try:
        conversation = (
            Conversation.objects.filter(id=conversation_id)
            .prefetch_related('participants')
            .first()
        )
        if not conversation:
            return

        participants = list(conversation.participants.all())
        for participant in participants:
            other = next((u for u in participants if u.id != participant.id), None)
            other_payload = None
            if other:
                other_payload = {
                    'id': other.id,
                    'username': other.username,
                    'avatar_url': other.get_avatar_url(),
                }
            async_to_sync(channel_layer.group_send)(
                f'chat_inbox_{participant.id}',
                {
                    'type': 'inbox_message',
                    'conversation_id': int(conversation_id),
                    'message': message_data,
                    'other_user': other_payload,
                },
            )
    except Exception:
        pass
