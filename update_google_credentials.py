#!/usr/bin/env python
import os
import sys
import django
import logging
from pathlib import Path

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def update_google_callback(ngrok_url=None):
    """Cập nhật thông tin SocialApp cho Google với URL ngrok mới"""
    print("=== CẬP NHẬT URL CALLBACK CHO GOOGLE OAUTH ===")
    
    if not ngrok_url:
        # Yêu cầu nhập URL ngrok
        print("Vui lòng nhập URL ngrok (https://xxxx.ngrok.io):")
        ngrok_url = input().strip()
    
    if not ngrok_url:
        print("× URL ngrok không được để trống!")
        return False
    
    # Chuẩn hóa URL
    if ngrok_url.endswith('/'):
        ngrok_url = ngrok_url[:-1]
    
    # Callback URLs
    callback_url = f"{ngrok_url}/accounts/google/login/callback/"
    print(f"URL callback mới: {callback_url}")
    
    # Cập nhật thông tin trong file .env
    env_path = Path('.env')
    if env_path.exists():
        # Đọc nội dung file
        content = env_path.read_text()
        
        # Tìm và cập nhật CSRF_TRUSTED_ORIGINS
        if 'CSRF_TRUSTED_ORIGINS=' in content:
            # Tìm dòng CSRF_TRUSTED_ORIGINS
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.startswith('CSRF_TRUSTED_ORIGINS='):
                    # Phân tách giá trị
                    parts = line.split('=', 1)
                    if len(parts) > 1:
                        value = parts[1]
                        # Tách các URL
                        urls = [url.strip() for url in value.split(',')]
                        # Thêm URL ngrok nếu chưa có
                        if ngrok_url not in urls:
                            urls.append(ngrok_url)
                        # Ghi lại giá trị mới
                        lines[i] = f"CSRF_TRUSTED_ORIGINS={','.join(urls)}"
                        # Lưu lại file
                        env_path.write_text('\n'.join(lines))
                        print(f"✓ Đã cập nhật CSRF_TRUSTED_ORIGINS trong file .env")
                        break
        else:
            # Nếu không có dòng CSRF_TRUSTED_ORIGINS, thêm mới
            with open(env_path, 'a') as f:
                f.write(f"\nCSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,{ngrok_url}\n")
            print(f"✓ Đã thêm CSRF_TRUSTED_ORIGINS vào file .env")
    
    # Cập nhật ALLOWED_HOSTS nếu cần
    # ...
    
    print("\n=== THÔNG TIN CẦN CẬP NHẬT TRONG GOOGLE CLOUD CONSOLE ===")
    print("1. Truy cập https://console.cloud.google.com/apis/credentials")
    print("2. Chọn OAuth 2.0 Client ID")
    print("3. Thêm URL redirect: " + callback_url)
    print("\nLưu ý: URL callback này chỉ có hiệu lực trong thời gian ngrok đang chạy.")
    print("Mỗi khi khởi động lại ngrok, bạn sẽ nhận được một URL mới và cần cập nhật lại.")
    
    return True

def update_facebook_callback(ngrok_url=None):
    """Cập nhật thông tin SocialApp cho Facebook với URL ngrok mới"""
    print("\n=== CẬP NHẬT URL CALLBACK CHO FACEBOOK OAUTH ===")
    
    if not ngrok_url:
        # Yêu cầu nhập URL ngrok
        print("Vui lòng nhập URL ngrok (https://xxxx.ngrok.io):")
        ngrok_url = input().strip()
    
    if not ngrok_url:
        print("× URL ngrok không được để trống!")
        return False
    
    # Chuẩn hóa URL
    if ngrok_url.endswith('/'):
        ngrok_url = ngrok_url[:-1]
    
    # Callback URLs
    callback_url = f"{ngrok_url}/accounts/facebook/login/callback/"
    print(f"URL callback mới: {callback_url}")
    
    print("\n=== THÔNG TIN CẦN CẬP NHẬT TRONG FACEBOOK DEVELOPERS ===")
    print("1. Truy cập https://developers.facebook.com/apps/")
    print("2. Chọn ứng dụng Facebook của bạn")
    print("3. Đi đến Products > Facebook Login > Settings")
    print("4. Thêm URL redirect: " + callback_url)
    print("\nLưu ý: URL callback này chỉ có hiệu lực trong thời gian ngrok đang chạy.")
    print("Mỗi khi khởi động lại ngrok, bạn sẽ nhận được một URL mới và cần cập nhật lại.")
    
    return True

if __name__ == "__main__":
    print("=== CẬP NHẬT URL CALLBACK CHO SOCIAL OAUTH ===")
    
    # Yêu cầu nhập URL ngrok
    print("Vui lòng nhập URL ngrok (https://xxxx.ngrok.io):")
    ngrok_url = input().strip()
    
    if not ngrok_url:
        print("× URL ngrok không được để trống!")
        sys.exit(1)
    
    # Cập nhật URL callback
    update_google_callback(ngrok_url)
    update_facebook_callback(ngrok_url)
    
    print("\n=== HOÀN TẤT ===")
    print("Đã cập nhật URL callback. Vui lòng cập nhật thông tin trong Google Cloud Console và Facebook Developers.")
    print("Sau đó khởi động lại server để áp dụng thay đổi.") 