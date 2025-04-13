#!/usr/bin/env python
import os
import sys
import subprocess
import time
import threading
import webbrowser
import json
import re
from pathlib import Path
from decouple import config

def check_ngrok_installed():
    """Kiểm tra xem ngrok đã được cài đặt chưa"""
    ngrok_path = Path("ngrok.exe")
    if not ngrok_path.exists():
        print("Không tìm thấy ngrok.exe trong thư mục hiện tại.")
        print("Vui lòng tải ngrok từ https://ngrok.com/download và giải nén vào thư mục này.")
        return False
    return True

def run_django_server():
    """Chạy server Django"""
    print("=== KHỞI ĐỘNG DJANGO SERVER ===")
    
    # Tìm script manage.py
    manage_py = Path("manage.py")
    if not manage_py.exists():
        print(f"Không tìm thấy file {manage_py} trong thư mục hiện tại.")
        return False
    
    # Chạy server Django
    django_process = subprocess.Popen(
        ["python", "manage.py", "runserver", "0.0.0.0:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Theo dõi output
    threading.Thread(target=stream_output, args=(django_process, "Django"), daemon=True).start()
    
    # Đợi server khởi động
    time.sleep(3)
    
    # Kiểm tra xem server đã chạy chưa
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('127.0.0.1', 8000))
        s.close()
        if result == 0:
            print("✓ Django server đã khởi động thành công!")
            return django_process
        else:
            print("× Django server không khởi động được.")
            django_process.terminate()
            return False
    except Exception as e:
        print(f"× Lỗi khi kiểm tra server: {str(e)}")
        django_process.terminate()
        return False

def run_ngrok():
    """Chạy ngrok để tạo tunnel"""
    print("\n=== KHỞI ĐỘNG NGROK ===")
    
    # Kiểm tra authtoken
    try:
        # Chạy ngrok
        ngrok_process = subprocess.Popen(
            ["ngrok", "http", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Theo dõi output
        threading.Thread(target=stream_output, args=(ngrok_process, "Ngrok"), daemon=True).start()
        
        # Chờ một lúc để ngrok khởi động
        time.sleep(3)
        
        # Lấy URL ngrok
        ngrok_url = get_ngrok_url()
        if ngrok_url:
            print(f"\n=== THÔNG TIN TRUY CẬP ===")
            print(f"URL Ngrok: {ngrok_url}")
            print(f"Đường dẫn callback: {ngrok_url}/accounts/google/login/callback/")
            print("\nCần thêm URL callback này vào Google Cloud Console:")
            print("1. Truy cập https://console.cloud.google.com/apis/credentials")
            print("2. Chọn OAuth 2.0 Client ID")
            print("3. Thêm URL redirect: " + f"{ngrok_url}/accounts/google/login/callback/")
            
            # Mở URL trong trình duyệt
            print("\nĐang mở URL trong trình duyệt...")
            webbrowser.open(ngrok_url)
            
            return ngrok_process, ngrok_url
        else:
            print("× Không thể lấy URL ngrok.")
            ngrok_process.terminate()
            return False, None
    except Exception as e:
        print(f"× Lỗi khi chạy ngrok: {str(e)}")
        return False, None

def get_ngrok_url():
    """Lấy URL public của ngrok"""
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
    except Exception:
        # Thử đọc từ output của ngrok
        try:
            output = subprocess.check_output(["ngrok", "status"], universal_newlines=True)
            match = re.search(r"URL:(https?://[\w\d-]+\.ngrok\.io)", output)
            if match:
                return match.group(1)
        except:
            pass
        
        return None

def stream_output(process, name):
    """Hiển thị output từ process"""
    try:
        for line in process.stdout:
            print(f"[{name}] {line.strip()}")
    except:
        pass

def main():
    """Hàm chính"""
    print("=== CHẠY DJANGO SERVER VỚI NGROK ===")
    
    # Kiểm tra ngrok
    if not check_ngrok_installed():
        return
    
    try:
        # Chạy Django server
        django_process = run_django_server()
        if not django_process:
            return
        
        # Chạy ngrok
        ngrok_process, ngrok_url = run_ngrok()
        if not ngrok_process:
            django_process.terminate()
            return
        
        print("\n=== SERVER ĐANG CHẠY ===")
        print("Nhấn Ctrl+C để dừng server và ngrok")
        
        # Chờ cho đến khi người dùng nhấn Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nĐang dừng server...")
        finally:
            # Dừng các process
            django_process.terminate()
            ngrok_process.terminate()
            
            print("Đã dừng server và ngrok.")
    
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main() 