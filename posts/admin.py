from django.contrib import admin
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import render
from django.urls import path
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from .models import Post, Media, PostMedia, Like, Comment, SavedPost, Hashtag, Mention, CommentLike, Story, StoryView, PostReport, UserInteraction
from .viral import (
    promote_post_viral,
    demote_post_viral,
    refresh_viral_score,
    ADMIN_PROMOTE_SCORE,
    is_post_trending,
)

User = get_user_model()


class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 0
    fields = ('file', 'media_type', 'order', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'author',
        'short_caption',
        'created_at',
        'likes_count',
        'comments_count',
        'views_count',
        'viral_score',
        'promoted_badge',
        'trending_badge',
        'is_archived',
        'visibility',
        'disable_comments',
    )
    list_filter = ('admin_promoted', 'visibility', 'is_archived', 'disable_comments', 'created_at')
    search_fields = ('author__username', 'caption', 'location', 'id')
    readonly_fields = (
        'created_at',
        'updated_at',
        'likes_count',
        'comments_count',
        'views_count',
        'shares_count',
        'saves_count',
        'viral_score_updated_at',
        'trending_status',
    )
    date_hierarchy = 'created_at'
    autocomplete_fields = ('author', 'shared_from')
    list_per_page = 40
    ordering = ('-admin_promoted', '-viral_score', '-created_at')
    list_editable = ('viral_score',)
    inlines = [PostMediaInline]
    actions = [
        'promote_viral',
        'demote_viral',
        'recalculate_viral',
        'archive_posts',
        'unarchive_posts',
        'disable_comments_action',
        'enable_comments',
    ]

    @admin.display(description='Caption')
    def short_caption(self, obj):
        text = (obj.caption or '').strip()
        return (text[:60] + '…') if len(text) > 60 else (text or '—')

    @admin.display(description='Admin viral', boolean=True)
    def promoted_badge(self, obj):
        return bool(obj.admin_promoted)

    @admin.display(description='Trending')
    def trending_badge(self, obj):
        if is_post_trending(obj):
            return format_html('<span style="color:#c2410c;font-weight:700;">🔥 Viral</span>')
        return '—'

    @admin.display(description='Trạng thái trending')
    def trending_status(self, obj):
        if is_post_trending(obj):
            reason = 'admin đẩy' if obj.admin_promoted else 'thuật toán'
            return f'Đang thịnh hành ({reason}) — điểm {obj.viral_score:.1f}'
        return f'Không trending — điểm {obj.viral_score:.1f}'

    fieldsets = (
        ('Thông tin bài viết', {
            'fields': ('author', 'caption', 'location', 'created_at', 'updated_at'),
            'description': 'Admin có thể sửa caption / location / tác giả của mọi bài.',
        }),
        ('Thống kê', {
            'fields': (
                'likes_count',
                'comments_count',
                'views_count',
                'shares_count',
                'saves_count',
            ),
        }),
        ('Viral / Trending (admin)', {
            'fields': (
                'admin_promoted',
                'admin_viral_boost',
                'viral_score',
                'viral_score_updated_at',
                'trending_status',
            ),
            'description': (
                'Bật "Admin đẩy viral" hoặc dùng action danh sách. '
                f'Sàn điểm mặc định ≈ {ADMIN_PROMOTE_SCORE:.0f}. '
                'Điểm tự nhiên không hạ xuống dưới sàn khi đang promote.'
            ),
        }),
        ('Cài đặt', {
            'fields': ('disable_comments', 'hide_likes', 'visibility', 'is_archived'),
        }),
        ('Chia sẻ', {
            'fields': ('shared_from',),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Đồng bộ sàn điểm khi admin tick promote hoặc sửa boost
        if obj.admin_promoted:
            floor = float(obj.admin_viral_boost or 0) or ADMIN_PROMOTE_SCORE
            if float(obj.viral_score or 0) < floor or not obj.admin_viral_boost:
                promote_post_viral(obj.id, score=floor)
        elif 'admin_promoted' in getattr(form, 'changed_data', []):
            demote_post_viral(obj.id)

    @admin.action(description='🔥 Đẩy viral / trending bài đã chọn')
    def promote_viral(self, request, queryset):
        n = 0
        for post in queryset:
            promote_post_viral(post.id)
            n += 1
        self.message_user(request, f'Đã đẩy viral {n} bài viết (điểm ≥ {ADMIN_PROMOTE_SCORE:.0f}).')

    @admin.action(description='Gỡ ép viral — tính lại điểm tự nhiên')
    def demote_viral(self, request, queryset):
        n = 0
        for post in queryset:
            demote_post_viral(post.id)
            n += 1
        self.message_user(request, f'Đã gỡ ép viral {n} bài viết.')

    @admin.action(description='Tính lại điểm viral (giữ sàn nếu đang promote)')
    def recalculate_viral(self, request, queryset):
        n = 0
        for post in queryset:
            refresh_viral_score(post.id, force=True)
            n += 1
        self.message_user(request, f'Đã tính lại viral_score cho {n} bài.')

    @admin.action(description='Lưu trữ bài viết được chọn')
    def archive_posts(self, request, queryset):
        updated = queryset.update(is_archived=True)
        self.message_user(request, f'Đã lưu trữ {updated} bài viết.')

    @admin.action(description='Bỏ lưu trữ bài viết được chọn')
    def unarchive_posts(self, request, queryset):
        updated = queryset.update(is_archived=False)
        self.message_user(request, f'Đã bỏ lưu trữ {updated} bài viết.')

    @admin.action(description='Tắt bình luận bài viết được chọn')
    def disable_comments_action(self, request, queryset):
        updated = queryset.update(disable_comments=True)
        self.message_user(request, f'Đã tắt bình luận cho {updated} bài viết.')

    @admin.action(description='Bật bình luận bài viết được chọn')
    def enable_comments(self, request, queryset):
        updated = queryset.update(disable_comments=False)
        self.message_user(request, f'Đã bật bình luận cho {updated} bài viết.')


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reason', 'created_at', 'is_resolved', 'is_valid', 'pending_badge')
    list_filter = ('reason', 'is_resolved', 'is_valid', 'created_at')
    search_fields = ('user__username', 'post__caption', 'details')
    readonly_fields = ('user', 'post', 'reason', 'details', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('is_resolved', '-created_at')
    list_per_page = 40
    autocomplete_fields = ('resolved_by',)

    @admin.display(description='Hàng đợi')
    def pending_badge(self, obj):
        if obj.is_resolved:
            return format_html('<span style="color:#16a34a;">Đã xử lý</span>')
        return format_html('<span style="color:#dc2626;font-weight:700;">Chờ duyệt</span>')

    fieldsets = (
        ('Thông tin báo cáo', {
            'fields': ('user', 'post', 'reason', 'details', 'created_at')
        }),
        ('Xét duyệt', {
            'fields': ('is_resolved', 'is_valid', 'admin_notes', 'resolved_at', 'resolved_by')
        }),
    )

    actions = ['mark_as_valid', 'mark_as_invalid', 'delete_reported_posts']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('report-statistics/', self.admin_site.admin_view(self.report_statistics_view), name='report_statistics'),
        ]
        return custom_urls + urls

    def report_statistics_view(self, request):
        most_reported_posts = Post.objects.annotate(
            report_count=Count('reports')
        ).filter(report_count__gt=0).order_by('-report_count')[:10]

        most_reported_authors = User.objects.annotate(
            post_report_count=Count('posts__reports')
        ).filter(post_report_count__gt=0).order_by('-post_report_count')[:10]

        most_reporting_users = User.objects.annotate(
            report_count=Count('post_reports')
        ).filter(report_count__gt=0).order_by('-report_count')[:10]

        report_reasons = PostReport.objects.values('reason').annotate(
            count=Count('id')
        ).order_by('-count')

        recent_reports = PostReport.objects.all().order_by('-created_at')[:20]

        report_status = {
            'total': PostReport.objects.count(),
            'resolved': PostReport.objects.filter(is_resolved=True).count(),
            'valid': PostReport.objects.filter(is_valid=True).count(),
            'invalid': PostReport.objects.filter(is_valid=False).count(),
            'pending': PostReport.objects.filter(is_resolved=False).count(),
        }

        context = {
            'title': 'Thống kê báo cáo',
            'most_reported_posts': most_reported_posts,
            'most_reported_authors': most_reported_authors,
            'most_reporting_users': most_reporting_users,
            'report_reasons': report_reasons,
            'recent_reports': recent_reports,
            'report_status': report_status,
            'opts': self.model._meta,
        }

        return render(request, 'admin/posts/postreport/report_statistics.html', context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_statistics_link'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def mark_as_valid(self, request, queryset):
        for report in queryset.filter(is_resolved=False):
            report.resolve(request.user)
            report.is_valid = True
            report.admin_notes = report.admin_notes or 'Báo cáo được xác nhận là hợp lệ'
            report.save()

        self.message_user(request, f'Đã đánh dấu {queryset.filter(is_resolved=True).count()} báo cáo là hợp lệ.')
    mark_as_valid.short_description = "Đánh dấu báo cáo được chọn là hợp lệ"

    def mark_as_invalid(self, request, queryset):
        for report in queryset.filter(is_resolved=False):
            report.resolve(request.user)
            report.is_valid = False
            report.admin_notes = report.admin_notes or 'Báo cáo được xác nhận là không hợp lệ'
            report.save()

        self.message_user(request, f'Đã đánh dấu {queryset.filter(is_resolved=True).count()} báo cáo là không hợp lệ.')
    mark_as_invalid.short_description = "Đánh dấu báo cáo được chọn là không hợp lệ"

    def delete_reported_posts(self, request, queryset):
        posts_to_delete = set()
        reports_to_update = []

        for report in queryset:
            posts_to_delete.add(report.post)
            reports_to_update.append(report)

        for report in reports_to_update:
            report.is_resolved = True
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.is_valid = True
            report.admin_notes = 'Bài viết đã bị xóa do vi phạm quy định'
            report.save()

        posts_count = len(posts_to_delete)
        for post in posts_to_delete:
            post.delete()

        self.message_user(request, f'Đã xóa {posts_count} bài viết bị báo cáo.')
    delete_reported_posts.short_description = "Xóa bài viết bị báo cáo được chọn"

    def save_model(self, request, obj, form, change):
        if 'is_resolved' in form.changed_data and obj.is_resolved:
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
    list_display = ('id', 'author', 'post', 'text', 'has_image', 'created_at', 'likes_count')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'text', 'post__caption')
    readonly_fields = ('created_at', 'updated_at', 'likes_count')

    @admin.display(boolean=True, description='Ảnh')
    def has_image(self, obj):
        return bool(obj.image)


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
