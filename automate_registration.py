#!/usr/bin/env python
"""
Script tự động tạo tài khoản thông qua giao diện web sử dụng Selenium
Cài đặt trước khi sử dụng: pip install selenium faker
"""

import random
import time
from datetime import datetime, timedelta
from faker import Faker
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Khởi tạo Faker
fake = Faker('vi_VN')

# Cấu hình Chrome driver
chrome_options = Options()
# Xóa comment dưới đây nếu muốn chạy ẩn danh
# chrome_options.add_argument("--incognito")
# Xóa comment dưới đây nếu muốn chạy ẩn
# chrome_options.add_argument("--headless")

def generate_profile():
    """Tạo thông tin người dùng ngẫu nhiên"""
    # Tạo tên người dùng
    first_name = fake.first_name().lower()
    last_name = fake.last_name().lower()
    username = f"{first_name}_{last_name}_{random.randint(1, 999)}"
    
    # Tạo email
    email = fake.email()
    
    # Tạo ngày sinh (18-60 tuổi)
    today = datetime.now()
    min_date = today - timedelta(days=365 * 60)  # 60 tuổi
    max_date = today - timedelta(days=365 * 18)  # 18 tuổi
    birth_date = fake.date_between(min_date, max_date)
    
    # Tạo giới tính
    gender = random.choice(['M', 'F', 'O'])
    
    # Tạo mật khẩu
    password = fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
    
    return {
        'username': username,
        'email': email,
        'birth_date': birth_date.strftime('%Y-%m-%d'),
        'gender': gender,
        'password': password
    }

def register_account(url, profile):
    """Đăng ký tài khoản thông qua giao diện web"""
    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Mở trang đăng ký
        driver.get(url)
        print(f"Đang mở trang đăng ký: {url}")
        time.sleep(2)
        
        # Điền thông tin vào form
        print("Đang điền thông tin đăng ký...")
        
        # Điền username
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id_username"))
        )
        username_field.send_keys(profile['username'])
        
        # Điền email
        email_field = driver.find_element(By.ID, "id_email")
        email_field.send_keys(profile['email'])
        
        # Điền ngày sinh
        birth_date_field = driver.find_element(By.ID, "id_birth_date")
        birth_date_field.send_keys(profile['birth_date'])
        
        # Chọn giới tính
        gender_select = driver.find_element(By.ID, "id_gender")
        if profile['gender'] == 'M':
            gender_select.find_element(By.XPATH, "//option[@value='M']").click()
        elif profile['gender'] == 'F':
            gender_select.find_element(By.XPATH, "//option[@value='F']").click()
        else:
            gender_select.find_element(By.XPATH, "//option[@value='O']").click()
        
        # Điền mật khẩu
        password1_field = driver.find_element(By.ID, "id_password1")
        password1_field.send_keys(profile['password'])
        
        # Xác nhận mật khẩu
        password2_field = driver.find_element(By.ID, "id_password2")
        password2_field.send_keys(profile['password'])
        
        # Chọn checkbox đồng ý điều khoản
        terms_checkbox = driver.find_element(By.ID, "terms")
        terms_checkbox.click()
        
        # Submit form
        print("Đang gửi form đăng ký...")
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()
        
        # Chờ một chút để trang xử lý
        time.sleep(5)
        
        # Kiểm tra kết quả
        if "login" in driver.current_url or "dashboard" in driver.current_url or "home" in driver.current_url:
            print("Đăng ký thành công!")
            print(f"Tên người dùng: {profile['username']}")
            print(f"Email: {profile['email']}")
            print(f"Ngày sinh: {profile['birth_date']}")
            print(f"Giới tính: {profile['gender']}")
            print(f"Mật khẩu: {profile['password']}")
        else:
            print("Đăng ký có thể không thành công. Kiểm tra lại trang hiện tại.")
            print(f"URL hiện tại: {driver.current_url}")
            error_messages = driver.find_elements(By.CLASS_NAME, "invalid-feedback")
            if error_messages:
                print("Lỗi được phát hiện:")
                for error in error_messages:
                    print(f"- {error.text}")
    
    except Exception as e:
        print(f"Lỗi trong quá trình đăng ký: {e}")
    
    finally:
        # Chờ một chút trước khi đóng browser
        time.sleep(3)
        driver.quit()

def main():
    print("=" * 60)
    print("CÔNG CỤ TẠO TÀI KHOẢN TỰ ĐỘNG QUA GIAO DIỆN WEB")
    print("=" * 60)
    
    # URL trang đăng ký
    registration_url = input("Nhập URL trang đăng ký (mặc định: http://localhost:8000/accounts/signup/): ")
    if not registration_url:
        registration_url = "http://localhost:8000/accounts/signup/"
    
    # Lựa chọn
    choice = input("Bạn muốn:\n1. Tạo tài khoản ngẫu nhiên\n2. Nhập thông tin tài khoản\nChọn (1/2): ")
    
    if choice == "1":
        # Tạo thông tin người dùng ngẫu nhiên
        profile = generate_profile()
        register_account(registration_url, profile)
    
    elif choice == "2":
        # Nhập thông tin người dùng
        username = input("Tên người dùng: ")
        email = input("Email: ")
        birth_date = input("Ngày sinh (YYYY-MM-DD): ")
        gender = input("Giới tính (M: Nam, F: Nữ, O: Khác): ").upper()
        password = input("Mật khẩu: ")
        
        # Kiểm tra và đặt giá trị mặc định nếu cần
        if not username:
            username = fake.user_name()
        if not email:
            email = fake.email()
        if not birth_date or not birth_date.count('-') == 2:
            birth_date = datetime.now().replace(year=datetime.now().year - 20).strftime('%Y-%m-%d')
        if gender not in ['M', 'F', 'O']:
            gender = 'M'
        if not password:
            password = fake.password(length=12)
        
        profile = {
            'username': username,
            'email': email,
            'birth_date': birth_date,
            'gender': gender,
            'password': password
        }
        
        register_account(registration_url, profile)
    
    else:
        print("Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main() 