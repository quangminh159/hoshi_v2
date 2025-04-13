#!/usr/bin/env python
import os
import sys
import django

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def check_social_apps():
    print("=== KIỂM TRA THÔNG TIN SOCIAL APPS ===")
    
    # Kiểm tra Facebook
    facebook_apps = SocialApp.objects.filter(provider='facebook')
    print("\nFacebook Apps:")
    if facebook_apps.exists():
        for app in facebook_apps:
            print(f"ID: {app.id}")
            print(f"Name: {app.name}")
            print(f"Client ID: {app.client_id}")
            print(f"Secret: {app.secret}")
            sites = app.sites.all()
            print(f"Sites: {', '.join([site.domain for site in sites])}")
    else:
        print("Không tìm thấy Facebook App nào.")
    
    # Kiểm tra Google
    google_apps = SocialApp.objects.filter(provider='google')
    print("\nGoogle Apps:")
    if google_apps.exists():
        for app in google_apps:
            print(f"ID: {app.id}")
            print(f"Name: {app.name}")
            print(f"Client ID: {app.client_id}")
            print(f"Secret: {app.secret}")
            sites = app.sites.all()
            print(f"Sites: {', '.join([site.domain for site in sites])}")
    else:
        print("Không tìm thấy Google App nào.")

if __name__ == "__main__":
    check_social_apps() 