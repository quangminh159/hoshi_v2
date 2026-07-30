from chat.models import UserSetting


def get_user_presence(user):
    """Trạng thái online / lần hoạt động cuối của người dùng."""
    try:
        settings = UserSetting.objects.get(user=user)
    except UserSetting.DoesNotExist:
        return {'is_online': False, 'last_seen': None}

    return {
        'is_online': settings.is_online,
        'last_seen': settings.last_seen,
    }
