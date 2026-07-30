from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', _('Like')),
        ('like_post', _('Like')),
        ('comment', _('Comment')),
        ('comment_reply', _('Comment Reply')),
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

    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    comment = models.ForeignKey('posts.Comment', on_delete=models.CASCADE, null=True, blank=True)
    message = models.ForeignKey('chat.Message', on_delete=models.CASCADE, null=True, blank=True)
    conversation = models.ForeignKey('chat.Conversation', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    original_post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='shared_notifications')

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
            self.save(update_fields=['is_read'])

    def _conversation_id(self):
        if self.conversation_id:
            return self.conversation_id
        if self.message_id and getattr(self.message, 'conversation_id', None):
            return self.message.conversation_id
        return None

    @property
    def link(self):
        post_types = ('like', 'like_post', 'comment', 'comment_reply', 'mention', 'share')
        if self.notification_type in post_types and self.post_id:
            if self.notification_type == 'share' and self.original_post_id:
                return reverse('posts:post_detail', args=[self.original_post_id])
            return reverse('posts:post_detail', args=[self.post_id])
        if self.notification_type == 'follow' and self.sender_id:
            return reverse('accounts:profile', args=[self.sender.username])
        if self.notification_type == 'message':
            conversation_id = self._conversation_id()
            if conversation_id:
                return reverse('chat:conversation_detail', args=[conversation_id])
        return '#'
