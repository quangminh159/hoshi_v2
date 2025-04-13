"""
Script để tạo các file monkey patch cho accounts/views.py để tránh lỗi thiếu thư viện
"""
import os
import sys

def create_accounts_views_patch():
    # Tạo thư mục nếu không tồn tại
    os.makedirs('accounts_patch', exist_ok=True)
    
    # Tạo file __init__.py trong thư mục patch
    with open('accounts_patch/__init__.py', 'w') as f:
        f.write('# Patch module for accounts app\n')
    
    # Tạo file views.py cho patch
    with open('accounts_patch/views.py', 'w') as f:
        f.write("""
# Monkey patch cho accounts/views.py
# File này chứa các stub và wrapper cho các imports có thể gây lỗi

# Tạo các stub class và function cho pyotp
class PyOTPStub:
    class TOTP:
        def __init__(self, *args, **kwargs):
            self.secret = 'dummy'
            
        def now(self):
            return '000000'
            
        def verify(self, token, valid_window=0):
            return False
            
    @staticmethod
    def random_base32():
        return 'FAKESECRETKEY'

# Kiểm tra xem thư viện pyotp có tồn tại không
try:
    import pyotp
    print("✓ Đã import pyotp thành công")
except ImportError:
    print("! Không tìm thấy pyotp, sử dụng stub class")
    # Sử dụng stub class nếu không có pyotp
    pyotp = PyOTPStub

# Các imports khác cần thiết cho accounts/views.py
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Exports
__all__ = [
    'pyotp',
    'settings',
    'messages',
    'get_user_model', 'login', 'authenticate',
    'login_required',
    'default_token_generator',
    'get_current_site',
    'EmailMessage',
    'HttpResponse', 'JsonResponse',
    'render', 'redirect', 'get_object_or_404',
    'render_to_string',
    'force_bytes', 'force_str',
    'urlsafe_base64_encode', 'urlsafe_base64_decode',
    'csrf_exempt',
    'require_POST',
]
""")

    # Tạo một patch loader script
    with open('apply_accounts_patch.py', 'w') as f:
        f.write("""
import os
import sys
import importlib.util
import shutil
from pathlib import Path

def apply_patch():
    print("===== ĐANG ÁP DỤNG PATCH CHO ACCOUNTS APP =====")
    
    # Kiểm tra xem module pyotp có tồn tại không
    try:
        import pyotp
        print("✓ Module pyotp đã được cài đặt, không cần patch")
        return True
    except ImportError:
        print("! Module pyotp không tìm thấy, đang áp dụng patch...")
    
    # Kiểm tra xem thư mục accounts có tồn tại không
    accounts_dir = Path('accounts')
    if not accounts_dir.exists() or not accounts_dir.is_dir():
        print("✗ Không tìm thấy thư mục accounts")
        return False
    
    # Kiểm tra xem file views.py có tồn tại không
    views_file = accounts_dir / 'views.py'
    if not views_file.exists() or not views_file.is_file():
        print("✗ Không tìm thấy file accounts/views.py")
        return False
    
    # Tạo backup
    backup_file = views_file.with_suffix('.py.bak')
    if not backup_file.exists():
        shutil.copy(views_file, backup_file)
        print(f"✓ Đã tạo backup tại {backup_file}")
    
    # Đọc nội dung file views.py
    with open(views_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kiểm tra xem file đã được patch chưa
    if '# PATCHED FOR RENDER DEPLOYMENT' in content:
        print("✓ File đã được patch trước đó")
        return True
    
    # Tìm dòng import pyotp
    import_line = None
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'import pyotp' in line:
            import_line = i
            break
    
    if import_line is None:
        print("✗ Không tìm thấy dòng 'import pyotp' trong file")
        return False
    
    # Thay thế dòng import bằng code patch
    new_lines = lines[:import_line]
    new_lines.append('# PATCHED FOR RENDER DEPLOYMENT')
    new_lines.append('try:')
    new_lines.append('    import pyotp')
    new_lines.append('    print("Successfully imported pyotp")')
    new_lines.append('except ImportError:')
    new_lines.append('    print("pyotp not found, using stub")')
    new_lines.append('    # Stub class for pyotp')
    new_lines.append('    class PyOTPStub:')
    new_lines.append('        class TOTP:')
    new_lines.append('            def __init__(self, *args, **kwargs):')
    new_lines.append('                self.secret = "dummy"')
    new_lines.append('            def now(self):')
    new_lines.append('                return "000000"')
    new_lines.append('            def verify(self, token, valid_window=0):')
    new_lines.append('                return False')
    new_lines.append('        @staticmethod')
    new_lines.append('        def random_base32():')
    new_lines.append('            return "FAKESECRETKEY"')
    new_lines.append('    pyotp = PyOTPStub')
    new_lines.extend(lines[import_line+1:])
    
    # Ghi lại vào file
    with open(views_file, 'w', encoding='utf-8') as f:
        f.write('\\n'.join(new_lines))
    
    print(f"✓ Đã patch file {views_file}")
    return True

def restore_from_backup():
    views_file = Path('accounts/views.py')
    backup_file = views_file.with_suffix('.py.bak')
    
    if backup_file.exists():
        shutil.copy(backup_file, views_file)
        print(f"✓ Đã khôi phục từ backup {backup_file}")
        return True
    else:
        print(f"✗ Không tìm thấy file backup {backup_file}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        restore_from_backup()
    else:
        apply_patch()
""")

    print("✓ Đã tạo script patch cho accounts/views.py")
    print("Bạn có thể chạy file apply_accounts_patch.py để áp dụng patch")
    print("Hoặc khôi phục từ backup với lệnh: python apply_accounts_patch.py --restore")

def create_accounts_urls_patch():
    # Tạo file urls.py cho patch
    with open('accounts_patch/urls.py', 'w') as f:
        f.write("""
# Monkey patch cho accounts/urls.py để tránh lỗi two_factor

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

# Kiểm tra xem two_factor có tồn tại không
try:
    from two_factor.urls import urlpatterns as tf_urls
    has_two_factor = True
    print("✓ Đã import two_factor URLs thành công")
except ImportError:
    has_two_factor = False
    print("! Không tìm thấy two_factor, sử dụng URLs thay thế")

# Xuất các elements cần thiết
__all__ = ['path', 'include', 'auth_views', 'views']

# Hàm hỗ trợ để tạo urls pattern thay thế cho two-factor
def get_substitute_urlpatterns():
    # Tạo một urlpatterns không có two-factor
    return [
        path('', views.user_home, name='profile'),
        path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
        path('logout/', auth_views.LogoutView.as_view(template_name='accounts/logout.html'), name='logout'),
        path('register/', views.register, name='register'),
        # Thêm các URL khác nếu cần
    ]

# Sử dụng như tf_urls khi import
if not has_two_factor:
    tf_urls = get_substitute_urlpatterns()
""")

    # Thêm vào apply_accounts_patch.py
    with open('apply_accounts_patch.py', 'a') as f:
        f.write("""

def patch_accounts_urls():
    print("===== ĐANG ÁP DỤNG PATCH CHO ACCOUNTS/URLS.PY =====")
    
    # Kiểm tra xem module two_factor có tồn tại không
    try:
        from two_factor.urls import urlpatterns as tf_urls
        print("✓ Module two_factor đã được cài đặt, không cần patch")
        return True
    except ImportError:
        print("! Module two_factor không tìm thấy, đang áp dụng patch...")
    
    # Kiểm tra xem thư mục accounts có tồn tại không
    accounts_dir = Path('accounts')
    if not accounts_dir.exists() or not accounts_dir.is_dir():
        print("✗ Không tìm thấy thư mục accounts")
        return False
    
    # Kiểm tra xem file urls.py có tồn tại không
    urls_file = accounts_dir / 'urls.py'
    if not urls_file.exists() or not urls_file.is_file():
        print("✗ Không tìm thấy file accounts/urls.py")
        return False
    
    # Tạo backup
    backup_file = urls_file.with_suffix('.py.bak')
    if not backup_file.exists():
        shutil.copy(urls_file, backup_file)
        print(f"✓ Đã tạo backup tại {backup_file}")
    
    # Đọc nội dung file urls.py
    with open(urls_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kiểm tra xem file đã được patch chưa
    if '# PATCHED FOR RENDER DEPLOYMENT' in content:
        print("✓ File urls.py đã được patch trước đó")
        return True
    
    # Tìm dòng import two_factor
    import_line = None
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'from two_factor.urls import' in line:
            import_line = i
            break
    
    if import_line is None:
        print("✗ Không tìm thấy dòng 'from two_factor.urls import' trong file")
        return False
    
    # Thay thế dòng import bằng code patch
    new_lines = lines[:import_line]
    new_lines.append('# PATCHED FOR RENDER DEPLOYMENT')
    new_lines.append('try:')
    new_lines.append('    from two_factor.urls import urlpatterns as tf_urls')
    new_lines.append('    print("Successfully imported two_factor URLs")')
    new_lines.append('except ImportError:')
    new_lines.append('    print("two_factor not found, using substitute URLs")')
    new_lines.append('    # Tạo URLs thay thế')
    new_lines.append('    tf_urls = [')
    new_lines.append('        path("", views.user_home, name="profile"),')
    new_lines.append('        path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),')
    new_lines.append('        path("logout/", auth_views.LogoutView.as_view(template_name="accounts/logout.html"), name="logout"),')
    new_lines.append('        path("register/", views.register, name="register"),')
    new_lines.append('    ]')
    new_lines.extend(lines[import_line+1:])
    
    # Ghi lại vào file
    with open(urls_file, 'w', encoding='utf-8') as f:
        f.write('\\n'.join(new_lines))
    
    print(f"✓ Đã patch file {urls_file}")
    return True

def restore_urls_from_backup():
    urls_file = Path('accounts/urls.py')
    backup_file = urls_file.with_suffix('.py.bak')
    
    if backup_file.exists():
        shutil.copy(backup_file, urls_file)
        print(f"✓ Đã khôi phục urls.py từ backup {backup_file}")
        return True
    else:
        print(f"✗ Không tìm thấy file backup {backup_file}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--restore':
            restore_from_backup()
            restore_urls_from_backup()
        elif sys.argv[1] == '--views':
            apply_patch()
        elif sys.argv[1] == '--urls':
            patch_accounts_urls()
    else:
        apply_patch()
        patch_accounts_urls()
""")

    print("✓ Đã thêm patch cho accounts/urls.py")

if __name__ == "__main__":
    create_accounts_views_patch()
    create_accounts_urls_patch()
    print("\n===== HOÀN TẤT =====")
    print("Chạy lệnh sau để áp dụng patches:")
    print("python apply_accounts_patch.py")
    print("Nếu muốn khôi phục:")
    print("python apply_accounts_patch.py --restore") 