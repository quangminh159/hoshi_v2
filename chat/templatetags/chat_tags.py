from django import template
from django.utils.html import urlize
from django.utils.safestring import mark_safe
import re

from chat.link_preview import extract_first_url

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
    return mark_safe(html)


@register.filter(name='first_url')
def first_url(value):
    return extract_first_url(value) or ''
