#!/usr/bin/env python
import os
import sys
import socket
import subprocess
from pathlib import Path

def get_local_ip():
    """Lấy địa chỉ IP local của máy"""
    try:
        # Tạo kết nối socket để lấy IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def update_settings():
    """Cập nhật file settings.py để cho phép kết nối từ máy khác"""
    # Tìm file .env
    env_file = Path(".env")
    if not env_file.exists():
        print("Không tìm thấy file .env")
        return False
    
    # Lấy IP local
    local_ip = get_local_ip()
    print(f"Địa chỉ IP local của bạn: {local_ip}")
    
    # Kiểm tra và cập nhật ALLOWED_HOSTS trong .env
    env_content = env_file.read_text()
    if "DJANGO_ALLOWED_HOSTS=" in env_content:
        lines = env_content.splitlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("DJANGO_ALLOWED_HOSTS="):
                hosts = line.split("=", 1)[1].strip()
                hosts_list = [h.strip() for h in hosts.split(",")]
                if local_ip not in hosts_list:
                    hosts_list.append(local_ip)
                    hosts_list = list(filter(None, hosts_list))  # Xóa các giá trị rỗng
                    lines[i] = f"DJANGO_ALLOWED_HOSTS={','.join(hosts_list)}"
                    updated = True
        
        if updated:
            env_file.write_text("\n".join(lines))
            print(f"Đã cập nhật DJANGO_ALLOWED_HOSTS trong file .env")
        else:
            print("DJANGO_ALLOWED_HOSTS đã có địa chỉ IP local")
    else:
        # Thêm DJANGO_ALLOWED_HOSTS vào cuối file
        with open(env_file, "a") as f:
            f.write(f"\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,{local_ip}\n")
        print(f"Đã thêm DJANGO_ALLOWED_HOSTS vào file .env")
    
    return True

def run_server():
    """Chạy server Django trên địa chỉ IP local"""
    local_ip = get_local_ip()
    port = 8000
    
    print(f"\n=== THÔNG TIN KẾT NỐI ===")
    print(f"Địa chỉ IP local: {local_ip}")
    print(f"Port: {port}")
    print(f"URL để truy cập từ máy khác: http://{local_ip}:{port}/")
    print("\nĐang khởi động server...")
    
    # Chạy lệnh runserver với IP và port
    cmd = f"python manage.py runserver {local_ip}:{port}"
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    print("=== CHẠY DJANGO TRÊN MẠNG LOCAL ===")
    if update_settings():
        run_server() 