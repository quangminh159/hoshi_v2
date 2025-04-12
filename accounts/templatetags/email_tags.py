from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
@stringfilter
def email_link(link, text=None):
    """Tạo một nút đẹp cho email HTML."""
    if text is None:
        text = link
        
    html = f"""
    <div style="text-align: center; margin: 25px 0;">
        <a href="{conditional_escape(link)}" 
           style="display: inline-block; background-color: #3f51b5; color: white; 
                  text-decoration: none; padding: 12px 25px; border-radius: 4px; 
                  font-weight: 500;">
            {conditional_escape(text)}
        </a>
    </div>
    """
    return mark_safe(html) 