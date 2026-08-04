"""Resolve @mention token → User (exact / unique prefix)."""
from django.contrib.auth import get_user_model


def resolve_mentioned_user(raw_username):
    """
    Tìm user từ chuỗi sau @.
    Ưu tiên khớp không phân biệt hoa thường; nếu không có thì khớp
    prefix duy nhất (vd: jack → jack97) khi token dài ≥ 3.
    """
    if not raw_username:
        return None

    User = get_user_model()
    user = User.objects.filter(username__iexact=raw_username).first()
    if user:
        return user

    if len(raw_username) < 3:
        return None

    matches = list(User.objects.filter(username__istartswith=raw_username)[:2])
    if len(matches) == 1:
        return matches[0]
    return None


def normalize_caption_mentions(caption):
    """Đổi @token thành @username chuẩn nếu resolve được."""
    import re

    if not caption:
        return caption

    def repl(match):
        token = match.group(1)
        user = resolve_mentioned_user(token)
        if user:
            return f'@{user.username}'
        return match.group(0)

    return re.sub(r'@(\w+)', repl, caption)
