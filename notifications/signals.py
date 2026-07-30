from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from accounts.models import UserFollowing
from posts.models import Like, Comment
from chat.models import ConversationMessage
from .models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()
channel_layer = get_channel_layer()


def send_notification_to_websocket(notification):
    """Gửi thông báo đến WebSocket."""
    try:
        unread_count = Notification.objects.filter(
            recipient=notification.recipient,
            is_read=False
        ).count()

        conversation_id = notification.conversation_id
        if not conversation_id and notification.message_id:
            conversation_id = getattr(notification.message, 'conversation_id', None)

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
                'post_id': notification.post_id,
                'comment_id': notification.comment_id,
                'conversation_id': conversation_id,
                'link': notification.link,
            },
            'unread_count': unread_count,
        }

        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.recipient.id}',
            notification_data
        )
    except Exception as e:
        print(f"Error sending notification to websocket: {e}")


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


@receiver(post_save, sender=ConversationMessage)
def create_conversation_message_notification(sender, instance, created, **kwargs):
    if not created or not instance.conversation_id or not instance.sender_id:
        return

    for participant in instance.conversation.participants.exclude(id=instance.sender_id):
        if hasattr(participant, 'message_notifications') and not participant.message_notifications:
            continue

        notification = Notification.objects.create(
            recipient=participant,
            sender=instance.sender,
            notification_type='message',
            conversation=instance.conversation,
            text=f'{instance.sender.username} đã gửi tin nhắn cho bạn'
        )
        send_notification_to_websocket(notification)


@receiver(post_save, sender=UserFollowing)
def create_follow_notification(sender, instance, created, **kwargs):
    if not created:
        return

    followed_user = instance.following_user
    follower = instance.user

    if hasattr(followed_user, 'follow_notifications') and not followed_user.follow_notifications:
        return

    notification = Notification.objects.create(
        recipient=followed_user,
        sender=follower,
        notification_type='follow',
        text=f'{follower.username} đã theo dõi bạn'
    )
    send_notification_to_websocket(notification)
