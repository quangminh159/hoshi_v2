from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.urls import reverse
import re

from posts.mention_utils import resolve_mentioned_user

register = template.Library()

URL_RE = re.compile(r'(https?://[^\s<]+|www\.[^\s<]+)', re.IGNORECASE)


def _apply_outside_tags(html, pattern, repl):
    """Chỉ thay thế trên text, không đụng vào thuộc tính trong thẻ HTML."""
    parts = re.split(r'(<[^>]+>)', html)
    for i, part in enumerate(parts):
        if part and not part.startswith('<'):
            parts[i] = pattern.sub(repl, part)
    return ''.join(parts)


def _linkify_urls(escaped_text):
    def url_repl(match):
        raw = match.group(0)
        url = raw
        trailing = ''
        while url and url[-1] in '.,;:!?)]':
            trailing = url[-1] + trailing
            url = url[:-1]
        if not url:
            return raw
        href = url if re.match(r'^https?://', url, re.I) else f'https://{url}'
        return (
            f'<a href="{href}" class="caption-link" target="_blank" '
            f'rel="noopener noreferrer" onclick="event.stopPropagation()">{url}</a>'
            f'{trailing}'
        )

    return URL_RE.sub(url_repl, escaped_text)


@register.filter
def format_caption(caption):
    """
    Format caption: URL clickable, @mention, #hashtag.
    """
    if not caption:
        return ''

    text = escape(caption)
    text = _linkify_urls(text)

    def mention_repl(match):
        token = match.group(1)
        user = resolve_mentioned_user(token)
        if not user:
            # Không tạo link chết → tránh 404 khi @sai / chưa chọn gợi ý
            return f'@{token}'
        url = reverse('accounts:profile', kwargs={'username': user.username})
        return (
            f'<a href="{url}" class="mention-link" '
            f'onclick="event.stopPropagation()">@{user.username}</a>'
        )

    def hashtag_repl(match):
        tag = match.group(1)
        url = f'{reverse("posts:search")}?q={tag}'
        return f'<a href="{url}" class="hashtag-link" onclick="event.stopPropagation()">#{tag}</a>'

    text = _apply_outside_tags(text, re.compile(r'@(\w+)'), mention_repl)
    text = _apply_outside_tags(text, re.compile(r'#(\w+)'), hashtag_repl)
    text = text.replace('\n', '<br>')

    return mark_safe(text)


@register.filter
def format_comment(text):
    """URL + xuống dòng cho bình luận (không bắt buộc mention/hashtag, nhưng hỗ trợ luôn)."""
    return format_caption(text)
