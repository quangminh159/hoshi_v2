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
    
    class Meta:
        unique_together = ('room', 'user')

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    media = models.FileField(upload_to='chat_media/', null=True, blank=True)
    media_type = models.CharField(max_length=10, choices=[
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('file', 'File')
    ], null=True, blank=True)
    is_read = models.BooleanField(default=False)
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
