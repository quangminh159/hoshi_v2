"""Validate ảnh / video ngắn trong bình luận."""

COMMENT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
COMMENT_VIDEO_MAX_BYTES = 15 * 1024 * 1024
COMMENT_VIDEO_MAX_SECONDS = 5
COMMENT_VIDEO_ALLOWED_TYPES = {
    'video/mp4',
    'video/webm',
    'video/quicktime',
    'video/x-m4v',
}


def validate_comment_image(image):
    content_type = (getattr(image, 'content_type', '') or '').lower()
    if not content_type.startswith('image/'):
        return 'File phải là ảnh'
    if image.size > COMMENT_IMAGE_MAX_BYTES:
        return 'Ảnh bình luận tối đa 5MB'
    return None


def validate_comment_video(video):
    content_type = (getattr(video, 'content_type', '') or '').lower()
    name = (getattr(video, 'name', '') or '').lower()
    ok_type = content_type in COMMENT_VIDEO_ALLOWED_TYPES or name.endswith(
        ('.mp4', '.webm', '.mov', '.m4v')
    )
    if not ok_type:
        return 'Video bình luận chỉ hỗ trợ MP4, WEBM, MOV'
    if video.size > COMMENT_VIDEO_MAX_BYTES:
        return 'Video bình luận tối đa 15MB'
    return None
