from django.contrib import admin

from .models import (
    Message,
    Thread,
    UserSetting,
    Conversation,
    ConversationParticipant,
    ConversationMessage,
    ReadReceipt,
)


@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'username', 'is_online', 'last_seen')
    list_filter = ('is_online',)
    search_fields = ('user__username', 'username')
    readonly_fields = ('last_seen',)


class MessageInline(admin.TabularInline):
    model = Message
    fields = ('sender', 'text', 'is_read', 'created_at')
    readonly_fields = ('sender', 'text', 'is_read', 'created_at')
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'unread_by_1', 'unread_by_2', 'created_at')
    search_fields = ('name', 'users__username')
    filter_horizontal = ('users',)
    inlines = (MessageInline,)
    readonly_fields = ('created_at', 'updated_at')


class ConversationParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0
    autocomplete_fields = ('user',)
    readonly_fields = ('joined_at',)


class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    fields = ('sender', 'short_content', 'created_at', 'is_deleted_for_everyone')
    readonly_fields = ('sender', 'short_content', 'created_at', 'is_deleted_for_everyone')
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ('-created_at',)

    def short_content(self, obj):
        text = (obj.content or '')[:80]
        return text or '(media/empty)'
    short_content.short_description = 'Nội dung'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'display_title',
        'is_group',
        'is_message_request',
        'participants_count',
        'last_message_time',
        'created_at',
    )
    list_filter = ('is_group', 'is_message_request', 'created_at')
    search_fields = ('name', 'participants__username', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'last_message_time')
    autocomplete_fields = ('created_by', 'message_request_for')
    date_hierarchy = 'last_message_time'
    inlines = (ConversationParticipantInline, ConversationMessageInline)
    actions = ['clear_message_request_flag']

    fieldsets = (
        ('Cuộc trò chuyện', {
            'fields': ('is_group', 'name', 'avatar', 'created_by'),
        }),
        ('Tin nhắn chờ', {
            'fields': ('is_message_request', 'message_request_for'),
            'description': 'Message request giống Facebook — người nhận chưa chấp nhận chat.',
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at', 'last_message_time'),
        }),
    )

    @admin.display(description='Tiêu đề')
    def display_title(self, obj):
        return obj.get_display_title()

    @admin.display(description='Thành viên')
    def participants_count(self, obj):
        return obj.participants.count()

    @admin.action(description='Gỡ cờ tin nhắn chờ (đánh dấu đã chấp nhận)')
    def clear_message_request_flag(self, request, queryset):
        updated = queryset.update(is_message_request=False, message_request_for=None)
        self.message_user(request, f'Đã cập nhật {updated} cuộc trò chuyện.')


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'user', 'is_admin', 'joined_at', 'left_at')
    list_filter = ('is_admin', 'joined_at')
    search_fields = ('user__username', 'conversation__name')
    autocomplete_fields = ('user', 'conversation')
    readonly_fields = ('joined_at',)


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'conversation',
        'sender',
        'preview',
        'created_at',
        'is_deleted_for_everyone',
        'has_attachment_flag',
    )
    list_filter = ('is_deleted_for_everyone', 'created_at')
    search_fields = ('content', 'sender__username', 'conversation__name')
    autocomplete_fields = ('sender', 'conversation', 'reply_to')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['soft_delete_for_everyone']

    @admin.display(description='Nội dung')
    def preview(self, obj):
        text = (obj.content or '').strip()
        if text:
            return text[:70] + ('…' if len(text) > 70 else '')
        if obj.image:
            return '[Ảnh]'
        if obj.video:
            return '[Video]'
        if obj.audio:
            return '[Audio]'
        if obj.document:
            return '[File]'
        return '—'

    @admin.display(boolean=True, description='Đính kèm')
    def has_attachment_flag(self, obj):
        return bool(obj.image or obj.video or obj.audio or obj.document or obj.shared_post_id)

    @admin.action(description='Xóa tin với mọi người (soft)')
    def soft_delete_for_everyone(self, request, queryset):
        updated = queryset.update(is_deleted_for_everyone=True, content='')
        self.message_user(request, f'Đã đánh dấu xóa {updated} tin nhắn.')


@admin.register(ReadReceipt)
class ReadReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'read_at')
    list_filter = ('read_at',)
    search_fields = ('user__username', 'message__content')
    autocomplete_fields = ('user', 'message')
    readonly_fields = ('read_at',)
