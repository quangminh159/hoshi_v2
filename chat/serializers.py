from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'content',
            'media', 'media_type', 'is_read', 'created_at'
        ]
        read_only_fields = ['sender', 'is_read']

class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserBasicSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_type', 'participants', 'last_message',
            'unread_count', 'other_user', 'created_at', 'updated_at'
        ]
    
    def get_last_message(self, obj):
        message = obj.messages.first()
        if message:
            return MessageSerializer(message).data
        return None
    
    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()
    
    def get_other_user(self, obj):
        user = self.context['request'].user
        other_user = obj.get_other_participant(user)
        if other_user:
            return UserBasicSerializer(other_user).data
        return None 