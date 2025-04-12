from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Conversation, ConversationMessage as Message
from .serializers import ConversationSerializer, MessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing conversations"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).order_by('-last_message_time')
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a conversation"""
        conversation = self.get_object()
        messages = Message.objects.filter(conversation=conversation).order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing messages"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        conversation_id = self.request.data.get('conversation')
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Kiểm tra quyền truy cập
        if not conversation.participants.filter(id=self.request.user.id).exists():
            return Response(
                {"error": "Bạn không có quyền gửi tin nhắn trong cuộc trò chuyện này"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer.save(sender=self.request.user, conversation=conversation)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        # Kiểm tra xem người dùng có quyền đánh dấu tin nhắn là đã đọc không
        if message.sender != request.user and message.conversation.participants.filter(id=request.user.id).exists():
            message.mark_as_read(request.user)
            return Response({"status": "success"})
        return Response(
            {"error": "Không thể đánh dấu tin nhắn là đã đọc"}, 
            status=status.HTTP_403_FORBIDDEN
        )