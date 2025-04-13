#!/usr/bin/env python
import os
import sys
import django
import subprocess
import json
import time
import re
from pathlib import Path

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

def get_ngrok_url():
    """Lấy URL public của ngrok từ API local"""
    try:
        # Lấy thông tin ngrok từ API local
        response = subprocess.check_output(["curl", "-s", "http://127.0.0.1:4040/api/tunnels"])
        data = json.loads(response)
        
        # Tìm URL HTTPS
        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        
        # Nếu không có HTTPS, dùng URL đầu tiên
        if data["tunnels"]:
            return data["tunnels"][0]["public_url"]
        
        return None
    except Exception as e:
        print(f"Lỗi khi lấy URL ngrok: {str(e)}")
        return None

def update_django_settings(ngrok_url):
    """Cập nhật file settings.py với URL ngrok mới"""
    settings_path = Path('hoshi/settings.py')
    if not settings_path.exists():
        print("Không tìm thấy file settings.py!")
        return False
    
    content = settings_path.read_text(encoding='utf-8')
    
    # Kiểm tra nếu đã có CSRF_TRUSTED_ORIGINS
    if 'CSRF_TRUSTED_ORIGINS' in content:
        # Tìm mẫu chuỗi CSRF_TRUSTED_ORIGINS hiện tại
        pattern = r"CSRF_TRUSTED_ORIGINS\s*=\s*\[(.*?)\]"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # Phân tích danh sách URL hiện tại
            urls_text = match.group(1)
            urls = [url.strip().strip("'\"") for url in re.findall(r"'[^']*'|\"[^\"]*\"", urls_text)]
            
            # Xóa URL ngrok cũ (bắt đầu bằng https://xxx.ngrok)
            urls = [url for url in urls if not url.startswith('https://') or not '.ngrok' in url]
            
            # Thêm URL ngrok mới
            urls.append(ngrok_url)
            
            # Tạo danh sách URL mới
            new_urls = ",\n    ".join([f"'{url}'" for url in urls])
            new_csrf_config = f"CSRF_TRUSTED_ORIGINS = [\n    {new_urls}\n]"
            
            # Thay thế cấu hình cũ bằng cấu hình mới
            content = re.sub(pattern, new_csrf_config, content, flags=re.DOTALL)
            
            # Lưu lại file
            settings_path.write_text(content, encoding='utf-8')
            print(f"✓ Đã cập nhật CSRF_TRUSTED_ORIGINS trong file settings.py")
            return True
    
    print("× Không tìm thấy cấu hình CSRF_TRUSTED_ORIGINS trong settings.py!")
    return False

def update_env_file(ngrok_url):
    """Cập nhật file .env với URL ngrok mới"""
    env_path = Path('.env')
    if not env_path.exists():
        print("Không tìm thấy file .env!")
        return False
    
    content = env_path.read_text(encoding='utf-8')
    
    # Tìm và cập nhật CSRF_TRUSTED_ORIGINS
    if 'CSRF_TRUSTED_ORIGINS=' in content:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('CSRF_TRUSTED_ORIGINS='):
                parts = line.split('=', 1)
                if len(parts) > 1:
                    value = parts[1]
                    urls = [url.strip() for url in value.split(',')]
                    # Xóa URL ngrok cũ
                    urls = [url for url in urls if not 'ngrok' in url]
                    # Thêm URL ngrok mới
                    urls.append(ngrok_url)
                    # Ghi lại giá trị mới
                    lines[i] = f"CSRF_TRUSTED_ORIGINS={','.join(urls)}"
                    env_path.write_text('\n'.join(lines), encoding='utf-8')
                    print(f"✓ Đã cập nhật CSRF_TRUSTED_ORIGINS trong file .env")
                    return True
    
    print("× Không tìm thấy cấu hình CSRF_TRUSTED_ORIGINS trong .env!")
    return False

def print_instructions(ngrok_url):
    """In hướng dẫn cập nhật callback URL trong Google Cloud Console"""
    google_callback = f"{ngrok_url}/accounts/google/login/callback/"
    facebook_callback = f"{ngrok_url}/accounts/facebook/login/callback/"
    
    print("\n=== THÔNG TIN CẦN CẬP NHẬT ===")
    print(f"URL Ngrok hiện tại: {ngrok_url}")
    print("\n=== URL CALLBACK CHO GOOGLE OAUTH ===")
    print(f"URL: {google_callback}")
    print("Cập nhật URL này trong Google Cloud Console:")
    print("1. Truy cập https://console.cloud.google.com/apis/credentials")
    print("2. Chọn OAuth 2.0 Client ID")
    print("3. Thêm URL này vào Authorized redirect URIs")
    
    print("\n=== URL CALLBACK CHO FACEBOOK OAUTH ===")
    print(f"URL: {facebook_callback}")
    print("Cập nhật URL này trong Facebook Developers:")
    print("1. Truy cập https://developers.facebook.com/apps/")
    print("2. Chọn ứng dụng của bạn")
    print("3. Đi đến Facebook Login > Settings")
    print("4. Thêm URL này vào Valid OAuth Redirect URIs")

def main():
    """Hàm chính"""
    print("=== TỰ ĐỘNG CẬP NHẬT URL NGROK ===")
    
    # Kiểm tra xem ngrok có đang chạy không
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print("× Không tìm thấy ngrok đang chạy!")
        print("  Vui lòng khởi động ngrok trước với lệnh: ngrok http 8000")
        return
    
    print(f"✓ Đã tìm thấy URL ngrok: {ngrok_url}")
    
    # Cập nhật cấu hình
    update_django_settings(ngrok_url)
    update_env_file(ngrok_url)
    
    # In hướng dẫn
    print_instructions(ngrok_url)
    
    print("\n=== HOÀN TẤT ===")
    print("Đã tự động cập nhật URL ngrok trong cấu hình.")
    print("Vui lòng khởi động lại server Django để áp dụng thay đổi.")

if __name__ == "__main__":
    main() 