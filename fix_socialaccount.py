#!/usr/bin/env python
import os
import sys
import django
import time

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

try:
    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site
    from django.db import models
    print("Đã import các module cần thiết thành công")
except ImportError as e:
    print(f"Lỗi import module: {e}")
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
            
            # Xóa các app cũ
            for app in apps[1:]:
                print(f"Xóa app cũ (ID: {app.id}, Tên: {app.name})")
                app.delete()
            
            # Đảm bảo app mới được liên kết với tất cả các site
            if latest_app.sites.count() == 0:
                # Nếu không có site nào, thêm site mặc định (id=1)
                try:
                    default_site = Site.objects.get(id=1)
                    latest_app.sites.add(default_site)
                    print(f"Đã thêm site mặc định (ID: 1) cho app")
                except Site.DoesNotExist:
                    print("Site mặc định không tồn tại, đang tạo...")
                    # Tạo site mặc định nếu không tồn tại
                    default_site = Site.objects.create(domain="hoshi.onrender.com", name="Hoshi")
                    latest_app.sites.add(default_site)
                    print(f"Đã tạo và thêm site mặc định cho app")
        else:
            print(f"Không có SocialApp trùng lặp cho provider '{provider}'")
            
            # Kiểm tra xem app có được liên kết với site nào không
            app = apps.first()
            if app and app.sites.count() == 0:
                print(f"App '{app.name}' (ID: {app.id}) không liên kết với site nào, đang thêm site mặc định...")
                try:
                    default_site = Site.objects.get(id=1)
                    app.sites.add(default_site)
                    print(f"Đã thêm site mặc định (ID: 1) cho app")
                except Site.DoesNotExist:
                    print("Site mặc định không tồn tại, đang tạo...")
                    # Tạo site mặc định nếu không tồn tại
                    default_site = Site.objects.create(domain="hoshi.onrender.com", name="Hoshi")
                    app.sites.add(default_site)
                    print(f"Đã tạo và thêm site mặc định cho app")
    
    print("Quá trình kiểm tra và sửa chữa đã hoàn tất!")

# Tạo hoặc cập nhật Site
def ensure_site_exists():
    """Đảm bảo site mặc định tồn tại và được cấu hình đúng."""
    try:
        # Tìm site mặc định (id=1)
        site = Site.objects.get(id=1)
        # Cập nhật tên và domain nếu cần
        if site.domain != "hoshi.onrender.com" or site.name != "Hoshi":
            site.domain = "hoshi.onrender.com"
            site.name = "Hoshi"
            site.save()
            print(f"Đã cập nhật site mặc định (ID: {site.id}): domain={site.domain}, name={site.name}")
        else:
            print(f"Site mặc định đã tồn tại và được cấu hình đúng: domain={site.domain}, name={site.name}")
    except Site.DoesNotExist:
        # Tạo site mặc định nếu không tồn tại
        site = Site.objects.create(id=1, domain="hoshi.onrender.com", name="Hoshi")
        print(f"Đã tạo site mặc định (ID: {site.id}): domain={site.domain}, name={site.name}")
    
    # Kiểm tra và xóa các site dư thừa
    extra_sites = Site.objects.exclude(id=1)
    if extra_sites.exists():
        count = extra_sites.count()
        extra_sites.delete()
        print(f"Đã xóa {count} site dư thừa")

# Hiển thị thông tin về SocialApp
def display_socialapps():
    """Hiển thị thông tin về các SocialApp."""
    apps = SocialApp.objects.all()
    print(f"\nDanh sách SocialApp ({apps.count()}):")
    for app in apps:
        sites = app.sites.all()
        site_names = ", ".join([site.domain for site in sites])
        print(f"- ID: {app.id}, Provider: {app.provider}, Tên: {app.name}, Client ID: {app.client_id}")
        print(f"  Sites: {site_names}")

if __name__ == "__main__":
    print("=== Bắt đầu sửa chữa cấu hình SocialApp ===")
    
    # Đảm bảo site mặc định tồn tại
    ensure_site_exists()
    
    # Sửa lỗi SocialApp trùng lặp
    fix_duplicate_socialapps()
    
    # Hiển thị thông tin sau khi sửa chữa
    display_socialapps()
    
    print("\n=== Quá trình sửa chữa đã hoàn tất ===")