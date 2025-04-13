"""
Script để phát hiện thư viện thiếu và tự động cài đặt
"""
import os
import sys
import importlib
import subprocess
import pkg_resources

# Danh sách các thư viện cần thiết
REQUIRED_PACKAGES = [
    'django',
    'python-decouple',
    'dj-database-url',
    'gunicorn',
    'whitenoise',
    'psycopg2-binary',
    'django-crispy-forms',
    'crispy-bootstrap5',
    'django-allauth',
    'django-filter',
    'django-bootstrap-datepicker-plus',
    'django-two-factor-auth',
    'pyotp',
    'python-dotenv',
    'channels',
    'channels-redis',
    'daphne',
    'pillow',
    'dateutils',
    'qrcode',
    'django-widget-tweaks',
    'django-imagekit',
    'django-ckeditor',
    'django-taggit',
    'djangorestframework',
    'django-cors-headers',
    'redis',
    'django-redis',
    'django-cleanup',
    'celery',
    'phonenumbers',
    'django-phonenumber-field',
    'python-magic',
    'django-countries',
    'django-notifications-hq',
    'django-otp',
]

# Danh sách các gói đã cài đặt
installed_packages = {pkg.key for pkg in pkg_resources.working_set}

print("===== KIỂM TRA THƯ VIỆN CÀI ĐẶT =====")
print(f"Tổng số thư viện cần kiểm tra: {len(REQUIRED_PACKAGES)}")

# Kiểm tra các thư viện
missing_packages = []
installed_with_version = []

for package in REQUIRED_PACKAGES:
    normalized_name = package.replace('-', '_')
    
    try:
        # Thử nhập thư viện
        module = importlib.import_module(normalized_name)
        try:
            version = pkg_resources.get_distribution(package).version
            print(f"✓ {package}=={version}")
            installed_with_version.append(f"{package}=={version}")
        except pkg_resources.DistributionNotFound:
            print(f"✓ {package} (không thể xác định phiên bản)")
            installed_with_version.append(f"{package}")
    except ImportError:
        print(f"✗ {package} (thiếu)")
        missing_packages.append(package)

# In danh sách các gói thiếu
if missing_packages:
    print("\n===== CÁC THƯ VIỆN THIẾU =====")
    for package in missing_packages:
        print(package)
    
    # Hỏi người dùng có muốn cài đặt không
    if input("\nBạn có muốn cài đặt các thư viện thiếu không? (y/n): ").lower() == 'y':
        for package in missing_packages:
            print(f"Đang cài đặt {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✓ Đã cài đặt {package}")
            except subprocess.CalledProcessError:
                print(f"✗ Không thể cài đặt {package}")

# Cập nhật file requirements_render.txt
if input("\nBạn có muốn cập nhật file requirements_render.txt với phiên bản đúng không? (y/n): ").lower() == 'y':
    try:
        # Tạo file requirements tạm thời
        with open('requirements_detected.txt', 'w') as f:
            f.write("# Được tạo tự động bởi detect_missing_libraries.py\n")
            f.write("# Core Django dependencies\n")
            for package in installed_with_version:
                if any(p in package for p in ['django', 'decouple', 'database-url', 'gunicorn', 'whitenoise', 'psycopg2']):
                    f.write(f"{package}\n")
            
            f.write("\n# Authentication và Social Login\n")
            for package in installed_with_version:
                if any(p in package for p in ['allauth', 'otp', 'two-factor', 'pyotp', 'qrcode']):
                    f.write(f"{package}\n")
            
            f.write("\n# UI và Forms\n")
            for package in installed_with_version:
                if any(p in package for p in ['crispy', 'bootstrap', 'widget', 'imagekit', 'ckeditor', 'taggit']):
                    f.write(f"{package}\n")
            
            f.write("\n# API và Real-time\n")
            for package in installed_with_version:
                if any(p in package for p in ['rest', 'cors', 'channels', 'daphne']):
                    f.write(f"{package}\n")
            
            f.write("\n# Database và Caching\n")
            for package in installed_with_version:
                if any(p in package for p in ['redis', 'cleanup']):
                    f.write(f"{package}\n")
            
            f.write("\n# Background processing\n")
            for package in installed_with_version:
                if 'celery' in package:
                    f.write(f"{package}\n")
            
            f.write("\n# Utilities\n")
            for package in installed_with_version:
                if any(p in package for p in ['filter', 'phone', 'magic', 'dotenv', 'countries', 'notifications']):
                    f.write(f"{package}\n")
            
            f.write("\n# Other libraries\n")
            for package in installed_with_version:
                if package not in open('requirements_detected.txt').read():
                    f.write(f"{package}\n")
        
        print(f"✓ Đã tạo file requirements_detected.txt")
        print("Bạn có thể so sánh với requirements_render.txt hiện tại và cập nhật thủ công.")
        
    except Exception as e:
        print(f"✗ Không thể cập nhật file requirements_render.txt: {e}")

print("\n===== HOÀN TẤT =====") 