#!/usr/bin/env python
import os
import shutil
import glob
import subprocess

# Xóa database
if os.path.exists('db.sqlite3'):
    try:
        os.remove('db.sqlite3')
        print("✅ Đã xóa db.sqlite3")
    except:
        print("❌ Không thể xóa db.sqlite3, có thể file đang được sử dụng")

# Xóa các file migrations (trừ __init__.py)
apps = ['accounts', 'posts', 'chat', 'notifications']

for app in apps:
    migrations_path = os.path.join(app, 'migrations')
    if os.path.exists(migrations_path):
        for file in glob.glob(os.path.join(migrations_path, '*.py')):
            if not file.endswith('__init__.py'):
                try:
                    os.remove(file)
                    print(f"✅ Đã xóa {file}")
                except:
                    print(f"❌ Không thể xóa {file}")
        
        # Xóa __pycache__ trong thư mục migrations
        pycache_path = os.path.join(migrations_path, '__pycache__')
        if os.path.exists(pycache_path):
            try:
                shutil.rmtree(pycache_path)
                print(f"✅ Đã xóa {pycache_path}")
            except:
                print(f"❌ Không thể xóa {pycache_path}")

# Tạo các file migrations và file __init__.py
for app in apps:
    migrations_path = os.path.join(app, 'migrations')
    if not os.path.exists(migrations_path):
        os.makedirs(migrations_path)
        print(f"✅ Đã tạo thư mục {migrations_path}")
    
    init_file = os.path.join(migrations_path, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            pass
        print(f"✅ Đã tạo file {init_file}")

print("\n=== Migration đã được reset ===")
print("Tiếp theo, hãy chạy các lệnh sau:")
print("1. python manage.py makemigrations")
print("2. python manage.py migrate")
print("3. python manage.py createsuperuser") 