from celery import shared_task
from django.utils import timezone
from .models import Story, Post
from notify.models import Notification

@shared_task
def cleanup_expired_stories():
    """Delete expired stories."""
    Story.objects.filter(expires_at__lt=timezone.now()).delete()

@shared_task
def process_post_media(post_id):
    """Process uploaded media files for a post."""
    post = Post.objects.get(id=post_id)
    for media in post.media.all():
        # Process image/video
        # Add watermark, optimize, generate thumbnails, etc.
        pass

@shared_task
def notify_post_likes(post_id, liker_id):
    """Send notification when someone likes a post."""
    post = Post.objects.get(id=post_id)
    if post.user.id != liker_id:  # Don't notify if user likes their own post
        Notification.objects.create(
            recipient=post.user,
            sender_id=liker_id,
            notification_type='like_post',
            text=f'{post.user.username} đã thích bài viết của bạn',
            content_type_id=post.content_type_id,
            object_id=post.id
        )

@shared_task
def notify_post_comments(post_id, comment_id, commenter_id):
    """Send notification when someone comments on a post."""
    post = Post.objects.get(id=post_id)
    if post.user.id != commenter_id:  # Don't notify if user comments on their own post
        Notification.objects.create(
            recipient=post.user,
            sender_id=commenter_id,
            notification_type='comment',
            text=f'{post.user.username} đã bình luận về bài viết của bạn',
            content_type_id=post.content_type_id,
            object_id=post.id
        ) 