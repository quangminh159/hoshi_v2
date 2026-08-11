from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render
from posts.views import home
from django.views.generic.base import RedirectView
from accounts.views import CustomPasswordResetView, password_reset_otp
from hoshi.range_media import serve_media_with_range


def redirect_legacy_profile(request, username):
    return redirect('accounts:profile', username=username)


def terms_of_service(request):
    return render(request, 'legal/terms.html')


def privacy_policy(request):
    return render(request, 'legal/privacy.html')


def community_guidelines(request):
    return render(request, 'legal/community.html')


def help_center(request):
    return render(request, 'help/center.html')


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('legal/terms/', terms_of_service, name='terms'),
    path('legal/privacy/', privacy_policy, name='privacy'),
    path('legal/community/', community_guidelines, name='community'),
    path('help/', help_center, name='help'),
    
    # App URLs
    path('posts/', include('posts.urls')),
    path('users/', include('accounts.urls')),
    path('accounts/profile/<str:username>/', redirect_legacy_profile),
    path('notifications/', include('notifications.urls')),
    # Override allauth password reset để hỗ trợ SĐT + OTP
    path('accounts/password/reset/', CustomPasswordResetView.as_view()),
    path('accounts/password/reset/otp/', password_reset_otp, name='account_reset_password_otp'),
    path('accounts/', include('allauth.urls')),
    path('chat/', include('chat.urls')),
    
    # API URLs
    path('api/posts/', include('posts.api_urls')),
    path('api/accounts/', include('accounts.api_urls')),
    path('api/notifications/', include('notifications.api_urls')),
    
    # Redirects for old endpoints
    path('api/comments/add/', RedirectView.as_view(url='/api/posts/comments/add/', permanent=False)),
    
    # Alias cho trang khôi phục tài khoản
    path('accounts/restore/', RedirectView.as_view(url='/users/restore/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]

# Media: view có HTTP Range (bắt buộc để tua audio/video file lớn).
# static() của Django + Daphne không trả 206 → trình duyệt không tua được.
_media_prefix = settings.MEDIA_URL.lstrip('/')
urlpatterns += [
    re_path(rf'^{_media_prefix}(?P<path>.*)$', serve_media_with_range),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 