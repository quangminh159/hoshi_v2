from django import template
from django.utils.html import urlize
from django.utils.safestring import mark_safe
import re

from chat.link_preview import extract_first_url
from chat.message_utils import extract_shared_comment_id

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
    # Link nội bộ tới bình luận: mở cùng tab để cuộn tới #comment-
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
