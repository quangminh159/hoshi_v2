#!/usr/bin/env python
import os
import sys
import django
from django.db import connection

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

# Sửa cấu trúc bảng EmailAddress trước khi tạo migrations
print("Đang sửa lỗi EmailAddress trong allauth...")

# Tạo migration trực tiếp cho mô hình EmailAddress
with connection.cursor() as cursor:
    # Tạo bảng tạm thời mới với cấu trúc đúng
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "account_emailaddress_new" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, 
        "email" varchar(254) NOT NULL, 
        "verified" bool NOT NULL, 
        "primary" bool NOT NULL, 
        "user_id" integer NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    )
    """)
    
    # Tạo index cho trường user_id
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS "account_emailaddress_user_id_2c513194" 
    ON "account_emailaddress_new" ("user_id")
    """)
    
    # Đảm bảo email là duy nhất cho mỗi user
    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS "account_emailaddress_user_id_email_85c5ac7d_uniq" 
    ON "account_emailaddress_new" ("user_id", "email")
    """)
    
    # Chuyển dữ liệu nếu có bảng cũ
    try:
        cursor.execute("""
        INSERT INTO "account_emailaddress_new" ("id", "email", "verified", "primary", "user_id")
        SELECT "id", "email", "verified", "primary", 1 FROM "account_emailaddress"
        """)
        print("Đã chuyển dữ liệu từ bảng cũ sang bảng mới")
    except:
        print("Không thể chuyển dữ liệu, có thể bảng cũ không tồn tại")
    
    # Xóa bảng cũ và đổi tên bảng mới
    try:
        cursor.execute('DROP TABLE IF EXISTS "account_emailaddress"')
        cursor.execute('ALTER TABLE "account_emailaddress_new" RENAME TO "account_emailaddress"')
        print("Đã xóa bảng cũ và đổi tên bảng mới")
    except:
        print("Không thể xóa bảng cũ hoặc đổi tên bảng mới")

print("Đã hoàn thành việc sửa lỗi EmailAddress")
print("Bây giờ bạn có thể chạy lệnh:")
print("python manage.py makemigrations")
print("python manage.py migrate") 