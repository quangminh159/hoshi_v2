"""Tiện ích cuộc trò chuyện — tạo DM/nhóm, gửi tin, broadcast."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserBlock
from chat.message_utils import serialize_chat_message
from chat.models import Conversation, ConversationMessage, ConversationParticipant

User = get_user_model()


def users_are_blocked(user_a, user_b):
    if not user_a or not user_b:
        return True
    return UserBlock.objects.filter(
        blocker=user_a, blocked=user_b
    ).exists() or UserBlock.objects.filter(
        blocker=user_b, blocked=user_a
    ).exists()


def find_direct_conversation(user, recipient):
    """Tìm DM 1-1 (không phải nhóm) giữa hai người — tái sử dụng hội thoại cũ."""
    from django.db.models import Count

    if not user or not recipient or user.id == recipient.id:
        return None

    # Dùng distinct=True để tránh Count bị nhân do JOIN M2M (filter 2 participants).
    return (
        Conversation.objects.filter(is_group=False)
        .filter(participants=user)
        .filter(participants=recipient)
        .annotate(member_count=Count('participants', distinct=True))
        .filter(member_count=2)
        .order_by('-last_message_time', '-id')
        .first()
    )


def get_direct_conversation_for_share(user, recipient, conversation_id=None):
    """
    Lấy hội thoại 1-1 để gửi tin chia sẻ.
    Ưu tiên conversation_id hợp lệ (đã có sẵn), không thì tìm DM cũ,
    chỉ tạo mới khi chưa từng chat với người đó.
    """
    from django.db.models import Count

    if conversation_id:
        try:
            cid = int(conversation_id)
        except (TypeError, ValueError):
            cid = None
        if cid:
            conversation = (
                Conversation.objects.filter(pk=cid, is_group=False)
                .annotate(member_count=Count('participants', distinct=True))
                .filter(member_count=2, participants=user)
                .filter(participants=recipient)
                .first()
            )
            if conversation:
                return conversation

    return get_or_create_direct_conversation(user, recipient)


def get_or_create_direct_conversation(user, recipient):
    """Tìm hoặc tạo cuộc trò chuyện 1-1 giữa hai người dùng."""
    conversation = find_direct_conversation(user, recipient)
    if conversation:
        return conversation

    conversation = Conversation.objects.create(is_group=False, created_by=user)
    ConversationParticipant.objects.create(conversation=conversation, user=user)
    ConversationParticipant.objects.create(conversation=conversation, user=recipient)
    return conversation


def create_group_conversation(creator, member_users, name=''):
    """Tạo nhóm chat với creator + danh sách thành viên."""
    members = []
    seen = {creator.id}
    members.append(creator)
    for u in member_users:
        if not u or u.id in seen:
            continue
        if users_are_blocked(creator, u):
            continue
        seen.add(u.id)
        members.append(u)

    if len(members) < 2:
        raise ValueError('Nhóm cần ít nhất 2 người (bạn và một người khác).')

    title = (name or '').strip()
    if not title:
        title = 'Nhóm của ' + ', '.join(m.username for m in members[:3])
        if len(members) > 3:
            title += f' +{len(members) - 3}'

    conversation = Conversation.objects.create(
        is_group=True,
        name=title[:120],
        created_by=creator,
    )
    for member in members:
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=member,
            is_admin=(member.id == creator.id),
        )
    return conversation


def create_system_message(conversation, actor, content):
    """Tạo tin hệ thống trong nhóm và broadcast realtime."""
    text = (content or '').strip()
    if not conversation or not text:
        return None

    message = ConversationMessage.objects.create(
        conversation=conversation,
        sender=actor,
        content=text,
        text=text,
        is_system=True,
        is_read=False,
        isread=False,
    )
    conversation.last_message_time = timezone.now()
    conversation.save(update_fields=['last_message_time'])

    payload = serialize_chat_message(message)
    broadcast_chat_message(conversation.id, payload)
    return message


def ensure_group_has_admin(conversation):
    """Nếu không còn admin, phong admin cho thành viên còn lại (ưu tiên created_by)."""
    if not conversation or not conversation.is_group:
        return
    if conversation.conversation_participants.filter(is_admin=True).exists():
        return
    remaining = conversation.conversation_participants.select_related('user')
    if not remaining.exists():
        return
    pick = None
    if conversation.created_by_id:
        pick = remaining.filter(user_id=conversation.created_by_id).first()
    if not pick:
        pick = remaining.first()
    if pick:
        pick.is_admin = True
        pick.save(update_fields=['is_admin'])
        if conversation.created_by_id != pick.user_id:
            conversation.created_by = pick.user
            conversation.save(update_fields=['created_by'])


def conversation_inbox_payload(conversation, viewer):
    """Metadata hiển thị trên danh sách inbox cho một viewer."""
    return {
        'id': conversation.id,
        'is_group': bool(conversation.is_group),
        'title': conversation.get_display_title(viewer),
        'avatar_url': conversation.get_display_avatar_url(viewer),
        'member_count': conversation.get_member_count() if conversation.is_group else 2,
    }


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
            .select_related('created_by')
            .first()
        )
        if not conversation:
            return

        participants = list(conversation.participants.all())
        for participant in participants:
            other = next((u for u in participants if u.id != participant.id), None)
            other_payload = None
            if other and not conversation.is_group:
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
                    'conversation': conversation_inbox_payload(conversation, participant),
                },
            )
    except Exception:
        pass
