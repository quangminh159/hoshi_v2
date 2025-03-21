from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from posts.models import Like, Comment, Post
from chat.models import Message
from .models import Notification

User = get_user_model()

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created and instance.user != instance.post.author:
        Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.user,
            notification_type='like',
            post=instance.post,
            text=f'{instance.user.username} đã thích bài viết của bạn'
        )

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created and instance.author != instance.post.author:
        Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.author,
            notification_type='comment',
            post=instance.post,
            comment=instance,
            text=f'{instance.author.username} đã bình luận về bài viết của bạn'
        )

@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    if created:
        for participant in instance.conversation.participants.all():
            if participant != instance.sender:
                Notification.objects.create(
                    recipient=participant,
                    sender=instance.sender,
                    notification_type='message',
                    message=instance,
                    text=f'{instance.sender.username} đã gửi tin nhắn mới'
                )

@receiver(m2m_changed, sender=User.followers.through)
def create_follow_notification(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for follower_id in pk_set:
            follower = User.objects.get(id=follower_id)
            Notification.objects.create(
                recipient=instance,
                sender=follower,
                notification_type='follow',
                text=f'{follower.username} đã theo dõi bạn'
            ) 