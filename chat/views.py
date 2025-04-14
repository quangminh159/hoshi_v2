from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, HttpResponse
from django.db.models import Q, Max, Count, Exists, OuterRef, Subquery
from .models import Conversation, ConversationMessage as Message, ConversationParticipant, Thread, UserSetting
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rich.console import Console
console = Console(style='bold green')
import re
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

User = get_user_model()

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
def conversation_list(request):
    """Hiển thị danh sách cuộc trò chuyện của người dùng"""
    user = request.user
    
    # Lấy danh sách ID người dùng trong quan hệ chặn (cả hai chiều)
    from accounts.models import UserBlock
    blocked_users = UserBlock.objects.filter(blocker=user).values_list('blocked_id', flat=True)
    blocking_users = UserBlock.objects.filter(blocked=user).values_list('blocker_id', flat=True)
    
    # Hợp nhất danh sách các ID người dùng bị chặn hoặc đã chặn user
    blocked_user_ids = list(blocked_users) + list(blocking_users)
    
    # Lấy tất cả cuộc trò chuyện của người dùng
    all_conversations = Conversation.objects.filter(participants=user).order_by('-last_message_time')
    
    # Đánh dấu các cuộc trò chuyện với người dùng bị chặn
    for conversation in all_conversations:
        other_participant = conversation.get_other_participant(user)
        conversation.is_blocked = other_participant.id in blocked_user_ids
    
    context = {
        'conversations': all_conversations
    }
    return render(request, 'chat/conversation_list.html', context)

@login_required
def conversation_detail(request, conversation_id):
    """Hiển thị chi tiết cuộc trò chuyện và tin nhắn"""
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Kiểm tra quyền truy cập
    if not conversation.participants.filter(id=user.id).exists():
        raise Http404("Không tìm thấy cuộc trò chuyện")
    
    # Lấy người dùng khác trong cuộc trò chuyện
    other_user = conversation.get_other_participant(user)
    conversation.other_user = other_user
    
    # Kiểm tra quan hệ chặn giữa hai người dùng
    from accounts.models import UserBlock
    
    block_relationship_exists = (
        UserBlock.objects.filter(blocker=other_user, blocked=user).exists() or 
        UserBlock.objects.filter(blocker=user, blocked=other_user).exists()
    )
    
    # Đánh dấu cuộc trò chuyện bị chặn nhưng vẫn hiển thị
    conversation.is_blocked = block_relationship_exists
    
    # Lấy tin nhắn
    messages = Message.objects.filter(conversation=conversation).order_by('created_at')
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'is_blocked': block_relationship_exists
    }
    
    return render(request, 'chat/conversation_detail.html', context)

@login_required
def send_message(request, conversation_id):
    """Xử lý gửi tin nhắn trong cuộc trò chuyện"""
    if request.method == 'POST':
        user = request.user
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Kiểm tra quyền truy cập
        if not conversation.participants.filter(id=user.id).exists():
            raise Http404("Không tìm thấy cuộc trò chuyện")
        
        # Lấy người nhận tin nhắn (người khác trong cuộc trò chuyện)
        other_participant = conversation.get_other_participant(user)
        
        # Kiểm tra quan hệ chặn giữa hai người dùng
        from accounts.models import UserBlock
        
        block_relationship_exists = (
            UserBlock.objects.filter(blocker=other_participant, blocked=user).exists() or 
            UserBlock.objects.filter(blocker=user, blocked=other_participant).exists()
        )
        
        if block_relationship_exists:
            from django.contrib import messages
            messages.error(request, f'Không thể gửi tin nhắn vì một trong hai người đã chặn người còn lại.')
            return redirect('chat:conversation_detail', conversation_id=conversation_id)
        
        message_content = request.POST.get('message', '').strip()
        
        if message_content:
            # Tạo tin nhắn mới
            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=message_content
            )
            
            # Cập nhật thời gian tin nhắn cuối cùng của cuộc trò chuyện
            conversation.last_message_time = message.created_at
            conversation.save()
    
    # Chuyển hướng về trang chi tiết cuộc trò chuyện
    return redirect('chat:conversation_detail', conversation_id=conversation_id)

@login_required
def direct_chat(request, username):
    """Bắt đầu hoặc tiếp tục cuộc trò chuyện với người dùng qua username"""
    user = request.user
    recipient = get_object_or_404(User, username=username)
    
    # Không thể chat với chính mình
    if user == recipient:
        return redirect('chat:conversation_list')
    
    # Kiểm tra quan hệ chặn giữa hai người dùng
    from accounts.models import UserBlock
    
    block_relationship_exists = (
        UserBlock.objects.filter(blocker=recipient, blocked=user).exists() or 
        UserBlock.objects.filter(blocker=user, blocked=recipient).exists()
    )
    
    if block_relationship_exists:
        from django.contrib import messages
        messages.error(request, f'Không thể tạo cuộc trò chuyện với {username} do một trong hai người đã chặn người còn lại.')
        return redirect('chat:conversation_list')
    
    # Tìm cuộc trò chuyện hiện có hoặc tạo mới
    conversation = Conversation.objects.filter(
        participants=user
    ).filter(
        participants=recipient
    ).first()
    
    if not conversation:
        # Tạo cuộc trò chuyện mới
        conversation = Conversation.objects.create()
        ConversationParticipant.objects.create(conversation=conversation, user=user)
        ConversationParticipant.objects.create(conversation=conversation, user=recipient)
    
    return redirect('chat:conversation_detail', conversation_id=conversation.id)

@login_required
def start_conversation(request):
    """Bắt đầu cuộc trò chuyện mới với người dùng được chọn"""
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
        
        # Tìm cuộc trò chuyện hiện có hoặc tạo mới
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=recipient
        ).first()
        
        if not conversation:
            # Tạo cuộc trò chuyện mới
            conversation = Conversation.objects.create()
            ConversationParticipant.objects.create(conversation=conversation, user=request.user)
            ConversationParticipant.objects.create(conversation=conversation, user=recipient)
        
        return redirect('chat:conversation_detail', conversation_id=conversation.id)
    
    # Hiển thị form chọn người dùng
    users = User.objects.exclude(id=request.user.id)
    context = {
        'users': users
    }
    return render(request, 'chat/start_conversation.html', context)

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
            messages = Message.objects.filter(thread=thread).order_by('-id')
            
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
    """Xóa cuộc trò chuyện"""
    user = request.user
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Kiểm tra quyền truy cập
    if not conversation.participants.filter(id=user.id).exists():
        return JsonResponse({"error": "Không có quyền xóa cuộc trò chuyện này"}, status=403)
    
    try:
        # Xóa tất cả tin nhắn trong cuộc trò chuyện
        Message.objects.filter(conversation=conversation).delete()
        
        # Xóa tất cả người tham gia 
        ConversationParticipant.objects.filter(conversation=conversation).delete()
        
        # Cuối cùng xóa cuộc trò chuyện
        conversation.delete()
        
        return JsonResponse({"success": True}, status=200)
    except Exception as e:
        console.print(f"Error deleting conversation: {e}")
        return JsonResponse({"error": "Đã xảy ra lỗi khi xóa cuộc trò chuyện"}, status=500)