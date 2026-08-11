"""Lọc chế độ xem bài viết: công khai / chỉ mình tôi."""
from django.db.models import Q

from .models import Post


def visibility_q_for_viewer(viewer):
    """Q object: bài viewer được phép xem theo visibility."""
    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        return Q(visibility=Post.VISIBILITY_PUBLIC) | Q(author=viewer)
    return Q(visibility=Post.VISIBILITY_PUBLIC)


def filter_visible_posts(queryset, viewer):
    """Lọc queryset Post theo chế độ xem."""
    return queryset.filter(visibility_q_for_viewer(viewer))


def can_view_post(post, viewer):
    """True nếu viewer được xem bài (không gồm private account / block)."""
    vis = getattr(post, 'visibility', Post.VISIBILITY_PUBLIC) or Post.VISIBILITY_PUBLIC
    if vis == Post.VISIBILITY_PUBLIC:
        return True
    if vis == Post.VISIBILITY_ONLY_ME:
        return (
            viewer is not None
            and getattr(viewer, 'is_authenticated', False)
            and viewer.id == post.author_id
        )
    return False


def normalize_visibility(value, default=Post.VISIBILITY_PUBLIC):
    allowed = {Post.VISIBILITY_PUBLIC, Post.VISIBILITY_ONLY_ME}
    value = (value or '').strip().lower()
    return value if value in allowed else default
