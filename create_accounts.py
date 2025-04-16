#!/usr/bin/env python
"""
Script tự động tạo tài khoản người dùng trong Django
Chạy lệnh: python create_accounts.py
"""

import os
import sys
import django
import datetime
import random
import string
from faker import Faker

# Thiết lập môi trường Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hoshi.settings")
django.setup()

# Import models sau khi đã thiết lập môi trường Django
from django.contrib.auth import get_user_model
from chat.models import UserSetting
from accounts.models import User

# Tạo đối tượng Faker để sinh dữ liệu giả
fake = Faker('vi_VN')

# File lưu thông tin tài khoản
ACCOUNTS_FILE = "created_accounts.txt"

def save_account_to_file(account_info):
    """Lưu thông tin tài khoản vào file"""
    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"Email: {account_info['email']}\n")
        f.write(f"Tên người dùng: {account_info['username']}\n")
        f.write(f"Ngày sinh: {account_info['birth_date']}\n")
        f.write(f"Giới tính: {account_info['gender']}\n")
        f.write(f"Mật khẩu: {account_info['password']}\n")
        f.write("-" * 40 + "\n")

def generate_password(length=10):
    """Tạo mật khẩu ngẫu nhiên với độ dài chỉ định"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*()_+'
    return ''.join(random.choice(chars) for _ in range(length))

def generate_username():
    """Tạo tên người dùng ngẫu nhiên"""
    first_name = fake.first_name().lower()
    last_name = fake.last_name().lower()
    username = f"{first_name}_{last_name}_{random.randint(1, 999)}"
    return username

def generate_birth_date():
    """Tạo ngày sinh ngẫu nhiên trong khoảng từ 18-60 tuổi"""
    return fake.date_of_birth(minimum_age=18, maximum_age=60)

def generate_gender():
    """Tạo giới tính ngẫu nhiên (M: Nam, F: Nữ, O: Khác)"""
    return random.choice(['M', 'F', 'O'])

def create_user(email=None, username=None, birth_date=None, gender=None, password=None):
    """Tạo người dùng mới với các thông tin cho trước hoặc ngẫu nhiên"""
    if not email:
        email = fake.email()
    if not username:
        username = generate_username()
    if not birth_date:
        birth_date = generate_birth_date()
    if not gender:
        gender = generate_gender()
    if not password:
        password = generate_password()
    
    try:
        # Kiểm tra xem email đã tồn tại chưa
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            print(f"Người dùng với email {email} đã tồn tại!")
            return None
        
        # Tạo người dùng mới
        user = User.objects.create_user(
            username=email,  # Django allauth sử dụng email làm username
            email=email,
            password=password,
            birth_date=birth_date,
            gender=gender
        )
        
        # Tạo UserSetting cho người dùng
        UserSetting.objects.create(user=user, username=username)
        
        # Chuẩn bị thông tin tài khoản để in ra và lưu vào file
        account_info = {
            'email': email,
            'username': username,
            'birth_date': birth_date,
            'gender': gender,
            'password': password
        }
        
        # In thông tin tài khoản ra console
        print(f"Đã tạo người dùng thành công:")
        print(f"Email: {email}")
        print(f"Tên người dùng: {username}")
        print(f"Ngày sinh: {birth_date}")
        print(f"Giới tính: {gender}")
        print(f"Mật khẩu: {password}")
        print("-" * 40)
        
        # Lưu thông tin tài khoản vào file
        save_account_to_file(account_info)
        
        return user
    except Exception as e:
        print(f"Lỗi khi tạo người dùng: {e}")
        return None

def create_multiple_users(count=10):
    """Tạo nhiều người dùng với số lượng chỉ định"""
    created_users = []
    
    # Tạo header cho file
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"DANH SÁCH TÀI KHOẢN ĐƯỢC TẠO ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
        f.write("=" * 60 + "\n\n")
    
    for _ in range(count):
        user = create_user()
        if user:
            created_users.append(user)
    
    print(f"Đã tạo {len(created_users)}/{count} người dùng thành công.")
    print(f"Danh sách tài khoản đã được lưu vào file {ACCOUNTS_FILE}")

def create_specific_user(email, username, birth_date, gender, password):
    """Tạo một người dùng cụ thể với thông tin cho trước"""
    if isinstance(birth_date, str):
        # Chuyển đổi chuỗi ngày tháng (YYYY-MM-DD) thành đối tượng date
        try:
            birth_date = datetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
        except ValueError:
            print("Định dạng ngày sinh không hợp lệ. Sử dụng định dạng YYYY-MM-DD.")
            return None
    
    # Tạo header cho file nếu không tồn tại
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"DANH SÁCH TÀI KHOẢN ĐƯỢC TẠO ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
            f.write("=" * 60 + "\n\n")
    
    user = create_user(email, username, birth_date, gender, password)
    if user:
        print(f"Thông tin tài khoản đã được lưu vào file {ACCOUNTS_FILE}")
    return user

if __name__ == "__main__":
    print("=" * 60)
    print("CÔNG CỤ TẠO TÀI KHOẢN TỰ ĐỘNG")
    print("=" * 60)
    
    choice = input("Bạn muốn:\n1. Tạo nhiều tài khoản ngẫu nhiên\n2. Tạo một tài khoản cụ thể\nChọn (1/2): ")
    
    if choice == "1":
        try:
            count = int(input("Nhập số lượng tài khoản cần tạo: "))
            create_multiple_users(count)
        except ValueError:
            print("Số lượng không hợp lệ. Đang tạo 10 tài khoản mặc định...")
            create_multiple_users(10)
    elif choice == "2":
        email = input("Email: ")
        username = input("Tên người dùng: ")
        birth_date = input("Ngày sinh (YYYY-MM-DD): ")
        gender = input("Giới tính (M: Nam, F: Nữ, O: Khác): ").upper()
        password = input("Mật khẩu (để trống để tự động tạo): ")
        
        if not email:
            print("Email là bắt buộc!")
        else:
            if not password:
                password = generate_password()
            if gender not in ['M', 'F', 'O']:
                print("Giới tính không hợp lệ. Sử dụng giá trị ngẫu nhiên.")
                gender = generate_gender()
            
            create_specific_user(email, username, birth_date, gender, password)
    else:
        print("Lựa chọn không hợp lệ!") 