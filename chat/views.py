from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Q, Max, Count, Exists, OuterRef, Subquery
from .models import Conversation, Message, ConversationParticipant

User = get_user_model()

@login_required
def chat_home(request):
    """Trang chủ chat - chuyển hướng đến danh sách cuộc trò chuyện"""
    return redirect('chat:conversation_list')

@login_required
def conversation_list(request):
    """Hiển thị danh sách cuộc trò chuyện của người dùng"""
    user = request.user
    
    # Lấy tất cả cuộc trò chuyện mà người dùng tham gia
    conversations = Conversation.objects.filter(
        participants=user,
        conversation_participants__left_at__isnull=True
    ).distinct().order_by('-updated_at')
    
    # Lấy tin nhắn cuối cùng và số tin chưa đọc cho mỗi cuộc trò chuyện
    for conversation in conversations:
        # Tin nhắn cuối cùng
        conversation.last_message = (
            Message.objects
            .filter(conversation=conversation)
            .order_by('-created_at')
            .first()
        )
        
        # Đếm số tin nhắn chưa đọc
        conversation.unread_count = (
            Message.objects
            .filter(conversation=conversation)
            .exclude(read_receipts__user=user)
            .count()
        )
        
        # Xác định người dùng khác trong cuộc trò chuyện (đối với chat 1-1)
        if not conversation.is_group:
            other_participants = conversation.participants.exclude(id=user.id)
            if other_participants.exists():
                conversation.other_user = other_participants.first()
            else:
                conversation.other_user = None
    
    context = {
        'conversations': conversations,
    }
    
    return render(request, 'chat/conversation_list.html', context)

@login_required
def conversation_detail(request, conversation_id):
    """Hiển thị chi tiết cuộc trò chuyện và tin nhắn"""
    user = request.user
    
    # Lấy cuộc trò chuyện
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=user
    )
    
    # Kiểm tra xem người dùng có phải là thành viên hiện tại không
    is_active_participant = ConversationParticipant.objects.filter(
        conversation=conversation,
        user=user,
        left_at__isnull=True
    ).exists()
    
    if not is_active_participant:
        raise Http404("Bạn không phải là thành viên của cuộc trò chuyện này")
    
    # Lấy tin nhắn (giới hạn 100 tin gần nhất)
    messages = (
        Message.objects
        .filter(conversation=conversation)
        .order_by('-created_at')[:100]
    )
    
    # Đảo ngược danh sách để hiển thị theo thứ tự thời gian
    messages = list(reversed(messages))
    
    # Lấy tất cả người tham gia
    participants = ConversationParticipant.objects.filter(
        conversation=conversation,
        left_at__isnull=True
    ).select_related('user')
    
    # Xác định người dùng khác trong cuộc trò chuyện (đối với chat 1-1)
    if not conversation.is_group:
        other_participants = conversation.participants.exclude(id=user.id)
        if other_participants.exists():
            conversation.other_user = other_participants.first()
        else:
            conversation.other_user = None
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'participants': participants,
        'conversation_id': conversation_id,  # Cần thiết cho WebSocket
    }
    
    return render(request, 'chat/conversation_detail.html', context)

@login_required
def direct_chat(request, username):
    """
    Tạo hoặc mở cuộc trò chuyện riêng với một người dùng
    """
    user = request.user
    
    # Kiểm tra người dùng cần nhắn tin
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404("Không tìm thấy người dùng")
    
    # Không thể chat với chính mình
    if user.id == other_user.id:
        return redirect('chat:conversation_list')
    
    # Kiểm tra xem người dùng có bị chặn không
    if hasattr(user, 'has_blocked') and user.has_blocked(other_user):
        return redirect('chat:conversation_list')
    if hasattr(user, 'is_blocked') and user.is_blocked(other_user):
        return redirect('chat:conversation_list')
    
    # Lấy hoặc tạo cuộc trò chuyện
    conversation = Conversation.get_or_create_for_users(user, other_user)
    
    return redirect('chat:conversation_detail', conversation_id=conversation.id)

@login_required
def start_conversation(request):
    """
    Bắt đầu cuộc trò chuyện mới từ form modal
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        message_content = request.POST.get('message')
        
        if not username or not message_content:
            return redirect('chat:conversation_list')
        
        try:
            other_user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Xử lý khi không tìm thấy người dùng
            return redirect('chat:conversation_list')
        
        # Không thể chat với chính mình
        if request.user.id == other_user.id:
            return redirect('chat:conversation_list')
        
        # Kiểm tra xem người dùng có bị chặn không
        if hasattr(request.user, 'has_blocked') and request.user.has_blocked(other_user):
            return redirect('chat:conversation_list')
        if hasattr(request.user, 'is_blocked') and request.user.is_blocked(other_user):
            return redirect('chat:conversation_list')
        
        # Lấy hoặc tạo cuộc trò chuyện
        conversation = Conversation.get_or_create_for_users(request.user, other_user)
        
        # Tạo tin nhắn mới
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_content
        )
        
        return redirect('chat:conversation_detail', conversation_id=conversation.id)
    
    # Nếu không phải POST, chuyển hướng về trang danh sách
    return redirect('chat:conversation_list') 