from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', _('Like')),
        ('comment', _('Comment')),
        ('follow', _('Follow')),
        ('mention', _('Mention')),
        ('message', _('Message')),
        ('share', _('Share')),
    )
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications_received'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications_sent'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    text = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Thêm các trường cụ thể cho từng loại thông báo
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    comment = models.ForeignKey('posts.Comment', on_delete=models.CASCADE, null=True, blank=True)
    message = models.ForeignKey('chat.Message', on_delete=models.CASCADE, null=True, blank=True)
    original_post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='shared_notifications')
    
    # Generic relation to the object that created the notification
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.sender} {self.get_notification_type_display()} -> {self.recipient}'
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save() 