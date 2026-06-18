from .models import Comment


def get_root_comment(comment):
    """Walk up to the top-level (root) comment in a thread."""
    root = comment
    while root.parent_id:
        root = Comment.objects.select_related('parent').get(pk=root.parent_id)
    return root


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
