"""Helpers chuẩn hóa payload tin nhắn chat."""


def _attachment_info(message):
    """Trả về (has_attachment, attachment_type, attachment_url)."""
    if message.image:
        return True, 'image', message.image.url
    if message.video:
        return True, 'video', message.video.url
    if message.audio:
        return True, 'audio', message.audio.url
    if message.document:
        return True, 'document', message.document.url
    return False, None, None


def serialize_shared_post(post):
    if not post:
        return None
    first_media = post.media.order_by('order').first()
    media_preview = None
    if first_media:
        media_preview = {
            'url': first_media.file.url,
            'media_type': first_media.media_type,
        }
    return {
        'id': post.id,
        'author_username': post.author.username,
        'author_avatar': post.author.get_avatar_url(),
        'caption': (post.caption or '')[:120],
        'url': post.get_absolute_url(),
        'media': media_preview,
    }


def serialize_reply_to(message):
    parent = getattr(message, 'reply_to', None)
    if not parent:
        return None

    has_attachment, attachment_type, attachment_url = _attachment_info(parent)

    return {
        'id': parent.id,
        'sender_id': parent.sender_id,
        'sender_username': parent.sender.username if parent.sender_id else '',
        'content': parent.content or '',
        'preview': parent.get_reply_preview(),
        'has_attachment': has_attachment,
        'attachment_type': attachment_type,
        'attachment_url': attachment_url,
        'file_name': parent.file_name,
    }


def serialize_chat_message(message, user=None):
    sender = user or message.sender
    has_attachment, attachment_type, attachment_url = _attachment_info(message)
    shared_post = getattr(message, 'shared_post', None)

    return {
        'id': message.id,
        'content': message.content or '',
        'sender_id': sender.id,
        'sender_username': sender.username,
        'sender_avatar': sender.get_avatar_url() if hasattr(sender, 'get_avatar_url') else None,
        'created_at': message.created_at.isoformat(),
        'has_attachment': has_attachment,
        'attachment_type': attachment_type,
        'attachment_url': attachment_url,
        'file_name': message.file_name,
        'file_size': message.file_size,
        'reply_to': serialize_reply_to(message),
        'shared_post': serialize_shared_post(shared_post),
    }
