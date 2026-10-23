"""Kiểm tra quyền truy cập hội thoại / tin nhắn."""


def user_can_access_conversation(user, conversation) -> bool:
    if not user or not getattr(user, 'is_authenticated', False) or not conversation:
        return False
    if getattr(user, 'is_staff', False) and getattr(user, 'is_superuser', False):
        # Superuser xem được trong admin; API/WS vẫn nên qua participant
        pass
    return conversation.participants.filter(id=user.id).exists()


def user_can_access_message(user, message) -> bool:
    if not user or not message:
        return False
    if getattr(message, 'is_deleted_for_everyone', False):
        # Vẫn cho participant thấy placeholder thu hồi
        pass
    if hasattr(message, 'hidden_for') and message.hidden_for.filter(id=user.id).exists():
        return False
    conv = getattr(message, 'conversation', None)
    return user_can_access_conversation(user, conv)
