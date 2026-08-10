"""Helpers chuẩn hóa payload tin nhắn chat."""

import re

from django.utils import timezone

COMMENT_ANCHOR_RE = re.compile(r'#comment-(\d+)')
POST_URL_RE = re.compile(r'/posts/\d+/?', re.IGNORECASE)


def _attachment_info(message):
    """Trả về (has_attachment, attachment_type, attachment_url)."""
    if message.image:
        return True, 'image', message.image.url
    if message.video:
        return True, 'video', message.video.url
    if message.audio:
        return True, 'audio', message.audio.url
    if message.document:
        return True, 'document', message.document.url
    return False, None, None


def extract_shared_comment_id(content):
    """Lấy comment id từ deep link #comment-<id> trong nội dung tin nhắn."""
    if not content:
        return None
    match = COMMENT_ANCHOR_RE.search(str(content))
    return int(match.group(1)) if match else None


def format_compact_count(n):
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        n = 0
    if n >= 1_000_000:
        s = f'{n / 1_000_000:.1f}'.rstrip('0').rstrip('.')
        return f'{s}M'
    if n >= 1_000:
        s = f'{n / 1_000:.1f}'.rstrip('0').rstrip('.')
        return f'{s}K'
    return str(n)


def format_short_time(dt):
    if not dt:
        return ''
    now = timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    secs = max(0, int((now - dt).total_seconds()))
    if secs < 60:
        return 'vừa xong'
    if secs < 3600:
        return f'{secs // 60}m'
    if secs < 86400:
        return f'{secs // 3600}h'
    if secs < 86400 * 7:
        return f'{secs // 86400}d'
    return dt.strftime('%d/%m')


def clean_shared_message_text(content):
    """Bỏ dòng preview 💬 / URL bài viết khi đã có card chia sẻ."""
    if not content:
        return ''
    kept = []
    for line in str(content).splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('💬'):
            continue
        if '#comment-' in s:
            continue
        if POST_URL_RE.search(s) and s.startswith(('http://', 'https://')):
            continue
        kept.append(line)
    return '\n'.join(kept).strip()


def _engagement_stats(likes=0, comments=0, reposts=0, shares=0):
    return {
        'likes_count': int(likes or 0),
        'comments_count': int(comments or 0),
        'reposts_count': int(reposts or 0),
        'shares_count': int(shares or 0),
        'likes_display': format_compact_count(likes),
        'comments_display': format_compact_count(comments),
        'reposts_display': format_compact_count(reposts),
        'shares_display': format_compact_count(shares),
    }


def serialize_shared_comment(comment):
    if not comment:
        return None
    replies = 0
    try:
        replies = comment.replies.count()
    except Exception:
        replies = 0
    stats = _engagement_stats(
        likes=comment.likes_count,
        comments=replies,
        reposts=0,
        shares=0,
    )
    return {
        'id': comment.id,
        'text': (comment.text or '')[:280],
        'author_username': comment.author.username if comment.author_id else '',
        'author_avatar': (
            comment.author.get_avatar_url()
            if comment.author_id and hasattr(comment.author, 'get_avatar_url')
            else '/static/img/default-avatar.png'
        ),
        'time_ago': format_short_time(comment.created_at),
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
        **stats,
    }


def serialize_shared_post(post, comment_id=None):
    if not post:
        return None
    first_media = post.media.order_by('order').first()
    media_preview = None
    if first_media:
        media_preview = {
            'url': first_media.file.url,
            'media_type': first_media.media_type,
        }
    url = post.get_absolute_url()
    if comment_id:
        url = f'{url}#comment-{comment_id}'

    try:
        reposts = post.shared_posts.count()
    except Exception:
        reposts = 0

    stats = _engagement_stats(
        likes=post.likes_count,
        comments=post.comments_count,
        reposts=reposts,
        shares=reposts,
    )

    data = {
        'id': post.id,
        'author_username': post.author.username,
        'author_avatar': post.author.get_avatar_url(),
        'caption': (post.caption or '')[:200],
        'url': url,
        'media': media_preview,
        'comment_id': comment_id,
        'is_shared_comment': bool(comment_id),
        'time_ago': format_short_time(post.created_at),
        'created_at': post.created_at.isoformat() if post.created_at else None,
        **stats,
        'comment': None,
    }

    if comment_id:
        from posts.models import Comment
        comment = (
            Comment.objects.select_related('author')
            .filter(pk=comment_id, post_id=post.id)
            .first()
        )
        data['comment'] = serialize_shared_comment(comment)

    return data


def serialize_reply_to(message):
    parent = getattr(message, 'reply_to', None)
    if not parent:
        return None

    has_attachment, attachment_type, attachment_url = _attachment_info(parent)

    return {
        'id': parent.id,
        'sender_id': parent.sender_id,
        'sender_username': parent.sender.username if parent.sender_id else '',
        'content': parent.content or '',
        'preview': parent.get_reply_preview(),
        'has_attachment': has_attachment,
        'attachment_type': attachment_type,
        'attachment_url': attachment_url,
        'file_name': parent.file_name,
    }


def serialize_chat_message(message, user=None):
    sender = message.sender or user
    has_attachment, attachment_type, attachment_url = _attachment_info(message)
    shared_post = getattr(message, 'shared_post', None)
    is_system = bool(getattr(message, 'is_system', False))
    comment_id = None if is_system else extract_shared_comment_id(message.content)
    raw_content = message.content or ''
    display_content = (
        clean_shared_message_text(raw_content)
        if shared_post and not is_system
        else raw_content
    )

    return {
        'id': message.id,
        'content': display_content,
        'raw_content': raw_content,
        'sender_id': sender.id if sender else None,
        'sender_username': sender.username if sender else 'Hệ thống',
        'sender_avatar': (
            sender.get_avatar_url() if sender and hasattr(sender, 'get_avatar_url') else None
        ),
        'created_at': message.created_at.isoformat(),
        'has_attachment': has_attachment,
        'attachment_type': attachment_type,
        'attachment_url': attachment_url,
        'file_name': message.file_name,
        'file_size': message.file_size,
        'reply_to': None if is_system else serialize_reply_to(message),
        'shared_post': None if is_system else serialize_shared_post(shared_post, comment_id=comment_id),
        'is_system': is_system,
    }
