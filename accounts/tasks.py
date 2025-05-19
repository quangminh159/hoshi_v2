from celery import shared_task
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import os
import json
import zipfile
import tempfile
import shutil
from datetime import timedelta
from .models import User, DataDownloadRequest
from django.db.models import Q
from django.urls import reverse

@shared_task
def cleanup_inactive_sessions():
    """Delete expired sessions."""
    Session.objects.filter(expire_date__lt=timezone.now()).delete()

@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new users."""
    user = User.objects.get(id=user_id)
    
    context = {
        'user': user,
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_URL
    }
    
    html_message = render_to_string(
        'accounts/email/welcome.html',
        context
    )
    
    send_mail(
        subject=f'Chào mừng bạn đến với {settings.SITE_NAME}!',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

@shared_task
def send_password_change_notification(user_id):
    """Send email notification when password is changed."""
    user = User.objects.get(id=user_id)
    
    context = {
        'user': user,
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_URL
    }
    
    html_message = render_to_string(
        'accounts/email/password_changed.html',
        context
    )
    
    send_mail(
        subject=f'[{settings.SITE_NAME}] Mật khẩu của bạn đã được thay đổi',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

@shared_task
def send_email_verification_reminder(user_id):
    """Send reminder to verify email address."""
    user = User.objects.get(id=user_id)
    
    if not user.emailaddress_set.filter(verified=True).exists():
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL
        }
        
        html_message = render_to_string(
            'accounts/email/verify_reminder.html',
            context
        )
        
        send_mail(
            subject=f'[{settings.SITE_NAME}] Xác thực email của bạn',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message
        )

@shared_task
def cleanup_unverified_users():
    """Delete unverified users after 7 days."""
    User.objects.filter(
        emailaddress__verified=False,
        date_joined__lt=timezone.now() - timezone.timedelta(days=7)
    ).delete()

@shared_task
def send_inactivity_notification(user_id):
    """Send notification to inactive users."""
    user = User.objects.get(id=user_id)
    
    if not user.last_login or (
        timezone.now() - user.last_login > timezone.timedelta(days=30)
    ):
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL
        }
        
        html_message = render_to_string(
            'accounts/email/inactivity_notification.html',
            context
        )
        
        send_mail(
            subject=f'[{settings.SITE_NAME}] Chúng tôi nhớ bạn!',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message
        )

@shared_task
def process_data_download_requests():
    """Xử lý các yêu cầu tải xuống dữ liệu người dùng đang chờ xử lý."""
    # Lấy tất cả yêu cầu đang chờ xử lý
    pending_requests = DataDownloadRequest.objects.filter(status='pending')
    
    for request in pending_requests:
        try:
            # Thử chạy task Celery
            generate_user_data_download.delay(request.id)
        except Exception as e:
            # Nếu có lỗi (ví dụ: Celery không chạy), chạy trực tiếp
            print(f"Could not run as Celery task, executing directly: {e}")
            generate_user_data_download(request.id)

@shared_task
def generate_user_data_download(request_id):
    """Tạo file zip chứa dữ liệu người dùng để tải xuống."""
    try:
        # Lấy yêu cầu tải xuống
        download_request = DataDownloadRequest.objects.get(id=request_id)
        user = download_request.user
        
        # Tạo thư mục tạm thời để lưu trữ dữ liệu
        temp_dir = tempfile.mkdtemp()
        
        # Tạo thông tin cơ bản của người dùng
        user_info = {
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name(),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'bio': user.bio,
            'website': user.website,
            'social_links': {
                'facebook': user.facebook,
                'twitter': user.twitter,
                'instagram': user.instagram,
                'linkedin': user.linkedin
            }
        }
        
        # Lưu thông tin cơ bản thành file JSON
        with open(os.path.join(temp_dir, 'user_info.json'), 'w', encoding='utf-8') as f:
            json.dump(user_info, f, ensure_ascii=False, indent=4)
        
        # Lấy danh sách bài viết của người dùng
        posts_data = []
        for post in user.posts.all():
            post_data = {
                'id': post.id,
                'caption': post.caption,
                'location': post.location,
                'created_at': post.created_at.isoformat(),
                'likes_count': post.likes_count,
                'comments_count': post.comments_count
            }
            posts_data.append(post_data)
        
        # Lưu bài viết thành file JSON
        with open(os.path.join(temp_dir, 'posts.json'), 'w', encoding='utf-8') as f:
            json.dump(posts_data, f, ensure_ascii=False, indent=4)
        
        # Lấy danh sách bình luận của người dùng
        comments_data = []
        for comment in user.comments.all():
            comment_data = {
                'id': comment.id,
                'text': comment.text,
                'created_at': comment.created_at.isoformat(),
                'post_id': comment.post.id if comment.post else None
            }
            comments_data.append(comment_data)
        
        # Lưu bình luận thành file JSON
        with open(os.path.join(temp_dir, 'comments.json'), 'w', encoding='utf-8') as f:
            json.dump(comments_data, f, ensure_ascii=False, indent=4)
        
        # Lấy danh sách người theo dõi và đang theo dõi
        followers_data = [{'username': follower.username, 'id': follower.id} 
                          for follower in user.followers.all()]
        following_data = [{'username': following.username, 'id': following.id} 
                          for following in user.following.all()]
        
        # Lưu thông tin theo dõi
        with open(os.path.join(temp_dir, 'followers.json'), 'w', encoding='utf-8') as f:
            json.dump(followers_data, f, ensure_ascii=False, indent=4)
        
        with open(os.path.join(temp_dir, 'following.json'), 'w', encoding='utf-8') as f:
            json.dump(following_data, f, ensure_ascii=False, indent=4)
        
        # Nếu yêu cầu bao gồm hình ảnh và video
        if download_request.include_media:
            media_dir = os.path.join(temp_dir, 'media')
            os.makedirs(media_dir, exist_ok=True)
            
            # Sao chép avatar người dùng (nếu có)
            if user.avatar:
                avatar_path = user.avatar.path
                avatar_filename = os.path.basename(avatar_path)
                shutil.copy(avatar_path, os.path.join(media_dir, avatar_filename))
            
            # Sao chép hình ảnh từ bài viết
            for post in user.posts.all():
                if hasattr(post, 'media'):
                    for media in post.media.all():
                        if media.file and os.path.exists(media.file.path):
                            media_filename = os.path.basename(media.file.path)
                            shutil.copy(media.file.path, os.path.join(media_dir, media_filename))
        
        # Tạo file ZIP từ thư mục tạm thời
        zip_filename = f"user_data_{user.username}_{timezone.now().strftime('%Y%m%d%H%M%S')}.zip"
        zip_path = os.path.join(settings.MEDIA_ROOT, 'user_downloads', zip_filename)
        
        # Đảm bảo thư mục đích tồn tại
        os.makedirs(os.path.dirname(zip_path), exist_ok=True)
        
        # Tạo file ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Cập nhật yêu cầu tải xuống
        download_request.status = 'ready'
        download_request.file_path = zip_path
        download_request.expires_at = timezone.now() + timedelta(hours=48)
        download_request.save()
        
        # Gửi email thông báo
        try:
            send_data_download_ready_notification.delay(download_request.id)
        except Exception as e:
            # Nếu có lỗi khi gửi thông qua Celery, gửi trực tiếp
            print(f"Could not send notification as Celery task, executing directly: {e}")
            send_data_download_ready_notification(download_request.id)
        
        # Xóa thư mục tạm thời
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"Error generating user data download: {str(e)}")
        # Ghi log lỗi nhưng không đánh dấu yêu cầu là lỗi
        # có thể thêm logic retry ở đây

@shared_task
def send_data_download_ready_notification(request_id):
    """Gửi thông báo cho người dùng khi dữ liệu đã sẵn sàng để tải xuống."""
    download_request = DataDownloadRequest.objects.get(id=request_id)
    user = download_request.user
    
    context = {
        'user': user,
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_URL,
        'download_url': f"{settings.SITE_URL}{reverse('accounts:download_data', args=[download_request.id])}",
        'expires_at': download_request.expires_at
    }
    
    html_message = render_to_string(
        'accounts/email/data_download_ready.html',
        context
    )
    
    send_mail(
        subject=f'[{settings.SITE_NAME}] Dữ liệu của bạn đã sẵn sàng để tải xuống',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message
    )

@shared_task
def cleanup_expired_data_downloads():
    """Xóa các file tải xuống dữ liệu đã hết hạn."""
    # Lấy tất cả yêu cầu đã hết hạn
    expired_requests = DataDownloadRequest.objects.filter(
        status='ready',
        expires_at__lt=timezone.now()
    )
    
    for request in expired_requests:
        # Xóa file nếu tồn tại
        if request.file_path and os.path.exists(request.file_path):
            try:
                os.remove(request.file_path)
            except Exception as e:
                print(f"Error deleting expired file {request.file_path}: {str(e)}")
        
        # Cập nhật trạng thái
        request.status = 'expired'
        request.save() 