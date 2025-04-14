from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords
from functools import partial
from django.utils.safestring import mark_safe
import hashlib
import os.path

class ActiveUserManager(UserManager):
    """Quản lý người dùng đang hoạt động, không bị xóa tạm thời"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class AllUserManager(UserManager):
    """Quản lý tất cả người dùng, bao gồm cả người dùng đã bị xóa tạm thời"""
    def get_queryset(self):
        return super().get_queryset()

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
    
    # Soft delete field
    is_deleted = models.BooleanField(_('deleted account'), default=False)
    deleted_at = models.DateTimeField(_('deleted at'), null=True, blank=True)
    deletion_reason = models.TextField(_('deletion reason'), blank=True, null=True)
    
    # Suspension fields
    is_suspended = models.BooleanField(_('suspended account'), default=False)
    suspension_reason = models.TextField(_('suspension reason'), blank=True, null=True)
    suspension_end_date = models.DateTimeField(_('suspension end date'), blank=True, null=True)
    
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
    
    # Managers
    objects = ActiveUserManager()  # Manager mặc định chỉ trả về người dùng chưa bị xóa
    all_objects = AllUserManager()  # Manager để truy vấn tất cả người dùng, kể cả đã bị xóa
    
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
        
        # Tạo URL cho avatar dạng text dựa trên username
        username = self.username or ''
        name_hash = hashlib.md5(username.encode('utf-8')).hexdigest()
        hue = int(name_hash[:8], 16) % 360  # Chọn màu dựa trên hash của tên người dùng
        
        # Kiểm tra các đường dẫn có file avatar mặc định
        avatar_base_url = getattr(settings, 'STATIC_URL', '/static/')
        
        # Thử với file ảnh mặc định theo giới tính
        gender_avatar_path = None
        if self.gender == 'M':
            gender_avatar_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'default-avatar-male.png')
            if os.path.exists(gender_avatar_path) and os.path.getsize(gender_avatar_path) > 100:
                return f"{avatar_base_url}img/default-avatar-male.png"
        elif self.gender == 'F':
            gender_avatar_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'default-avatar-female.png')
            if os.path.exists(gender_avatar_path) and os.path.getsize(gender_avatar_path) > 100:
                return f"{avatar_base_url}img/default-avatar-female.png"
        
        # Thử với file ảnh mặc định chung
        default_avatar_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'default-avatar.png')
        if os.path.exists(default_avatar_path) and os.path.getsize(default_avatar_path) > 100:
            return f"{avatar_base_url}img/default-avatar.png"
        
        # Nếu không có file ảnh mặc định hoặc file quá nhỏ, trả về data URL cho avatar text
        return self.generate_text_avatar()
        
    def generate_text_avatar(self):
        # Tạo avatar dựa trên chữ cái đầu của tên người dùng
        username = self.username or ''
        initial = username[0].upper() if username else '?'
        
        # Tạo màu ngẫu nhiên nhưng nhất quán dựa trên username
        name_hash = hashlib.md5(username.encode('utf-8')).hexdigest()
        hue = int(name_hash[:8], 16) % 360
        
        # Tạo data URL với SVG
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
            <rect width="100" height="100" fill="hsl({hue}, 70%, 60%)" />
            <text x="50" y="50" font-family="Arial, sans-serif" font-size="45" 
                  font-weight="bold" fill="white" text-anchor="middle" dominant-baseline="central">
                {initial}
            </text>
        </svg>
        '''
        
        import base64
        svg_bytes = svg.encode('utf-8')
        b64_svg = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{b64_svg}"
        
    def is_blocked(self, user):
        """Kiểm tra xem người dùng hiện tại có bị chặn bởi user không"""
        return UserBlock.objects.filter(blocker=user, blocked=self).exists()
        
    def has_blocked(self, user):
        """Kiểm tra xem người dùng hiện tại có chặn user không"""
        return UserBlock.objects.filter(blocker=self, blocked=user).exists()
        
    def has_block_relationship(self, user):
        """Kiểm tra xem có tồn tại mối quan hệ chặn giữa hai người dùng không (theo cả hai chiều)"""
        return self.is_blocked(user) or self.has_blocked(user)
        
    def get_custom_social_links(self):
        """Trả về các liên kết mạng xã hội tùy chỉnh"""
        # Danh sách các trường mạng xã hội tiêu chuẩn
        standard_fields = ['website', 'facebook', 'twitter', 'instagram', 'linkedin']
        custom_links = {}
        
        # Lấy tất cả các thuộc tính của đối tượng
        for field in self._meta.fields:
            field_name = field.name
            
            # Kiểm tra nếu là URLField và không phải là trường tiêu chuẩn
            if isinstance(field, models.URLField) and field_name not in standard_fields:
                value = getattr(self, field_name)
                if value:  # Chỉ thêm vào nếu có giá trị
                    # Chuyển đổi tên trường thành tên hiển thị đẹp hơn
                    display_name = field_name.replace('_', ' ')
                    custom_links[display_name] = value
                    
        return custom_links

    def check_suspension_status(self):
        """Kiểm tra và cập nhật trạng thái đình chỉ"""
        # Nếu không bị đình chỉ, không cần kiểm tra
        if not self.is_suspended:
            return False
            
        # Nếu đã hết thời gian đình chỉ, cập nhật trạng thái
        if self.suspension_end_date and timezone.now() >= self.suspension_end_date:
            self.is_suspended = False
            self.suspension_reason = None
            self.suspension_end_date = None
            self.save(update_fields=['is_suspended', 'suspension_reason', 'suspension_end_date'])
            return False
            
        # Vẫn đang trong thời gian đình chỉ
        return True
    
    def is_usable(self):
        """Kiểm tra xem tài khoản có thể sử dụng được không (không bị đình chỉ và không bị xóa)"""
        # Kiểm tra xem tài khoản có bị xóa không
        if self.is_deleted:
            return False
            
        # Cập nhật trạng thái đình chỉ (nếu hết hạn sẽ tự động gỡ đình chỉ)
        is_still_suspended = self.check_suspension_status()
        
        # Nếu vẫn bị đình chỉ, tài khoản không thể sử dụng
        if is_still_suspended:
            return False
            
        # Tài khoản có thể sử dụng
        return True
    
    def suspend(self, reason, days=15):
        """Đình chỉ tài khoản người dùng"""
        self.is_suspended = True
        self.suspension_reason = reason
        self.suspension_end_date = timezone.now() + timezone.timedelta(days=days)
        self.save(update_fields=['is_suspended', 'suspension_reason', 'suspension_end_date'])
        
    def unsuspend(self):
        """Gỡ bỏ đình chỉ tài khoản"""
        self.is_suspended = False
        self.suspension_reason = None
        self.suspension_end_date = None
        self.save(update_fields=['is_suspended', 'suspension_reason', 'suspension_end_date'])

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

class UserReport(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.CharField(_('reason'), max_length=100)
    description = models.TextField(_('description'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(_('resolved'), default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='resolved_reports',
        null=True,
        blank=True
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Thêm trường mới cho việc đánh giá báo cáo
    is_valid = models.BooleanField(_('valid report'), null=True, blank=True)
    admin_notes = models.TextField(_('admin notes'), blank=True, null=True)
    
    class Meta:
        unique_together = ('reporter', 'reported_user')
        ordering = ['-created_at']
        verbose_name = _('user report')
        verbose_name_plural = _('user reports')
    
    def __str__(self):
        return f"{self.reporter} reported {self.reported_user} for {self.reason}"
        
    def resolve(self, resolved_by):
        self.resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.save()
        
    @staticmethod
    def check_for_automatic_suspension(user):
        """Kiểm tra và tự động đình chỉ người dùng nếu có quá nhiều báo cáo hợp lệ"""
        # Lấy số lượng báo cáo hợp lệ trong 30 ngày qua
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        valid_reports = UserReport.objects.filter(
            reported_user=user,
            is_valid=True,
            created_at__gte=thirty_days_ago
        ).count()
        
        # Nếu có từ 5 báo cáo hợp lệ trở lên trong 30 ngày, đình chỉ tài khoản 15 ngày
        if valid_reports >= 5 and not user.is_suspended:
            user.is_suspended = True
            user.suspension_reason = "Nhiều báo cáo vi phạm hợp lệ"
            user.suspension_end_date = timezone.now() + timezone.timedelta(days=15)
            user.save(update_fields=['is_suspended', 'suspension_reason', 'suspension_end_date'])
            return True
        
        return False
