from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render
from posts.views import home
from django.views.generic.base import RedirectView
from accounts.views import CustomPasswordResetView, password_reset_otp


def redirect_legacy_profile(request, username):
    return redirect('accounts:profile', username=username)


def terms_of_service(request):
    return render(request, 'legal/terms.html')


def privacy_policy(request):
    return render(request, 'legal/privacy.html')


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('legal/terms/', terms_of_service, name='terms'),
    path('legal/privacy/', privacy_policy, name='privacy'),
    
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
    
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 