from django import template
from django.utils.html import urlize
from django.utils.safestring import mark_safe
import re

from chat.link_preview import extract_first_url
from chat.message_utils import (
    clean_shared_message_text,
    extract_shared_comment_id,
    format_compact_count,
    format_short_time,
)

register = template.Library()


@register.filter(name='linkify', needs_autoescape=True)
def linkify(value, autoescape=True):
    """Chuyển URL trong text thành link mở tab mới."""
    if value is None:
        return ''
    text = str(value)
    if not text.strip():
        return ''
    html = urlize(text, nofollow=False, autoescape=autoescape)
    html = re.sub(
        r'<a\s+',
        '<a target="_blank" rel="noopener noreferrer" class="message-link" ',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'(<a\b[^>]*href=["\'][^"\']*#comment-\d+["\'][^>]*)\s+target=["\']_blank["\']',
        r'\1',
        html,
        flags=re.IGNORECASE,
    )
    return mark_safe(html)


@register.filter(name='first_url')
def first_url(value):
    return extract_first_url(value) or ''


@register.filter(name='shared_comment_id')
def shared_comment_id(content):
    comment_id = extract_shared_comment_id(content)
    return comment_id or ''


@register.filter(name='shared_post_href')
def shared_post_href(message):
    post = getattr(message, 'shared_post', None)
    if not post:
        return '#'
    url = post.get_absolute_url()
    comment_id = extract_shared_comment_id(getattr(message, 'content', '') or '')
    if comment_id:
        return f'{url}#comment-{comment_id}'
    return url


@register.filter(name='shared_display_text')
def shared_display_text(message):
    """Nội dung tin nhắn còn lại sau khi đã có card chia sẻ."""
    if not message:
        return ''
    if getattr(message, 'shared_post_id', None):
        return clean_shared_message_text(getattr(message, 'content', '') or '')
    return getattr(message, 'content', '') or ''


@register.filter(name='msp_compact')
def msp_compact(value):
    return format_compact_count(value)


@register.filter(name='msp_short_time')
def msp_short_time(value):
    return format_short_time(value)


@register.filter(name='shared_comment_obj')
def shared_comment_obj(comment_id, post):
    if not comment_id or not post:
        return None
    try:
        cid = int(comment_id)
    except (TypeError, ValueError):
        return None
    from posts.models import Comment
    return (
        Comment.objects.select_related('author')
        .filter(pk=cid, post_id=post.id)
        .first()
    )
