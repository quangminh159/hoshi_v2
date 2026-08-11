"""
Cấu hình Django Admin cho Moora — branding + dashboard kiểm duyệt.
"""
from django.contrib import admin
from django.utils import timezone
from datetime import timedelta


def _dashboard_stats():
    """KPI cho trang chủ admin (kiểu Facebook Community Ops)."""
    from django.contrib.auth import get_user_model
    from accounts.models import UserReport, UserBlock
    from posts.models import Post, Comment, PostReport, Story
    from chat.models import Conversation, ConversationMessage
    from notifications.models import Notification

    User = get_user_model()
    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    pending_user_reports = UserReport.objects.filter(resolved=False).count()
    pending_post_reports = PostReport.objects.filter(is_resolved=False).count()
    suspended_users = User.all_objects.filter(is_suspended=True, is_deleted=False).count()
    deleted_users = User.all_objects.filter(is_deleted=True).count()
    message_requests = Conversation.objects.filter(is_message_request=True).count()

    return {
        'moora_dashboard': {
            'pending_reports': pending_user_reports + pending_post_reports,
            'pending_user_reports': pending_user_reports,
            'pending_post_reports': pending_post_reports,
            'suspended_users': suspended_users,
            'deleted_users': deleted_users,
            'message_requests': message_requests,
            'users_24h': User.all_objects.filter(date_joined__gte=day_ago).count(),
            'posts_24h': Post.objects.filter(created_at__gte=day_ago).count(),
            'comments_24h': Comment.objects.filter(created_at__gte=day_ago).count(),
            'messages_24h': ConversationMessage.objects.filter(created_at__gte=day_ago).count(),
            'stories_active': Story.objects.filter(expires_at__gt=now).count(),
            'blocks_week': UserBlock.objects.filter(created_at__gte=week_ago).count(),
            'unread_notifications': Notification.objects.filter(is_read=False).count(),
            'total_users': User.all_objects.filter(is_deleted=False).count(),
            'total_posts': Post.objects.count(),
            'total_conversations': Conversation.objects.count(),
        }
    }


def configure_admin():
    admin.site.site_header = 'Moora Quản trị'
    admin.site.site_title = 'Moora Admin'
    admin.site.index_title = 'Trung tâm kiểm duyệt & vận hành'

    if getattr(admin.site, '_moora_index_patched', False):
        return

    original_index = admin.site.index

    def patched_index(request, extra_context=None):
        extra_context = extra_context or {}
        try:
            extra_context.update(_dashboard_stats())
        except Exception:
            extra_context['moora_dashboard'] = None
        return original_index(request, extra_context)

    admin.site.index = patched_index
    admin.site._moora_index_patched = True


def ensure_moora_theme():
    """Tạo / kích hoạt theme Moora sau khi đã migrate admin_interface."""
    try:
        from admin_interface.models import Theme
    except Exception:
        return

    theme = Theme.objects.filter(name='Moora').first()
    if theme is None:
        theme = Theme(name='Moora')

    updates = {
        'active': True,
        'title': 'Moora Quản trị',
        'title_visible': True,
        'env_name': 'Moora',
        'env_color': '#0EA5E9',
        'env_visible_in_header': True,
        'language_chooser_active': False,
        'css_header_background_color': '#0F172A',
        'css_header_text_color': '#F8FAFC',
        'css_header_link_color': '#E2E8F0',
        'css_header_link_hover_color': '#FFFFFF',
        'css_module_background_color': '#0F172A',
        'css_module_text_color': '#F8FAFC',
        'css_module_link_color': '#E2E8F0',
        'css_module_link_hover_color': '#FFFFFF',
        'css_module_rounded_corners': True,
        'css_generic_link_color': '#0284C7',
        'css_generic_link_hover_color': '#0369A1',
        'css_save_button_background_color': '#0EA5E9',
        'css_save_button_background_hover_color': '#0284C7',
        'css_save_button_text_color': '#FFFFFF',
        'css_delete_button_background_color': '#DC2626',
        'css_delete_button_background_hover_color': '#B91C1C',
        'css_delete_button_text_color': '#FFFFFF',
        'related_modal_active': True,
        'list_filter_dropdown': True,
        'foldable_apps': True,
        'recent_actions_visible': True,
    }
    for key, value in updates.items():
        if hasattr(theme, key):
            setattr(theme, key, value)

    Theme.objects.exclude(pk=theme.pk).update(active=False) if theme.pk else Theme.objects.update(active=False)
    theme.save()
