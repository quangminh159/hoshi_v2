import os
import django
import sys
import inspect
import re

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from allauth.socialaccount.providers.base.mixins import get_provider
from allauth.socialaccount.models import SocialApp
import allauth.socialaccount.adapter

def patch_get_app_method():
    """Patch phương thức get_app trong SocialAccountAdapter để tránh lỗi MultipleObjectsReturned"""
    
    # Lấy mã nguồn của adapter
    adapter_code = inspect.getsource(allauth.socialaccount.adapter)
    
    # Tìm phương thức get_app trong adapter
    get_app_pattern = r"def get_app\(self, request, provider\):(.*?)(?=\n    def|\Z)"
    get_app_match = re.search(get_app_pattern, adapter_code, re.DOTALL)
    
    if not get_app_match:
        print("Không tìm thấy phương thức get_app trong adapter.py")
        return False
    
    # Mã get_app hiện tại
    current_get_app = get_app_match.group(0)
    print("\n=== PHƯƠNG THỨC HIỆN TẠI ===")
    print(current_get_app)
    
    # Phiên bản get_app mới để tránh lỗi MultipleObjectsReturned
    patched_get_app = """def get_app(self, request, provider):
        # NOTE: Đã được sửa để tránh lỗi MultipleObjectsReturned bằng cách lấy app mới nhất
        app = None
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
            return None"""
    
    print("\n=== PHƯƠNG THỨC ĐÃ SỬA ===")
    print(patched_get_app)
    
    # Tạo phiên bản patched của adapter.py
    patched_code = re.sub(get_app_pattern, patched_get_app, adapter_code, flags=re.DOTALL)
    
    # Định vị adapter.py trong thư mục site-packages
    adapter_path = os.path.abspath(inspect.getfile(allauth.socialaccount.adapter))
    print(f"\nVị trí file adapter.py: {adapter_path}")
    
    # Tạo bản sao lưu
    backup_path = adapter_path + ".backup"
    try:
        if not os.path.exists(backup_path):
            with open(adapter_path, "r") as f_in:
                with open(backup_path, "w") as f_out:
                    f_out.write(f_in.read())
            print(f"Đã tạo bản sao lưu tại: {backup_path}")
        else:
            print(f"Đã tồn tại bản sao lưu tại: {backup_path}")
    except Exception as e:
        print(f"Lỗi khi tạo bản sao lưu: {e}")
        return False
    
    # Ghi nội dung đã sửa vào adapter.py
    try:
        with open(adapter_path, "w") as f:
            f.write(patched_code)
        print(f"Đã sửa đổi thành công file: {adapter_path}")
        return True
    except Exception as e:
        print(f"Lỗi khi sửa đổi file: {e}")
        return False

if __name__ == "__main__":
    print("=== BẮT ĐẦU SỬA ĐỔI ADAPTER ===")
    try:
        if patch_get_app_method():
            print("\n=== HOÀN TẤT THÀNH CÔNG ===")
            print("Đã sửa phương thức get_app trong adapter.py. Khởi động lại server để áp dụng thay đổi.")
        else:
            print("\n=== HOÀN TẤT KHÔNG THÀNH CÔNG ===")
            print("Không thể sửa phương thức get_app. Vui lòng sửa thủ công.")
    except Exception as e:
        print(f"\n=== LỖI: {e} ===")
        print("Không thể hoàn tất quá trình sửa đổi adapter.") 