from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Q, OuterRef, Subquery, Count, F, Exists
from django.core.paginator import Paginator
from django.conf import settings
from django.utils import timezone
from .models import ChatRoom, ChatRoomParticipant, Message, MessageRead, MessageReaction
import json

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
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        chatroomparticipant__is_accepted=True
    )
    
    # Đếm số tin nhắn chưa đọc trong mỗi phòng
    unread_counts = {}
    for room in rooms:
        unread_counts[room.id] = Message.objects.filter(
            room=room,
            is_read=False
        ).exclude(sender=request.user).count()
    
    # Lấy tin nhắn mới nhất của mỗi phòng
    latest_messages = {}
    for room in rooms:
        latest_message = Message.objects.filter(
            room=room, 
            is_deleted=False
        ).order_by('-created_at').first()
        latest_messages[room.id] = latest_message
    
    # Lấy danh sách người dùng để tạo phòng chat mới
    users = User.objects.exclude(id=request.user.id)
    
    # Lấy phòng chat chờ chấp nhận
    pending_rooms = ChatRoom.objects.filter(
        participants=request.user,
        chatroomparticipant__is_accepted=False
    )
    
    return render(request, 'chat/room_list.html', {
        'rooms': rooms,
        'users': users,
        'unread_counts': unread_counts,
        'latest_messages': latest_messages,
        'pending_rooms': pending_rooms
    })

@login_required
def room_detail(request, room_id):
    try:
        # Lấy phòng chat và kiểm tra quyền truy cập
        room = get_object_or_404(
            ChatRoom, 
            id=room_id, 
            participants=request.user, 
            chatroomparticipant__is_accepted=True
        )
        
        # Đánh dấu tất cả tin nhắn trong phòng là đã đọc
        unread_messages = Message.objects.filter(
            room=room, 
            is_read=False
        ).exclude(sender=request.user)
        
        for message in unread_messages:
            MessageRead.objects.get_or_create(
                message=message,
                user=request.user
            )
            message.is_read = True
            message.save()
        
        # Lấy tin nhắn trong phòng
        messages = Message.objects.filter(
            room=room, 
            is_deleted=False
        ).order_by('-created_at')[:50]
        
        # Lấy phản ứng cho từng tin nhắn
        message_reactions = {}
        for message in messages:
            reactions = MessageReaction.objects.filter(message=message)
            message_reactions[message.id] = reactions
        
        # Kiểm tra xem phòng chat có đang ở chế độ vanish mode không
        is_vanish_mode = room.is_vanish_mode
        
        # Chuẩn bị dữ liệu tin nhắn cho JavaScript
        messages_json = []
        for message in messages:
            # Lấy thông tin về tin nhắn được trả lời (nếu có)
            replied_to_data = None
            if message.replied_to:
                replied_to_data = {
                    'id': message.replied_to.id,
                    'content': message.replied_to.content,
                    'sender': message.replied_to.sender.username
                }
            
            # Tạo đối tượng tin nhắn để truyền cho JavaScript
            message_data = {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender.id,
                'sender': message.sender.username,
                'created_at': message.created_at.isoformat(),
                'media': message.media.url if message.media else None,
                'media_type': message.media_type,
                'is_read': message.is_read,
                'replied_to': replied_to_data
            }
            messages_json.append(message_data)
        
        return render(request, 'chat/room_detail.html', {
            'room': room,
            'messages': messages,
            'message_reactions': message_reactions,
            'is_vanish_mode': is_vanish_mode,
            'messages_json': json.dumps(messages_json)
        })
    except ChatRoom.DoesNotExist:
        return redirect('chat:room_list')

@login_required
def toggle_vanish_mode(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    room = get_object_or_404(
        ChatRoom, 
        id=room_id, 
        participants=request.user, 
        chatroomparticipant__is_accepted=True
    )
    
    room.is_vanish_mode = not room.is_vanish_mode
    room.save()
    
    return JsonResponse({
        'status': 'success',
        'is_vanish_mode': room.is_vanish_mode
    })

@login_required
def create_room(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            participant = get_object_or_404(User, id=user_id)
            
            # Kiểm tra xem đã có phòng chat trực tiếp giữa 2 người chưa
            existing_room = ChatRoom.objects.filter(
                room_type='direct',
                participants=request.user,
                chatroomparticipant__is_accepted=True
            ).filter(
                participants=participant,
                chatroomparticipant__is_accepted=True
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
                is_admin=True,
                is_accepted=True
            )
            ChatRoomParticipant.objects.create(
                room=room,
                user=participant,
                is_accepted=False  # Người được mời cần chấp nhận lời mời
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
                participants=request.user,
                chatroomparticipant__is_accepted=True
            ).filter(
                participants=user,
                chatroomparticipant__is_accepted=True
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
                is_admin=True,
                is_accepted=True
            )
            ChatRoomParticipant.objects.create(
                room=room,
                user=user,
                is_accepted=False  # Người được mời cần chấp nhận lời mời
            )
            
            return redirect('chat:room_detail', room_id=room.id)
    
    return redirect('chat:room_list')

@login_required
def accept_chat_request(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    participant = get_object_or_404(
        ChatRoomParticipant, 
        room_id=room_id, 
        user=request.user,
        is_accepted=False
    )
    
    participant.is_accepted = True
    participant.save()
    
    return JsonResponse({'status': 'success'})

@login_required
def decline_chat_request(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    participant = get_object_or_404(
        ChatRoomParticipant, 
        room_id=room_id, 
        user=request.user,
        is_accepted=False
    )
    
    # Xóa phòng chat nếu chỉ có 2 người tham gia
    room = participant.room
    if room.participants.count() <= 2:
        room.delete()
    else:
        participant.delete()
    
    return JsonResponse({'status': 'success'})

@login_required
def send_message(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(
            ChatRoom, 
            id=room_id, 
            participants=request.user, 
            chatroomparticipant__is_accepted=True
        )
        
        content = request.POST.get('content')
        media = request.FILES.get('media')
        media_type = request.POST.get('media_type', 'text')
        replied_to_id = request.POST.get('replied_to')
        
        replied_to = None
        if replied_to_id:
            replied_to = get_object_or_404(Message, id=replied_to_id, room=room)
        
        if content or media:
            message = Message.objects.create(
                room=room,
                sender=request.user,
                content=content or '',
                media=media,
                media_type=media_type,
                replied_to=replied_to
            )
            
            # Cập nhật thời gian của phòng chat
            room.save()  # Tự động cập nhật updated_at
            
            # Xử lý tin nhắn trong chế độ vanish mode
            will_vanish = room.is_vanish_mode
            
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'created_at': message.created_at.isoformat(),
                    'media': message.media.url if message.media else None,
                    'media_type': message.media_type,
                    'will_vanish': will_vanish,
                    'replied_to': {
                        'id': replied_to.id,
                        'content': replied_to.content,
                        'sender': replied_to.sender.username
                    } if replied_to else None
                }
            })
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_message(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.is_deleted = True
    message.content = "Tin nhắn này đã bị xóa"
    message.save()
    
    return JsonResponse({'status': 'success'})

@login_required
def react_to_message(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    message = get_object_or_404(
        Message, 
        id=message_id, 
        room__participants=request.user,
        room__chatroomparticipant__is_accepted=True
    )
    
    reaction_type = request.POST.get('reaction', 'like')
    
    # Kiểm tra xem người dùng đã phản ứng với tin nhắn này chưa
    existing_reaction = MessageReaction.objects.filter(
        message=message,
        user=request.user
    ).first()
    
    if existing_reaction:
        # Nếu chọn cùng reaction, xóa reaction
        if existing_reaction.reaction == reaction_type:
            existing_reaction.delete()
            action = 'removed'
        else:
            # Nếu chọn reaction khác, cập nhật
            existing_reaction.reaction = reaction_type
            existing_reaction.save()
            action = 'updated'
    else:
        # Tạo reaction mới
        MessageReaction.objects.create(
            message=message,
            user=request.user,
            reaction=reaction_type
        )
        action = 'added'
    
    # Lấy tất cả reactions cho tin nhắn này
    reactions = MessageReaction.objects.filter(message=message)
    
    return JsonResponse({
        'status': 'success',
        'action': action,
        'reactions': [
            {
                'id': r.id,
                'user': r.user.username,
                'reaction': r.reaction,
                'emoji': dict(MessageReaction.REACTION_TYPES).get(r.reaction, '❤️')
            }
            for r in reactions
        ]
    })

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
            'avatar': user.avatar.url if hasattr(user, 'avatar') and user.avatar else None
        } for user in users]
    })

@login_required
def mark_message_as_read(request, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    message = get_object_or_404(
        Message, 
        id=message_id, 
        room__participants=request.user,
        room__chatroomparticipant__is_accepted=True
    )
    
    # Đánh dấu tin nhắn là đã đọc
    if not message.is_read and message.sender != request.user:
        MessageRead.objects.get_or_create(
            message=message,
            user=request.user
        )
        message.is_read = True
        message.save()
        
        # Nếu là tin nhắn trong chế độ vanish mode
        if message.room.is_vanish_mode:
            message.is_vanished = True
            message.save()
    
    return JsonResponse({'status': 'success'})

@login_required
def toggle_mute(request, room_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    participant = get_object_or_404(
        ChatRoomParticipant, 
        room_id=room_id, 
        user=request.user,
        is_accepted=True
    )
    
    participant.is_muted = not participant.is_muted
    participant.save()
    
    return JsonResponse({
        'status': 'success',
        'is_muted': participant.is_muted
    })

@login_required
def get_new_messages(request, room_id):
    """API để lấy tin nhắn mới từ phòng chat"""
    since = request.GET.get('since')
    try:
        # Lấy phòng chat và kiểm tra quyền truy cập
        room = get_object_or_404(
            ChatRoom, 
            id=room_id, 
            participants=request.user, 
            chatroomparticipant__is_accepted=True
        )
        
        # Lấy tin nhắn mới từ thời điểm đã cho
        query = Message.objects.filter(
            room=room, 
            is_deleted=False
        )
        
        if since:
            query = query.filter(created_at__gt=since)
        
        messages = query.order_by('-created_at')[:20]
        
        # Đánh dấu tin nhắn là đã đọc
        for message in messages:
            if not message.is_read and message.sender != request.user:
                MessageRead.objects.get_or_create(
                    message=message,
                    user=request.user
                )
                message.is_read = True
                message.save()
        
        return JsonResponse({
            'status': 'success',
            'messages': [
                {
                    'id': message.id,
                    'content': message.content,
                    'sender_id': message.sender.id,
                    'sender': message.sender.username,
                    'created_at': message.created_at.isoformat(),
                    'media': message.media.url if message.media else None,
                    'media_type': message.media_type,
                    'replied_to': {
                        'id': message.replied_to.id,
                        'content': message.replied_to.content,
                        'sender': message.replied_to.sender.username
                    } if message.replied_to else None
                }
                for message in messages
            ]
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
