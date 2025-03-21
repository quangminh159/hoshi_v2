from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings
from .models import ChatRoom, ChatRoomParticipant, Message

User = get_user_model()

# Số lượng item trên mỗi trang
POSTS_PER_PAGE = 10
MESSAGES_PER_PAGE = 20
NOTIFICATIONS_PER_PAGE = 15

# Giới hạn kích thước file upload (10MB)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

@login_required
def room_list(request):
    # Lấy danh sách phòng chat mà user tham gia
    rooms = ChatRoom.objects.filter(participants=request.user)
    # Lấy danh sách user để tạo phòng chat mới
    users = User.objects.exclude(id=request.user.id)
    
    return render(request, 'chat/room_list.html', {
        'rooms': rooms,
        'users': users
    })

@login_required
def room_detail(request, room_id):
    try:
        # Lấy phòng chat và kiểm tra quyền truy cập
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        # Lấy tin nhắn trong phòng
        messages = Message.objects.filter(room=room).order_by('-created_at')[:50]
        
        return render(request, 'chat/room_detail.html', {
            'room': room,
            'messages': messages
        })
    except ChatRoom.DoesNotExist:
        return redirect('chat:room_list')

@login_required
def create_room(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            participant = get_object_or_404(User, id=user_id)
            
            # Kiểm tra xem đã có phòng chat trực tiếp giữa 2 người chưa
            existing_room = ChatRoom.objects.filter(
                room_type='direct',
                participants=request.user
            ).filter(
                participants=participant
            ).first()
            
            if existing_room:
                return redirect('chat:room_detail', room_id=existing_room.id)
            
            # Tạo phòng chat mới
            room = ChatRoom.objects.create(
                room_type='direct'
            )
            # Thêm người tham gia
            ChatRoomParticipant.objects.create(
                room=room,
                user=request.user,
                is_admin=True
            )
            ChatRoomParticipant.objects.create(
                room=room,
                user=participant
            )
            
            return redirect('chat:room_detail', room_id=room.id)
    else:
        # Xử lý tham số user từ URL
        username = request.GET.get('user')
        if username:
            user = get_object_or_404(User, username=username)
            # Kiểm tra xem đã có phòng chat trực tiếp giữa 2 người chưa
            existing_room = ChatRoom.objects.filter(
                room_type='direct',
                participants=request.user
            ).filter(
                participants=user
            ).first()
            
            if existing_room:
                return redirect('chat:room_detail', room_id=existing_room.id)
            
            # Tạo phòng chat mới
            room = ChatRoom.objects.create(
                room_type='direct'
            )
            # Thêm người tham gia
            ChatRoomParticipant.objects.create(
                room=room,
                user=request.user,
                is_admin=True
            )
            ChatRoomParticipant.objects.create(
                room=room,
                user=user
            )
            
            return redirect('chat:room_detail', room_id=room.id)
    
    return redirect('chat:room_list')

@login_required
def send_message(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        content = request.POST.get('content')
        
        if content:
            message = Message.objects.create(
                room=room,
                sender=request.user,
                content=content
            )
            
            # Cập nhật thời gian của phòng chat
            room.save()  # Tự động cập nhật updated_at
            
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'created_at': message.created_at.isoformat()
                }
            })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_message(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.delete()
    
    return JsonResponse({'status': 'success'})

@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(email__icontains=query)
    ).exclude(
        id=request.user.id
    )[:10]
    
    return JsonResponse({
        'users': [{
            'id': user.id,
            'username': user.username,
            'avatar': user.avatar.url if user.avatar else None
        } for user in users]
    })
