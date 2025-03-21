from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.text import slugify
from notifications.models import Notification
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit
from taggit.managers import TaggableManager
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse

User = get_user_model()

class Post(models.Model):
    author = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='posts')
    caption = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Engagement metrics
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    # Settings
    disable_comments = models.BooleanField(default=False)
    hide_likes = models.BooleanField(default=False)
    
    # For notifications
    notifications = GenericRelation(Notification)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]
    
    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"

    def get_absolute_url(self):
        return reverse('posts:post_detail', kwargs={'post_id': self.id})

class Media(models.Model):
    MEDIA_TYPES = (
        ('image', _('Image')),
        ('video', _('Video')),
    )
    
    post = models.ForeignKey(Post,
                           on_delete=models.CASCADE,
                           related_name='post_media')
    file = models.FileField(upload_to='posts/',
                          verbose_name=_('file'))
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPES, default='image')
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = _('media')
        verbose_name_plural = _('media')

    def __str__(self):
        return f"{self.media_type} for {self.post}"

class Like(models.Model):
    user = models.ForeignKey(User,
                           on_delete=models.CASCADE,
                           related_name='user_likes')
    post = models.ForeignKey(Post,
                           on_delete=models.CASCADE,
                           related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
        verbose_name = _('like')
        verbose_name_plural = _('likes')

    def __str__(self):
        return f"{self.user.username} likes {self.post}"

class Comment(models.Model):
    post = models.ForeignKey(Post,
                           on_delete=models.CASCADE,
                           related_name='comments')
    author = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='comments')
    text = models.TextField()
    parent = models.ForeignKey('self',
                             on_delete=models.CASCADE,
                             null=True,
                             blank=True,
                             related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes_count = models.PositiveIntegerField(default=0)
    
    # For notifications
    notifications = GenericRelation(Notification)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.post}"

class SavedPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='saved_posts')
    post = models.ForeignKey(Post,
                           on_delete=models.CASCADE,
                           related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'post']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.post}"

class Hashtag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    posts = models.ManyToManyField(Post, related_name='hashtags')
    posts_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"#{self.name}"

    def get_absolute_url(self):
        return reverse('posts:hashtag', kwargs={'name': self.name})

class Mention(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='mentions')
    post = models.ForeignKey(Post,
                           on_delete=models.CASCADE,
                           related_name='mentions')
    comment = models.ForeignKey(Comment,
                              on_delete=models.CASCADE,
                              null=True,
                              blank=True,
                              related_name='mentions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For notifications
    notifications = GenericRelation(Notification)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} mentioned in {self.post}"

class PostMedia(models.Model):
    MEDIA_TYPES = (
        ('image', _('Image')),
        ('video', _('Video')),
    )
    
    post = models.ForeignKey(Post,
                            on_delete=models.CASCADE,
                            related_name='media')
    file = models.FileField(upload_to='posts',
                          verbose_name=_('file'))
    media_type = models.CharField(_('media type'),
                                max_length=5,
                                choices=MEDIA_TYPES,
                                default='image')
    order = models.PositiveIntegerField(_('order'), default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = _('post media')
        verbose_name_plural = _('post media')

class CommentLike(models.Model):
    user = models.ForeignKey(User,
                           on_delete=models.CASCADE,
                           related_name='comment_likes')
    comment = models.ForeignKey(Comment,
                              on_delete=models.CASCADE,
                              related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')
        ordering = ['-created_at']
        verbose_name = _('comment like')
        verbose_name_plural = _('comment likes')

    def __str__(self):
        return f"{self.user.username} likes comment {self.comment.id}"

class Story(models.Model):
    MEDIA_TYPES = (
        ('image', _('Image')),
        ('video', _('Video')),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='stories')
    media = ProcessedImageField(upload_to='stories',
                              processors=[ResizeToFit(1080, 1920)],
                              format='JPEG',
                              options={'quality': 90})
    media_type = models.CharField(_('media type'),
                                max_length=5,
                                choices=MEDIA_TYPES,
                                default='image')
    caption = models.TextField(_('caption'), max_length=2200, blank=True)
    location = models.CharField(_('location'), max_length=100, blank=True)
    is_highlight = models.BooleanField(_('highlight'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    # Relationships
    viewers = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                   through='StoryView',
                                   related_name='viewed_stories')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('story')
        verbose_name_plural = _('stories')
    
    def __str__(self):
        return f"Story by {self.user.username} on {self.created_at}"

class StoryView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='story_views')
    story = models.ForeignKey(Story,
                            on_delete=models.CASCADE,
                            related_name='views')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'story')
        ordering = ['-created_at']
        verbose_name = _('story view')
        verbose_name_plural = _('story views')

class PostReport(models.Model):
    REASON_CHOICES = (
        ('spam', _('Spam')),
        ('inappropriate', _('Inappropriate content')),
        ('violence', _('Violence')),
        ('hate_speech', _('Hate speech')),
        ('other', _('Other')),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='post_reports')
    post = models.ForeignKey(Post,
                           on_delete=models.CASCADE,
                           related_name='reports')
    reason = models.CharField(_('reason'),
                            max_length=20,
                            choices=REASON_CHOICES)
    details = models.TextField(_('details'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
        verbose_name = _('post report')
        verbose_name_plural = _('post reports')
    
    def __str__(self):
        return f"Report on {self.post} by {self.user.username}"
