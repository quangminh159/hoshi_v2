"""
Django settings cho môi trường Render.
"""

from pathlib import Path
import os

# Đảm bảo có thư viện cần thiết
try:
    import dj_database_url
except ImportError:
    import sys
    print("dj-database-url không được tìm thấy, đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dj-database-url==2.1.0"])
    import dj_database_url

try:
    from decouple import config
except ImportError:
    import sys
    print("python-decouple không được tìm thấy, đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-decouple==3.8"])
    from decouple import config

# Kiểm tra crispy_bootstrap5
try:
    import crispy_bootstrap5
    CRISPY_BOOTSTRAP5_INSTALLED = True
    print("Đã tìm thấy crispy-bootstrap5")
except ImportError:
    CRISPY_BOOTSTRAP5_INSTALLED = False
    print("Không tìm thấy crispy-bootstrap5, đang cố gắng cài đặt...")
    try:
        import sys
        # Sử dụng phiên bản 2025.4 thay vì 2022.1
        subprocess.check_call([sys.executable, "-m", "pip", "install", "crispy-bootstrap5==2025.4"])
        import crispy_bootstrap5
        CRISPY_BOOTSTRAP5_INSTALLED = True
        print("Đã cài đặt và import crispy-bootstrap5 thành công")
    except Exception as e:
        print(f"Không thể cài đặt crispy-bootstrap5: {e}")
        CRISPY_BOOTSTRAP5_INSTALLED = False

# Kiểm tra pyotp
try:
    import pyotp
    PYOTP_INSTALLED = True
    print("Đã tìm thấy pyotp")
except ImportError:
    PYOTP_INSTALLED = False
    print("Không tìm thấy pyotp, đang cố gắng cài đặt...")
    try:
        import sys
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyotp==2.9.0"])
        import pyotp
        PYOTP_INSTALLED = True
        print("Đã cài đặt và import pyotp thành công")
    except Exception as e:
        print(f"Không thể cài đặt pyotp: {e}")
        PYOTP_INSTALLED = False

# Kiểm tra two_factor
try:
    import two_factor
    TWO_FACTOR_INSTALLED = True
    print("Đã tìm thấy django-two-factor-auth")
except ImportError:
    TWO_FACTOR_INSTALLED = False
    print("Không tìm thấy two_factor, đang cố gắng cài đặt...")
    try:
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "django-two-factor-auth==1.16.0"])
        import two_factor
        TWO_FACTOR_INSTALLED = True
        print("Đã cài đặt và import django-two-factor-auth thành công")
    except Exception as e:
        print(f"Không thể cài đặt django-two-factor-auth: {e}")
        TWO_FACTOR_INSTALLED = False

# Import settings cơ bản
import sys
import importlib
original_path = sys.path.copy()

# Avoid circular import
module_name = 'hoshi.settings'
if module_name in sys.modules:
    del sys.modules[module_name]

# Tải setting từ django.conf
from django.conf import settings as django_settings

# Lấy các biến từ settings.py
try:
    settings_module = importlib.import_module('hoshi.settings')
    # Sao chép tất cả các biến từ settings.py
    for key in dir(settings_module):
        if key.isupper():
            locals()[key] = getattr(settings_module, key)
except Exception as e:
    print(f"Lỗi khi import settings: {e}")
    # Định nghĩa lại các biến cần thiết
    BASE_DIR = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fallback-secret-key')
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.sites',
    ]
    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]
    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]
    STATIC_URL = '/static/'
    LOGIN_URL = '/accounts/login/'
    SOCIALACCOUNT_PROVIDERS = {
        'google': {'APP': {'client_id': '', 'secret': '', 'key': ''}},
        'facebook': {'APP': {'client_id': '', 'secret': '', 'key': ''}},
    }

# Xử lý crispy_bootstrap5
if 'INSTALLED_APPS' in locals() and not CRISPY_BOOTSTRAP5_INSTALLED:
    if 'crispy_bootstrap5' in INSTALLED_APPS:
        INSTALLED_APPS.remove('crispy_bootstrap5')
        print("Đã loại bỏ crispy_bootstrap5 khỏi INSTALLED_APPS")
    
    # Cập nhật CRISPY_TEMPLATE_PACK nếu cần
    if 'CRISPY_TEMPLATE_PACK' in locals() and CRISPY_TEMPLATE_PACK == 'bootstrap5':
        CRISPY_TEMPLATE_PACK = 'bootstrap4'
        print("Đã thay đổi CRISPY_TEMPLATE_PACK thành bootstrap4")

# Xử lý two_factor và pyotp
if 'INSTALLED_APPS' in locals():
    # Nếu không có pyotp, vô hiệu hóa các tính năng xác thực hai yếu tố
    if not PYOTP_INSTALLED or not TWO_FACTOR_INSTALLED:
        # Loại bỏ tất cả các ứng dụng two_factor
        two_factor_apps = [
            'two_factor',
            'two_factor.plugins.yubikey',
            'django_otp',
            'django_otp.plugins.otp_totp',
            'django_otp.plugins.otp_static',
            'django_otp.plugins.otp_email'
        ]
        
        for app in two_factor_apps:
            if app in INSTALLED_APPS:
                INSTALLED_APPS.remove(app)
                print(f"Đã loại bỏ {app} khỏi INSTALLED_APPS")
        
        # Loại bỏ middleware liên quan
        two_factor_middleware = 'django_otp.middleware.OTPMiddleware'
        if 'MIDDLEWARE' in locals() and two_factor_middleware in MIDDLEWARE:
            MIDDLEWARE.remove(two_factor_middleware)
            print(f"Đã loại bỏ {two_factor_middleware} khỏi MIDDLEWARE")
        
        # Sửa đổi URLs nếu cần
        if 'LOGIN_URL' in locals() and 'two_factor' in LOGIN_URL:
            LOGIN_URL = '/accounts/login/'
            print("Đã thay đổi LOGIN_URL")
    else:
        print("Xác thực hai yếu tố đã sẵn sàng sử dụng")

# Khôi phục sys.path
sys.path = original_path

# Cấu hình riêng cho Render
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
if 'default' in DATABASES and 'ENGINE' in DATABASES['default'] and 'sqlite' in DATABASES['default']['ENGINE']:
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