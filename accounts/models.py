from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords
from functools import partial

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
    _is_verified = models.BooleanField(_('verified account'), default=False, db_column='is_verified')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Social links
    facebook = models.URLField(_('facebook'), max_length=200, blank=True)
    twitter = models.URLField(_('twitter'), max_length=200, blank=True)
    instagram = models.URLField(_('instagram'), max_length=200, blank=True)
    linkedin = models.URLField(_('linkedin'), max_length=200, blank=True)
    
    # Notification settings
    push_notifications = models.BooleanField(_('push notifications'), default=False)
    email_notifications = models.BooleanField(_('email notifications'), default=False)
    like_notifications = models.BooleanField(_('like notifications'), default=False)
    comment_notifications = models.BooleanField(_('comment notifications'), default=False)
    follow_notifications = models.BooleanField(_('follow notifications'), default=False)
    mention_notifications = models.BooleanField(_('mention notifications'), default=False)
    message_notifications = models.BooleanField(_('message notifications'), default=False)
    
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
    blocked_users = models.ManyToManyField('self',
                                     through='UserBlock',
                                     related_name='blocked_by',
                                     symmetrical=False)
    
    # Add historical records
    history = HistoricalRecords()
    
    @property
    def is_verified(self):
        """Ensure is_verified always returns a boolean value"""
        if isinstance(self._is_verified, bool):
            return self._is_verified
        return False
        
    @is_verified.setter
    def is_verified(self, value):
        """Ensure is_verified is always stored as a boolean value"""
        if isinstance(value, bool):
            self._is_verified = value
        else:
            self._is_verified = False
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        
    def __str__(self):
        return self.username
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_followers_count(self):
        return self.followers_relationships.count()
    
    def get_following_count(self):
        return self.following_relationships.count()
    
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
        
    def is_blocked(self, user):
        """Kiểm tra xem người dùng hiện tại có bị chặn bởi user không"""
        return UserBlock.objects.filter(blocker=user, blocked=self).exists()
        
    def has_blocked(self, user):
        """Kiểm tra xem người dùng hiện tại có chặn user không"""
        return UserBlock.objects.filter(blocker=self, blocked=user).exists()

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

class UserBlock(models.Model):
    blocker = models.ForeignKey(User,
                             related_name='blocking_relationships',
                             on_delete=models.CASCADE)
    blocked = models.ForeignKey(User,
                             related_name='blocked_relationships',
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(_('reason'), blank=True, null=True)
    
    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']
        verbose_name = _('block')
        verbose_name_plural = _('blocks')
    
    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"

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
