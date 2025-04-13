#!/usr/bin/env python
import os
import sys
import glob
import django
import shutil
from pathlib import Path

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

def find_base_template():
    """Tìm template base của ứng dụng"""
    print("=== TÌM TEMPLATE BASE CỦA ỨNG DỤNG ===")
    
    # Các template phổ biến
    base_candidates = [
        "templates/base.html",
        "templates/layout.html",
        "templates/master.html",
        "templates/main.html",
        "**/templates/base.html",
        "**/templates/layout.html"
    ]
    
    found_templates = []
    for pattern in base_candidates:
        found_templates.extend(glob.glob(pattern, recursive=True))
    
    # Tìm các file template khác có thể là base
    all_templates = glob.glob("**/templates/**/*.html", recursive=True)
    
    potential_base_templates = []
    for template in all_templates:
        with open(template, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Kiểm tra các dấu hiệu của template base
            if ('{% block content %}' in content or '{% block main %}' in content) and '<!DOCTYPE html>' in content:
                potential_base_templates.append(template)
    
    # Kết hợp kết quả
    base_templates = list(set(found_templates) | set(potential_base_templates))
    
    if not base_templates:
        print("Không tìm thấy template base nào!")
        return None
    
    print(f"Tìm thấy {len(base_templates)} template base tiềm năng:")
    for i, template in enumerate(base_templates):
        print(f"{i+1}. {template}")
    
    if len(base_templates) > 1:
        choice = input("Chọn template base (nhập số): ")
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(base_templates):
                return base_templates[choice_idx]
            else:
                return base_templates[0]
        except ValueError:
            return base_templates[0]
    else:
        return base_templates[0]

def copy_js_file():
    """Copy file JavaScript vào thư mục static"""
    print("\n=== COPY FILE JAVASCRIPT VÀO THƯ MỤC STATIC ===")
    
    # Tìm thư mục static
    static_dirs = glob.glob("**/static", recursive=True)
    if not static_dirs:
        print("Không tìm thấy thư mục static nào!")
        return None
    
    # Chọn thư mục static đầu tiên
    static_dir = static_dirs[0]
    print(f"Tìm thấy thư mục static: {static_dir}")
    
    # Tạo thư mục js nếu chưa tồn tại
    js_dir = os.path.join(static_dir, "js")
    os.makedirs(js_dir, exist_ok=True)
    
    # Copy file JavaScript
    src_js = "disable_multiple_submissions.js"
    dest_js = os.path.join(js_dir, "disable_multiple_submissions.js")
    
    if not os.path.exists(src_js):
        print(f"Không tìm thấy file {src_js}!")
        return None
    
    shutil.copy2(src_js, dest_js)
    print(f"Đã copy file JavaScript vào: {dest_js}")
    
    # Trả về đường dẫn tương đối cho template
    static_path = os.path.join("js", "disable_multiple_submissions.js")
    return static_path

def add_js_to_template(template_path, js_path):
    """Thêm file JavaScript vào template base"""
    print(f"\n=== THÊM FILE JAVASCRIPT VÀO TEMPLATE {template_path} ===")
    
    if not os.path.exists(template_path):
        print(f"Không tìm thấy file template: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Kiểm tra xem file JS đã được thêm chưa
    if f"disable_multiple_submissions.js" in content:
        print("File JavaScript đã được thêm vào template!")
        return False
    
    # Tìm vị trí để thêm script
    if '</body>' in content:
        # Thêm trước thẻ đóng body
        new_content = content.replace('</body>', f'<script src="{{ static \'{js_path}\' }}"></script>\n</body>')
    elif '</head>' in content:
        # Thêm trước thẻ đóng head
        new_content = content.replace('</head>', f'<script src="{{ static \'{js_path}\' }}"></script>\n</head>')
    else:
        # Thêm vào cuối file
        new_content = content + f'\n<script src="{{ static \'{js_path}\' }}"></script>\n'
    
    # Kiểm tra xem đã có {% load static %} chưa
    if '{% load static %}' not in content and "{% load staticfiles %}" not in content:
        new_content = '{% load static %}\n' + new_content
    
    # Lưu lại template
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Đã thêm file JavaScript vào template thành công!")
    return True

def create_server_validation():
    """Tạo validation trên server để ngăn bài đăng trùng lặp"""
    print("\n=== TẠO VALIDATION TRÊN SERVER ===")
    
    # Tìm model của bài đăng
    from django.apps import apps
    post_models = []
    
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if 'post' in model.__name__.lower() or 'comment' in model.__name__.lower():
                post_models.append((app_config.name, model.__name__))
    
    if not post_models:
        print("Không tìm thấy model bài đăng nào!")
        return
    
    print("Tìm thấy các model có thể là bài đăng:")
    for app_name, model_name in post_models:
        print(f"- {app_name}.{model_name}")
    
    print("\nĐề xuất thêm code ngăn bài đăng trùng lặp vào views.py:")
    print("""
# Trong hàm xử lý form đăng bài, thêm code sau:
from django.utils import timezone
from datetime import timedelta

def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            # Kiểm tra bài đăng trùng lặp
            content = form.cleaned_data['content']  # Thay 'content' bằng trường nội dung của bạn
            time_threshold = timezone.now() - timedelta(minutes=1)
            
            # Kiểm tra xem người dùng đã đăng bài với nội dung tương tự trong 1 phút qua chưa
            recent_posts = Post.objects.filter(
                user=request.user,
                content=content,
                created_at__gte=time_threshold
            )
            
            if recent_posts.exists():
                # Đã có bài đăng tương tự, thông báo cho người dùng
                messages.warning(request, 'Bạn vừa đăng bài với nội dung tương tự. Vui lòng đợi một lát trước khi đăng lại.')
                return redirect('post_list')  # Thay bằng URL thích hợp
            
            # Nếu không có bài trùng lặp, lưu bài đăng mới
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            return redirect('post_list')  # Thay bằng URL thích hợp
    """)

if __name__ == "__main__":
    print("=== THÊM GIẢI PHÁP CHỐNG BÀI ĐĂNG TRÙNG LẶP ===")
    
    # Bước 1: Tìm base template
    base_template = find_base_template()
    if not base_template:
        print("Không thể tiếp tục vì không tìm thấy template base!")
        sys.exit(1)
    
    # Bước 2: Copy file JavaScript vào thư mục static
    js_path = copy_js_file()
    if not js_path:
        print("Không thể tiếp tục vì không copy được file JavaScript!")
        sys.exit(1)
    
    # Bước 3: Thêm file JavaScript vào template
    add_js_to_template(base_template, js_path)
    
    # Bước 4: Tạo validation trên server
    create_server_validation()
    
    print("\n=== HOÀN TẤT ===")
    print("Đã triển khai giải pháp chống bài đăng trùng lặp!")
    print("Bạn cần chạy 'python manage.py collectstatic' và khởi động lại server để áp dụng thay đổi.") 