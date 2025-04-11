from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit

class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
    )
    
    name = models.CharField(max_length=255, blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='direct')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ChatRoomParticipant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar = models.ImageField(upload_to='chat/avatars/', null=True, blank=True)
    is_vanish_mode = models.BooleanField(default=False, help_text=_("Tin nhắn sẽ biến mất sau khi xem"))
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.room_type == 'direct':
            participants = self.participants.all()
            return f'Chat between {" and ".join(user.username for user in participants)}'
        return self.name or f'Group Chat {self.id}'

class ChatRoomParticipant(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=True, help_text=_("Đã chấp nhận lời mời trò chuyện"))
    is_muted = models.BooleanField(default=False, help_text=_("Tắt thông báo"))
    
    class Meta:
        unique_together = ('room', 'user')

class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('file', 'File'),
        ('reaction', 'Reaction'),
        ('story_reply', 'Story Reply'),
        ('voice', 'Voice Message')
    ]
    
    room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(max_length=5000)
    media = models.FileField(upload_to='chat_media/', null=True, blank=True)
    media_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, help_text=_("Tin nhắn đã xóa"))
    is_vanished = models.BooleanField(default=False, help_text=_("Tin nhắn đã biến mất (vanish mode)"))
    replied_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.sender.username}: {self.content[:50]}'

    def mark_as_read(self):
        """Đánh dấu tin nhắn đã đọc"""
        if not self.is_read:
            self.is_read = True
            self.save()

class MessageRead(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
        ordering = ['-read_at']

class MessageReaction(models.Model):
    REACTION_TYPES = [
        ('like', '❤️'),
        ('laugh', '😂'),
        ('sad', '😢'),
        ('angry', '😡'),
        ('wow', '😮'),
        ('thumbs_up', '👍'),
        ('thumbs_down', '👎')
    ]
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=20, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
