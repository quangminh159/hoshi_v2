from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

class NotificationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar']

class NotificationSerializer(serializers.ModelSerializer):
    sender = NotificationUserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'notification_type',
            'text', 'is_read', 'created_at'
        ]
        read_only_fields = ['sender', 'notification_type', 'text'] 