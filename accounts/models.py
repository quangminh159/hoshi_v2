from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords

class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone_number = PhoneNumberField(_('phone number'), blank=True, null=True, unique=True)
    avatar = ProcessedImageField(upload_to='avatars',
                               processors=[ResizeToFill(300, 300)],
                               format='JPEG',
                               options={'quality': 90},
                               blank=True,
                               null=True)
    bio = models.TextField(_('bio'), max_length=500, blank=True)
    website = models.URLField(_('website'), max_length=200, blank=True)
    birth_date = models.DateField(_('birth date'), null=True, blank=True)
    gender = models.CharField(_('gender'), max_length=10, choices=[
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
    ], blank=True)
    is_private = models.BooleanField(_('private account'), default=False)
    is_verified = models.BooleanField(_('verified account'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Social links
    facebook = models.URLField(_('facebook'), max_length=200, blank=True)
    twitter = models.URLField(_('twitter'), max_length=200, blank=True)
    instagram = models.URLField(_('instagram'), max_length=200, blank=True)
    linkedin = models.URLField(_('linkedin'), max_length=200, blank=True)
    
    # Notification settings
    push_notifications = models.BooleanField(_('push notifications'), default=True)
    email_notifications = models.BooleanField(_('email notifications'), default=True)
    like_notifications = models.BooleanField(_('like notifications'), default=True)
    comment_notifications = models.BooleanField(_('comment notifications'), default=True)
    follow_notifications = models.BooleanField(_('follow notifications'), default=True)
    mention_notifications = models.BooleanField(_('mention notifications'), default=True)
    
    # Privacy settings
    private_account = models.BooleanField(_('private account'), default=False)
    hide_activity = models.BooleanField(_('hide activity status'), default=False)
    block_messages = models.BooleanField(_('block messages from non-followers'), default=False)
    
    # Security settings
    two_factor_auth = models.BooleanField(_('two-factor authentication'), default=False)
    
    # Relationships
    followers = models.ManyToManyField('self', 
                                     through='UserFollowing',
                                     related_name='following',
                                     symmetrical=False)
    
    # Add historical records
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_followers_count(self):
        return self.followers.count()
    
    def get_following_count(self):
        return self.following.count()
    
    def get_posts_count(self):
        return self.posts.count()

    def get_avatar_url(self):
        # Nếu có avatar, trả về URL của avatar
        if self.avatar:
            return self.avatar.url
        
        # Nếu không có avatar, trả về avatar mặc định dựa trên giới tính
        if self.gender == 'M':
            return '/static/img/default-avatar-male.png'
        elif self.gender == 'F':
            return '/static/img/default-avatar-female.png'
        
        # Nếu không có giới tính, trả về avatar mặc định chung
        return '/static/img/default-avatar.png'

class UserFollowing(models.Model):
    user = models.ForeignKey(User,
                            related_name='following_relationships',
                            on_delete=models.CASCADE)
    following_user = models.ForeignKey(User,
                                     related_name='followers_relationships',
                                     on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'following_user')
        ordering = ['-created_at']
        verbose_name = _('following')
        verbose_name_plural = _('followings')
    
    def __str__(self):
        return f"{self.user} follows {self.following_user}"

class Device(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=50)  # mobile, tablet, desktop
    device_name = models.CharField(max_length=255)
    browser = models.CharField(max_length=100)
    os = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-last_active']
        
    def __str__(self):
        return f"{self.device_name} ({self.device_type})"

class DataDownloadRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Đang xử lý'),
        ('ready', 'Sẵn sàng tải xuống'),
        ('expired', 'Đã hết hạn'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    include_media = models.BooleanField(default=False)
    file_path = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at and self.status == 'ready':
            # Đặt thời gian hết hạn là 48 giờ sau khi file sẵn sàng
            self.expires_at = timezone.now() + timezone.timedelta(hours=48)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Data request for {self.user.username} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']
