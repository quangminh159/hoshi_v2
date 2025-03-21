from celery import shared_task
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import User

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