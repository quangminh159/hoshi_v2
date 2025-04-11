from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max, Exists, OuterRef, Subquery, F
from django.utils import timezone
from .models import Conversation, Message, ConversationParticipant, MessageRead
from .serializers import (
    ConversationSerializer, 
    MessageSerializer, 
    ConversationListSerializer
)

User = get_user_model()

class ConversationViewSet(viewsets.ModelViewSet):
    """
    API endpoint cho cuộc trò chuyện
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Lấy danh sách cuộc trò chuyện của người dùng hiện tại"""
        user = self.request.user
        
        # Lấy tất cả cuộc trò chuyện mà người dùng tham gia
        queryset = Conversation.objects.filter(
            participants=user,
            conversation_participants__left_at__isnull=True
        ).distinct()
        
        # Sắp xếp theo thời gian cập nhật gần nhất
        return queryset.order_by('-updated_at')
    
    def get_serializer_class(self):
        """Trả về serializer phù hợp dựa trên action"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        """Tạo cuộc trò chuyện mới"""
        user_ids = request.data.get('participants', [])
        is_group = request.data.get('is_group', False)
        name = request.data.get('name', '') if is_group else None
        
        # Thêm người dùng hiện tại vào danh sách người tham gia
        if request.user.id not in user_ids:
            user_ids.append(request.user.id)
        
        # Nếu là chat riêng tư và chỉ có 2 người, kiểm tra xem đã có cuộc trò chuyện chưa
        if not is_group and len(user_ids) == 2:
            other_user_id = next(uid for uid in user_ids if uid != request.user.id)
            try:
                other_user = User.objects.get(id=other_user_id)
                conversation = Conversation.get_or_create_for_users(request.user, other_user)
                serializer = self.get_serializer(conversation)
                return Response(serializer.data)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Tạo cuộc trò chuyện mới
        conversation = Conversation.objects.create(
            creator=request.user,
            is_group=is_group,
            name=name
        )
        
        # Thêm người tham gia
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=user,
                    is_admin=(user.id == request.user.id)  # Người tạo là admin
                )
            except User.DoesNotExist:
                pass
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Lấy tin nhắn của cuộc trò chuyện"""
        conversation = self.get_object()
        
        # Kiểm tra người dùng có quyền xem không
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "Not a participant of this conversation"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Phân trang
        page = self.paginate_queryset(
            Message.objects.filter(conversation=conversation)
            .order_by('-created_at')
        )
        
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(
            Message.objects.filter(conversation=conversation).order_by('-created_at'),
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Thêm người tham gia vào cuộc trò chuyện"""
        conversation = self.get_object()
        
        # Kiểm tra quyền admin
        is_admin = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user,
            is_admin=True
        ).exists()
        
        if not is_admin:
            return Response(
                {"error": "Only admin can add participants"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            
            # Kiểm tra người dùng đã tham gia chưa
            if conversation.participants.filter(id=user.id).exists():
                # Nếu đã tham gia nhưng đã rời đi, cập nhật lại
                participant = ConversationParticipant.objects.get(
                    conversation=conversation,
                    user=user
                )
                if participant.left_at is not None:
                    participant.left_at = None
                    participant.save()
                    return Response({"status": "User re-added to conversation"})
                
                return Response(
                    {"error": "User already a participant"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Thêm người dùng mới
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=user
            )
            return Response({"status": "User added to conversation"})
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Rời khỏi cuộc trò chuyện"""
        conversation = self.get_object()
        
        try:
            participant = ConversationParticipant.objects.get(
                conversation=conversation,
                user=request.user
            )
            participant.left_at = timezone.now()
            participant.save()
            return Response({"status": "Left conversation"})
        except ConversationParticipant.DoesNotExist:
            return Response(
                {"error": "Not a participant of this conversation"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Đánh dấu tất cả tin nhắn trong cuộc trò chuyện là đã đọc"""
        conversation = self.get_object()
        
        # Kiểm tra người dùng có phải là thành viên không
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "Not a participant of this conversation"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Lấy tất cả tin nhắn chưa đọc
        unread_messages = Message.objects.filter(
            conversation=conversation
        ).exclude(
            read_receipts__user=request.user
        )
        
        # Đánh dấu đã đọc
        for message in unread_messages:
            MessageRead.objects.get_or_create(
                message=message,
                user=request.user
            )
        
        return Response({"status": "All messages marked as read"})


class MessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint cho tin nhắn
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Lấy tất cả tin nhắn từ cuộc trò chuyện mà người dùng tham gia
        return Message.objects.filter(
            conversation__participants=user
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Tạo tin nhắn mới"""
        conversation_id = request.data.get('conversation')
        content = request.data.get('content')
        attachment = request.data.get('attachment')
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Kiểm tra người dùng có quyền gửi tin nhắn không
            if not conversation.participants.filter(id=request.user.id).exists():
                return Response(
                    {"error": "Not a participant of this conversation"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Tạo tin nhắn mới
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content,
                attachment=attachment
            )
            
            # Đánh dấu là đã đọc đối với người gửi
            MessageRead.objects.create(
                message=message,
                user=request.user
            )
            
            # Cập nhật thời gian cập nhật của cuộc trò chuyện
            conversation.updated_at = timezone.now()
            conversation.save()
            
            serializer = self.get_serializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Đánh dấu tin nhắn là đã đọc"""
        message = self.get_object()
        
        # Kiểm tra người dùng có quyền đọc tin nhắn không
        if not message.conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "Not a participant of this conversation"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Đánh dấu đã đọc
        MessageRead.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        return Response({"status": "Message marked as read"})
    
    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        """Xóa mềm tin nhắn"""
        message = self.get_object()
        
        # Chỉ người gửi mới có quyền xóa
        if message.sender.id != request.user.id:
            return Response(
                {"error": "Only sender can delete message"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Xóa mềm tin nhắn
        message.soft_delete()
        
        return Response({"status": "Message deleted"}) 