#!/usr/bin/env python
import os
import sys
import django

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def check_social_apps():
    """Kiểm tra thông tin các Social Apps đã đăng ký trong cơ sở dữ liệu"""
    
    print("=== KIỂM TRA THÔNG TIN SOCIAL APPS ===\n")
    
    # Kiểm tra Google Apps
    google_apps = SocialApp.objects.filter(provider='google')
    print("Google Apps:")
    if google_apps.exists():
        for app in google_apps:
            print(f"- ID: {app.id}")
            print(f"  Tên: {app.name}")
            print(f"  Client ID: {app.client_id}")
            print(f"  Secret: {app.secret}")
            print(f"  Sites: {', '.join(site.domain for site in app.sites.all())}")
    else:
        print("Không tìm thấy Google App nào.")
    
    print()
    
    # Kiểm tra Facebook Apps
    fb_apps = SocialApp.objects.filter(provider='facebook')
    print("Facebook Apps:")
    if fb_apps.exists():
        for app in fb_apps:
            print(f"- ID: {app.id}")
            print(f"  Tên: {app.name}")
            print(f"  Client ID: {app.client_id}")
            print(f"  Secret: {app.secret}")
            print(f"  Sites: {', '.join(site.domain for site in app.sites.all())}")
    else:
        print("Không tìm thấy Facebook App nào.")
    
    print()
    
    # Kiểm tra các sites đang có
    sites = Site.objects.all()
    print(f"Sites: {', '.join(site.domain for site in sites)}")

if __name__ == "__main__":
    check_social_apps() 