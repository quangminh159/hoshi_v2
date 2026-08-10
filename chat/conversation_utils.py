"""Tiện ích cuộc trò chuyện — tạo DM/nhóm, gửi tin, broadcast."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
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


def _direct_conversation_qs(user, recipient):
    """Query DM 1-1 giữa hai user (có thể nhiều bản trùng do race/bug cũ)."""
    # Không annotate Count trên cùng queryset đã filter(participants=...) —
    # JOIN M2M làm Count luôn = 1 và tạo DM trùng vô hạn.
    both = (
        Conversation.objects.filter(is_group=False, participants=user)
        .filter(participants=recipient)
        .values('id')
    )
    return (
        Conversation.objects.filter(is_group=False, id__in=both)
        .annotate(member_count=Count('participants', distinct=True))
        .filter(member_count=2)
    )


def find_all_direct_conversations(user, recipient):
    if not user or not recipient or user.id == recipient.id:
        return []
    return list(
        _direct_conversation_qs(user, recipient)
        .annotate(msg_count=Count('messages', distinct=True))
        .order_by('-msg_count', '-last_message_time', '-id')
    )


def choose_canonical_direct_conversation(conversations):
    """Ưu tiên hội thoại có tin nhắn / mới nhất."""
    if not conversations:
        return None
    scored = []
    for c in conversations:
        msg_count = getattr(c, 'msg_count', None)
        if msg_count is None:
            msg_count = c.messages.count()
        scored.append((msg_count, c.last_message_time or c.created_at, c.id, c))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return scored[0][3]


def merge_duplicate_direct_conversations(conversations):
    """
    Gộp các DM trùng cùng 2 người vào 1 hội thoại.
    Chuyển tin nhắn sang bản giữ lại, xóa bản thừa (thường là trống).
    """
    conversations = [c for c in conversations if c is not None]
    if not conversations:
        return None
    if len(conversations) == 1:
        return conversations[0]

    keep = choose_canonical_direct_conversation(conversations)
    if not keep:
        return None

    with transaction.atomic():
        keep = Conversation.objects.select_for_update().get(pk=keep.pk)
        for other in conversations:
            if other.id == keep.id:
                continue
            other = Conversation.objects.select_for_update().filter(pk=other.id).first()
            if not other:
                continue
            ConversationMessage.objects.filter(conversation_id=other.id).update(
                conversation_id=keep.id
            )
            other.delete()

        latest = (
            ConversationMessage.objects.filter(conversation_id=keep.id)
            .order_by('-created_at')
            .values_list('created_at', flat=True)
            .first()
        )
        if latest and (not keep.last_message_time or latest > keep.last_message_time):
            keep.last_message_time = latest
            keep.save(update_fields=['last_message_time'])

    return Conversation.objects.filter(pk=keep.pk).first() or keep


def find_direct_conversation(user, recipient):
    """Tìm DM 1-1 (không phải nhóm) giữa hai người — tái sử dụng hội thoại cũ."""
    convs = find_all_direct_conversations(user, recipient)
    if not convs:
        return None
    if len(convs) > 1:
        return merge_duplicate_direct_conversations(convs)
    return convs[0]


def get_direct_conversation_for_share(user, recipient, conversation_id=None):
    """
    Lấy hội thoại 1-1 để gửi tin chia sẻ.
    Ưu tiên conversation_id hợp lệ (đã có sẵn), không thì tìm DM cũ,
    chỉ tạo mới khi chưa từng chat với người đó.
    """
    if conversation_id:
        try:
            cid = int(conversation_id)
        except (TypeError, ValueError):
            cid = None
        if cid:
            both = (
                Conversation.objects.filter(pk=cid, is_group=False, participants=user)
                .filter(participants=recipient)
                .values('id')
            )
            conversation = (
                Conversation.objects.filter(pk=cid, is_group=False, id__in=both)
                .annotate(member_count=Count('participants', distinct=True))
                .filter(member_count=2)
                .first()
            )
            if conversation:
                siblings = find_all_direct_conversations(user, recipient)
                if len(siblings) > 1:
                    return merge_duplicate_direct_conversations(siblings)
                return conversation

    return get_or_create_direct_conversation(user, recipient)


def get_or_create_direct_conversation(user, recipient):
    """Tìm hoặc tạo cuộc trò chuyện 1-1 giữa hai người dùng (chống race tạo trùng)."""
    if not user or not recipient or user.id == recipient.id:
        raise ValueError('Cần hai người dùng khác nhau để tạo DM.')

    conversation = find_direct_conversation(user, recipient)
    if conversation:
        unhide_conversation_for_user(conversation, user)
        return conversation

    # Khóa 2 user theo id tăng dần để 2 request song song không tạo 2 DM.
    ids = sorted([user.id, recipient.id])
    with transaction.atomic():
        list(User.objects.select_for_update().filter(id__in=ids).order_by('id'))

        conversation = find_direct_conversation(user, recipient)
        if conversation:
            unhide_conversation_for_user(conversation, user)
            return conversation

        conversation = Conversation.objects.create(is_group=False, created_by=user)
        ConversationParticipant.objects.create(conversation=conversation, user=user)
        ConversationParticipant.objects.create(conversation=conversation, user=recipient)
        return conversation


def dedupe_direct_conversations_for_user(user, conversations):
    """
    Trong danh sách inbox: chỉ giữ 1 DM cho mỗi người đối diện.
    Gộp bản trùng trong DB nếu phát hiện.
    """
    if not user:
        return list(conversations or [])

    result = []
    seen_other = {}
    pending_merge = {}

    for conv in conversations or []:
        if getattr(conv, 'is_group', False):
            result.append(conv)
            continue
        other = getattr(conv, 'other_user', None) or conv.get_other_participant(user)
        other_id = getattr(other, 'id', None)
        if other_id is None:
            result.append(conv)
            continue

        if other_id not in seen_other:
            seen_other[other_id] = conv
            result.append(conv)
            continue

        keep = seen_other[other_id]
        pending_merge.setdefault(other_id, [keep]).append(conv)

    for other_id, group in pending_merge.items():
        group_ids = {c.id for c in group}
        first_id = group[0].id
        result = [c for c in result if c.id not in group_ids or c.id == first_id]
        canonical = merge_duplicate_direct_conversations(group)
        if not canonical:
            continue
        for i, c in enumerate(result):
            if c.id == first_id or c.id == canonical.id:
                canonical.other_user = (
                    getattr(group[0], 'other_user', None)
                    or canonical.get_other_participant(user)
                )
                canonical.display_title = canonical.get_display_title(user)
                canonical.display_avatar = canonical.get_display_avatar_url(user)
                canonical.is_blocked = getattr(group[0], 'is_blocked', False)
                canonical.unread_count = sum(
                    getattr(x, 'unread_count', 0) or 0 for x in group
                )
                result[i] = canonical
                break
        else:
            canonical.other_user = canonical.get_other_participant(user)
            canonical.display_title = canonical.get_display_title(user)
            canonical.display_avatar = canonical.get_display_avatar_url(user)
            result.append(canonical)

    result.sort(key=lambda c: c.last_message_time or c.created_at, reverse=True)
    return result


def hide_conversation_for_user(conversation, user):
    """
    Xóa phía mình (DM): chỉ ẩn khỏi inbox của user, không xóa dữ liệu bên kia.
    Nếu mọi thành viên đều đã ẩn → xóa hẳn hội thoại.
    """
    if not conversation or not user:
        return {'hidden': False}

    row = ConversationParticipant.objects.filter(
        conversation=conversation, user=user
    ).first()
    if not row:
        return {'hidden': False}

    row.left_at = timezone.now()
    row.save(update_fields=['left_at'])

    active_left = ConversationParticipant.objects.filter(
        conversation=conversation, left_at__isnull=True
    ).exists()
    if not active_left:
        ConversationMessage.objects.filter(conversation=conversation).delete()
        conversation.delete()
        return {'hidden': True, 'deleted': True}

    return {'hidden': True, 'deleted': False}


def unhide_conversation_for_user(conversation, user):
    """Hiện lại hội thoại đã ẩn cho một user (khi mở lại / nhận tin mới)."""
    if not conversation or not user:
        return
    ConversationParticipant.objects.filter(
        conversation=conversation, user=user, left_at__isnull=False
    ).update(left_at=None)


def unhide_conversation_participants(conversation, except_user=None):
    """Bỏ ẩn cho mọi thành viên (thường khi có tin nhắn mới)."""
    if not conversation:
        return
    qs = ConversationParticipant.objects.filter(
        conversation=conversation, left_at__isnull=False
    )
    if except_user is not None:
        # Vẫn hiện lại cả người gửi nếu họ từng ẩn — tin mới của chính họ cũng mở lại thread
        pass
    qs.update(left_at=None)


def hidden_conversation_ids_for_user(user):
    if not user:
        return []
    return list(
        ConversationParticipant.objects.filter(user=user, left_at__isnull=False)
        .values_list('conversation_id', flat=True)
    )


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

    unhide_conversation_participants(conversation)

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
    unhide_conversation_participants(conversation)

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
