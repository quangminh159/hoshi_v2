from concurrent.futures import thread
from chat.managers import ThreadManager
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
import os, uuid
from django.utils import timezone

User = get_user_model()

# Create your models here.
def random_file_name(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join('profile-pics', filename)

class UserSetting(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    username = models.CharField(max_length=32, default="")
    profile_image = models.ImageField(upload_to=random_file_name, blank=True, null=True, default='\\profile-pics\\default.jpg')
    is_online = models.BooleanField(default=False)
    
    def __str__(self):
        return str(self.user)

class TrackingModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Thread(TrackingModel):
    name = models.CharField(max_length=50, null=True, blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    unread_by_1 = models.PositiveIntegerField(default=0)
    unread_by_2 = models.PositiveIntegerField(default=0)

    objects = ThreadManager()

    def __str__(self):
        return f'{self.name} \t -> \t {self.users.first()} - {self.users.last()}'

class Message(TrackingModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, null=True, blank=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    text = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    isread = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f'From Thread - {self.thread.name if self.thread else "No Thread"}'
    
    def save(self, *args, **kwargs):
        if self.text and not self.content:
            self.content = self.text
        elif self.content and not self.text:
            self.text = self.content
        if self.isread and not self.is_read:
            self.is_read = self.isread
        elif self.is_read and not self.isread:
            self.isread = self.is_read
        super().save(*args, **kwargs)

# Mô hình trò chuyện mới
class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ConversationParticipant', related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_time = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        participants_str = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation between {participants_str}"
    
    def get_other_participant(self, user=None):
        """Lấy người dùng khác trong cuộc trò chuyện"""
        if user:
            return self.participants.exclude(id=user.id).first()
        else:
            # Nếu không cung cấp người dùng, trả về người dùng khác so với người đầu tiên
            first_user = self.participants.first()
            if first_user:
                return self.participants.exclude(id=first_user.id).first()
            return None
    
    def get_last_message(self):
        """Lấy tin nhắn cuối cùng của cuộc trò chuyện"""
        return self.messages.order_by('-created_at').first()

class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='conversation_participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('conversation', 'user')
        
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"

class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages', null=True)
    content = models.TextField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_read = models.BooleanField(default=False)
    isread = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation}"
    
    def mark_as_read(self, user):
        """Đánh dấu tin nhắn là đã đọc"""
        if user != self.sender and self.conversation.participants.filter(id=user.id).exists():
            self.is_read = True
            self.isread = True
            self.save()
            
    def save(self, *args, **kwargs):
        if self.text and not self.content:
            self.content = self.text
        elif self.content and not self.text:
            self.text = self.content
        if self.isread and not self.is_read:
            self.is_read = self.isread
        elif self.is_read and not self.isread:
            self.isread = self.is_read
        super().save(*args, **kwargs)

class ReadReceipt(models.Model):
    message = models.ForeignKey(ConversationMessage, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
        
    def __str__(self):
        return f"{self.user.username} read message {self.message.id}"
