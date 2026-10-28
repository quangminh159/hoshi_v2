
from __future__ import annotations

MAX_EDIT_HISTORY = 10


def post_is_edited(post) -> bool:
    created = getattr(post, 'created_at', None)
    updated = getattr(post, 'updated_at', None)
    if not created or not updated:
        return False
    return (updated - created).total_seconds() > 2


def record_post_edit_history(post, *, old_caption: str, old_location: str) -> bool:
    """
    Lưu snapshot nội dung cũ nếu caption/location đổi.
    Trả về True nếu đã ghi lịch sử.
    """
    from .models import PostEditHistory

    new_caption = post.caption or ''
    new_location = post.location or ''
    prev_caption = old_caption or ''
    prev_location = old_location or ''
    if new_caption == prev_caption and new_location == prev_location:
        return False

    PostEditHistory.objects.create(
        post=post,
        caption=prev_caption,
        location=prev_location,
    )
    # Giữ tối đa N bản gần nhất
    keep_ids = list(
        PostEditHistory.objects.filter(post=post)
        .order_by('-created_at')
        .values_list('id', flat=True)[:MAX_EDIT_HISTORY]
    )
    if keep_ids:
        PostEditHistory.objects.filter(post=post).exclude(id__in=keep_ids).delete()
    return True
