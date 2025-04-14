from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django.utils import timezone
from .models import User, UserFollowing, UserBlock, Device, DataDownloadRequest, UserReport

# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', '_is_verified', 'is_suspended')
    list_filter = BaseUserAdmin.list_filter + ('_is_verified', 'is_suspended')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin cá nhân', {'fields': ('phone_number', 'bio', 'birth_date', 'gender', 'avatar')}),
        ('Liên kết mạng xã hội', {'fields': ('website', 'facebook', 'twitter', 'instagram', 'linkedin')}),
        ('Cài đặt thông báo', {'fields': ('push_notifications', 'email_notifications', 'like_notifications', 
                                        'comment_notifications', 'follow_notifications', 'mention_notifications')}),
        ('Cài đặt quyền riêng tư', {'fields': ('private_account', 'hide_activity', 'block_messages')}),
        ('Cài đặt bảo mật', {'fields': ('two_factor_auth', '_is_verified')}),
        ('Đình chỉ tài khoản', {'fields': ('is_suspended', 'suspension_reason', 'suspension_end_date')}),
    )
    
    actions = ['suspend_users', 'unsuspend_users']
    
    def suspend_users(self, request, queryset):
        """Đình chỉ tài khoản người dùng được chọn trong 15 ngày"""
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend("Đình chỉ bởi quản trị viên", days=15)
                count += 1
        
        self.message_user(request, f'Đã đình chỉ {count} tài khoản trong 15 ngày.')
    suspend_users.short_description = "Đình chỉ tài khoản được chọn (15 ngày)"
    
    def unsuspend_users(self, request, queryset):
        """Gỡ bỏ đình chỉ tài khoản người dùng được chọn"""
        count = 0
        for user in queryset:
            if user.is_suspended:
                user.unsuspend()
                count += 1
        
        self.message_user(request, f'Đã gỡ bỏ đình chỉ cho {count} tài khoản.')
    unsuspend_users.short_description = "Gỡ bỏ đình chỉ tài khoản được chọn"
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        
        # Nếu có đối tượng (khi chỉnh sửa) và có các trường mạng xã hội tùy chỉnh
        if obj:
            custom_social_fields = []
            
            # Lấy tất cả các trường URL không phải là trường tiêu chuẩn
            standard_fields = ['website', 'facebook', 'twitter', 'instagram', 'linkedin']
            
            for field in obj._meta.fields:
                if isinstance(field, models.URLField) and field.name not in standard_fields:
                    custom_social_fields.append(field.name)
            
            # Nếu có trường tùy chỉnh, thêm vào fieldsets
            if custom_social_fields:
                # Tìm fieldset liên kết mạng xã hội
                for i, (name, options) in enumerate(fieldsets):
                    if name == 'Liên kết mạng xã hội':
                        # Lấy danh sách trường hiện tại và thêm các trường tùy chỉnh
                        current_fields = list(options['fields'])
                        current_fields.extend(custom_social_fields)
                        
                        # Cập nhật danh sách trường
                        fieldsets[i] = (name, {'fields': tuple(current_fields)})
                        break
        
        return fieldsets

@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'reason', 'created_at', 'resolved', 'is_valid')
    list_filter = ('reason', 'resolved', 'is_valid', 'created_at')
    search_fields = ('reporter__username', 'reported_user__username', 'description')
    readonly_fields = ('reporter', 'reported_user', 'reason', 'description', 'created_at')
    fieldsets = (
        ('Thông tin báo cáo', {
            'fields': ('reporter', 'reported_user', 'reason', 'description', 'created_at')
        }),
        ('Xét duyệt', {
            'fields': ('resolved', 'is_valid', 'admin_notes', 'resolved_at', 'resolved_by')
        }),
    )
    
    actions = ['mark_as_valid', 'mark_as_invalid', 'suspend_reported_users']
    
    def mark_as_valid(self, request, queryset):
        """Đánh dấu báo cáo là hợp lệ"""
        for report in queryset.filter(resolved=False):
            report.resolve(request.user)
            report.is_valid = True
            report.admin_notes = 'Báo cáo được xác nhận là hợp lệ'
            report.save()
        
        self.message_user(request, f'Đã đánh dấu {queryset.filter(resolved=True).count()} báo cáo là hợp lệ.')
    mark_as_valid.short_description = "Đánh dấu báo cáo được chọn là hợp lệ"
    
    def mark_as_invalid(self, request, queryset):
        """Đánh dấu báo cáo là không hợp lệ"""
        for report in queryset.filter(resolved=False):
            report.resolve(request.user)
            report.is_valid = False
            report.admin_notes = 'Báo cáo được xác nhận là không hợp lệ'
            report.save()
        
        self.message_user(request, f'Đã đánh dấu {queryset.filter(resolved=True).count()} báo cáo là không hợp lệ.')
    mark_as_invalid.short_description = "Đánh dấu báo cáo được chọn là không hợp lệ"
    
    def suspend_reported_users(self, request, queryset):
        """Đình chỉ người dùng bị báo cáo trong 15 ngày"""
        users_to_suspend = set()
        for report in queryset:
            if not report.reported_user.is_suspended:
                users_to_suspend.add(report.reported_user)
        
        for user in users_to_suspend:
            user.suspend("Đình chỉ do vi phạm được báo cáo", days=15)
        
        self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo.')
    suspend_reported_users.short_description = "Đình chỉ người dùng bị báo cáo được chọn (15 ngày)"
    
    def save_model(self, request, obj, form, change):
        """Xử lý khi lưu model"""
        # Nếu báo cáo được đánh dấu là đã xem xét
        if 'resolved' in form.changed_data and obj.resolved:
            # Cập nhật thông tin người xem xét
            obj.resolved_by = request.user
            obj.resolved_at = timezone.now()
            
            # Nếu báo cáo được đánh dấu là hợp lệ, kiểm tra xem có cần đình chỉ người dùng không
            if obj.is_valid:
                UserReport.check_for_automatic_suspension(obj.reported_user)
        
        super().save_model(request, obj, form, change)

@admin.register(UserFollowing)
class UserFollowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'following_user', 'created_at')
    search_fields = ('user__username', 'following_user__username')

@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username', 'reason')

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'device_type', 'ip_address', 'last_active', 'is_current')
    list_filter = ('device_type', 'is_current')
    search_fields = ('user__username', 'device_name', 'ip_address')

@admin.register(DataDownloadRequest)
class DataDownloadRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'expires_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'file_path')
