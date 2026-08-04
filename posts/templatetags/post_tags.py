from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.urls import reverse
import re

register = template.Library()


@register.filter
def format_caption(caption):
    """
    Format caption với các đề cập (@username) và hashtags (#hashtag)
    - @username: hiển thị nổi bật và liên kết đến trang profile
    - #hashtag: hiển thị màu nổi bật và liên kết đến trang tìm kiếm
    """
    if not caption:
        return ''

    text = escape(caption)

    def mention_repl(match):
        username = match.group(1)
        url = reverse('accounts:profile', kwargs={'username': username})
        return (
            f'<a href="{url}" class="mention-link" '
            f'onclick="event.stopPropagation()">@{username}</a>'
        )

    def hashtag_repl(match):
        tag = match.group(1)
        url = f'{reverse("posts:search")}?q={tag}'
        return f'<a href="{url}" class="hashtag-link" onclick="event.stopPropagation()">#{tag}</a>'

    text = re.sub(r'@(\w+)', mention_repl, text)
    text = re.sub(r'#(\w+)', hashtag_repl, text)
    text = text.replace('\n', '<br>')

    return mark_safe(text)
