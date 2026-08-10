from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from accounts.models import UserFollowing
from posts.models import Like, Comment, Mention
from chat.models import ConversationMessage
from .models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()
channel_layer = get_channel_layer()


def _pref_enabled(user, flag_name):
    return bool(getattr(user, flag_name, True))


def send_notification_to_websocket(notification):
    """Gửi thông báo đến WebSocket nếu recipient bật push."""
    try:
        recipient = notification.recipient
        if not _pref_enabled(recipient, 'push_notifications'):
            return

        unread_count = Notification.objects.filter(
            recipient=recipient,
            is_read=False,
        ).exclude(
            notification_type='message',
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
            f'notifications_{recipient.id}',
            notification_data
        )
    except Exception as e:
        print(f"Error sending notification to websocket: {e}")


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if not created or instance.user == instance.post.author:
        return
    recipient = instance.post.author
    if not _pref_enabled(recipient, 'like_notifications'):
        return

    notification = Notification.objects.create(
        recipient=recipient,
        sender=instance.user,
        notification_type='like',
        post=instance.post,
        text=f'{instance.user.username} đã thích bài viết của bạn'
    )
    send_notification_to_websocket(notification)


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if not created or instance.author == instance.post.author:
        return
    recipient = instance.post.author
    if not _pref_enabled(recipient, 'comment_notifications'):
        return

    notification = Notification.objects.create(
        recipient=recipient,
        sender=instance.author,
        notification_type='comment',
        post=instance.post,
        comment=instance,
        text=f'{instance.author.username} đã bình luận về bài viết của bạn'
    )
    send_notification_to_websocket(notification)


@receiver(post_save, sender=Mention)
def create_mention_notification(sender, instance, created, **kwargs):
    if not created:
        return
    recipient = instance.user
    # Mention trong bình luận → người gửi là tác giả cmt; trong caption → tác giả bài
    sender_user = None
    if instance.comment_id:
        sender_user = getattr(instance.comment, 'author', None)
    if not sender_user:
        sender_user = getattr(instance.post, 'author', None)
    if not sender_user or sender_user == recipient:
        return
    if not _pref_enabled(recipient, 'mention_notifications'):
        return

    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender_user,
        notification_type='mention',
        post=instance.post,
        comment=instance.comment,
        text=f'{sender_user.username} đã nhắc đến bạn'
    )
    send_notification_to_websocket(notification)


@receiver(post_save, sender=ConversationMessage)
def create_conversation_message_notification(sender, instance, created, **kwargs):
    # Tin nhắn chỉ hiện ở mục Chat (unread badge), không đẩy vào trang Thông báo.
    return


@receiver(post_save, sender=UserFollowing)
def create_follow_notification(sender, instance, created, **kwargs):
    if not created:
        return

    followed_user = instance.following_user
    follower = instance.user

    if not _pref_enabled(followed_user, 'follow_notifications'):
        return

    notification = Notification.objects.create(
        recipient=followed_user,
        sender=follower,
        notification_type='follow',
        text=f'đã theo dõi bạn'
    )
    send_notification_to_websocket(notification)
