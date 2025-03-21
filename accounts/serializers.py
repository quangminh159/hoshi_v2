from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Device, DataDownloadRequest, UserFollowing

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'name', 'avatar', 'bio', 'website',
            'is_private', 'is_verified', 'created_at', 'followers_count',
            'following_count', 'posts_count', 'is_following'
        ]
        read_only_fields = ['email', 'is_verified']
        
    def get_followers_count(self, obj):
        return obj.get_followers_count()
        
    def get_following_count(self, obj):
        return obj.get_following_count()
        
    def get_posts_count(self, obj):
        return obj.get_posts_count()
        
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFollowing.objects.filter(
                user=request.user,
                following_user=obj
            ).exists()
        return False
        
    def get_name(self, obj):
        return obj.get_full_name()

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id', 'device_type', 'device_name', 'browser', 'os',
            'ip_address', 'last_active', 'created_at', 'is_current'
        ]
        read_only_fields = ['user', 'device_id', 'ip_address', 'last_active']

class DataDownloadRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DataDownloadRequest
        fields = [
            'id', 'status', 'status_display', 'include_media',
            'created_at', 'expires_at'
        ]
        read_only_fields = ['status', 'created_at', 'expires_at']

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'push_notifications', 'email_notifications',
            'like_notifications', 'comment_notifications',
            'follow_notifications', 'mention_notifications',
            'private_account', 'hide_activity', 'block_messages',
            'two_factor_auth'
        ]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password1'] != data['new_password2']:
            raise serializers.ValidationError({
                'new_password2': 'Mật khẩu xác nhận không khớp.'
            })
        return data 