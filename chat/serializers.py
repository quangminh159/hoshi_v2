from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Exists, OuterRef, Subquery
from .models import Conversation, Message, ConversationParticipant, MessageRead

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer cho thông tin cơ bản của người dùng"""
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar_url', 'is_private']
    
    def get_avatar_url(self, obj):
        if hasattr(obj, 'get_avatar_url'):
            return obj.get_avatar_url()
        return None

class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer cho thành viên của cuộc trò chuyện"""
    user = UserSerializer()
    
    class Meta:
        model = ConversationParticipant
        fields = ['user', 'is_admin', 'muted', 'joined_at', 'left_at']

class MessageSerializer(serializers.ModelSerializer):
    """Serializer cho tin nhắn"""
    sender = UserSerializer(read_only=True)
    read_by = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 
            'attachment', 'is_read', 'created_at', 
            'updated_at', 'is_deleted', 'read_by'
        ]
        read_only_fields = ['sender', 'is_deleted', 'read_by']
    
    def get_read_by(self, obj):
        """Lấy danh sách người dùng đã đọc tin nhắn"""
        users = User.objects.filter(message_receipts__message=obj)
        return UserSerializer(users, many=True).data

class LastMessageSerializer(serializers.ModelSerializer):
    """Serializer cho tin nhắn cuối cùng (hiển thị trong danh sách hội thoại)"""
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'created_at', 'is_read']

class ConversationListSerializer(serializers.ModelSerializer):
    """
    Serializer cho danh sách cuộc trò chuyện (hiển thị tổng quan)
    """
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'is_group', 'participants', 
            'last_message', 'unread_count', 'updated_at'
        ]
    
    def get_last_message(self, obj):
        """Lấy tin nhắn cuối cùng của cuộc trò chuyện"""
        try:
            last_message = obj.messages.order_by('-created_at').first()
            if last_message:
                return LastMessageSerializer(last_message).data
        except Exception:
            pass
        return None
    
    def get_unread_count(self, obj):
        """Đếm số tin nhắn chưa đọc"""
        user = self.context['request'].user
        
        # Đếm số tin nhắn không có trong bảng MessageRead
        unread_count = obj.messages.exclude(
            read_receipts__user=user
        ).count()
        
        return unread_count

class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer chi tiết cho cuộc trò chuyện
    """
    participants = serializers.SerializerMethodField()
    creator = UserSerializer(read_only=True)
    messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'creator', 'is_group', 
            'participants', 'messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['creator']
    
    def get_participants(self, obj):
        """Lấy thông tin chi tiết về người tham gia"""
        participants = ConversationParticipant.objects.filter(
            conversation=obj
        ).order_by('joined_at')
        
        return ConversationParticipantSerializer(participants, many=True).data
    
    def get_messages(self, obj):
        """Lấy tin nhắn gần đây nhất của cuộc trò chuyện"""
        # Chỉ lấy 20 tin nhắn gần nhất để tránh quá tải
        recent_messages = obj.messages.order_by('-created_at')[:20]
        return MessageSerializer(
            reversed(list(recent_messages)), 
            many=True, 
            context=self.context
        ).data 