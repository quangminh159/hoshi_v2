from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer

User = get_user_model()

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatRoom.objects.filter(participants=self.request.user)
    
    def create(self, request):
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return Response(
                {'error': 'Vui lòng chọn người dùng để trò chuyện'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Người dùng không tồn tại'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Kiểm tra xem phòng chat đã tồn tại chưa
        room = ChatRoom.objects.filter(
            participants=request.user,
            room_type='direct'
        ).filter(
            participants=other_user
        ).first()
        
        if room:
            serializer = self.get_serializer(room)
            return Response(serializer.data)
        
        # Tạo phòng chat mới
        room = ChatRoom.objects.create(room_type='direct')
        room.participants.add(request.user, other_user)
        
        serializer = self.get_serializer(room)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        room = self.get_object()
        Message.objects.filter(
            room=room
        ).exclude(
            sender=request.user
        ).update(is_read=True)
        return Response(status=status.HTTP_200_OK)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        room_id = self.kwargs.get('room_pk')
        return Message.objects.filter(room_id=room_id)
    
    def create(self, request, room_pk=None):
        room = ChatRoom.objects.get(id=room_pk)
        
        if request.user not in room.participants.all():
            return Response(
                {'error': 'Bạn không có quyền gửi tin nhắn trong phòng chat này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                room=room,
                sender=request.user
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 