"""Helpers chuẩn hóa payload tin nhắn chat."""


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

    has_attachment = bool(parent.image or parent.video or parent.document)
    attachment_type = None
    attachment_url = None

    if parent.image:
        attachment_type = 'image'
        attachment_url = parent.image.url
    elif parent.video:
        attachment_type = 'video'
        attachment_url = parent.video.url
    elif parent.document:
        attachment_type = 'document'
        attachment_url = parent.document.url

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
    has_attachment = bool(message.image or message.video or message.document)
    attachment_type = None
    attachment_url = None

    if message.image:
        attachment_type = 'image'
        attachment_url = message.image.url
    elif message.video:
        attachment_type = 'video'
        attachment_url = message.video.url
    elif message.document:
        attachment_type = 'document'
        attachment_url = message.document.url

    shared_post = getattr(message, 'shared_post', None)

    return {
        'id': message.id,
        'content': message.content or '',
        'sender_id': sender.id,
        'sender_username': sender.username,
        'created_at': message.created_at.isoformat(),
        'has_attachment': has_attachment,
        'attachment_type': attachment_type,
        'attachment_url': attachment_url,
        'file_name': message.file_name,
        'file_size': message.file_size,
        'reply_to': serialize_reply_to(message),
        'shared_post': serialize_shared_post(shared_post),
    }
