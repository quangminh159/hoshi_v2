"""
Django settings cho môi trường Render.
"""

from pathlib import Path
import os

# Kế thừa cài đặt cơ bản
from .settings import *

# Đảm bảo dj-database-url được import đúng cách
try:
    import dj_database_url
except ImportError:
    import sys
    print("dj-database-url không được tìm thấy, đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dj-database-url==2.1.0"])
    import dj_database_url

# Tắt DEBUG trong môi trường production
DEBUG = False

# Cấu hình host cho Render
ALLOWED_HOSTS = ['.onrender.com', 'hoshi.onrender.com']

# Cấu hình Database cho Render
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
    }
else:
    print("Cảnh báo: DATABASE_URL không được cấu hình.")

# Đảm bảo SQLite không được sử dụng trong môi trường production
if 'sqlite' in DATABASES['default']['ENGINE']:
    print("Cảnh báo: Đang sử dụng SQLite trong môi trường production.")

# Cấu hình Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Thêm Whitenoise middleware
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Cấu hình Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Cấu hình Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 năm
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cấu hình CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://hoshi.onrender.com',
    'https://*.onrender.com',
]

# Cấu hình OAuth callback
OAUTH_CALLBACK_DOMAIN = 'https://hoshi.onrender.com'

# Thiết lập một số biến môi trường khác từ Render
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', SECRET_KEY)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Cấu hình Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Cấu hình Social Auth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
FACEBOOK_CLIENT_ID = os.environ.get('FACEBOOK_CLIENT_ID', '')
FACEBOOK_CLIENT_SECRET = os.environ.get('FACEBOOK_CLIENT_SECRET', '')

# Cập nhật các social apps với credentials mới từ environment
try:
    SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'] = GOOGLE_CLIENT_ID
    SOCIALACCOUNT_PROVIDERS['google']['APP']['secret'] = GOOGLE_CLIENT_SECRET
    SOCIALACCOUNT_PROVIDERS['facebook']['APP']['client_id'] = FACEBOOK_CLIENT_ID
    SOCIALACCOUNT_PROVIDERS['facebook']['APP']['secret'] = FACEBOOK_CLIENT_SECRET
except Exception as e:
    print(f"Lỗi khi cập nhật SOCIALACCOUNT_PROVIDERS: {e}")

# Vô hiệu hóa thông báo không cần thiết
SILENCED_SYSTEM_CHECKS = ['allauth.socialaccount.W002'] 