from django.urls import path, include
from . import views
from django.views.generic import RedirectView
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    # Settings URLs
    path('settings/', views.settings, name='settings'),
    path('settings/revoke-device/<int:device_id>/', views.revoke_device, name='revoke_device'),
    path('settings/unlink-social/<str:provider>/', views.unlink_social, name='unlink_social'),
    path('settings/setup-2fa/', views.setup_two_factor, name='setup_two_factor'),
    path('settings/verify-2fa/', views.verify_two_factor, name='verify_two_factor'),
    
    # Block/Unblock URLs
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('report-user/', views.report_user, name='report_user'),
    
    # Password Reset URLs - chuyển hướng đến allauth
    path('password/reset/', RedirectView.as_view(url=reverse_lazy('account_reset_password')), name='account_reset_password'),
    path('password/reset/done/', RedirectView.as_view(url=reverse_lazy('account_reset_password_done')), name='account_reset_password_done'),
    
    # API URLs
    path('suggestions/', views.get_suggestions, name='get_suggestions'),
    path('api/<str:username>/posts/', views.api_load_profile_posts, name='api_load_profile_posts'),
    
    # Download data
    path('download-data/<int:request_id>/', views.download_user_data, name='download_data'),
    
    # Khôi phục tài khoản
    path('restore/', views.restore_account, name='restore_account'),
    
    # Các URL đặc biệt
    path('suspension-notice/', views.suspension_notice, name='suspension_notice'),
    
    # Profile URL - phải đặt cuối cùng vì nó match mọi string
    path('<str:username>/', views.profile, name='profile'),
] 