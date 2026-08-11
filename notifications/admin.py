from django.contrib import admin
from django.utils.html import format_html

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'recipient',
        'sender',
        'notification_type',
        'is_read',
        'created_at',
        'status_badge',
    )
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'sender__username')
    autocomplete_fields = ('recipient', 'sender', 'post', 'comment')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    actions = ['mark_read', 'mark_unread']

    @admin.display(description='Trạng thái')
    def status_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:#16a34a;font-weight:600;">Đã đọc</span>')
        return format_html('<span style="color:#dc2626;font-weight:600;">Chưa đọc</span>')

    @admin.action(description='Đánh dấu đã đọc')
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'Đã đánh dấu {updated} thông báo là đã đọc.')

    @admin.action(description='Đánh dấu chưa đọc')
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'Đã đánh dấu {updated} thông báo là chưa đọc.')
