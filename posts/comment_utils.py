from .models import Comment
from django.db.models import Count


def get_root_comment(comment):
    """Walk up to the top-level (root) comment in a thread."""
    root = comment
    while root.parent_id:
        root = Comment.objects.select_related('parent').get(pk=root.parent_id)
    return root


def get_root_comments_qs(post):
    """
    Root comments ordered by engagement then newest:
    likes_count ↓ → replies_count ↓ → created_at ↓
    """
    return (
        Comment.objects.filter(post=post, parent=None)
        .select_related('author')
        .annotate(replies_total=Count('replies', distinct=True))
        .order_by('-likes_count', '-replies_total', '-created_at')
    )


def serialize_comment(comment, post_id=None, is_duplicate=False, parent_data=None, can_delete=True):
    """JSON payload for comment create/list responses."""
    return {
        'id': comment.id,
        'text': comment.text or '',
        'image': comment.image_url,
        'image_url': comment.image_url,
        'video': comment.video_url,
        'video_url': comment.video_url,
        'author_id': comment.author_id,
        'author_username': comment.author.username,
        'author_avatar': comment.author.get_avatar_url() if hasattr(comment.author, 'get_avatar_url') else (
            comment.author.avatar.url if getattr(comment.author, 'avatar', None) else None
        ),
        'created_at': comment.created_at.isoformat(),
        'likes_count': comment.likes_count,
        'parent': parent_data,
        'parent_id': comment.parent_id,
        'post_id': post_id or comment.post_id,
        'is_duplicate': is_duplicate,
        'can_delete': can_delete,
    }


def get_thread_reply_ids(post, root_id):
    """All reply comment IDs under a root comment (any nesting depth)."""
    frontier = {root_id}
    collected = set()
    while True:
        children = list(
            Comment.objects.filter(post=post, parent_id__in=frontier)
            .values_list('id', flat=True)
        )
        new = [cid for cid in children if cid not in collected]
        if not new:
            break
        collected.update(new)
        frontier = set(new)
    return collected


def get_thread_replies_qs(post, root_comment):
    """Queryset of all replies in a thread, ordered for feed display."""
    root = get_root_comment(root_comment)
    thread_ids = get_thread_reply_ids(post, root.id)
    if not thread_ids:
        return Comment.objects.none()
    return (
        Comment.objects.filter(id__in=thread_ids)
        .select_related('author')
        .order_by('-likes_count', '-created_at')
    )


def resolve_reply_parent(post, parent_id):
    """
    Resolve direct parent and root parent for a new reply.
    New replies are stored under the root comment (flat thread).
    Returns (root_parent, direct_parent) or (None, None).
    """
    if not parent_id:
        return None, None
    direct = Comment.objects.get(id=parent_id, post=post)
    root = get_root_comment(direct)
    return root, direct
