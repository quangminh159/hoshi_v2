from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, HttpResponse
from django.db.models import Q, Max, Count, Exists, OuterRef, Subquery
from .presence import get_user_presence
from .models import Conversation, ConversationMessage, ConversationParticipant, Thread, UserSetting
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rich.console import Console
console = Console(style='bold green')
import re
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from hoshi.spam import ratelimit

User = get_user_model()


from .message_utils import serialize_chat_message, serialize_reply_to


def _serialize_reply_to(message):
    return serialize_reply_to(message)


def _serialize_chat_message(message, user=None):
    return serialize_chat_message(message, user)


def _broadcast_chat_message(conversation_id, message_data):
    """Gửi tin nhắn realtime tới phòng chat + inbox."""
    from .conversation_utils import broadcast_chat_message
    broadcast_chat_message(conversation_id, message_data)


def _apply_attachment_to_message(message, request):
    """Gắn file đính kèm vào tin nhắn từ request.FILES."""
    if 'image' in request.FILES:
        image_file = request.FILES['image']
        message.image = image_file
        message.file_name = image_file.name
        message.file_size = image_file.size
        message.file_type = 'image'
        return True
    if 'video' in request.FILES:
        video_file = request.FILES['video']
        message.video = video_file
        message.file_name = video_file.name
        message.file_size = video_file.size
        message.file_type = 'video'
        return True
    if 'audio' in request.FILES:
        audio_file = request.FILES['audio']
        # Giới hạn ~10MB cho tin nhắn thoại (~2 phút)
        if audio_file.size > 10 * 1024 * 1024:
            return False
        content_type = getattr(audio_file, 'content_type', '') or ''
        if content_type and not content_type.startswith('audio/') and content_type not in (
            'application/octet-stream',
            'video/webm',  # một số trình duyệt ghi audio/webm dưới dạng video/webm
        ):
            # vẫn cho phép nếu tên file là voice.*
            name = (audio_file.name or '').lower()
            if not name.endswith(('.webm', '.m4a', '.ogg', '.mp3', '.wav', '.mp4')):
                return False
        message.audio = audio_file
        message.file_name = audio_file.name
        message.file_size = audio_file.size
        message.file_type = 'audio'
        return True
    if 'document' in request.FILES:
        document_file = request.FILES['document']
        message.document = document_file
        message.file_name = document_file.name
        message.file_size = document_file.size
        message.file_type = 'document'
        return True
    return False

def email_valid(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(re.fullmatch(regex, email)):
        return True
    return False

@login_required
def chat_home(request):
    """Trang chủ chat - chuyển hướng đến danh sách cuộc trò chuyện"""
    return redirect('chat:conversation_list')

@login_required
def call_window(request):
    """Cửa sổ popup riêng cho gọi thoại/video — sống độc lập với tab app chính."""
    return render(request, 'chat/call_window.html', {
        'title': 'Cuộc gọi',
    })


@login_required
def conversation_list(request):
    """Hiển thị danh sách cuộc trò chuyện của người dùng"""
    user = request.user
    
    # Lấy danh sách ID người dùng trong quan hệ chặn (cả hai chiều)
    from accounts.models import UserBlock
    from .unread import get_conversation_unread_counts

    blocked_users = UserBlock.objects.filter(blocker=user).values_list('blocked_id', flat=True)
    blocking_users = UserBlock.objects.filter(blocked=user).values_list('blocker_id', flat=True)
    
    # Hợp nhất danh sách các ID người dùng bị chặn hoặc đã chặn user
    blocked_user_ids = list(blocked_users) + list(blocking_users)
    
    # Lấy cuộc trò chuyện chưa bị user ẩn (xóa phía mình)
    from .conversation_utils import (
        dedupe_direct_conversations_for_user,
        inbox_conversations_qs,
        pending_message_request_count,
    )
    all_conversations = list(inbox_conversations_qs(user))
    unread_map = get_conversation_unread_counts(user, [c.id for c in all_conversations])
    
    # Đánh dấu các cuộc trò chuyện với người dùng bị chặn
    for conversation in all_conversations:
        other_participant = conversation.get_other_participant(user)
        conversation.other_user = other_participant
        conversation.display_title = conversation.get_display_title(user)
        conversation.display_avatar = conversation.get_display_avatar_url(user)
        if conversation.is_group:
            conversation.is_blocked = False
        else:
            conversation.is_blocked = (
                other_participant.id in blocked_user_ids if other_participant else False
            )
        conversation.unread_count = unread_map.get(conversation.id, 0)
        conversation.preview_message = conversation.get_last_message(user)
        part = next(
            (
                p for p in conversation.conversation_participants.all()
                if p.user_id == user.id
            ),
            None,
        )
        conversation.is_pinned = bool(getattr(part, 'is_pinned', False))
        conversation.is_muted = bool(getattr(part, 'is_muted', False))
        conversation.pinned_at = getattr(part, 'pinned_at', None)

    # Gộp DM trùng (cùng 1 người nhưng nhiều hội thoại do race tạo cũ)
    all_conversations = dedupe_direct_conversations_for_user(user, all_conversations)
    # Ghim lên đầu (sau dedupe)
    all_conversations.sort(
        key=lambda c: (
            0 if getattr(c, 'is_pinned', False) else 1,
            -(c.pinned_at.timestamp() if getattr(c, 'pinned_at', None) else 0),
            -(c.last_message_time.timestamp() if c.last_message_time else 0),
        )
    )

    context = {
        'conversations': all_conversations,
        'message_request_count': pending_message_request_count(user),
    }
    return render(request, 'chat/conversation_list.html', context)


@login_required
def message_requests(request):
    """Danh sách tin nhắn chờ (Message Requests)."""
    from accounts.models import UserBlock
    from .unread import get_conversation_unread_counts
    from .conversation_utils import pending_message_request_qs

    user = request.user
    blocked_users = UserBlock.objects.filter(blocker=user).values_list('blocked_id', flat=True)
    blocking_users = UserBlock.objects.filter(blocked=user).values_list('blocker_id', flat=True)
    blocked_user_ids = list(blocked_users) + list(blocking_users)

    requests_list = list(pending_message_request_qs(user))
    unread_map = get_conversation_unread_counts(user, [c.id for c in requests_list])

    for conversation in requests_list:
        other = conversation.get_other_participant(user)
        conversation.other_user = other
        conversation.display_title = conversation.get_display_title(user)
        conversation.display_avatar = conversation.get_display_avatar_url(user)
        conversation.is_blocked = bool(other and other.id in blocked_user_ids)
        conversation.unread_count = unread_map.get(conversation.id, 0)
        conversation.preview_message = conversation.get_last_message(user)

    return render(request, 'chat/message_requests.html', {
        'conversations': requests_list,
        'message_request_count': len(requests_list),
    })


@login_required
@require_POST
def accept_message_request_view(request, conversation_id):
    from django.contrib import messages
    from django.urls import reverse
    from .conversation_utils import accept_message_request, is_pending_message_request_for

    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    if not is_pending_message_request_for(conversation, request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Không phải tin nhắn chờ.'}, status=400)
        messages.error(request, 'Không phải tin nhắn chờ.')
        return redirect('chat:message_requests')

    accept_message_request(conversation, request.user)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'redirect_url': reverse('chat:conversation_detail', args=[conversation.id]),
        })
    messages.success(request, 'Đã chấp nhận tin nhắn. Cuộc trò chuyện chuyển vào hộp thư chính.')
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
@require_POST
def decline_message_request_view(request, conversation_id):
    from django.contrib import messages
    from django.urls import reverse
    from .conversation_utils import decline_message_request, is_pending_message_request_for

    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    if not is_pending_message_request_for(conversation, request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Không phải tin nhắn chờ.'}, status=400)
        messages.error(request, 'Không phải tin nhắn chờ.')
        return redirect('chat:message_requests')

    decline_message_request(conversation, request.user)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'redirect_url': reverse('chat:message_requests')})
    messages.info(request, 'Đã từ chối tin nhắn chờ.')
    return redirect('chat:message_requests')


@login_required
def conversation_detail(request, conversation_id):
    """Hiển thị chi tiết cuộc trò chuyện và tin nhắn"""
    user = request.user
    conversation = get_object_or_404(
        Conversation.objects.select_related('created_by').prefetch_related('participants'),
        id=conversation_id,
    )
    
    # Kiểm tra quyền truy cập
    if not conversation.participants.filter(id=user.id).exists():
        raise Http404("Không tìm thấy cuộc trò chuyện")

    # Mở lại hội thoại đã ẩn phía mình
    from .conversation_utils import (
        is_pending_message_request_for,
        message_request_limit_info,
        unhide_conversation_for_user,
    )
    unhide_conversation_for_user(conversation, user)
    is_pending_request = is_pending_message_request_for(conversation, user)
    request_limit = message_request_limit_info(conversation, user)
    
    # Lấy người dùng khác trong cuộc trò chuyện (DM)
    other_user = None if conversation.is_group else conversation.get_other_participant(user)
    conversation.other_user = other_user
    conversation.display_title = conversation.get_display_title(user)
    conversation.display_avatar = conversation.get_display_avatar_url(user)
    member_rows = []
    members = []
    if conversation.is_group:
        member_rows = list(
            conversation.conversation_participants.select_related('user').order_by(
                '-is_admin', 'joined_at'
            )
        )
        members = [row.user for row in member_rows]
    else:
        members = list(conversation.participants.all())
    
    # Kiểm tra quan hệ chặn giữa hai người dùng (chỉ DM)
    from accounts.models import UserBlock
    
    block_relationship_exists = False
    if other_user and not conversation.is_group:
        block_relationship_exists = (
            UserBlock.objects.filter(blocker=other_user, blocked=user).exists() or
            UserBlock.objects.filter(blocker=user, blocked=other_user).exists()
        )
    
    # Đánh dấu cuộc trò chuyện bị chặn nhưng vẫn hiển thị
    conversation.is_blocked = block_relationship_exists
    
    # Lấy tin nhắn
    chat_messages = ConversationMessage.objects.filter(
        conversation=conversation
    ).exclude(
        hidden_for=user
    ).select_related(
        'sender', 'reply_to', 'reply_to__sender',
        'shared_post', 'shared_post__author',
    ).prefetch_related('shared_post__media').order_by('created_at')

    from .unread import mark_conversation_messages_read
    from .conversation_utils import broadcast_messages_read
    read_ids = mark_conversation_messages_read(conversation, user)
    if read_ids:
        broadcast_messages_read(conversation.id, read_ids, user.id)

    followable_users = []
    is_group_admin = False
    if conversation.is_group:
        is_group_admin = conversation.user_is_admin(user)
        from accounts.models import UserFollowing
        following_ids = UserFollowing.objects.filter(user=user).values_list(
            'following_user_id', flat=True
        )
        member_ids = {m.id for m in members}
        followable_users = list(
            User.objects.filter(id__in=following_ids).exclude(id__in=member_ids)
        )
    
    if other_user and getattr(other_user, 'hide_activity', False):
        other_presence = {'is_online': False, 'last_seen': None}
    else:
        other_presence = get_user_presence(other_user) if other_user else {}

    context = {
        'conversation': conversation,
        'chat_messages': chat_messages,
        'is_blocked': block_relationship_exists,
        'today': timezone.localdate(),
        'other_presence': other_presence,
        'members': members,
        'member_rows': member_rows,
        'is_group': conversation.is_group,
        'is_group_admin': is_group_admin,
        'is_group_owner': bool(
            conversation.is_group
            and conversation.created_by_id
            and conversation.created_by_id == user.id
        ),
        'followable_users': followable_users,
        'is_pending_request': is_pending_request,
        'message_request_limit': request_limit,
    }
    
    return render(request, 'chat/conversation_detail.html', context)

@login_required
@ratelimit(rate='60/m', key='user')
def send_message(request, conversation_id):
    """Xử lý gửi tin nhắn trong cuộc trò chuyện"""
    if request.method == 'POST':
        user = request.user
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Kiểm tra quyền truy cập
        if not conversation.participants.filter(id=user.id).exists():
            raise Http404("Không tìm thấy cuộc trò chuyện")
        
        if not conversation.is_group:
            # Lấy người nhận tin nhắn (người khác trong cuộc trò chuyện)
            other_participant = conversation.get_other_participant(user)
            
            # Kiểm tra quan hệ chặn giữa hai người dùng
            from accounts.models import UserBlock
            
            block_relationship_exists = (
                other_participant and (
                    UserBlock.objects.filter(blocker=other_participant, blocked=user).exists() or
                    UserBlock.objects.filter(blocker=user, blocked=other_participant).exists()
                )
            )
            
            if block_relationship_exists:
                from django.contrib import messages
                messages.error(request, f'Không thể gửi tin nhắn vì một trong hai người đã chặn người còn lại.')
                return redirect('chat:conversation_detail', conversation_id=conversation_id)

            from .conversation_utils import accept_message_request, can_send_in_message_request, is_pending_message_request_for
            if is_pending_message_request_for(conversation, user):
                accept_message_request(conversation, user)
            elif other_participant and not other_participant.can_receive_message_from(user):
                # Đã là tin chờ do mình gửi → vẫn cho nhắn tiếp (có hạn mức)
                if not (
                    conversation.is_message_request
                    and conversation.created_by_id == user.id
                ):
                    from django.contrib import messages
                    messages.error(
                        request,
                        f'{other_participant.username} chỉ nhận tin nhắn từ người họ đang theo dõi.'
                    )
                    return redirect('chat:conversation_detail', conversation_id=conversation_id)

            ok, err = can_send_in_message_request(conversation, user)
            if not ok:
                from django.contrib import messages
                messages.error(request, err)
                return redirect('chat:conversation_detail', conversation_id=conversation_id)
        
        message_content = request.POST.get('message', '').strip()
        has_attachment = any(key in request.FILES for key in ('image', 'video', 'document', 'audio'))
        
        # Tạo tin nhắn mới nếu có nội dung hoặc đính kèm
        if message_content or has_attachment:
            from .conversation_utils import unhide_conversation_participants
            unhide_conversation_participants(conversation)

            # Tạo tin nhắn mới
            message = ConversationMessage.objects.create(
                conversation=conversation,
                sender=user,
                content=message_content
            )
            
            _apply_attachment_to_message(message, request)
            
            # Lưu tin nhắn sau khi đã xử lý đính kèm
            message.save()
            
            # Cập nhật thời gian tin nhắn cuối cùng của cuộc trò chuyện
            conversation.last_message_time = message.created_at
            conversation.save()
    
    # Chuyển hướng về trang chi tiết cuộc trò chuyện
    return redirect('chat:conversation_detail', conversation_id=conversation_id)

@login_required
def direct_chat(request, username):
    """Bắt đầu hoặc tiếp tục cuộc trò chuyện với người dùng qua username"""
    from .conversation_utils import get_or_create_direct_conversation, users_are_blocked

    user = request.user
    recipient = get_object_or_404(User, username=username)
    
    # Không thể chat với chính mình
    if user == recipient:
        return redirect('chat:conversation_list')
    
    if users_are_blocked(user, recipient):
        from django.contrib import messages
        messages.error(request, f'Không thể tạo cuộc trò chuyện với {username} do một trong hai người đã chặn người còn lại.')
        return redirect('chat:conversation_list')
    
    from .conversation_utils import find_direct_conversation
    conversation = find_direct_conversation(user, recipient)
    
    if not conversation:
        if not recipient.can_receive_message_from(user):
            from django.contrib import messages
            messages.error(
                request,
                f'{username} chỉ nhận tin nhắn từ người họ đang theo dõi.'
            )
            return redirect('chat:conversation_list')
        conversation = get_or_create_direct_conversation(user, recipient)
    
    return redirect('chat:conversation_detail', conversation_id=conversation.id)

@login_required
def start_conversation(request):
    """Bắt đầu cuộc trò chuyện mới với người dùng được chọn"""
    from .conversation_utils import find_direct_conversation, get_or_create_direct_conversation

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        recipient = get_object_or_404(User, id=user_id)
        
        # Kiểm tra quan hệ chặn giữa hai người dùng
        from accounts.models import UserBlock
        
        block_relationship_exists = (
            UserBlock.objects.filter(blocker=recipient, blocked=request.user).exists() or 
            UserBlock.objects.filter(blocker=request.user, blocked=recipient).exists()
        )
        
        if block_relationship_exists:
            from django.contrib import messages
            messages.error(request, f'Không thể tạo cuộc trò chuyện với {recipient.username} do một trong hai người đã chặn người còn lại.')
            return redirect('chat:conversation_list')
        
        conversation = find_direct_conversation(request.user, recipient)
        
        if not conversation:
            if not recipient.can_receive_message_from(request.user):
                from django.contrib import messages
                messages.error(
                    request,
                    f'{recipient.username} chỉ nhận tin nhắn từ người họ đang theo dõi.'
                )
                return redirect('chat:conversation_list')
            conversation = get_or_create_direct_conversation(request.user, recipient)
        
        return redirect('chat:conversation_detail', conversation_id=conversation.id)
    
    # Hiển thị form chọn người dùng
    # Chỉ hiển thị những người mà người dùng hiện tại đang theo dõi (following)
    from accounts.models import UserFollowing
    
    # Lấy ID của những người mà người dùng hiện tại đang theo dõi
    following_ids = UserFollowing.objects.filter(
        user=request.user
    ).values_list('following_user_id', flat=True)
    
    users = User.objects.filter(id__in=following_ids)
    
    context = {
        'users': users
    }
    return render(request, 'chat/start_conversation.html', context)


@login_required
@require_POST
@csrf_protect
def create_group(request):
    """Tạo nhóm chat mới từ danh sách thành viên đang follow."""
    from django.contrib import messages
    from .conversation_utils import create_group_conversation

    name = (request.POST.get('name') or '').strip()
    member_ids = request.POST.getlist('member_ids')
    if not member_ids:
        raw = request.POST.get('member_ids_csv', '')
        member_ids = [x.strip() for x in raw.split(',') if x.strip()]

    try:
        member_ids = [int(x) for x in member_ids]
    except (TypeError, ValueError):
        messages.error(request, 'Danh sách thành viên không hợp lệ.')
        return redirect('chat:start_conversation')

    members = list(User.objects.filter(id__in=member_ids).exclude(id=request.user.id))
    if not members:
        messages.error(request, 'Chọn ít nhất một thành viên để tạo nhóm.')
        return redirect('chat:start_conversation')

    try:
        conversation = create_group_conversation(request.user, members, name=name)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('chat:start_conversation')

    from .conversation_utils import create_system_message
    create_system_message(
        conversation,
        request.user,
        f'{request.user.username} đã tạo nhóm "{conversation.name}"',
    )
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
@require_POST
@csrf_protect
def leave_group(request, conversation_id):
    """Rời nhóm chat (hoặc xóa nhóm nếu không còn thành viên)."""
    from .conversation_utils import create_system_message, ensure_group_has_admin

    conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)
    if not conversation.participants.filter(id=request.user.id).exists():
        raise Http404("Không tìm thấy cuộc trò chuyện")

    leaver_name = request.user.username
    create_system_message(conversation, request.user, f'{leaver_name} đã rời nhóm')

    ConversationParticipant.objects.filter(
        conversation=conversation, user=request.user
    ).delete()

    remaining = conversation.participants.count()
    if remaining == 0:
        ConversationMessage.objects.filter(conversation=conversation).delete()
        if conversation.avatar:
            conversation.avatar.delete(save=False)
        conversation.delete()
    else:
        if conversation.created_by_id == request.user.id:
            next_admin = (
                conversation.conversation_participants.filter(is_admin=True)
                .select_related('user')
                .first()
            )
            if not next_admin:
                next_admin = conversation.conversation_participants.select_related('user').first()
            if next_admin:
                conversation.created_by = next_admin.user
                conversation.save(update_fields=['created_by'])
                if not next_admin.is_admin:
                    next_admin.is_admin = True
                    next_admin.save(update_fields=['is_admin'])
                    create_system_message(
                        conversation,
                        next_admin.user,
                        f'{next_admin.user.username} đã trở thành admin nhóm',
                    )
        ensure_group_has_admin(conversation)

    return redirect('chat:conversation_list')


@login_required
@require_POST
@csrf_protect
def rename_group(request, conversation_id):
    """Đổi tên nhóm (chỉ admin)."""
    from django.contrib import messages
    from .conversation_utils import create_system_message

    conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)
    if not conversation.participants.filter(id=request.user.id).exists():
        raise Http404("Không tìm thấy cuộc trò chuyện")
    if not conversation.user_is_admin(request.user):
        messages.error(request, 'Chỉ admin nhóm mới được đổi tên.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    name = (request.POST.get('name') or '').strip()[:120]
    if not name:
        messages.error(request, 'Tên nhóm không được để trống.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    conversation.name = name
    conversation.save(update_fields=['name'])
    create_system_message(
        conversation,
        request.user,
        f'{request.user.username} đã đổi tên nhóm thành "{name}"',
    )
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
@require_POST
@csrf_protect
def update_group_avatar(request, conversation_id):
    """Đổi ảnh đại diện nhóm (chỉ admin)."""
    from django.contrib import messages
    from .conversation_utils import create_system_message

    conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)
    if not conversation.participants.filter(id=request.user.id).exists():
        raise Http404("Không tìm thấy cuộc trò chuyện")
    if not conversation.user_is_admin(request.user):
        messages.error(request, 'Chỉ admin nhóm mới được đổi ảnh đại diện.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    avatar = request.FILES.get('avatar')
    if not avatar:
        messages.error(request, 'Vui lòng chọn ảnh.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    content_type = (getattr(avatar, 'content_type', '') or '').lower()
    if content_type and not content_type.startswith('image/'):
        messages.error(request, 'File phải là ảnh.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)
    if avatar.size > 5 * 1024 * 1024:
        messages.error(request, 'Ảnh đại diện tối đa 5MB.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    if conversation.avatar:
        conversation.avatar.delete(save=False)
    conversation.avatar = avatar
    conversation.save(update_fields=['avatar'])
    create_system_message(
        conversation,
        request.user,
        f'{request.user.username} đã đổi ảnh đại diện nhóm',
    )
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
@require_POST
@csrf_protect
def add_group_members(request, conversation_id):
    """Thêm thành viên vào nhóm (chỉ admin, từ người đang follow)."""
    from django.contrib import messages
    from accounts.models import UserFollowing
    from .conversation_utils import create_system_message, users_are_blocked

    conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)
    if not conversation.participants.filter(id=request.user.id).exists():
        raise Http404("Không tìm thấy cuộc trò chuyện")
    if not conversation.user_is_admin(request.user):
        messages.error(request, 'Chỉ admin nhóm mới được thêm thành viên.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    member_ids = request.POST.getlist('member_ids')
    try:
        member_ids = [int(x) for x in member_ids]
    except (TypeError, ValueError):
        messages.error(request, 'Danh sách thành viên không hợp lệ.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    following_ids = set(
        UserFollowing.objects.filter(user=request.user).values_list(
            'following_user_id', flat=True
        )
    )
    existing_ids = set(conversation.participants.values_list('id', flat=True))
    added_names = []
    for uid in member_ids:
        if uid in existing_ids or uid not in following_ids:
            continue
        try:
            member = User.objects.get(id=uid)
        except User.DoesNotExist:
            continue
        if users_are_blocked(request.user, member):
            continue
        ConversationParticipant.objects.create(
            conversation=conversation, user=member, is_admin=False
        )
        existing_ids.add(uid)
        added_names.append(member.username)

    if added_names:
        if len(added_names) == 1:
            text = f'{request.user.username} đã thêm {added_names[0]} vào nhóm'
        else:
            text = f'{request.user.username} đã thêm {", ".join(added_names)} vào nhóm'
        create_system_message(conversation, request.user, text)
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
@require_POST
@csrf_protect
def set_group_admin(request, conversation_id):
    """Phân quyền / gỡ admin thành viên (chỉ admin)."""
    from django.contrib import messages
    from .conversation_utils import create_system_message, ensure_group_has_admin

    conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)
    if not conversation.user_is_admin(request.user):
        messages.error(request, 'Chỉ admin nhóm mới được phân quyền.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    try:
        user_id = int(request.POST.get('user_id', 0))
    except (TypeError, ValueError):
        messages.error(request, 'Thành viên không hợp lệ.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    make_admin = request.POST.get('make_admin') in ('1', 'true', 'on', 'yes')
    target = ConversationParticipant.objects.filter(
        conversation=conversation, user_id=user_id
    ).select_related('user').first()
    if not target:
        messages.error(request, 'Người này không còn trong nhóm.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    # Không thay đổi quyền người tạo nhóm
    if conversation.created_by_id == target.user_id:
        messages.error(request, 'Không thể thay đổi quyền của người tạo nhóm.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    if target.user_id == request.user.id and not make_admin:
        messages.error(request, 'Bạn không thể tự gỡ quyền admin của mình tại đây. Hãy phân quyền cho người khác rồi rời nhóm.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    target.is_admin = bool(make_admin)
    target.save(update_fields=['is_admin'])
    ensure_group_has_admin(conversation)

    if make_admin:
        create_system_message(
            conversation,
            request.user,
            f'{request.user.username} đã phong admin cho {target.user.username}',
        )
    else:
        create_system_message(
            conversation,
            request.user,
            f'{request.user.username} đã gỡ quyền admin của {target.user.username}',
        )
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
@require_POST
@csrf_protect
def kick_group_member(request, conversation_id):
    """Kick thành viên khỏi nhóm (chỉ admin)."""
    from django.contrib import messages
    from .conversation_utils import create_system_message, ensure_group_has_admin

    conversation = get_object_or_404(Conversation, id=conversation_id, is_group=True)
    if not conversation.user_is_admin(request.user):
        messages.error(request, 'Chỉ admin nhóm mới được kick thành viên.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    try:
        user_id = int(request.POST.get('user_id', 0))
    except (TypeError, ValueError):
        messages.error(request, 'Thành viên không hợp lệ.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    if user_id == request.user.id:
        messages.error(request, 'Không thể tự kick chính mình. Hãy dùng Rời nhóm.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    if conversation.created_by_id == user_id:
        messages.error(request, 'Không thể kick người tạo nhóm.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    target = ConversationParticipant.objects.filter(
        conversation=conversation, user_id=user_id
    ).select_related('user').first()
    if not target:
        messages.error(request, 'Người này không còn trong nhóm.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    # Admin thường không kick được admin khác; người tạo thì được
    if target.is_admin and conversation.created_by_id != request.user.id:
        messages.error(request, 'Chỉ người tạo nhóm mới được kick admin khác.')
        return redirect('chat:conversation_detail', conversation_id=conversation.id)

    username = target.user.username
    target.delete()
    ensure_group_has_admin(conversation)
    create_system_message(
        conversation,
        request.user,
        f'{request.user.username} đã kick {username} khỏi nhóm',
    )
    return redirect('chat:conversation_detail', conversation_id=conversation.id)

# Giữ lại các hàm API hiện có
@login_required
def api_online_users(request, id=0):
    users_json = {}
    
    if id != 0:
        user = User.objects.get(id=id)
        user_settings = UserSetting.objects.get(user=user)
        users_json['user'] = get_dictionary(user, user_settings)
    else:
        all_users = User.objects.all().exclude(username=request.user)
        for user in all_users:
            user_settings = UserSetting.objects.get(user=user)
            users_json[user.id] = get_dictionary(user, user_settings)

    return HttpResponse(
        json.dumps(users_json),
        content_type = 'application/javascript; charset=utf8'
    )

def get_dictionary(user, user_settings):
    return  {
                'id': user.id,
                'username': user_settings.username,
                'profile-image': user_settings.profile_image.url,
                'is-online': user_settings.is_online
            }

@login_required
def api_chat_messages(request, id):
    messages_json = {}
    count = int(request.GET.get('count', 0))
    
    try:
        thread = Thread.objects.filter(users=request.user).filter(users__id=id).first()
        if thread:
            messages = ConversationMessage.objects.filter(thread=thread).order_by('-id')
            
            for i, message in enumerate(messages, start=1):
                messages_json[message.id] = {
                    'sender': message.sender.id,
                    'text': message.text,
                    'timestamp': message.created_at.isoformat(),
                    'isread': message.isread,
                }
                if i == count: break
    except Exception as e:
        console.print(f"Error: {e}")

    return HttpResponse(
        json.dumps(messages_json),
        content_type = 'application/javascript; charset=utf8'
    )

@login_required
def api_unread_total(request):
    """Tổng số tin nhắn chưa đọc cho badge icon chat."""
    from .unread import get_unread_message_count
    count = get_unread_message_count(request.user)
    return JsonResponse({'ok': True, 'unread_count': count})


@login_required
def api_unread(request):
    messages_json = {}
    
    user = request.user
    threads = Thread.objects.filter(users=user)
    for i, thread in enumerate(threads):
        if(user == thread.users.first()): 
            sender = thread.users.last()
            unread = thread.unread_by_1
        else: 
            sender = thread.users.first()
            unread = thread.unread_by_2
        
        messages_json[i] = {
            'sender': sender.id,
            'count': unread,
        }

    return HttpResponse(
        json.dumps(messages_json),
        content_type = 'application/javascript; charset=utf8'
    )


@login_required
def api_link_preview(request):
    """Trả về Open Graph / oEmbed preview cho URL chia sẻ trong chat."""
    from .link_preview import get_link_preview, extract_first_url, is_safe_public_url

    raw = (request.GET.get('url') or '').strip()
    if not raw:
        return JsonResponse({'ok': False, 'error': 'missing_url'}, status=400)

    # Cho phép gửi cả đoạn text chứa URL
    url = extract_first_url(raw) or raw
    if not is_safe_public_url(url):
        return JsonResponse({'ok': False, 'error': 'invalid_url'}, status=400)

    preview = get_link_preview(url)
    if not preview:
        return JsonResponse({'ok': False, 'error': 'unavailable'}, status=404)

    return JsonResponse({'ok': True, 'preview': preview})


@login_required
def api_ice_servers(request):
    """ICE/STUN/TURN config cho WebRTC (có TURN nếu đã cấu hình env)."""
    from .ice_servers import ice_servers_payload

    payload = ice_servers_payload()
    return JsonResponse({'ok': True, **payload})


@login_required
def api_search_messages(request, conversation_id):
    """Tìm tin nhắn theo ký tự trong một cuộc trò chuyện."""
    from django.db.models import Q

    conversation = get_object_or_404(Conversation, id=conversation_id)
    if not conversation.participants.filter(id=request.user.id).exists():
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    q = (request.GET.get('q') or '').strip()
    if len(q) < 1:
        return JsonResponse({'ok': True, 'results': [], 'count': 0})

    try:
        limit = min(int(request.GET.get('limit') or 50), 100)
    except (TypeError, ValueError):
        limit = 50

    qs = (
        ConversationMessage.objects.filter(conversation=conversation)
        .exclude(hidden_for=request.user)
        .exclude(is_deleted_for_everyone=True)
        .filter(is_system=False)
        .filter(
            Q(content__icontains=q)
            | Q(text__icontains=q)
            | Q(file_name__icontains=q)
        )
        .select_related('sender')
        .order_by('-created_at')[:limit]
    )

    results = []
    for msg in qs:
        preview = (msg.content or msg.text or msg.file_name or '').strip()
        if len(preview) > 120:
            preview = preview[:117] + '…'
        results.append({
            'id': msg.id,
            'content': preview,
            'sender_username': msg.sender.username if msg.sender_id else '',
            'created_at': msg.created_at.isoformat(),
            'is_mine': bool(msg.sender_id and msg.sender_id == request.user.id),
        })

    return JsonResponse({'ok': True, 'results': results, 'count': len(results), 'q': q})


@login_required
def index(request, id=0):
    user = User.objects.get(username=request.user)
    Usettings = UserSetting.objects.get(user=user)   

    context = {
        "settings" : Usettings,
        'id' : id,
    }
    return render(request, 'index.html', context=context)


def login_view(request):
    logout(request)
    context = {}

    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
        
        user = authenticate(username=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('/')
        else:
            context = {
            "error": 'Email or Password was wrong.',
            }    
        
    return render(request, 'login.html',context)


def signup_view(request):
    logout(request)

    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        error = ''
        
        if not email_valid(email):
            error = "Wrong email address."
        try:
            if User.objects.get(username=email) is not None:
                error = 'This email is already used.'
        except: pass

        if error:  return render(request, "signup.html", context={'error': error})

        user = User.objects.create_user(
            username = email, 
            password = password,
        )
        userset = UserSetting.objects.create(user=user, username=username)
        
        login(request, user)
        return redirect('/')

    return render(request, 'signup.html')

@login_required
def settings_view(request):
    user = User.objects.get(username=request.user)
    Usettings = UserSetting.objects.get(user=user)  

    if request.method == 'POST':
        try:    avatar = request.FILES["avatar"]
        except: avatar = None
        username = request.POST['username']

        Usettings.username = username
        if(avatar != None):
            Usettings.profile_image.delete(save=True)
            Usettings.profile_image = avatar
        Usettings.save()

    context = {
        "settings" : Usettings,
        'user' : user,
    }
    return render(request, 'settings.html', context=context)

@login_required
def new_chat(request, conversation_id=None):
    """Hiển thị giao diện chat mới"""
    # Nếu có conversation_id, hiển thị cuộc trò chuyện đó
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        # Kiểm tra quyền truy cập
        if not conversation.participants.filter(id=request.user.id).exists():
            raise Http404("Không tìm thấy cuộc trò chuyện")
    
    # Lấy tất cả cuộc trò chuyện của người dùng
    conversations = Conversation.objects.filter(participants=request.user).order_by('-last_message_time')
    
    context = {
        'active_conversation': conversation if conversation_id else None,
        'conversations': conversations,
        'all_users': User.objects.exclude(id=request.user.id),
    }
    
    return render(request, 'chat/new_chat.html', context)

@login_required
@require_POST
@csrf_protect
def delete_conversation(request, conversation_id):
    """Xóa cuộc trò chuyện phía mình (DM) hoặc rời nhóm."""
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Kiểm tra quyền truy cập
    if not conversation.participants.filter(id=user.id).exists():
        return JsonResponse({"error": "Không có quyền xóa cuộc trò chuyện này"}, status=403)
    
    try:
        if conversation.is_group:
            # Rời nhóm thay vì xóa toàn bộ
            ConversationParticipant.objects.filter(
                conversation=conversation, user=user
            ).delete()
            remaining = conversation.participants.count()
            if remaining == 0:
                ConversationMessage.objects.filter(conversation=conversation).delete()
                conversation.delete()
            elif conversation.created_by_id == user.id:
                conversation.created_by = conversation.participants.first()
                conversation.save(update_fields=['created_by'])
            return JsonResponse({"success": True, "left_group": True}, status=200)

        # DM: chỉ ẩn phía mình — bên kia vẫn giữ cuộc trò chuyện
        from .conversation_utils import hide_conversation_for_user
        result = hide_conversation_for_user(conversation, user)
        return JsonResponse({
            "success": True,
            "hidden": True,
            "deleted": bool(result.get('deleted')),
        }, status=200)
    except Exception as e:
        console.print(f"Error deleting conversation: {e}")
        return JsonResponse({"error": "Đã xảy ra lỗi khi xóa cuộc trò chuyện"}, status=500)


@login_required
@require_POST
@csrf_protect
def toggle_pin_conversation(request, conversation_id):
    """Ghim / bỏ ghim cuộc trò chuyện (chỉ phía mình)."""
    from django.utils import timezone

    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    part = ConversationParticipant.objects.filter(
        conversation=conversation, user=user, left_at__isnull=True
    ).first()
    if not part:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    part.is_pinned = not part.is_pinned
    part.pinned_at = timezone.now() if part.is_pinned else None
    part.save(update_fields=['is_pinned', 'pinned_at'])
    return JsonResponse({
        'ok': True,
        'is_pinned': part.is_pinned,
        'conversation_id': conversation.id,
    })


@login_required
@require_POST
@csrf_protect
def toggle_mute_conversation(request, conversation_id):
    """Tắt / bật thông báo cuộc trò chuyện (chỉ phía mình)."""
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    part = ConversationParticipant.objects.filter(
        conversation=conversation, user=user, left_at__isnull=True
    ).first()
    if not part:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    part.is_muted = not part.is_muted
    part.save(update_fields=['is_muted'])
    return JsonResponse({
        'ok': True,
        'is_muted': part.is_muted,
        'conversation_id': conversation.id,
    })


@login_required
def upload_attachment(request, conversation_id):
    """Xử lý tải lên tệp đính kèm thông qua AJAX"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Phương thức không được hỗ trợ'}, status=405)

    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if not conversation.participants.filter(id=user.id).exists():
        return JsonResponse({'status': 'error', 'message': 'Không có quyền truy cập'}, status=403)

    if not conversation.is_group:
        other_participant = conversation.get_other_participant(user)
        from accounts.models import UserBlock

        if other_participant and (
            UserBlock.objects.filter(blocker=other_participant, blocked=user).exists()
            or UserBlock.objects.filter(blocker=user, blocked=other_participant).exists()
        ):
            return JsonResponse({'status': 'error', 'message': 'Không thể gửi tin nhắn do bị chặn'}, status=403)

    from .conversation_utils import can_send_in_message_request
    ok, err = can_send_in_message_request(conversation, user)
    if not ok:
        return JsonResponse({'status': 'error', 'message': err}, status=403)

    if not any(key in request.FILES for key in ('image', 'video', 'document', 'audio')):
        return JsonResponse({'status': 'error', 'message': 'Không có tệp đính kèm'}, status=400)

    message_content = request.POST.get('message', '').strip()
    from .conversation_utils import unhide_conversation_participants
    unhide_conversation_participants(conversation)

    message = ConversationMessage.objects.create(
        conversation=conversation,
        sender=user,
        content=message_content,
    )

    if not _apply_attachment_to_message(message, request):
        message.delete()
        return JsonResponse({'status': 'error', 'message': 'Không thể lưu tệp đính kèm'}, status=400)

    message.save()
    conversation.last_message_time = message.created_at
    conversation.save()

    payload = _serialize_chat_message(message, user)
    _broadcast_chat_message(conversation_id, payload)

    return JsonResponse({
        'status': 'success',
        'success': True,
        'message': payload,
    })