from django.contrib import admin
from django.utils import timezone
from .models import Post, Media, PostMedia, Like, Comment, SavedPost, Hashtag, Mention, CommentLike, Story, StoryView, PostReport, UserInteraction

# Register your models here.

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'created_at', 'likes_count', 'comments_count', 'is_archived')
    list_filter = ('is_archived', 'created_at')
    search_fields = ('author__username', 'caption', 'location')
    readonly_fields = ('created_at', 'updated_at', 'likes_count', 'comments_count')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Thông tin bài viết', {
            'fields': ('author', 'caption', 'location', 'created_at', 'updated_at')
        }),
        ('Thống kê', {
            'fields': ('likes_count', 'comments_count')
        }),
        ('Cài đặt', {
            'fields': ('disable_comments', 'hide_likes', 'is_archived')
        }),
        ('Chia sẻ', {
            'fields': ('shared_from',)
        }),
    )
    
    actions = ['archive_posts', 'unarchive_posts', 'disable_comments', 'enable_comments']
    
    def archive_posts(self, request, queryset):
        updated = queryset.update(is_archived=True)
        self.message_user(request, f'Đã lưu trữ {updated} bài viết.')
    archive_posts.short_description = "Lưu trữ bài viết được chọn"
    
    def unarchive_posts(self, request, queryset):
        updated = queryset.update(is_archived=False)
        self.message_user(request, f'Đã bỏ lưu trữ {updated} bài viết.')
    unarchive_posts.short_description = "Bỏ lưu trữ bài viết được chọn"
    
    def disable_comments(self, request, queryset):
        updated = queryset.update(disable_comments=True)
        self.message_user(request, f'Đã tắt bình luận cho {updated} bài viết.')
    disable_comments.short_description = "Tắt bình luận bài viết được chọn"
    
    def enable_comments(self, request, queryset):
        updated = queryset.update(disable_comments=False)
        self.message_user(request, f'Đã bật bình luận cho {updated} bài viết.')
    enable_comments.short_description = "Bật bình luận bài viết được chọn"

@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reason', 'created_at', 'is_resolved', 'is_valid')
    list_filter = ('reason', 'is_resolved', 'is_valid', 'created_at')
    search_fields = ('user__username', 'post__caption', 'details')
    readonly_fields = ('user', 'post', 'reason', 'details', 'created_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Thông tin báo cáo', {
            'fields': ('user', 'post', 'reason', 'details', 'created_at')
        }),
        ('Xét duyệt', {
            'fields': ('is_resolved', 'is_valid', 'admin_notes', 'resolved_at', 'resolved_by')
        }),
    )
    
    actions = ['mark_as_valid', 'mark_as_invalid', 'delete_reported_posts']
    
    def mark_as_valid(self, request, queryset):
        """Đánh dấu báo cáo là hợp lệ"""
        for report in queryset.filter(is_resolved=False):
            report.resolve(request.user)
            report.is_valid = True
            report.admin_notes = report.admin_notes or 'Báo cáo được xác nhận là hợp lệ'
            report.save()
        
        self.message_user(request, f'Đã đánh dấu {queryset.filter(is_resolved=True).count()} báo cáo là hợp lệ.')
    mark_as_valid.short_description = "Đánh dấu báo cáo được chọn là hợp lệ"
    
    def mark_as_invalid(self, request, queryset):
        """Đánh dấu báo cáo là không hợp lệ"""
        for report in queryset.filter(is_resolved=False):
            report.resolve(request.user)
            report.is_valid = False
            report.admin_notes = report.admin_notes or 'Báo cáo được xác nhận là không hợp lệ'
            report.save()
        
        self.message_user(request, f'Đã đánh dấu {queryset.filter(is_resolved=True).count()} báo cáo là không hợp lệ.')
    mark_as_invalid.short_description = "Đánh dấu báo cáo được chọn là không hợp lệ"
    
    def delete_reported_posts(self, request, queryset):
        """Xóa bài viết bị báo cáo"""
        posts_to_delete = set()
        for report in queryset:
            posts_to_delete.add(report.post)
        
        # Xóa bài viết
        posts_count = len(posts_to_delete)
        for post in posts_to_delete:
            post.delete()
        
        # Đánh dấu báo cáo là đã xử lý
        for report in queryset:
            report.resolve(request.user)
            report.is_valid = True
            report.admin_notes = 'Bài viết đã bị xóa do vi phạm quy định'
            report.save()
        
        self.message_user(request, f'Đã xóa {posts_count} bài viết bị báo cáo.')
    delete_reported_posts.short_description = "Xóa bài viết bị báo cáo được chọn"
    
    def save_model(self, request, obj, form, change):
        """Xử lý khi lưu model"""
        # Nếu báo cáo được đánh dấu là đã xem xét
        if 'is_resolved' in form.changed_data and obj.is_resolved:
            # Cập nhật thông tin người xem xét
            obj.resolved_by = request.user
            obj.resolved_at = timezone.now()
        
        super().save_model(request, obj, form, change)

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'media_type', 'order')
    list_filter = ('media_type',)
    search_fields = ('post__caption', 'post__author__username')

@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'media_type', 'order', 'created_at')
    list_filter = ('media_type', 'created_at')
    search_fields = ('post__caption', 'post__author__username')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'text', 'created_at', 'likes_count')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'text', 'post__caption')
    readonly_fields = ('created_at', 'updated_at', 'likes_count')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__caption')
    readonly_fields = ('created_at',)

@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'comment__text')
    readonly_fields = ('created_at',)

@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__caption')
    readonly_fields = ('created_at',)

@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'posts_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    readonly_fields = ('posts_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Mention)
class MentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__caption')
    readonly_fields = ('created_at',)

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'media_type', 'created_at', 'expires_at', 'is_highlight')
    list_filter = ('is_highlight', 'media_type', 'created_at')
    search_fields = ('user__username', 'caption', 'location')
    readonly_fields = ('created_at',)

@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'story', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'story__caption')
    readonly_fields = ('created_at',)

@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'interaction_type', 'duration', 'created_at')
    list_filter = ('interaction_type', 'created_at')
    search_fields = ('user__username', 'post__caption')
    readonly_fields = ('created_at',)
