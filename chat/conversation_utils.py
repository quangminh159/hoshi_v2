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

# Người gửi tin chờ chỉ được nhắn tối đa N tin trước khi được chấp nhận.
MESSAGE_REQUEST_MAX_MESSAGES = 3


def users_are_blocked(user_a, user_b):
    if not user_a or not user_b:
        return True
    return UserBlock.objects.filter(
        blocker=user_a, blocked=user_b
    ).exists() or UserBlock.objects.filter(
        blocker=user_b, blocked=user_a
    ).exists()


def should_create_as_message_request(sender, recipient):
    """
    Tin nhắn chờ khi người nhận chưa theo dõi người gửi (và không bị chặn cứng).
    Nếu recipient.block_messages → vẫn hard-deny ở can_receive_message_from.
    """
    if not sender or not recipient or sender.id == recipient.id:
        return False
    if users_are_blocked(sender, recipient):
        return False
    # Đã follow người gửi → inbox chính
    if recipient.is_following_user(sender):
        return False
    return True


def is_pending_message_request_for(conversation, user):
    if not conversation or not user:
        return False
    return bool(
        conversation.is_message_request
        and conversation.message_request_for_id == user.id
    )


def is_outgoing_message_request(conversation, user):
    """User đang là người gửi tin chờ (chưa được người nhận chấp nhận)."""
    if not conversation or not user or conversation.is_group:
        return False
    return bool(
        conversation.is_message_request
        and conversation.message_request_for_id
        and conversation.message_request_for_id != user.id
    )


def message_request_sent_count(conversation, user):
    """Số tin người gửi đã gửi trong cuộc tin chờ (không tính tin hệ thống)."""
    if not conversation or not user:
        return 0
    return (
        ConversationMessage.objects.filter(
            conversation=conversation,
            sender=user,
            is_system=False,
        ).count()
    )


def message_request_limit_info(conversation, user):
    """
    Thông tin hạn mức tin chờ cho user.
    Trả về None nếu không phải người gửi tin chờ đang pending.
    """
    if not is_outgoing_message_request(conversation, user):
        return None
    sent = message_request_sent_count(conversation, user)
    max_n = MESSAGE_REQUEST_MAX_MESSAGES
    remaining = max(0, max_n - sent)
    return {
        'sent': sent,
        'max': max_n,
        'remaining': remaining,
        'at_limit': remaining <= 0,
    }


def can_send_in_message_request(conversation, user):
    """
    Cho phép gửi tin trong tin chờ?
    Returns (ok: bool, error_message: str|None)
    """
    info = message_request_limit_info(conversation, user)
    if info is None:
        return True, None
    if info['at_limit']:
        return False, (
            f'Bạn chỉ có thể gửi tối đa {MESSAGE_REQUEST_MAX_MESSAGES} tin nhắn '
            'trước khi người nhận chấp nhận.'
        )
    return True, None


def accept_message_request(conversation, user):
    """Chấp nhận tin nhắn chờ → chuyển vào hộp thư chính."""
    if not is_pending_message_request_for(conversation, user):
        return False
    conversation.is_message_request = False
    conversation.message_request_for = None
    conversation.save(update_fields=['is_message_request', 'message_request_for'])
    unhide_conversation_for_user(conversation, user)
    broadcast_message_request_accepted(conversation, user)
    return True


def broadcast_message_request_accepted(conversation, accepted_by):
    """Realtime: báo phòng chat + inbox rằng tin chờ đã được chấp nhận."""
    if not conversation or not accepted_by:
        return
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    accepted_payload = {
        'id': accepted_by.id,
        'username': accepted_by.username,
    }
    conversation_id = int(conversation.id)

    try:
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {
                'type': 'message_request_accepted',
                'conversation_id': conversation_id,
                'accepted_by': accepted_payload,
            },
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
                    'type': 'inbox_message_request_accepted',
                    'conversation_id': conversation_id,
                    'accepted_by': accepted_payload,
                    'other_user': other_payload,
                    'conversation': conversation_inbox_payload(conversation, participant),
                },
            )
    except Exception:
        pass


def decline_message_request(conversation, user):
    """Từ chối tin nhắn chờ — ẩn/xóa phía người nhận."""
    if not is_pending_message_request_for(conversation, user):
        return {'ok': False}
    # Xóa trạng thái request rồi ẩn phía mình
    conversation.is_message_request = False
    conversation.message_request_for = None
    conversation.save(update_fields=['is_message_request', 'message_request_for'])
    return hide_conversation_for_user(conversation, user)


def pending_message_request_qs(user):
    """Các tin nhắn chờ dành cho user."""
    if not user:
        return Conversation.objects.none()
    hidden_ids = hidden_conversation_ids_for_user(user)
    return (
        Conversation.objects.filter(
            is_group=False,
            is_message_request=True,
            message_request_for=user,
            participants=user,
        )
        .exclude(id__in=hidden_ids)
        .select_related('created_by', 'message_request_for')
        .prefetch_related('participants')
        .order_by('-last_message_time')
    )


def pending_message_request_count(user):
    return pending_message_request_qs(user).count()


def inbox_conversations_qs(user):
    """Inbox chính — loại tin nhắn chờ của chính user."""
    if not user:
        return Conversation.objects.none()
    hidden_ids = hidden_conversation_ids_for_user(user)
    return (
        Conversation.objects.filter(participants=user)
        .exclude(id__in=hidden_ids)
        .exclude(is_message_request=True, message_request_for=user)
        .select_related('created_by', 'message_request_for')
        .prefetch_related('participants')
        .order_by('-last_message_time')
    )


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
        # Người nhận reply vào tin chờ → tự chấp nhận
        if is_pending_message_request_for(conversation, user):
            accept_message_request(conversation, user)
        return conversation

    # Khóa 2 user theo id tăng dần để 2 request song song không tạo 2 DM.
    ids = sorted([user.id, recipient.id])
    with transaction.atomic():
        list(User.objects.select_for_update().filter(id__in=ids).order_by('id'))

        conversation = find_direct_conversation(user, recipient)
        if conversation:
            unhide_conversation_for_user(conversation, user)
            if is_pending_message_request_for(conversation, user):
                accept_message_request(conversation, user)
            return conversation

        as_request = should_create_as_message_request(user, recipient)
        conversation = Conversation.objects.create(
            is_group=False,
            created_by=user,
            is_message_request=as_request,
            message_request_for=recipient if as_request else None,
        )
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
    is_request = bool(
        conversation.is_message_request
        and conversation.message_request_for_id == getattr(viewer, 'id', None)
    )
    return {
        'id': conversation.id,
        'is_group': bool(conversation.is_group),
        'is_message_request': is_request,
        'title': conversation.get_display_title(viewer),
        'avatar_url': conversation.get_display_avatar_url(viewer),
        'member_count': conversation.get_member_count() if conversation.is_group else 2,
    }


def send_conversation_message(user, conversation, content='', shared_post=None):
    """Tạo tin nhắn, cập nhật conversation và broadcast qua WebSocket."""
    ok, err = can_send_in_message_request(conversation, user)
    if not ok:
        raise ValueError(err or 'Không thể gửi thêm tin nhắn chờ.')

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


def broadcast_messages_read(conversation_id, message_ids, read_by_id):
    """Realtime: báo tin đã được xem (Đã xem) tới phòng chat + inbox."""
    ids = [int(i) for i in (message_ids or []) if i is not None]
    if not conversation_id or not ids or not read_by_id:
        return
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = {
        'conversation_id': int(conversation_id),
        'message_ids': ids,
        'read_by': int(read_by_id),
    }
    try:
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {
                'type': 'messages_read',
                'message_ids': ids,
                'read_by': int(read_by_id),
            },
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
        for participant in conversation.participants.all():
            if participant.id == read_by_id:
                continue
            async_to_sync(channel_layer.group_send)(
                f'chat_inbox_{participant.id}',
                {
                    'type': 'inbox_messages_read',
                    **payload,
                },
            )
    except Exception:
        pass


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
