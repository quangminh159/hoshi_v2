import os
import django
import sys
import traceback

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from allauth.socialaccount.models import SocialApp

def fix_adapter_manually():
    """Tạo ra một lớp adapter tùy chỉnh để khắc phục lỗi MultipleObjectsReturned"""
    
    # Đường dẫn đến thư mục của dự án
    project_dir = os.path.abspath('.')
    
    # Tạo thư mục 'patches' nếu chưa tồn tại
    patches_dir = os.path.join(project_dir, 'patches')
    if not os.path.exists(patches_dir):
        os.makedirs(patches_dir)
    
    # Tạo tệp adapter_patch.py
    adapter_patch_path = os.path.join(patches_dir, 'adapter_patch.py')
    
    adapter_patch_content = """\"\"\"
Patched version of the SocialAccountAdapter to avoid MultipleObjectsReturned error.
This should be imported in your views.py file.
\"\"\"

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp

class FixedSocialAccountAdapter(DefaultSocialAccountAdapter):
    \"\"\"
    A version of SocialAccountAdapter that avoids MultipleObjectsReturned error
    by getting the first app when multiple apps exist for the same provider.
    \"\"\"
    
    def get_app(self, request, provider):
        \"\"\"
        Get the first matching SocialApp for the given provider.
        This avoids the MultipleObjectsReturned error.
        \"\"\"
        try:
            app = SocialApp.objects.filter(provider=provider.id).order_by('-id').first()
            if app is None:
                if request is None:
                    raise RuntimeError("Make sure you've configured a SocialApp in the database for provider %s" % provider.id)
                raise SocialApp.DoesNotExist()
            return app
        except SocialApp.DoesNotExist:
            if request is None:
                raise RuntimeError("Make sure you've configured a SocialApp in the database for provider %s" % provider.id)
            return None
"""

    # Ghi nội dung vào tệp
    with open(adapter_patch_path, 'w') as f:
        f.write(adapter_patch_content)
    
    print(f"✓ Đã tạo tệp adapter_patch.py tại: {adapter_patch_path}")
    
    # Tạo tệp __init__.py trong thư mục patches để có thể import
    init_path = os.path.join(patches_dir, '__init__.py')
    with open(init_path, 'w') as f:
        f.write('# Patches package for fixing django-allauth issues')
    
    print(f"✓ Đã tạo tệp __init__.py tại: {init_path}")
    
    try:
        # Tạo tệp cấu hình để sử dụng adapter tùy chỉnh
        settings_path = os.path.join(project_dir, 'config', 'settings.py')
        
        # Đọc nội dung settings.py hiện tại
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        
        # Kiểm tra xem đã cấu hình adapter tùy chỉnh chưa
        if 'SOCIALACCOUNT_ADAPTER' not in settings_content:
            # Thêm vào cuối file
            settings_content += '\n\n# Custom adapter to fix MultipleObjectsReturned error\nSOCIALACCOUNT_ADAPTER = "patches.adapter_patch.FixedSocialAccountAdapter"\n'
            
            # Ghi nội dung mới vào file settings.py
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(settings_content)
            
            print(f"✓ Đã thêm cấu hình SOCIALACCOUNT_ADAPTER vào: {settings_path}")
        else:
            print("✓ Cấu hình SOCIALACCOUNT_ADAPTER đã tồn tại trong settings.py")
    except Exception as e:
        print(f"✗ Lỗi khi xử lý file settings.py: {e}")
        print(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    print("=== BẮT ĐẦU KHẮC PHỤC LỖI ADAPTER ===")
    try:
        if fix_adapter_manually():
            print("\n=== HOÀN TẤT THÀNH CÔNG ===")
            print("Đã tạo adapter tùy chỉnh để khắc phục lỗi MultipleObjectsReturned.")
            print("Khởi động lại server để áp dụng thay đổi.")
        else:
            print("\n=== HOÀN TẤT KHÔNG THÀNH CÔNG ===")
            print("Không thể tạo adapter tùy chỉnh.")
    except Exception as e:
        print(f"\n=== LỖI: {e} ===")
        print(traceback.format_exc())
        print("Không thể hoàn tất quá trình khắc phục lỗi adapter.") 