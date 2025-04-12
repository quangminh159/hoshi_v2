from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, ConversationMessage as Message, ConversationParticipant

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'last_message_time', 'last_message', 'unread_count']
    
    def get_last_message(self, obj):
        request = self.context.get('request')
        last_message = Message.objects.filter(conversation=obj).order_by('-created_at').first()
        if last_message:
            return {
                'id': last_message.id,
                'content': last_message.content,
                'sender_id': last_message.sender.id,
                'created_at': last_message.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Message.objects.filter(
                conversation=obj, 
                read_receipts__user=request.user
            ).count()
        return 0

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'created_at', 'is_read']
        read_only_fields = ['sender', 'is_read']