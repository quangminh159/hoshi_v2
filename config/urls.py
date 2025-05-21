from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from posts.views import home
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    
    # App URLs
    path('posts/', include('posts.urls')),
    path('users/', include('accounts.urls')),
    path('notifications/', include('notifications.urls')),
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