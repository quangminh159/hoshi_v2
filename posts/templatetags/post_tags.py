from django import template
from django.utils.html import mark_safe
from django.urls import reverse
import re

register = template.Library()

@register.filter
def format_caption(caption):
    """
    Format caption với các đề cập (@username) và hashtags (#hashtag)
    - @username: hiển thị màu xanh và liên kết đến trang profile
    - #hashtag: hiển thị màu xanh và liên kết đến trang tìm kiếm hashtag
    """
    # Xử lý mentions (@username)
    caption = re.sub(
        r'@(\w+)',
        lambda match: f'<a href="{reverse("accounts:profile", kwargs={"username": match.group(1)})}" class="text-primary fw-bold">@{match.group(1)}</a>',
        caption
    )
    
    # Xử lý hashtags (#hashtag)
    caption = re.sub(
        r'#(\w+)',
        lambda match: f'<a href="{reverse("posts:explore")}?tag={match.group(1)}" class="text-primary">#{match.group(1)}</a>',
        caption
    )
    
    # Thêm xuống dòng
    caption = caption.replace('\n', '<br>')
    
    return mark_safe(caption) 