#!/usr/bin/env python
import os
import sys
import django
from django.db import models

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

try:
    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site
except ImportError:
    print("Không thể import allauth hoặc django.contrib.sites, đảm bảo đã cài đặt.")
    sys.exit(1)

def fix_duplicate_socialapps():
    """Sửa lỗi nhiều SocialApp cho cùng một provider."""
    print("Đang kiểm tra các SocialApp trùng lặp...")
    
    # Lấy danh sách providers
    providers = SocialApp.objects.values_list('provider', flat=True).distinct()
    
    for provider in providers:
        apps = SocialApp.objects.filter(provider=provider).order_by('-id')
        
        # Nếu có nhiều hơn 1 app cho cùng provider
        if apps.count() > 1:
            print(f"Tìm thấy {apps.count()} SocialApp cho provider '{provider}'")
            
            # Giữ lại app mới nhất, xóa các app cũ
            latest_app = apps.first()
            print(f"Giữ lại app mới nhất (ID: {latest_app.id}, Tên: {latest_app.name})")
            
            # Lấy danh sách site của app
            sites = latest_app.sites.all()
            site_ids = [site.id for site in sites]
            
            # Xóa các app cũ
            for app in apps[1:]:
                print(f"Xóa app cũ (ID: {app.id}, Tên: {app.name})")
                app.delete()
            
            # Đảm bảo app mới được liên kết với tất cả các site
            if not site_ids:
                # Nếu không có site nào, thêm site mặc định (id=1)
                try:
                    default_site = Site.objects.get(id=1)
                    latest_app.sites.add(default_site)
                    print(f"Đã thêm site mặc định (ID: 1) cho app")
                except Site.DoesNotExist:
                    print("Site mặc định không tồn tại, đang tạo...")
                    # Tạo site mặc định nếu không tồn tại
                    default_site = Site.objects.create(domain="example.com", name="Default Site")
                    latest_app.sites.add(default_site)
                    print(f"Đã tạo và thêm site mặc định cho app")
        else:
            print(f"Không có SocialApp trùng lặp cho provider '{provider}'")
            
            # Kiểm tra xem app có được liên kết với site nào không
            app = apps.first()
            if app:
                sites = app.sites.all()
                if not sites.exists():
                    print(f"App '{app.name}' (ID: {app.id}) không liên kết với site nào, đang thêm site mặc định...")
                    try:
                        default_site = Site.objects.get(id=1)
                        app.sites.add(default_site)
                        print(f"Đã thêm site mặc định (ID: 1) cho app")
                    except Site.DoesNotExist:
                        print("Site mặc định không tồn tại, đang tạo...")
                        # Tạo site mặc định nếu không tồn tại
                        default_site = Site.objects.create(domain="example.com", name="Default Site")
                        app.sites.add(default_site)
                        print(f"Đã tạo và thêm site mặc định cho app")
    
    print("Quá trình kiểm tra và sửa chữa đã hoàn tất!")

# Patch lớp SocialAccountAdapter để xử lý trường hợp nhiều app
def patch_socialaccount_adapter():
    from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
    
    # Lưu trữ phương thức get_app gốc
    original_get_app = DefaultSocialAccountAdapter.get_app
    
    def patched_get_app(self, request, provider):
        try:
            return original_get_app(self, request, provider)
        except models.MultipleObjectsReturned:
            print(f"Phát hiện lỗi MultipleObjectsReturned cho provider {provider}, đang sửa chữa...")
            fix_duplicate_socialapps()
            
            # Lấy app mới nhất sau khi đã sửa chữa
            from allauth.socialaccount.models import SocialApp
            return SocialApp.objects.filter(provider=provider).order_by('-id').first()
    
    # Áp dụng patch
    DefaultSocialAccountAdapter.get_app = patched_get_app
    print("Đã patch DefaultSocialAccountAdapter.get_app để xử lý lỗi MultipleObjectsReturned")

if __name__ == "__main__":
    print("Bắt đầu sửa chữa SocialApp trùng lặp...")
    fix_duplicate_socialapps()
    patch_socialaccount_adapter()
    print("Đã hoàn thành việc sửa chữa!")