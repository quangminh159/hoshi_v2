from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Message, MessageRead


@receiver(post_save, sender=MessageRead)
def message_read_handler(sender, instance, created, **kwargs):
    """
    Xử lý khi tin nhắn được đánh dấu là đã đọc
    """
    if created:
        channel_layer = get_channel_layer()
        conversation_id = instance.message.conversation.id
        group_name = f'chat_{conversation_id}'
        
        # Gửi thông báo đến tất cả thành viên trong cuộc trò chuyện
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'message_read',
                'message_id': instance.message.id,
                'user_id': instance.user.id,
                'timestamp': instance.read_at.isoformat()
            }
        )


@receiver(post_save, sender=Message)
def new_message_notification(sender, instance, created, **kwargs):
    """
    Xử lý khi có tin nhắn mới để gửi thông báo
    """
    if created:
        # Gửi thông báo đến các thành viên không online (nếu cần)
        # Đây là nơi bạn có thể tích hợp notification system
        pass 