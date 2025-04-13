from .settings import *
import os
import dj_database_url

# Cấu hình Production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

# SECURITY WARNING: Cập nhật domain này theo tên miền Railway của bạn
ALLOWED_HOSTS = ['.up.railway.app', os.environ.get('RAILWAY_STATIC_URL', '').replace('https://', ''), 'localhost', '127.0.0.1']

# CSRF & CORS
CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
    os.environ.get('RAILWAY_STATIC_URL', '')
]

CORS_ALLOWED_ORIGINS = [
    'https://*.up.railway.app',
    os.environ.get('RAILWAY_STATIC_URL', '')
]

# Database (PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
    }

# Redis Cache (nếu có)
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }

# Static và Media files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Đảm bảo thư mục staticfiles tồn tại
os.makedirs(STATIC_ROOT, exist_ok=True)

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# AWS S3 cho lưu trữ media (nếu cần)
if os.environ.get('AWS_ACCESS_KEY_ID'):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-southeast-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

# Logging
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
}

# Security
# Tạm tắt redirect SSL trong quá trình debug
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 năm
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True 