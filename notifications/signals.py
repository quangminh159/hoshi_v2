from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from posts.models import Like, Comment, Post
from chat.models import Message
from .models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

User = get_user_model()
channel_layer = get_channel_layer()

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created and instance.user != instance.post.author:
        notification = Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.user,
            notification_type='like',
            post=instance.post,
            text=f'{instance.user.username} đã thích bài viết của bạn'
        )
        send_notification_to_websocket(notification)

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created and instance.author != instance.post.author:
        notification = Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.author,
            notification_type='comment',
            post=instance.post,
            comment=instance,
            text=f'{instance.author.username} đã bình luận về bài viết của bạn'
        )
        send_notification_to_websocket(notification)

@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    if created:
        for participant in instance.conversation.participants.all():
            if participant != instance.sender:
                notification = Notification.objects.create(
                    recipient=participant,
                    sender=instance.sender,
                    notification_type='message',
                    message=instance,
                    text=f'{instance.sender.username} đã gửi tin nhắn mới'
                )
                send_notification_to_websocket(notification)

@receiver(m2m_changed, sender=User.followers.through)
def create_follow_notification(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for follower_id in pk_set:
            follower = User.objects.get(id=follower_id)
            notification = Notification.objects.create(
                recipient=instance,
                sender=follower,
                notification_type='follow',
                text=f'{follower.username} đã theo dõi bạn'
            )
            send_notification_to_websocket(notification)

def send_notification_to_websocket(notification):
    """Gửi thông báo đến WebSocket"""
    try:
        # Đếm số lượng thông báo chưa đọc
        unread_count = Notification.objects.filter(
            recipient=notification.recipient, 
            is_read=False
        ).count()
        
        # Chuẩn bị dữ liệu thông báo
        notification_data = {
            'type': 'notification_message',
            'message': 'new_notification',
            'notification_id': notification.id,
            'notification': {
                'id': notification.id,
                'sender_id': notification.sender.id,
                'sender_username': notification.sender.username,
                'sender_avatar': notification.sender.get_avatar_url(),
                'notification_type': notification.notification_type,
                'text': notification.text,
                'created_at': notification.created_at.isoformat(),
                'is_read': notification.is_read,
                'post_id': notification.post.id if notification.post else None,
                'comment_id': notification.comment.id if notification.comment else None,
                'conversation_id': notification.message.conversation.id if notification.message else None,
                'object_id': notification.object_id,
                'content_type': str(notification.content_type) if notification.content_type else None,
            },
            'unread_count': unread_count
        }
        
        # Gửi thông báo đến nhóm của người nhận
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            notification_data
        )
    except Exception as e:
        print(f"Error sending notification to websocket: {e}") 