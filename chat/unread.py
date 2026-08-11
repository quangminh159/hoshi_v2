from django.db.models import Count, Q
from .models import ConversationMessage


def get_unread_message_count(user):
    """Số tin nhắn chưa đọc gửi tới user (không tính tin mình gửi)."""
    if not user or not user.is_authenticated:
        return 0
    return (
        ConversationMessage.objects.filter(
            conversation__participants=user,
            is_read=False,
        )
        .exclude(sender=user)
        .count()
    )


def get_conversation_unread_counts(user, conversation_ids=None):
    """Trả về dict {conversation_id: unread_count}."""
    if not user or not user.is_authenticated:
        return {}
    qs = (
        ConversationMessage.objects.filter(
            conversation__participants=user,
            is_read=False,
        )
        .exclude(sender=user)
    )
    if conversation_ids is not None:
        qs = qs.filter(conversation_id__in=conversation_ids)
    rows = qs.values('conversation_id').annotate(c=Count('id'))
    return {row['conversation_id']: row['c'] for row in rows}


def mark_conversation_messages_read(conversation, user):
    """
    Đánh dấu đã đọc mọi tin nhắn từ người khác trong cuộc trò chuyện.
    Trả về list id tin vừa được đánh dấu (để broadcast realtime).
    """
    if not user or not user.is_authenticated:
        return []
    qs = ConversationMessage.objects.filter(
        conversation=conversation,
        is_read=False,
    ).exclude(sender=user)
    ids = list(qs.values_list('id', flat=True))
    if not ids:
        return []
    qs.update(is_read=True, isread=True)
    return ids
