from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Conversation(models.Model):
    """
    Mô hình đại diện cho một cuộc trò chuyện giữa các người dùng.
    Có thể là cuộc trò chuyện 1-1 hoặc nhóm.
    """
    name = models.CharField(_('tên nhóm chat'), max_length=255, blank=True, null=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_conversations',
        null=True
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        through='ConversationParticipant'
    )
    is_group = models.BooleanField(_('nhóm chat'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('cuộc trò chuyện')
        verbose_name_plural = _('cuộc trò chuyện')
    
    def __str__(self):
        if self.is_group and self.name:
            return self.name
        participants_names = ", ".join([user.username for user in self.participants.all()[:3]])
        if self.participants.count() > 3:
            participants_names += f" và {self.participants.count() - 3} người khác"
        return participants_names

    @classmethod
    def get_or_create_for_users(cls, user1, user2):
        """
        Lấy hoặc tạo cuộc trò chuyện giữa hai người dùng
        """
        # Tìm kiếm cuộc trò chuyện có cả hai người dùng
        conversations = cls.objects.filter(is_group=False)
        conversations = conversations.filter(participants=user1).filter(participants=user2)
        
        if conversations.exists():
            return conversations.first()
        
        # Tạo cuộc trò chuyện mới
        conversation = cls.objects.create(is_group=False, creator=user1)
        ConversationParticipant.objects.create(conversation=conversation, user=user1)
        ConversationParticipant.objects.create(conversation=conversation, user=user2)
        
        return conversation

class ConversationParticipant(models.Model):
    """
    Mô hình liên kết giữa người dùng và cuộc trò chuyện,
    lưu trữ thông tin về vai trò, trạng thái, v.v.
    """
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='conversation_participants'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_conversations'
    )
    is_admin = models.BooleanField(_('quản trị viên'), default=False)
    muted = models.BooleanField(_('đã tắt tiếng'), default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('conversation', 'user')
        verbose_name = _('thành viên')
        verbose_name_plural = _('thành viên')
    
    def __str__(self):
        return f"{self.user.username} trong {self.conversation}"

class Message(models.Model):
    """
    Mô hình đại diện cho một tin nhắn trong cuộc trò chuyện
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sent_messages',
        null=True
    )
    content = models.TextField(_('nội dung'))
    attachment = models.FileField(
        _('tệp đính kèm'),
        upload_to='chat_attachments/',
        null=True,
        blank=True
    )
    is_read = models.BooleanField(_('đã đọc'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = _('tin nhắn')
        verbose_name_plural = _('tin nhắn')
    
    def __str__(self):
        return f"Tin nhắn từ {self.sender.username} lúc {self.created_at.strftime('%H:%M:%S %d/%m/%Y')}"
    
    def soft_delete(self):
        """Xóa mềm tin nhắn"""
        self.deleted_at = timezone.now()
        self.save()
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None

class MessageRead(models.Model):
    """
    Mô hình theo dõi trạng thái đọc tin nhắn của từng người dùng
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_receipts'
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
        verbose_name = _('trạng thái đọc')
        verbose_name_plural = _('trạng thái đọc')
    
    def __str__(self):
        return f"{self.user.username} đã đọc tin nhắn {self.message.id} lúc {self.read_at.strftime('%H:%M:%S %d/%m/%Y')}" 