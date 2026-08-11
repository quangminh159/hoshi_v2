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

def message_file_path(instance, filename):
    """Tạo đường dẫn ngẫu nhiên cho tệp đính kèm tin nhắn"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('chat_attachments', filename)


def group_avatar_path(instance, filename):
    """Đường dẫn ảnh đại diện nhóm chat."""
    ext = filename.split('.')[-1].lower()
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        ext = 'jpg'
    return os.path.join('group_avatars', f"{uuid.uuid4()}.{ext}")

class UserSetting(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    username = models.CharField(max_length=32, default="")
    profile_image = models.ImageField(upload_to=random_file_name, blank=True, null=True, default='\\profile-pics\\default.jpg')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    
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
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_time = models.DateTimeField(default=timezone.now)
    is_group = models.BooleanField(default=False)
    name = models.CharField(max_length=120, blank=True, default='')
    avatar = models.ImageField(upload_to=group_avatar_path, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_conversations',
    )
    # Tin nhắn chờ 
    is_message_request = models.BooleanField(default=False, db_index=True)
    message_request_for = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_message_requests',
        help_text='User cần chấp nhận tin nhắn chờ này',
    )

    def __str__(self):
        if self.is_group and self.name:
            return f"Group: {self.name}"
        participants_str = ", ".join([user.username for user in self.participants.all()[:5]])
        return f"Conversation between {participants_str}"

    def get_other_participant(self, user=None):
        """Lấy người tham gia còn lại (chỉ hợp lệ cho chat 1-1)."""
        qs = self.participants.all()
        if user is not None:
            return qs.exclude(id=user.id).first()
        first_user = qs.first()
        if not first_user:
            return None
        return qs.exclude(id=first_user.id).first()

    def get_display_title(self, viewer=None):
        if self.is_group:
            if self.name:
                return self.name
            names = list(
                self.participants.exclude(id=getattr(viewer, 'id', None)).values_list(
                    'username', flat=True
                )[:3]
            )
            if not names:
                names = list(self.participants.values_list('username', flat=True)[:3])
            title = ', '.join(names)
            extra = self.participants.count() - len(names)
            if extra > 0:
                title = f'{title} +{extra}'
            return title or 'Nhóm chat'
        other = self.get_other_participant(viewer)
        return other.username if other else 'Cuộc trò chuyện'

    def get_display_avatar_url(self, viewer=None):
        if self.is_group:
            if self.avatar:
                try:
                    return self.avatar.url
                except Exception:
                    pass
            # Fallback: avatar người tạo hoặc thành viên đầu tiên
            owner = self.created_by
            if owner and self.participants.filter(id=owner.id).exists():
                return owner.get_avatar_url()
            first = self.participants.first()
            return first.get_avatar_url() if first else '/static/img/default-avatar.png'
        other = self.get_other_participant(viewer)
        return other.get_avatar_url() if other else '/static/img/default-avatar.png'

    def get_member_count(self):
        return self.participants.count()

    def get_participant_row(self, user):
        if not user:
            return None
        return self.conversation_participants.filter(user=user).first()

    def user_is_admin(self, user):
        """Kiểm tra user có phải admin nhóm (hoặc người tạo)."""
        if not user or not self.is_group:
            return False
        if self.created_by_id and self.created_by_id == user.id:
            return True
        row = self.get_participant_row(user)
        return bool(row and row.is_admin)

    def get_last_message(self, viewer=None):
        """Lấy tin nhắn cuối cùng của cuộc trò chuyện (ẩn tin đã xóa phía viewer)."""
        qs = self.messages.order_by('-created_at')
        if viewer is not None:
            qs = qs.exclude(hidden_for=viewer)
        return qs.first()

class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='conversation_participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('conversation', 'user')
        
    def __str__(self):
        role = 'admin' if self.is_admin else 'member'
        return f"{self.user.username} ({role}) in {self.conversation}"

class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages', null=True)
    content = models.TextField(blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_read = models.BooleanField(default=False)
    isread = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)
    
    # Trường đính kèm
    image = models.ImageField(upload_to=message_file_path, blank=True, null=True)
    video = models.FileField(upload_to=message_file_path, blank=True, null=True)
    document = models.FileField(upload_to=message_file_path, blank=True, null=True)
    audio = models.FileField(upload_to=message_file_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.IntegerField(blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
    )
    shared_post = models.ForeignKey(
        'posts.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shared_in_messages',
    )
    # Xóa tin: chỉ mình (M2M) hoặc thu hồi cả hai bên
    is_deleted_for_everyone = models.BooleanField(default=False, db_index=True)
    deleted_for_everyone_at = models.DateTimeField(null=True, blank=True)
    hidden_for = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='hidden_chat_messages',
    )
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation}"
    
    def has_attachment(self):
        """Kiểm tra xem tin nhắn có đính kèm tệp không"""
        if self.is_deleted_for_everyone:
            return False
        return bool(self.image or self.video or self.document or self.audio)

    def clear_attachments(self):
        """Xóa file đính kèm trên disk và gỡ field (khi thu hồi tin)."""
        import os
        for field_name in ('image', 'video', 'audio', 'document'):
            field = getattr(self, field_name, None)
            if not field:
                continue
            try:
                if field.name and os.path.isfile(field.path):
                    os.remove(field.path)
            except Exception:
                pass
            setattr(self, field_name, None)
        self.file_name = None
        self.file_size = None
        self.file_type = None

    def get_attachment_url(self):
        """Lấy URL của tệp đính kèm"""
        if self.is_deleted_for_everyone:
            return None
        if self.image:
            return self.image.url
        elif self.video:
            return self.video.url
        elif self.document:
            return self.document.url
        elif self.audio:
            return self.audio.url
        return None

    def get_reply_preview(self):
        """Nội dung rút gọn để hiển thị khi được trả lời / preview inbox."""
        if getattr(self, 'is_deleted_for_everyone', False):
            return 'Tin nhắn đã được thu hồi'
        if self.shared_post_id:
            from chat.message_utils import extract_shared_comment_id
            if extract_shared_comment_id(self.content):
                return 'Đã chia sẻ một bình luận'
            author = ''
            try:
                if self.shared_post_id and self.shared_post:
                    author = self.shared_post.author.username
            except Exception:
                author = ''
            return f'Đã chia sẻ một bài viết' + (f' của @{author}' if author else '')
        if self.content:
            return self.content
        if self.image:
            return '[Hình ảnh]'
        if self.video:
            return '[Video]'
        if self.audio:
            return '[Tin nhắn thoại]'
        if self.document:
            name = self.file_name or 'tài liệu'
            return f'[Tài liệu: {name}]'
        return '[Tin nhắn]'
    
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
