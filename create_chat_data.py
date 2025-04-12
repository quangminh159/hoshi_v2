import os
import django
import random
from datetime import datetime, timedelta

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

# Import các model sau khi đã thiết lập Django
from django.contrib.auth import get_user_model
from chat.models import (
    Conversation, ConversationParticipant, ConversationMessage,
    UserSetting, Thread, Message
)
from django.utils import timezone

# Lấy model User đúng
User = get_user_model()

# Tạo người dùng mẫu nếu chưa có
def create_sample_users():
    users = []
    
    # Tạo người dùng thử nghiệm
    test_usernames = ['testuser1', 'testuser2', 'testuser3']
    
    for i, username in enumerate(test_usernames, 1):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': f'Test',
                'last_name': f'User {i}',
                'is_active': True
            }
        )
        
        if created:
            user.set_password('test12345')
            user.save()
            print(f"Đã tạo người dùng: {username}")
        else:
            print(f"Người dùng {username} đã tồn tại")
        
        # Tạo UserSetting nếu chưa có
        try:
            user_setting, created = UserSetting.objects.get_or_create(
                user=user,
                defaults={
                    'username': username,
                    'is_online': random.choice([True, False])
                }
            )
            if created:
                print(f"Đã tạo UserSetting cho {username}")
            else:
                print(f"UserSetting cho {username} đã tồn tại")
        except Exception as e:
            print(f"Lỗi khi tạo UserSetting cho {username}: {e}")
        
        users.append(user)
    
    return users

# Tạo các cuộc trò chuyện
def create_conversations(users):
    conversations = []
    
    # Lấy admin nếu có
    admin = User.objects.filter(is_superuser=True).first()
    if admin and admin not in users:
        users.append(admin)
        print(f"Đã thêm admin {admin.username} vào danh sách người dùng")
    
    # Tạo cuộc trò chuyện giữa các người dùng
    for i, user1 in enumerate(users):
        for j, user2 in enumerate(users):
            if i < j:  # Chỉ tạo cuộc trò chuyện giữa các cặp người dùng khác nhau
                # Kiểm tra xem đã có cuộc trò chuyện giữa hai người chưa
                existing_conversation = Conversation.objects.filter(
                    participants=user1
                ).filter(
                    participants=user2
                ).first()
                
                if existing_conversation:
                    print(f"Cuộc trò chuyện giữa {user1.username} và {user2.username} đã tồn tại")
                    # Lấy thread nếu có
                    thread = Thread.objects.filter(users=user1).filter(users=user2).first()
                    if not thread:
                        thread_name = f"thread_{user1.id}_{user2.id}"
                        thread = Thread.objects.create(name=thread_name)
                        thread.users.add(user1, user2)
                        thread.save()
                        print(f"Đã tạo thread giữa {user1.username} và {user2.username}")
                    
                    conversations.append((existing_conversation, thread, user1, user2))
                    continue
                
                # Tạo cuộc trò chuyện mới
                conversation = Conversation.objects.create(
                    last_message_time=timezone.now()
                )
                
                # Thêm người tham gia
                ConversationParticipant.objects.create(conversation=conversation, user=user1)
                ConversationParticipant.objects.create(conversation=conversation, user=user2)
                
                print(f"Đã tạo cuộc trò chuyện giữa {user1.username} và {user2.username}")
                
                # Tạo Thread cho cả hai hệ thống
                thread_name = f"thread_{user1.id}_{user2.id}"
                thread = Thread.objects.create(name=thread_name)
                thread.users.add(user1, user2)
                thread.save()
                
                print(f"Đã tạo thread giữa {user1.username} và {user2.username}")
                
                conversations.append((conversation, thread, user1, user2))
    
    return conversations

# Tạo tin nhắn mẫu
def create_messages(conversations):
    messages_content = [
        "Xin chào! Bạn khỏe không?",
        "Hôm nay thời tiết đẹp quá!",
        "Bạn đã ăn trưa chưa?",
        "Đồ án của chúng ta sắp hoàn thành rồi.",
        "Chúng ta nên gặp nhau để thảo luận chi tiết hơn.",
        "Tôi đã hoàn thành phần UI cho ứng dụng.",
        "Còn các phần khác thì sao?",
        "Backend đang có một số vấn đề cần giải quyết.",
        "Đừng lo lắng, tôi sẽ giúp bạn.",
        "Cuối tuần này bạn có rảnh không?",
        "Tôi thích thiết kế mới của ứng dụng.",
        "Còn mấy ngày nữa là đến deadline rồi."
    ]
    
    for conversation, thread, user1, user2 in conversations:
        # Kiểm tra xem đã có tin nhắn nào trong cuộc trò chuyện chưa
        existing_messages = ConversationMessage.objects.filter(conversation=conversation).count()
        
        if existing_messages > 0:
            print(f"Cuộc trò chuyện giữa {user1.username} và {user2.username} đã có {existing_messages} tin nhắn")
            continue
        
        # Tạo 5-12 tin nhắn cho mỗi cuộc trò chuyện
        num_messages = random.randint(5, 12)
        
        for i in range(num_messages):
            try:
                # Người gửi là user1 hoặc user2
                sender = random.choice([user1, user2])
                recipient = user2 if sender == user1 else user1
                
                # Thời gian gửi tin nhắn (trong khoảng 7 ngày gần đây)
                minutes_ago = random.randint(1, 7 * 24 * 60)  # Tối đa 7 ngày trước
                sent_time = timezone.now() - timedelta(minutes=minutes_ago)
                
                # Nội dung tin nhắn
                content = random.choice(messages_content)
                
                # Tạo tin nhắn cho ConversationMessage
                is_read = random.choice([True, False])
                conversation_msg = ConversationMessage.objects.create(
                    conversation=conversation,
                    sender=sender,
                    content=content,
                    text=content,
                    created_at=sent_time,
                    is_read=is_read,
                    isread=is_read
                )
                
                # Cập nhật thời gian tin nhắn cuối cùng
                if sent_time > conversation.last_message_time:
                    conversation.last_message_time = sent_time
                    conversation.save()
                
                # Kiểm tra xem thread có tồn tại không
                if thread:
                    # Tạo tin nhắn cho Thread (hệ thống cũ)
                    Message.objects.create(
                        thread=thread,
                        sender=sender,
                        text=content,
                        content=content,
                        isread=is_read,
                        is_read=is_read
                    )
                
                print(f"Đã tạo tin nhắn từ {sender.username} đến {recipient.username}: {content[:20]}...")
            except Exception as e:
                print(f"Lỗi khi tạo tin nhắn: {e}")

if __name__ == "__main__":
    print("Bắt đầu tạo dữ liệu mẫu cho hệ thống chat...")
    try:
        users = create_sample_users()
        conversations = create_conversations(users)
        create_messages(conversations)
        print("Hoàn thành tạo dữ liệu mẫu!")
    except Exception as e:
        print(f"Lỗi: {e}") 