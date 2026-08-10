"""Broadcast realtime engagement (like / comment counts) tới mọi client đang online."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

FEED_ENGAGEMENT_GROUP = 'feed_engagement'


def broadcast_post_engagement(
    post_id,
    *,
    likes_count=None,
    comments_count=None,
    action=None,
    actor_id=None,
    comment_id=None,
    comment_likes_count=None,
    parent_comment_id=None,
    replies_count=None,
):
    """
    Gửi event post_engagement tới group feed_engagement.
    Client (notifications WS) cập nhật số like/cmt (và like/reply của comment) trên DOM.
    """
    if post_id is None and comment_id is None:
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = {
        'type': 'post_engagement',
        'post_id': int(post_id) if post_id is not None else None,
        'action': action,
        'actor_id': int(actor_id) if actor_id is not None else None,
    }
    if likes_count is not None:
        payload['likes_count'] = int(likes_count)
    if comments_count is not None:
        payload['comments_count'] = int(comments_count)
    if comment_id is not None:
        payload['comment_id'] = int(comment_id)
    if comment_likes_count is not None:
        payload['comment_likes_count'] = int(comment_likes_count)
    if parent_comment_id is not None:
        payload['parent_comment_id'] = int(parent_comment_id)
    if replies_count is not None:
        payload['replies_count'] = int(replies_count)

    try:
        async_to_sync(channel_layer.group_send)(
            FEED_ENGAGEMENT_GROUP,
            {
                'type': 'post.engagement',
                'payload': payload,
            },
        )
    except Exception:
        # Không làm hỏng API nếu channel layer lỗi
        pass
