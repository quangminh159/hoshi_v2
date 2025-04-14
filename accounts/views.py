from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from django.db.models import Prefetch
from django.urls import reverse_lazy
from allauth.account.views import PasswordResetView, PasswordResetDoneView
from allauth.account.forms import ResetPasswordForm

from .forms import (
    ProfileForm,
    CustomPasswordChangeForm,
    NotificationSettingsForm,
    PrivacySettingsForm,
    SecuritySettingsForm,
    DeleteAccountForm,
    CustomResetPasswordForm
)
from .models import Device, DataDownloadRequest, UserFollowing, UserBlock, UserReport
import pyotp
import qrcode
from posts.models import SavedPost, Post, Comment

User = get_user_model()

def profile(request, username):
    user = get_object_or_404(User, username=username)
    is_own_profile = request.user == user
    is_saved_posts = request.GET.get('tab') == 'saved'
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

    if is_saved_posts and is_own_profile:
        # Lấy các bài viết đã lưu giống như feed
        saved_posts = SavedPost.objects.filter(user=request.user).select_related('post', 'post__author')
        posts = [saved_post.post for saved_post in saved_posts]
        
        # Prefetch related data giống như trong home view
        posts = Post.objects.filter(id__in=[post.id for post in posts]).prefetch_related(
            'media', 
            Prefetch('comments', queryset=Comment.objects.filter(parent__isnull=True).select_related('author'))
        ).select_related('author')
    else:
        # Logic hiện tại cho các bài viết của người dùng
        posts = Post.objects.filter(author=user).prefetch_related(
            'media', 
            Prefetch('comments', queryset=Comment.objects.filter(parent__isnull=True).select_related('author'))
        )

    # Pagination
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile_user': user,
        'posts': page_obj,
        'is_own_profile': is_own_profile,
        'is_saved_posts': is_saved_posts,
        # followers: những người đang theo dõi tài khoản này
        'followers_count': user.get_followers_count(),
        # following: những người mà tài khoản này đang theo dõi
        'following_count': user.get_following_count(),
        'posts_count': posts.count(),
        'is_following': is_following,
    }

    # Debug print
    for post in page_obj:
        print(f"Post {post.id} media: {list(post.media.all())}")

    return render(request, 'accounts/profile.html', context)

@login_required
def settings(request):
    active_tab = request.GET.get('tab', 'profile')
    
    # Khởi tạo các form
    profile_form = ProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(request.user)
    notification_form = NotificationSettingsForm(instance=request.user)
    privacy_form = PrivacySettingsForm(instance=request.user)
    security_form = SecuritySettingsForm(instance=request.user)
    delete_form = DeleteAccountForm(request.user)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                # Xử lý việc xóa avatar
                if profile_form.cleaned_data.get('remove_avatar'):
                    # Nếu checkbox xóa avatar được chọn, xóa avatar hiện tại
                    if request.user.avatar:
                        request.user.avatar.delete()
                
                # Lưu form ban đầu
                user = profile_form.save()
                
                # Xử lý các trường tùy chỉnh từ form
                for key, value in request.POST.items():
                    if (key.startswith('custom_') or key.startswith('social_link_')) and value:
                        field_name = key
                        # Lưu trực tiếp từ request.POST vào user instance
                        setattr(user, field_name, value)
                
                # Lưu lại user với các trường tùy chỉnh
                user.save()
                
                messages.success(request, 'Hồ sơ của bạn đã được cập nhật thành công.')
                return redirect('accounts:settings')
                
        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Mật khẩu đã được thay đổi.')
                return redirect('accounts:settings')
                
        elif 'update_notifications' in request.POST:
            notification_form = NotificationSettingsForm(request.POST, instance=request.user)
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Cài đặt thông báo đã được cập nhật.')
                return redirect('accounts:settings')
                
        elif 'update_privacy' in request.POST:
            privacy_form = PrivacySettingsForm(request.POST, instance=request.user)
            if privacy_form.is_valid():
                privacy_form.save()
                messages.success(request, 'Cài đặt quyền riêng tư đã được cập nhật.')
                return redirect('accounts:settings')
                
        elif 'update_security' in request.POST:
            security_form = SecuritySettingsForm(request.POST, instance=request.user)
            if security_form.is_valid():
                security_form.save()
                messages.success(request, 'Cài đặt bảo mật đã được cập nhật.')
                return redirect('accounts:settings')
                
        elif 'delete_account' in request.POST:
            delete_form = DeleteAccountForm(request.user, request.POST)
            if delete_form.is_valid():
                request.user.delete()
                messages.success(request, 'Tài khoản của bạn đã được xóa.')
                return redirect('home')
    
    # Lấy danh sách thiết bị
    devices = Device.objects.filter(user=request.user).order_by('-last_active')
    
    # Lấy yêu cầu tải xuống dữ liệu
    data_requests = DataDownloadRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Lấy danh sách người dùng đã bị chặn
    blocked_users = UserBlock.objects.filter(blocker=request.user).select_related('blocked').order_by('-created_at')
    
    context = {
        'active_tab': active_tab,
        'profile_form': profile_form,
        'password_form': password_form,
        'notification_form': notification_form,
        'privacy_form': privacy_form,
        'security_form': security_form,
        'delete_form': delete_form,
        'devices': devices,
        'data_requests': data_requests,
        'blocked_users': blocked_users,
        'notifications': {
            'push': request.user.notification_settings.push_enabled if hasattr(request.user, 'notification_settings') else False,
            'email': request.user.notification_settings.email_enabled if hasattr(request.user, 'notification_settings') else False,
            'likes': request.user.notification_settings.likes_enabled if hasattr(request.user, 'notification_settings') else False,
            'comments': request.user.notification_settings.comments_enabled if hasattr(request.user, 'notification_settings') else False,
            'follows': request.user.notification_settings.follows_enabled if hasattr(request.user, 'notification_settings') else False,
            'mentions': request.user.notification_settings.mentions_enabled if hasattr(request.user, 'notification_settings') else False,
        },
        'privacy': {
            'private_account': request.user.privacy_settings.private_account if hasattr(request.user, 'privacy_settings') else False,
            'hide_activity': request.user.privacy_settings.hide_activity if hasattr(request.user, 'privacy_settings') else False,
            'block_messages': request.user.privacy_settings.block_messages if hasattr(request.user, 'privacy_settings') else False,
        },
        'security': {
            'two_factor': request.user.two_factor_auth if hasattr(request.user, 'two_factor_auth') else False,
        }
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
def request_data_download(request):
    include_media = request.POST.get('include_media', False)
    
    # Kiểm tra xem có yêu cầu nào đang xử lý không
    if DataDownloadRequest.objects.filter(
        user=request.user,
        status='pending',
        created_at__gte=timezone.now() - timezone.timedelta(days=1)
    ).exists():
        messages.error(request, 'Bạn đã có một yêu cầu đang được xử lý. Vui lòng thử lại sau.')
        return redirect('accounts:settings')
    
    # Tạo yêu cầu mới
    DataDownloadRequest.objects.create(
        user=request.user,
        include_media=include_media
    )
    
    messages.success(request, 'Yêu cầu của bạn đã được ghi nhận. Chúng tôi sẽ thông báo khi dữ liệu sẵn sàng để tải xuống.')
    return redirect('accounts:settings')

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
        return redirect('accounts:settings')
    
    # Tạo secret key và QR code
    secret_key = pyotp.random_base32()
    totp = pyotp.TOTP(secret_key)
    qr_code = qrcode.make(totp.provisioning_uri(
        request.user.email,
        issuer_name="Hoshi"
    ))
    
    # Lưu secret key tạm thời
    request.session['temp_2fa_secret'] = secret_key
    
    context = {
        'qr_code': qr_code,
        'secret_key': secret_key
    }
    
    return render(request, 'accounts/setup_2fa.html', context)

@login_required
@require_POST
def verify_two_factor(request):
    code = request.POST.get('code')
    secret_key = request.session.get('temp_2fa_secret')
    
    if not secret_key:
        messages.error(request, 'Phiên thiết lập đã hết hạn. Vui lòng thử lại.')
        return redirect('accounts:setup_two_factor')
    
    totp = pyotp.TOTP(secret_key)
    if totp.verify(code):
        request.user.two_factor_auth = True
        request.user.two_factor_secret = secret_key
        request.user.save()
        
        del request.session['temp_2fa_secret']
        messages.success(request, 'Xác thực hai yếu tố đã được kích hoạt.')
        return redirect('accounts:settings')
    
    messages.error(request, 'Mã xác thực không chính xác.')
    return redirect('accounts:setup_two_factor')

@login_required
def get_suggestions(request):
    # Lấy người dùng chưa được follow
    suggestions = User.objects.exclude(
        id__in=request.user.following.values_list('id', flat=True)
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
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1
    
    # Lấy thông tin người dùng
    user = get_object_or_404(User, username=username)
    
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
    
    # Lấy bài viết của người dùng
    posts = user.posts.all().order_by('-created_at')
    
    # Phân trang
    posts_per_page = 6  # Số bài viết mỗi trang
    paginator = Paginator(posts, posts_per_page)
    
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        # Nếu trang không tồn tại, trả về một danh sách trống
        return JsonResponse({'posts': [], 'has_next': False})
    
    # Chuẩn bị dữ liệu cho JSON response
    posts_data = []
    for post in page_obj.object_list:
        # Lấy thông tin về media của bài viết
        media_files = []
        for media in post.media.all():
            media_files.append({
                'id': media.id,
                'file_url': media.file.url,
                'media_type': media.media_type,
                'order': media.order
            })
        
        posts_data.append({
            'id': post.id,
            'caption': post.caption,
            'location': post.location,
            'created_at': post.created_at.isoformat(),
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'is_liked': post.post_likes.filter(user=request.user).exists(),
            'media': media_files,
            'disable_comments': post.disable_comments,
        })
    
    return JsonResponse({
        'posts': posts_data,
        'has_next': page_obj.has_next()
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
    template_name = 'accounts/password_reset.html'
    success_url = reverse_lazy('accounts:account_reset_password_done')
    form_class = CustomResetPasswordForm

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'

# Đăng ký các view mới
password_reset = CustomPasswordResetView.as_view()
password_reset_done = CustomPasswordResetDoneView.as_view()

def suspension_notice(request):
    """Hiển thị thông báo khi tài khoản bị đình chỉ"""
    if not request.user.is_authenticated:
        return redirect('home')
        
    # Kiểm tra lại trạng thái đình chỉ
    is_suspended = request.user.check_suspension_status()
    
    # Nếu không còn bị đình chỉ, chuyển hướng về trang chủ
    if not is_suspended:
        messages.success(request, 'Tài khoản của bạn không còn bị đình chỉ. Bạn có thể tiếp tục sử dụng dịch vụ.')
        return redirect('home')
    
    context = {
        'suspension_reason': request.user.suspension_reason,
        'suspension_end_date': request.user.suspension_end_date,
    }
    
    return render(request, 'accounts/suspension_notice.html', context)
