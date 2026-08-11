from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, get_user_model, logout, login
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import login as auth_login
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from django.urls import reverse_lazy
from allauth.account.views import PasswordResetView, PasswordResetDoneView
from allauth.account.forms import ResetPasswordForm

from .forms import (
    ProfileForm,
    CustomPasswordChangeForm,
    NotificationSettingsForm,
    PrivacySettingsForm,
    DeleteAccountForm,
    CustomResetPasswordForm,
    DisableTwoFactorForm,
    VerifyTwoFactorLoginForm,
    ChangeEmailRequestForm,
    ChangePhoneRequestForm,
    ContactOtpVerifyForm,
    LanguageSettingsForm,
)
from .models import Device, DataDownloadRequest, UserFollowing, UserBlock, UserReport, FollowRequest
import pyotp
import qrcode
import base64
import io
from posts.models import SavedPost, Post
from posts.views import prepare_posts_json
import os
import mimetypes

User = get_user_model()


@require_http_methods(["GET"])
def check_username_available(request):
    """Kiểm tra tên đăng nhập đã được dùng chưa (dùng ở form đăng ký)."""
    username = (request.GET.get('username') or '').strip()
    if not username:
        return JsonResponse({'available': False, 'message': 'Vui lòng nhập tên đăng nhập.'})
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Tên đăng nhập cần ít nhất 3 ký tự.'})
    taken = User.objects.filter(username__iexact=username).exists()
    if taken:
        return JsonResponse({
            'available': False,
            'message': 'Đã có người sử dụng tên đăng nhập này rồi.',
        })
    return JsonResponse({'available': True, 'message': 'Tên đăng nhập này còn trống.'})


def profile(request, username):
    user = get_object_or_404(User, username__iexact=username)
    # Chuẩn hóa URL nếu khác hoa/thường so với username thật
    if user.username != username:
        return redirect('accounts:profile', username=user.username)
    is_own_profile = request.user == user
    tab = request.GET.get('tab', '')
    is_saved_posts = tab == 'saved'
    is_shared_posts = tab == 'shared'
    is_following = False
    
    # Kiểm tra xem người dùng có bị chặn không
    if request.user.is_authenticated and not is_own_profile:
        # Kiểm tra quan hệ chặn theo cả hai chiều
        block_relationship_exists = (
            UserBlock.objects.filter(blocker=user, blocked=request.user).exists() or 
            UserBlock.objects.filter(blocker=request.user, blocked=user).exists()
        )
        
        if block_relationship_exists:
            messages.error(request, f'Bạn không thể xem trang cá nhân của {username}.')
            return redirect('home')
        
        # Kiểm tra trạng thái theo dõi
        is_following = UserFollowing.objects.filter(
            user=request.user,
            following_user=user
        ).exists()

    follow_request_sent = False
    if request.user.is_authenticated and not is_own_profile and not is_following:
        follow_request_sent = FollowRequest.pending_exists(request.user, user)

    can_view_posts = user.posts_visible_to(request.user)

    context = {
        'profile_user': user,
        'is_own_profile': is_own_profile,
        'is_saved_posts': is_saved_posts,
        'is_shared_posts': is_shared_posts,
        'followers_count': user.get_followers_count(),
        'following_count': user.get_following_count(),
        'posts_count': Post.objects.filter(author=user).count(),
        'is_following': is_following,
        'follow_request_sent': follow_request_sent,
        'can_view_posts': can_view_posts,
        'is_private_account': user.is_account_private(),
        'profile_tab': 'saved' if is_saved_posts else ('shared' if is_shared_posts else 'posts'),
    }

    return render(request, 'accounts/profile.html', context)

def _settings_redirect(tab='profile'):
    from django.urls import reverse
    return redirect(f"{reverse('accounts:settings')}?tab={tab}")


@login_required
def settings(request):
    active_tab = request.GET.get('tab', 'profile')

    profile_form = ProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(request.user)
    notification_form = NotificationSettingsForm(instance=request.user)
    privacy_form = PrivacySettingsForm(instance=request.user)
    delete_form = DeleteAccountForm(request.user)
    disable_2fa_form = DisableTwoFactorForm(request.user)
    language_form = LanguageSettingsForm(instance=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Hồ sơ của bạn đã được cập nhật thành công.')
                return _settings_redirect('profile')
            active_tab = 'profile'

        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Mật khẩu đã được thay đổi.')
                return _settings_redirect('password')
            active_tab = 'password'

        elif 'update_notifications' in request.POST:
            notification_form = NotificationSettingsForm(request.POST, instance=request.user)
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Cài đặt thông báo đã được cập nhật.')
                return _settings_redirect('notifications')
            active_tab = 'notifications'

        elif 'update_privacy' in request.POST:
            privacy_form = PrivacySettingsForm(request.POST, instance=request.user)
            if privacy_form.is_valid():
                privacy_form.save()
                messages.success(request, 'Cài đặt quyền riêng tư đã được cập nhật.')
                return _settings_redirect('privacy')
            messages.error(request, 'Có lỗi khi cập nhật cài đặt quyền riêng tư.')
            active_tab = 'privacy'

        elif 'disable_two_factor' in request.POST:
            disable_2fa_form = DisableTwoFactorForm(request.user, request.POST)
            if disable_2fa_form.is_valid():
                request.user.two_factor_auth = False
                request.user.two_factor_secret = None
                request.user.save(update_fields=['two_factor_auth', 'two_factor_secret'])
                messages.success(request, 'Đã tắt xác thực hai yếu tố.')
                return _settings_redirect('security')
            messages.error(request, 'Không thể tắt 2FA. Kiểm tra mật khẩu hoặc mã xác thực.')
            active_tab = 'security'

        elif 'update_language' in request.POST:
            language_form = LanguageSettingsForm(request.POST, instance=request.user)
            if language_form.is_valid():
                user = language_form.save()
                from django.utils import translation
                from django.conf import settings as django_settings
                translation.activate(user.language)
                request.LANGUAGE_CODE = user.language
                messages.success(
                    request,
                    translation.gettext('Đã cập nhật ngôn ngữ hiển thị.')
                )
                response = _settings_redirect('language')
                response.set_cookie(
                    django_settings.LANGUAGE_COOKIE_NAME,
                    user.language,
                    max_age=getattr(django_settings, 'LANGUAGE_COOKIE_AGE', 60 * 60 * 24 * 365),
                    path=getattr(django_settings, 'LANGUAGE_COOKIE_PATH', '/'),
                    domain=getattr(django_settings, 'LANGUAGE_COOKIE_DOMAIN', None),
                    secure=getattr(django_settings, 'LANGUAGE_COOKIE_SECURE', False),
                    httponly=getattr(django_settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
                    samesite=getattr(django_settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
                )
                return response
            active_tab = 'language'

        elif 'delete_account' in request.POST:
            delete_form = DeleteAccountForm(request.user, request.POST)
            if delete_form.is_valid():
                reason = delete_form.cleaned_data.get('reason')
                request.user.deletion_reason = reason
                request.user.is_deleted = True
                request.user.deleted_at = timezone.now()
                request.user.save()
                logout(request)
                messages.success(request, 'Tài khoản của bạn đã được xóa thành công.')
                return redirect('home')
            messages.error(request, 'Có lỗi xảy ra khi xóa tài khoản. Vui lòng kiểm tra các thông tin đã nhập.')
            active_tab = 'delete'

        elif 'request_data_download' in request.POST:
            include_media = request.POST.get('include_media', '') == 'on'
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if DataDownloadRequest.objects.filter(
                user=request.user,
                status='pending',
                created_at__gte=timezone.now() - timezone.timedelta(days=1)
            ).exists():
                error_msg = 'Bạn đã có một yêu cầu đang được xử lý. Vui lòng thử lại sau.'
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return _settings_redirect('data')

            data_request = DataDownloadRequest.objects.create(
                user=request.user,
                include_media=include_media
            )

            try:
                from .tasks import generate_user_data_download
                generate_user_data_download.delay(data_request.id)
            except Exception:
                try:
                    from .tasks import generate_user_data_download
                    generate_user_data_download(data_request.id)
                except Exception:
                    pass

            success_msg = 'Yêu cầu của bạn đã được ghi nhận. Chúng tôi sẽ thông báo khi dữ liệu sẵn sàng để tải xuống.'
            if is_ajax:
                return JsonResponse({'status': 'success', 'message': success_msg})
            messages.success(request, success_msg)
            return _settings_redirect('data')

    devices = Device.objects.filter(user=request.user).order_by('-last_active')
    data_requests = DataDownloadRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    blocked_users = UserBlock.objects.filter(
        blocker=request.user
    ).select_related('blocked').order_by('-created_at')
    linked_social = list(request.user.socialaccount_set.values_list('provider', flat=True))

    notification_settings = {
        'push': request.user.push_notifications,
        'email': request.user.email_notifications,
        'likes': request.user.like_notifications,
        'comments': request.user.comment_notifications,
        'follows': request.user.follow_notifications,
        'mentions': request.user.mention_notifications,
        'messages': request.user.message_notifications,
        'summary': request.user.summary_notifications,
        'inactive': request.user.inactive_notifications,
    }
    privacy_settings = {
        'private_account': request.user.private_account,
        'hide_activity': request.user.hide_activity,
        'block_messages': request.user.block_messages,
    }

    context = {
        'active_tab': active_tab,
        'profile_form': profile_form,
        'password_form': password_form,
        'notification_form': notification_form,
        'privacy_form': privacy_form,
        'delete_form': delete_form,
        'disable_2fa_form': disable_2fa_form,
        'language_form': language_form,
        'devices': devices,
        'data_requests': data_requests,
        'blocked_users': blocked_users,
        'linked_social': linked_social,
        'notification_settings': notification_settings,
        'privacy_settings': privacy_settings,
        'two_factor_enabled': request.user.two_factor_auth,
    }

    return render(request, 'accounts/settings.html', context)

@login_required
@require_POST
def revoke_device(request, device_id):
    try:
        device = Device.objects.get(id=device_id, user=request.user)
        if not device.is_current:
            device.delete()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Không thể đăng xuất khỏi thiết bị hiện tại'})
    except Device.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Thiết bị không tồn tại'})

@login_required
@require_POST
def unlink_social(request, provider):
    if provider in ['google', 'facebook', 'apple']:
        social_account = request.user.socialaccount_set.filter(provider=provider).first()
        if social_account:
            social_account.delete()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Không thể hủy liên kết tài khoản'})

@login_required
def setup_two_factor(request):
    if request.user.two_factor_auth:
        messages.error(request, 'Xác thực hai yếu tố đã được kích hoạt.')
        return _settings_redirect('security')

    secret_key = request.session.get('temp_2fa_secret') or pyotp.random_base32()
    request.session['temp_2fa_secret'] = secret_key

    totp = pyotp.TOTP(secret_key)
    provisioning_uri = totp.provisioning_uri(
        name=request.user.email or request.user.username,
        issuer_name="Moora"
    )
    qr_img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_code_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render(request, 'accounts/setup_2fa.html', {
        'qr_code': qr_code_b64,
        'secret_key': secret_key,
    })


@login_required
@require_POST
def verify_two_factor(request):
    code = request.POST.get('code')
    secret_key = request.session.get('temp_2fa_secret')

    if not secret_key:
        messages.error(request, 'Phiên thiết lập đã hết hạn. Vui lòng thử lại.')
        return redirect('accounts:setup_two_factor')

    totp = pyotp.TOTP(secret_key)
    if totp.verify(code, valid_window=1):
        request.user.two_factor_auth = True
        request.user.two_factor_secret = secret_key
        request.user.save(update_fields=['two_factor_auth', 'two_factor_secret'])
        request.session.pop('temp_2fa_secret', None)
        messages.success(request, 'Xác thực hai yếu tố đã được kích hoạt.')
        return _settings_redirect('security')

    messages.error(request, 'Mã xác thực không chính xác.')
    return redirect('accounts:setup_two_factor')


@require_http_methods(['GET', 'POST'])
def verify_two_factor_login(request):
    """Second step after password login when 2FA is enabled."""
    user_id = request.session.get('pending_2fa_user_id')
    if not user_id:
        messages.error(request, 'Phiên xác thực đã hết hạn. Vui lòng đăng nhập lại.')
        return redirect('account_login')

    try:
        user = User.all_objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.pop('pending_2fa_user_id', None)
        messages.error(request, 'Không tìm thấy tài khoản. Vui lòng đăng nhập lại.')
        return redirect('account_login')

    if not user.two_factor_auth or not user.two_factor_secret:
        request.session.pop('pending_2fa_user_id', None)
        return redirect('account_login')

    form = VerifyTwoFactorLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(form.cleaned_data['code'], valid_window=1):
            request.session.pop('pending_2fa_user_id', None)
            backend = request.session.pop('pending_2fa_backend', None)
            request.session['two_factor_verified'] = True
            if backend:
                user.backend = backend
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, user)
            request.session.pop('two_factor_verified', None)
            messages.success(request, 'Đăng nhập thành công.')
            return redirect('home')
        form.add_error('code', 'Mã xác thực không chính xác.')

    return render(request, 'accounts/verify_2fa_login.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def change_email(request):
    """Request email change — OTP is sent to the CURRENT email."""
    from .otp_utils import (
        generate_otp, store_otp, is_in_cooldown, deliver_contact_otp, get_otp_record
    )

    pending = get_otp_record(request.user.id, 'change_email')
    if pending and request.method == 'GET' and request.GET.get('step') == 'verify':
        return redirect('accounts:verify_change_email')

    form = ChangeEmailRequestForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if is_in_cooldown(request.user.id, 'change_email'):
            messages.error(request, 'Vui lòng đợi khoảng 1 phút trước khi gửi lại mã.')
            return redirect('accounts:change_email')

        if not request.user.email:
            messages.error(request, 'Tài khoản chưa có email hiện tại để nhận mã xác thực.')
            return redirect('accounts:change_email')

        new_email = form.cleaned_data['new_email']
        code = generate_otp()
        store_otp(request.user.id, 'change_email', code, {'new_email': new_email})
        result = deliver_contact_otp(request.user, 'email', code, 'đổi email')
        if not result['ok']:
            messages.error(request, result['message'])
            return redirect('accounts:change_email')

        messages.success(request, result['message'])
        return redirect('accounts:verify_change_email')

    return render(request, 'accounts/change_email.html', {
        'form': form,
        'current_email': request.user.email,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def verify_change_email(request):
    from .otp_utils import verify_otp, get_otp_record, generate_otp, store_otp, deliver_contact_otp, is_in_cooldown

    record = get_otp_record(request.user.id, 'change_email')
    if not record:
        messages.error(request, 'Không có yêu cầu đổi email đang chờ. Vui lòng thử lại.')
        return redirect('accounts:change_email')

    form = ContactOtpVerifyForm(request.POST or None)
    if request.method == 'POST':
        if 'resend' in request.POST:
            if is_in_cooldown(request.user.id, 'change_email'):
                messages.error(request, 'Vui lòng đợi khoảng 1 phút trước khi gửi lại mã.')
            else:
                code = generate_otp()
                store_otp(request.user.id, 'change_email', code, record.get('payload') or {})
                result = deliver_contact_otp(request.user, 'email', code, 'đổi email')
                messages.success(request, result['message'] if result['ok'] else result['message'])
            return redirect('accounts:verify_change_email')

        if form.is_valid():
            ok, payload, error = verify_otp(request.user.id, 'change_email', form.cleaned_data['code'])
            if not ok:
                form.add_error('code', error)
            else:
                new_email = payload.get('new_email')
                if not new_email:
                    messages.error(request, 'Yêu cầu không hợp lệ. Vui lòng thử lại.')
                    return redirect('accounts:change_email')
                if User.objects.exclude(pk=request.user.pk).filter(email__iexact=new_email).exists():
                    messages.error(request, 'Email này đã được sử dụng.')
                    return redirect('accounts:change_email')
                request.user.email = new_email
                request.user.save(update_fields=['email'])
                try:
                    from allauth.account.models import EmailAddress
                    EmailAddress.objects.filter(user=request.user, primary=True).update(email=new_email)
                    EmailAddress.objects.update_or_create(
                        user=request.user,
                        email=new_email,
                        defaults={'primary': True, 'verified': False},
                    )
                except Exception:
                    pass
                messages.success(request, f'Đã đổi email thành {new_email}.')
                return _settings_redirect('profile')

    return render(request, 'accounts/verify_contact_change.html', {
        'form': form,
        'title': 'Xác thực đổi email',
        'hint': f'Nhập mã 6 số đã gửi đến email hiện tại: {request.user.email}',
        'pending_value': (record.get('payload') or {}).get('new_email'),
        'pending_label': 'Email mới',
        'resend_url': 'accounts:verify_change_email',
        'cancel_url': 'accounts:change_email',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def change_phone(request):
    """Request phone change — OTP is sent to the CURRENT phone (email fallback)."""
    from .otp_utils import (
        generate_otp, store_otp, is_in_cooldown, deliver_contact_otp, get_otp_record
    )

    form = ChangePhoneRequestForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if is_in_cooldown(request.user.id, 'change_phone'):
            messages.error(request, 'Vui lòng đợi khoảng 1 phút trước khi gửi lại mã.')
            return redirect('accounts:change_phone')

        new_phone = form.cleaned_data['new_phone']
        code = generate_otp()
        store_otp(request.user.id, 'change_phone', code, {'new_phone': str(new_phone)})
        result = deliver_contact_otp(request.user, 'phone', code, 'đổi số điện thoại')
        if not result['ok']:
            messages.error(request, result['message'])
            return redirect('accounts:change_phone')

        messages.success(request, result['message'])
        return redirect('accounts:verify_change_phone')

    return render(request, 'accounts/change_phone.html', {
        'form': form,
        'current_phone': request.user.phone_number,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def verify_change_phone(request):
    from .otp_utils import verify_otp, get_otp_record, generate_otp, store_otp, deliver_contact_otp, is_in_cooldown

    record = get_otp_record(request.user.id, 'change_phone')
    if not record:
        messages.error(request, 'Không có yêu cầu đổi số điện thoại đang chờ. Vui lòng thử lại.')
        return redirect('accounts:change_phone')

    form = ContactOtpVerifyForm(request.POST or None)
    if request.method == 'POST':
        if 'resend' in request.POST:
            if is_in_cooldown(request.user.id, 'change_phone'):
                messages.error(request, 'Vui lòng đợi khoảng 1 phút trước khi gửi lại mã.')
            else:
                code = generate_otp()
                store_otp(request.user.id, 'change_phone', code, record.get('payload') or {})
                result = deliver_contact_otp(request.user, 'phone', code, 'đổi số điện thoại')
                messages.success(request, result['message'] if result['ok'] else result['message'])
            return redirect('accounts:verify_change_phone')

        if form.is_valid():
            ok, payload, error = verify_otp(request.user.id, 'change_phone', form.cleaned_data['code'])
            if not ok:
                form.add_error('code', error)
            else:
                new_phone = payload.get('new_phone')
                if not new_phone:
                    messages.error(request, 'Yêu cầu không hợp lệ. Vui lòng thử lại.')
                    return redirect('accounts:change_phone')
                if User.objects.exclude(pk=request.user.pk).filter(phone_number=new_phone).exists():
                    messages.error(request, 'Số điện thoại này đã được sử dụng.')
                    return redirect('accounts:change_phone')
                request.user.phone_number = new_phone
                request.user.save(update_fields=['phone_number'])
                messages.success(request, f'Đã đổi số điện thoại thành {new_phone}.')
                return _settings_redirect('profile')

    dest_hint = (
        f'số điện thoại hiện tại: {request.user.phone_number}'
        if request.user.phone_number
        else f'email: {request.user.email}'
    )
    return render(request, 'accounts/verify_contact_change.html', {
        'form': form,
        'title': 'Xác thực đổi số điện thoại',
        'hint': f'Nhập mã 6 số đã gửi đến {dest_hint}',
        'pending_value': (record.get('payload') or {}).get('new_phone'),
        'pending_label': 'SĐT mới',
        'resend_url': 'accounts:verify_change_phone',
        'cancel_url': 'accounts:change_phone',
    })


@login_required
def get_suggestions(request):
    # Lấy người dùng chưa được follow
    suggestions = User.objects.exclude(
        id__in=request.user.get_following_user_ids()
    ).exclude(
        id=request.user.id
    ).order_by('?')[:5]  # Random 5 người dùng
    
    data = [{
        'id': user.id,
        'username': user.username,
        'name': f"{user.first_name} {user.last_name}".strip(),
        'avatar': user.avatar.url if user.avatar else None,
        'followers_count': user.followers.count()
    } for user in suggestions]
    
    return JsonResponse({'suggestions': data})

@login_required
def api_load_profile_posts(request, username):
    """API endpoint để tải thêm bài viết cho trang cá nhân với cuộn vô hạn"""
    page_number = request.GET.get('page', 1)
    tab = request.GET.get('tab', '')
    
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1
    
    # Lấy thông tin người dùng
    user = get_object_or_404(User, username__iexact=username)
    
    # Kiểm tra quan hệ chặn theo cả hai chiều
    block_relationship_exists = (
        UserBlock.objects.filter(blocker=user, blocked=request.user).exists() or 
        UserBlock.objects.filter(blocker=request.user, blocked=user).exists()
    )
    
    if block_relationship_exists:
        return JsonResponse({
            'status': 'error',
            'message': 'Bạn không thể xem bài viết từ người dùng này.',
            'posts': [],
            'has_next': False
        })

    if not user.posts_visible_to(request.user):
        return JsonResponse({
            'status': 'private',
            'message': 'Tài khoản này ở chế độ riêng tư. Hãy theo dõi để xem bài viết.',
            'posts': [],
            'has_next': False,
            'is_private': True,
        })
    
    # Xác định loại bài viết cần lấy dựa vào tab
    if tab == 'saved' and request.user == user:
        posts = Post.objects.filter(
            id__in=SavedPost.objects.filter(user=user).values_list('post_id', flat=True)
        ).order_by('-created_at')
    elif tab == 'shared':
        posts = Post.objects.filter(
            author=user,
            shared_from__isnull=False
        ).order_by('-created_at')
    else:
        posts = user.posts.all().order_by('-created_at')

    posts = posts.select_related(
        'author', 'shared_from', 'shared_from__author'
    ).prefetch_related('media', 'shared_from__media')

    posts_per_page = 6
    paginator = Paginator(posts, posts_per_page)

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        return JsonResponse({'posts': [], 'has_next': False})

    return JsonResponse({
        'posts': prepare_posts_json(page_obj.object_list, request.user, include_comments=True),
        'has_next': page_obj.has_next(),
    })

@login_required
def block_user(request, user_id):
    """Chặn một người dùng khác"""
    if request.method == 'POST':
        try:
            user_to_block = User.objects.get(id=user_id)
            
            # Xử lý dữ liệu từ cả JSON và form data
            if request.content_type == 'application/json':
                import json
                data = json.loads(request.body)
                delete_chat = str(data.get('delete_chat', 'false')).lower()
            else:
                delete_chat = request.POST.get('delete_chat', 'false').lower()
            
            # Không thể tự chặn chính mình
            if user_to_block == request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bạn không thể chặn chính mình.'
                })
            
            # Kiểm tra xem đã chặn người dùng này chưa
            if request.user.has_blocked(user_to_block):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bạn đã chặn người dùng này rồi.'
                })
            
            # Tạo bản ghi chặn
            UserBlock.objects.create(
                blocker=request.user,
                blocked=user_to_block
            )
            
            # Nếu đang theo dõi người dùng này, hủy theo dõi
            UserFollowing.objects.filter(
                user=request.user,
                following_user=user_to_block
            ).delete()

            # Nếu người dùng này đang theo dõi mình, xóa theo dõi
            UserFollowing.objects.filter(
                user=user_to_block,
                following_user=request.user
            ).delete()

            FollowRequest.delete_between(request.user, user_to_block)

            # Xử lý phòng chat tùy theo lựa chọn của người dùng
            from chat.models import ChatRoom
            one_to_one_rooms = ChatRoom.objects.filter(
                is_group=False,
                participants=request.user
            ).filter(
                participants=user_to_block
            )
            
            if delete_chat == 'true':
                # Xóa tất cả các phòng chat 1-1 giữa hai người dùng
                for room in one_to_one_rooms:
                    room.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Đã chặn {user_to_block.username} thành công.'
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Không tìm thấy người dùng.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Phương thức không được hỗ trợ.'
    })

@login_required
def unblock_user(request, user_id):
    """Bỏ chặn một người dùng"""
    if request.method == 'POST':
        try:
            user_to_unblock = User.objects.get(id=user_id)
            
            # Kiểm tra xem có đang chặn người dùng này không
            block_record = UserBlock.objects.filter(
                blocker=request.user,
                blocked=user_to_unblock
            ).first()
            
            if not block_record:
                if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Bạn chưa chặn người dùng này.'
                    })
                else:
                    messages.error(request, 'Bạn chưa chặn người dùng này.')
                    return redirect('accounts:settings')
            
            # Xóa bản ghi chặn
            block_record.delete()
            
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f'Đã bỏ chặn {user_to_unblock.username} thành công.'
                })
            else:
                messages.success(request, f'Đã bỏ chặn {user_to_unblock.username} thành công.')
                return redirect('accounts:settings')
            
        except User.DoesNotExist:
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Không tìm thấy người dùng.'
                })
            else:
                messages.error(request, 'Không tìm thấy người dùng.')
                return redirect('accounts:settings')
    
    # Xử lý GET request hoặc các method khác
    return redirect('accounts:settings')

@login_required
def report_user(request):
    """Báo cáo người dùng"""
    if request.method == 'POST':
        try:
            user_id = request.POST.get('user_id')
            reason = request.POST.get('reason')
            description = request.POST.get('description', '')
            block_user = request.POST.get('block_user') == 'on'
            
            if not user_id or not reason:
                if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Thiếu thông tin cần thiết để báo cáo.'
                    })
                else:
                    messages.error(request, 'Thiếu thông tin cần thiết để báo cáo.')
                    return redirect('home')
            
            reported_user = User.objects.get(id=user_id)
            
            # Không thể tự báo cáo chính mình
            if reported_user == request.user:
                if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Bạn không thể báo cáo chính mình.'
                    })
                else:
                    messages.error(request, 'Bạn không thể báo cáo chính mình.')
                    return redirect('home')
            
            # Tạo báo cáo mới
            report = UserReport.objects.create(
                reporter=request.user,
                reported_user=reported_user,
                reason=reason,
                description=description
            )
            
            # Kiểm tra và đình chỉ người dùng nếu cần thiết
            # Kiểm tra xem người dùng này đã có đủ báo cáo hợp lệ từ trước chưa
            UserReport.check_for_automatic_suspension(reported_user)
            
            # Chặn người dùng nếu được yêu cầu
            if block_user:
                # Kiểm tra nếu đã chặn
                if not request.user.has_blocked(reported_user):
                    UserBlock.objects.create(
                        blocker=request.user,
                        blocked=reported_user,
                        reason=f"Báo cáo: {reason}"
                    )
            
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Báo cáo của bạn đã được gửi. Chúng tôi sẽ xem xét nội dung báo cáo sớm nhất có thể.'
                })
            else:
                messages.success(request, 'Báo cáo của bạn đã được gửi. Chúng tôi sẽ xem xét nội dung báo cáo sớm nhất có thể.')
                return redirect('home')
            
        except User.DoesNotExist:
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Không tìm thấy người dùng được báo cáo.'
                })
            else:
                messages.error(request, 'Không tìm thấy người dùng được báo cáo.')
                return redirect('home')
        except Exception as e:
            if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Có lỗi xảy ra: {str(e)}'
                })
            else:
                messages.error(request, f'Có lỗi xảy ra: {str(e)}')
                return redirect('home')
    
    # Phương thức không được hỗ trợ
    if 'HTTP_X_REQUESTED_WITH' in request.META and request.META['HTTP_X_REQUESTED_WITH'] == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Phương thức không được hỗ trợ.'
        })
    else:
        messages.error(request, 'Phương thức không được hỗ trợ.')
        return redirect('home')

# Custom views cho việc đặt lại mật khẩu
class CustomPasswordResetView(PasswordResetView):
    template_name = 'account/password_reset.html'
    success_url = reverse_lazy('account_reset_password_done')
    form_class = CustomResetPasswordForm

    def form_valid(self, form):
        from allauth.core import ratelimit

        rate_key = str(form.cleaned_data.get('email') or '').lower()
        r429 = ratelimit.consume_or_429(
            self.request,
            action='reset_password_email',
            key=rate_key,
        )
        if r429:
            return r429

        form.save(self.request)
        if getattr(form, 'reset_via_phone', False):
            return redirect('account_reset_password_otp')
        return super(PasswordResetView, self).form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'account/password_reset_done.html'


# Đăng ký các view mới
password_reset = CustomPasswordResetView.as_view()
password_reset_done = CustomPasswordResetDoneView.as_view()


@require_http_methods(['GET', 'POST'])
def password_reset_otp(request):
    """Xác thực OTP khi đặt lại mật khẩu bằng số điện thoại."""
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import user_pk_to_url_str
    from django.urls import reverse
    from .otp_utils import (
        verify_otp,
        generate_otp,
        store_otp,
        deliver_password_reset_otp,
        is_in_cooldown,
        is_otp_locked,
        consume_ip_rate,
        client_ip,
        register_otp_failure,
        PASSWORD_RESET_NEUTRAL_MESSAGE,
        OTP_IP_VERIFY_LIMIT,
        OTP_IP_VERIFY_WINDOW,
        OTP_IP_RESEND_LIMIT,
        OTP_IP_RESEND_WINDOW,
    )

    uid = request.session.get('pwd_reset_uid')
    hint = request.session.get('pwd_reset_hint') or '****'
    info_message = request.session.get('pwd_reset_message') or PASSWORD_RESET_NEUTRAL_MESSAGE

    if request.session.get('pwd_reset_channel') != 'phone' and not uid and not hint:
        messages.error(request, 'Vui lòng nhập số điện thoại để nhận mã xác thực.')
        return redirect('account_reset_password')

    # Luôn ghi đè message session về bản trung tính (tránh message cũ lộ PII)
    request.session['pwd_reset_message'] = PASSWORD_RESET_NEUTRAL_MESSAGE
    info_message = PASSWORD_RESET_NEUTRAL_MESSAGE

    form = ContactOtpVerifyForm(request.POST or None)
    ip = client_ip(request)

    if request.method == 'POST':
        if 'resend' in request.POST:
            allowed, hint_msg = consume_ip_rate(
                ip, 'pwd_reset_resend', OTP_IP_RESEND_LIMIT, OTP_IP_RESEND_WINDOW
            )
            if not allowed:
                messages.error(request, hint_msg)
                return redirect('account_reset_password_otp')

            messages.success(request, PASSWORD_RESET_NEUTRAL_MESSAGE)

            if uid:
                user = User.objects.filter(pk=uid, is_active=True).first()
                if (
                    user
                    and not is_in_cooldown(user.id, 'password_reset')
                    and not is_otp_locked(user.id, 'password_reset')
                ):
                    code = generate_otp(8)
                    store_otp(user.id, 'password_reset', code, {})
                    deliver_password_reset_otp(user, code)
            return redirect('account_reset_password_otp')

        if form.is_valid():
            allowed, hint_msg = consume_ip_rate(
                ip, 'pwd_reset_verify', OTP_IP_VERIFY_LIMIT, OTP_IP_VERIFY_WINDOW
            )
            if not allowed:
                form.add_error('code', hint_msg)
            elif not uid:
                # Không tiết lộ account không tồn tại; đếm fail theo session giả
                fake_id = f'session:{request.session.session_key or ip}'
                locked, _attempts = register_otp_failure(fake_id, 'password_reset')
                if locked:
                    form.add_error(
                        'code',
                        'Quá nhiều lần thử sai. Vui lòng thử lại sau khoảng 15 phút.',
                    )
                else:
                    form.add_error('code', 'Mã xác thực không chính xác.')
            else:
                ok, _payload, error = verify_otp(
                    uid, 'password_reset', form.cleaned_data['code']
                )
                if not ok:
                    form.add_error('code', error)
                else:
                    user = User.objects.filter(pk=uid, is_active=True).first()
                    if not user:
                        form.add_error('code', 'Yêu cầu không hợp lệ. Vui lòng thử lại.')
                    else:
                        for key in (
                            'pwd_reset_uid',
                            'pwd_reset_hint',
                            'pwd_reset_message',
                            'pwd_reset_channel',
                        ):
                            request.session.pop(key, None)

                        temp_key = default_token_generator.make_token(user)
                        path = reverse(
                            'account_reset_password_from_key',
                            kwargs={
                                'uidb36': user_pk_to_url_str(user),
                                'key': temp_key,
                            },
                        )
                        return redirect(path)

    return render(request, 'account/password_reset_otp.html', {
        'form': form,
        'phone_hint': hint,
        'info_message': info_message,
    })


def suspension_notice(request):
    """Hiển thị thông báo khi tài khoản bị đình chỉ"""
    # Kiểm tra xem người dùng có đăng nhập không
    if not request.user.is_authenticated:
        return redirect('account_login')
        
    # Kiểm tra trạng thái đình chỉ
    is_suspended = request.user.check_suspension_status()
    
    # Nếu tài khoản không bị đình chỉ, chuyển hướng về trang chủ
    if not is_suspended:
        return redirect('home')
    
    context = {
        'user': request.user,
        'suspension_reason': request.user.suspension_reason,
        'suspension_end_date': request.user.suspension_end_date,
    }
    
    return render(request, 'accounts/suspension_notice.html', context)

@login_required
def download_user_data(request, request_id):
    """Tải xuống file dữ liệu người dùng đã được tạo."""
    data_request = get_object_or_404(DataDownloadRequest, id=request_id, user=request.user)
    
    # Kiểm tra trạng thái yêu cầu
    if data_request.status != 'ready':
        messages.error(request, 'Dữ liệu của bạn chưa sẵn sàng hoặc đã hết hạn.')
        return redirect('accounts:settings')
    
    # Kiểm tra thời gian hết hạn
    if data_request.expires_at and data_request.expires_at < timezone.now():
        data_request.status = 'expired'
        data_request.save()
        messages.error(request, 'Liên kết tải xuống đã hết hạn. Vui lòng yêu cầu lại.')
        return redirect('accounts:settings')
    
    # Kiểm tra xem file có tồn tại không
    if not data_request.file_path or not os.path.exists(data_request.file_path):
        messages.error(request, 'File dữ liệu không tồn tại. Vui lòng yêu cầu lại.')
        return redirect('accounts:settings')
    
    # Lấy tên file từ đường dẫn
    file_name = os.path.basename(data_request.file_path)
    
    # Mở file để gửi đến người dùng
    try:
        response = FileResponse(open(data_request.file_path, 'rb'))
        response['Content-Type'] = mimetypes.guess_type(data_request.file_path)[0] or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        messages.error(request, 'Đã xảy ra lỗi khi tải xuống file. Vui lòng thử lại sau.')
        return redirect('accounts:settings')

def restore_account(request):
    """Khôi phục tài khoản đã bị xóa tạm thời"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = User.all_objects.filter(username=username, is_deleted=True).first()
        
        if user is not None and user.check_password(password):
            # Khôi phục tài khoản
            user.is_deleted = False
            user.deleted_at = None
            user.deletion_reason = None
            # Kích hoạt lại tài khoản
            user.is_active = True
            user.save()
            
            # Đăng nhập người dùng với backend cụ thể
            from django.contrib.auth import get_backends
            backend = get_backends()[0]  # Sử dụng backend đầu tiên trong danh sách
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            
            messages.success(request, 'Tài khoản của bạn đã được khôi phục thành công.')
            return redirect('home')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác.')
    
    return render(request, 'accounts/restore_account.html')

def save(self, request):
    # Lưu user từ form cha
    user = super().save(request)
    
    # Xử lý avatar
    avatar = self.cleaned_data.get('avatar')
    if avatar:
        user.avatar = avatar
    
    # Lưu giới tính
    user.gender = self.cleaned_data.get('gender')
    
    # Lưu số điện thoại
    user.phone_number = self.cleaned_data.get('phone_number')
    
    # Đảm bảo tất cả các thông báo được bật mặc định
    user.push_notifications = True
    user.email_notifications = True
    user.like_notifications = True
    user.comment_notifications = True
    user.follow_notifications = True
    user.mention_notifications = True
    user.message_notifications = True
    user.summary_notifications = True
    user.inactive_notifications = True
    
    user.save()
    
    return user
