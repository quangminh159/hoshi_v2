from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import path
from django.template.response import TemplateResponse
from django.shortcuts import render
from django import forms
from .models import User, UserFollowing, UserBlock, Device, DataDownloadRequest, UserReport

# Register your models here.

class CustomSuspendForm(forms.Form):
    suspension_days = forms.IntegerField(label='Số ngày đình chỉ', min_value=1, max_value=365)
    suspension_reason = forms.CharField(label='Lý do đình chỉ', widget=forms.Textarea, required=True)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', '_is_verified', 'is_suspended', 'is_deleted')
    list_filter = BaseUserAdmin.list_filter + ('_is_verified', 'is_suspended', 'is_deleted')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin cá nhân', {'fields': ('phone_number', 'bio', 'birth_date', 'gender', 'avatar')}),
        ('Liên kết mạng xã hội', {'fields': ('website', 'facebook', 'twitter', 'instagram', 'linkedin')}),
        ('Cài đặt thông báo', {'fields': ('push_notifications', 'email_notifications', 'like_notifications', 
                                        'comment_notifications', 'follow_notifications', 'mention_notifications')}),
        ('Cài đặt quyền riêng tư', {'fields': ('private_account', 'hide_activity', 'block_messages')}),
        ('Cài đặt bảo mật', {'fields': ('two_factor_auth', '_is_verified')}),
        ('Đình chỉ tài khoản', {'fields': ('is_suspended', 'suspension_reason', 'suspension_end_date')}),
        ('Xóa tài khoản', {'fields': ('is_deleted', 'deleted_at', 'deletion_reason')}),
    )
    
    actions = ['suspend_users_3days', 'suspend_users_7days', 'suspend_users_15days', 'suspend_users_30days', 'suspend_users_90days', 'suspend_users_custom', 'unsuspend_users', 'soft_delete_users', 'restore_deleted_users']
    
    def get_queryset(self, request):
        # Ghi đè phương thức này để sử dụng all_objects thay vì objects
        # Điều này giúp hiển thị cả người dùng đã bị xóa tạm thời trong admin
        return User.all_objects.get_queryset()
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('suspend-custom/', self.admin_site.admin_view(self.suspend_custom_view), name='accounts_user_suspend_custom'),
        ]
        return custom_urls + urls
    
    def suspend_custom_view(self, request):
        user_ids = request.POST.getlist('_selected_action')
        users = User.objects.filter(id__in=user_ids)
        
        if 'apply' in request.POST:
            form = CustomSuspendForm(request.POST)
            if form.is_valid():
                suspension_days = form.cleaned_data['suspension_days']
                suspension_reason = form.cleaned_data['suspension_reason']
                
                count = 0
                for user in users:
                    if not user.is_suspended:
                        user.suspend(suspension_reason, days=suspension_days)
                        count += 1
                
                self.message_user(request, f'Đã đình chỉ {count} tài khoản trong {suspension_days} ngày.')
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = CustomSuspendForm(initial={'suspension_days': 15, 'suspension_reason': 'Đình chỉ bởi quản trị viên'})
        
        context = {
            'form': form,
            'users': users,
            'opts': self.model._meta,
            'title': 'Tùy chỉnh thời gian đình chỉ tài khoản',
        }
        return render(request, 'admin/accounts/user/suspend_custom.html', context)
    
    def suspend_users_custom(self, request, queryset):
        selected = request.POST.getlist('_selected_action')
        return HttpResponseRedirect(f"suspend-custom/?ids={','.join(selected)}")
    suspend_users_custom.short_description = "Đình chỉ tài khoản được chọn (tùy chỉnh thời gian)"
    
    def suspend_users_3days(self, request, queryset):
        """Đình chỉ tài khoản người dùng được chọn trong 3 ngày"""
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend("Đình chỉ bởi quản trị viên", days=3)
                count += 1
        
        self.message_user(request, f'Đã đình chỉ {count} tài khoản trong 3 ngày.')
    suspend_users_3days.short_description = "Đình chỉ tài khoản được chọn (3 ngày)"
    
    def suspend_users_7days(self, request, queryset):
        """Đình chỉ tài khoản người dùng được chọn trong 7 ngày"""
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend("Đình chỉ bởi quản trị viên", days=7)
                count += 1
        
        self.message_user(request, f'Đã đình chỉ {count} tài khoản trong 7 ngày.')
    suspend_users_7days.short_description = "Đình chỉ tài khoản được chọn (7 ngày)"
    
    def suspend_users_15days(self, request, queryset):
        """Đình chỉ tài khoản người dùng được chọn trong 15 ngày"""
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend("Đình chỉ bởi quản trị viên", days=15)
                count += 1
        
        self.message_user(request, f'Đã đình chỉ {count} tài khoản trong 15 ngày.')
    suspend_users_15days.short_description = "Đình chỉ tài khoản được chọn (15 ngày)"
    
    def suspend_users_30days(self, request, queryset):
        """Đình chỉ tài khoản người dùng được chọn trong 30 ngày"""
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend("Đình chỉ bởi quản trị viên", days=30)
                count += 1
        
        self.message_user(request, f'Đã đình chỉ {count} tài khoản trong 30 ngày.')
    suspend_users_30days.short_description = "Đình chỉ tài khoản được chọn (30 ngày)"
    
    def suspend_users_90days(self, request, queryset):
        """Đình chỉ tài khoản người dùng được chọn trong 90 ngày"""
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend("Đình chỉ bởi quản trị viên", days=90)
                count += 1
        
        self.message_user(request, f'Đã đình chỉ {count} tài khoản trong 90 ngày.')
    suspend_users_90days.short_description = "Đình chỉ tài khoản được chọn (90 ngày)"
    
    def unsuspend_users(self, request, queryset):
        """Gỡ bỏ đình chỉ tài khoản người dùng được chọn"""
        count = 0
        for user in queryset:
            if user.is_suspended:
                user.unsuspend()
                count += 1
        
        self.message_user(request, f'Đã gỡ bỏ đình chỉ cho {count} tài khoản.')
    unsuspend_users.short_description = "Gỡ bỏ đình chỉ tài khoản được chọn"
    
    def soft_delete_users(self, request, queryset):
        """Xóa tạm thời người dùng (có thể khôi phục)"""
        # Kiểm tra xem có người dùng là admin trong danh sách không
        if queryset.filter(is_superuser=True).exists():
            self.message_user(request, 'Không thể xóa tài khoản quản trị viên!', level='error')
            return
        
        # Đánh dấu người dùng là đã xóa
        count = 0
        for user in queryset:
            if not user.is_deleted:
                user.is_deleted = True
                user.deleted_at = timezone.now()
                user.deletion_reason = "Xóa bởi quản trị viên"
                # Tạm ngừng hoạt động của tài khoản
                user.is_active = False
                user.save()
                count += 1
        
        self.message_user(request, f'Đã xóa tạm thời {count} tài khoản. Bạn có thể khôi phục các tài khoản này sau.')
    soft_delete_users.short_description = "Xóa tạm thời người dùng được chọn (có thể khôi phục)"
    
    def restore_deleted_users(self, request, queryset):
        """Khôi phục người dùng đã xóa tạm thời"""
        count = 0
        for user in queryset.filter(is_deleted=True):
            user.is_deleted = False
            user.deleted_at = None
            user.deletion_reason = None
            # Kích hoạt lại tài khoản
            user.is_active = True
            user.save()
            count += 1
        
        self.message_user(request, f'Đã khôi phục {count} tài khoản đã xóa.')
    restore_deleted_users.short_description = "Khôi phục người dùng đã xóa"
    
    def delete_selected_users(self, request, queryset):
        """Xóa người dùng được chọn khỏi hệ thống"""
        # Kiểm tra xem có người dùng là admin trong danh sách không
        if queryset.filter(is_superuser=True).exists():
            self.message_user(request, 'Không thể xóa tài khoản quản trị viên!', level='error')
            return
        
        # Đếm số tài khoản trước khi xóa
        count = queryset.count()
        
        # Xóa người dùng
        queryset.delete()
        
        self.message_user(request, f'Đã xóa {count} tài khoản khỏi hệ thống.')
    delete_selected_users.short_description = "Xóa vĩnh viễn người dùng được chọn"
    
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
    
    actions = ['mark_as_valid', 'mark_as_invalid', 'suspend_reported_users_3days', 'suspend_reported_users_7days', 'suspend_reported_users_15days', 'suspend_reported_users_30days', 'suspend_reported_users_90days', 'suspend_reported_users_custom', 'soft_delete_reported_users', 'delete_reported_users']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('suspend-reported-custom/', self.admin_site.admin_view(self.suspend_reported_custom_view), name='accounts_userreport_suspend_custom'),
        ]
        return custom_urls + urls
    
    def suspend_reported_custom_view(self, request):
        report_ids = request.POST.getlist('_selected_action')
        reports = UserReport.objects.filter(id__in=report_ids)
        
        if 'apply' in request.POST:
            form = CustomSuspendForm(request.POST)
            if form.is_valid():
                suspension_days = form.cleaned_data['suspension_days']
                suspension_reason = form.cleaned_data['suspension_reason']
                
                users_to_suspend = set()
                for report in reports:
                    if not report.reported_user.is_suspended:
                        users_to_suspend.add(report.reported_user)
                
                for user in users_to_suspend:
                    user.suspend(suspension_reason, days=suspension_days)
                
                self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo trong {suspension_days} ngày.')
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = CustomSuspendForm(initial={'suspension_days': 15, 'suspension_reason': 'Đình chỉ do vi phạm được báo cáo'})
        
        context = {
            'form': form,
            'reports': reports,
            'opts': self.model._meta,
            'title': 'Tùy chỉnh thời gian đình chỉ người dùng bị báo cáo',
        }
        return render(request, 'admin/accounts/userreport/suspend_custom.html', context)
    
    def suspend_reported_users_custom(self, request, queryset):
        selected = request.POST.getlist('_selected_action')
        return HttpResponseRedirect(f"suspend-reported-custom/?ids={','.join(selected)}")
    suspend_reported_users_custom.short_description = "Đình chỉ người dùng bị báo cáo được chọn (tùy chỉnh thời gian)"
    
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
    
    def suspend_reported_users_3days(self, request, queryset):
        """Đình chỉ người dùng bị báo cáo trong 3 ngày"""
        users_to_suspend = set()
        for report in queryset:
            if not report.reported_user.is_suspended:
                users_to_suspend.add(report.reported_user)
        
        for user in users_to_suspend:
            user.suspend("Đình chỉ do vi phạm được báo cáo", days=3)
        
        self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo trong 3 ngày.')
    suspend_reported_users_3days.short_description = "Đình chỉ người dùng bị báo cáo được chọn (3 ngày)"
    
    def suspend_reported_users_7days(self, request, queryset):
        """Đình chỉ người dùng bị báo cáo trong 7 ngày"""
        users_to_suspend = set()
        for report in queryset:
            if not report.reported_user.is_suspended:
                users_to_suspend.add(report.reported_user)
        
        for user in users_to_suspend:
            user.suspend("Đình chỉ do vi phạm được báo cáo", days=7)
        
        self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo trong 7 ngày.')
    suspend_reported_users_7days.short_description = "Đình chỉ người dùng bị báo cáo được chọn (7 ngày)"
    
    def suspend_reported_users_15days(self, request, queryset):
        """Đình chỉ người dùng bị báo cáo trong 15 ngày"""
        users_to_suspend = set()
        for report in queryset:
            if not report.reported_user.is_suspended:
                users_to_suspend.add(report.reported_user)
        
        for user in users_to_suspend:
            user.suspend("Đình chỉ do vi phạm được báo cáo", days=15)
        
        self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo trong 15 ngày.')
    suspend_reported_users_15days.short_description = "Đình chỉ người dùng bị báo cáo được chọn (15 ngày)"
    
    def suspend_reported_users_30days(self, request, queryset):
        """Đình chỉ người dùng bị báo cáo trong 30 ngày"""
        users_to_suspend = set()
        for report in queryset:
            if not report.reported_user.is_suspended:
                users_to_suspend.add(report.reported_user)
        
        for user in users_to_suspend:
            user.suspend("Đình chỉ do vi phạm được báo cáo", days=30)
        
        self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo trong 30 ngày.')
    suspend_reported_users_30days.short_description = "Đình chỉ người dùng bị báo cáo được chọn (30 ngày)"
    
    def suspend_reported_users_90days(self, request, queryset):
        """Đình chỉ người dùng bị báo cáo trong 90 ngày"""
        users_to_suspend = set()
        for report in queryset:
            if not report.reported_user.is_suspended:
                users_to_suspend.add(report.reported_user)
        
        for user in users_to_suspend:
            user.suspend("Đình chỉ do vi phạm được báo cáo", days=90)
        
        self.message_user(request, f'Đã đình chỉ {len(users_to_suspend)} người dùng bị báo cáo trong 90 ngày.')
    suspend_reported_users_90days.short_description = "Đình chỉ người dùng bị báo cáo được chọn (90 ngày)"
    
    def delete_reported_users(self, request, queryset):
        """Xóa vĩnh viễn người dùng bị báo cáo"""
        # Lấy danh sách người dùng bị báo cáo
        users_to_delete = set()
        for report in queryset:
            # Kiểm tra xem người dùng có phải là admin không
            if not report.reported_user.is_superuser and not report.reported_user.is_staff:
                users_to_delete.add(report.reported_user)
        
        # Nếu không có người dùng nào để xóa
        if not users_to_delete:
            self.message_user(request, 'Không thể xóa tài khoản quản trị viên hoặc nhân viên!', level='error')
            return
        
        # Đếm số người dùng trước khi xóa
        users_count = len(users_to_delete)
        
        # Xóa người dùng
        for user in users_to_delete:
            user.delete()
        
        # Cập nhật báo cáo là đã xử lý
        for report in queryset:
            if report.reported_user not in users_to_delete:
                continue
                
            report.resolve(request.user)
            report.is_valid = True
            report.admin_notes = 'Người dùng đã bị xóa do vi phạm quy định'
            report.save()
        
        self.message_user(request, f'Đã xóa vĩnh viễn {users_count} người dùng bị báo cáo.')
    delete_reported_users.short_description = "Xóa vĩnh viễn người dùng bị báo cáo được chọn"
    
    def soft_delete_reported_users(self, request, queryset):
        """Xóa tạm thời người dùng bị báo cáo (có thể khôi phục)"""
        # Lấy danh sách người dùng bị báo cáo
        users_to_delete = set()
        for report in queryset:
            # Kiểm tra xem người dùng có phải là admin không
            if not report.reported_user.is_superuser and not report.reported_user.is_staff and not report.reported_user.is_deleted:
                users_to_delete.add(report.reported_user)
        
        # Nếu không có người dùng nào để xóa
        if not users_to_delete:
            self.message_user(request, 'Không thể xóa tài khoản quản trị viên, nhân viên hoặc tài khoản đã bị xóa!', level='error')
            return
        
        # Đếm số người dùng trước khi xóa
        users_count = len(users_to_delete)
        
        # Đánh dấu người dùng là đã xóa
        for user in users_to_delete:
            user.is_deleted = True
            user.deleted_at = timezone.now()
            user.deletion_reason = "Xóa do vi phạm được báo cáo"
            # Tạm ngừng hoạt động của tài khoản
            user.is_active = False
            user.save()
        
        # Cập nhật báo cáo là đã xử lý
        for report in queryset:
            if report.reported_user not in users_to_delete:
                continue
                
            report.resolve(request.user)
            report.is_valid = True
            report.admin_notes = 'Người dùng đã bị xóa tạm thời do vi phạm quy định'
            report.save()
        
        self.message_user(request, f'Đã xóa tạm thời {users_count} người dùng bị báo cáo. Bạn có thể khôi phục các tài khoản này sau.')
    soft_delete_reported_users.short_description = "Xóa tạm thời người dùng bị báo cáo được chọn (có thể khôi phục)"
    
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
