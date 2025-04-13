#!/usr/bin/env python
import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

# Import sau khi đã thiết lập Django
from django.db.models import Count
from django.contrib.auth import get_user_model
# Thay thế 'app_name' và 'Post' với tên app và model bài đăng thực tế của bạn
# from app_name.models import Post

def check_duplicate_posts():
    """Kiểm tra bài đăng trùng lặp trong hệ thống"""
    print("=== KIỂM TRA BÀI ĐĂNG TRÙNG LẶP ===")
    
    # Kiểm tra các model trong dự án
    from django.apps import apps
    post_models = []
    
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if 'post' in model.__name__.lower() or 'comment' in model.__name__.lower() or 'article' in model.__name__.lower():
                post_models.append((app_config.name, model.__name__, model))
    
    if not post_models:
        print("Không tìm thấy model bài đăng nào trong dự án!")
        return
    
    print(f"Tìm thấy {len(post_models)} model có thể là bài đăng:")
    for app_name, model_name, model in post_models:
        print(f"- {app_name}.{model_name}")
    
    # Chọn model đầu tiên để kiểm tra
    selected_app, selected_model, Model = post_models[0]
    
    try:
        # Tìm các bài trùng lặp (đăng cùng nội dung trong 1 phút)
        time_threshold = timezone.now() - timedelta(minutes=60)
        
        # Lấy tất cả bài đăng trong 60 phút gần đây
        recent_posts = Model.objects.filter(created_at__gte=time_threshold).order_by('-created_at')
        
        if not recent_posts.exists():
            print(f"Không có bài đăng nào trong 60 phút gần đây!")
            return
        
        print(f"Số bài đăng trong 60 phút gần đây: {recent_posts.count()}")
        
        # Nhóm theo người dùng để kiểm tra trùng lặp
        duplicates = []
        users = set()
        
        for post in recent_posts:
            if not hasattr(post, 'user') and not hasattr(post, 'author'):
                print("Model không có trường user hoặc author!")
                break
                
            user = getattr(post, 'user', None) or getattr(post, 'author', None)
            if user in users:
                # Kiểm tra nội dung trùng lặp
                user_posts = recent_posts.filter(user=user) if hasattr(post, 'user') else recent_posts.filter(author=user)
                
                # Tìm các bài đăng có cùng nội dung
                if hasattr(post, 'content'):
                    content_field = 'content'
                elif hasattr(post, 'text'):
                    content_field = 'text'
                elif hasattr(post, 'body'):
                    content_field = 'body'
                else:
                    print("Không thể xác định trường nội dung của bài đăng!")
                    break
                
                # Xây dựng filter động cho trường nội dung
                filter_kwargs = {content_field: getattr(post, content_field)}
                similar_posts = user_posts.filter(**filter_kwargs)
                
                if similar_posts.count() > 1:
                    # Nếu có nhiều hơn 1 bài với cùng nội dung
                    duplicates.append((user, similar_posts, content_field))
            else:
                users.add(user)
        
        # Hiển thị và đề xuất xử lý
        if duplicates:
            print(f"\nTìm thấy {len(duplicates)} người dùng có bài đăng trùng lặp:")
            for user, posts, content_field in duplicates:
                username = user.username if hasattr(user, 'username') else str(user)
                print(f"- Người dùng: {username}")
                print(f"  Số bài trùng lặp: {posts.count()}")
                print(f"  Nội dung: {getattr(posts[0], content_field)[:50]}...")
                
                # Giữ lại bài mới nhất, xóa các bài còn lại
                newest_post = posts.order_by('-created_at').first()
                posts_to_delete = posts.exclude(id=newest_post.id)
                print(f"  Đề xuất: Giữ lại bài mới nhất (ID: {newest_post.id}), xóa {posts_to_delete.count()} bài cũ hơn")
                
                confirm = input("  Bạn có muốn xóa các bài trùng lặp không? (y/n): ")
                if confirm.lower() == 'y':
                    deleted_count = posts_to_delete.delete()[0]
                    print(f"  ✓ Đã xóa {deleted_count} bài trùng lặp")
                else:
                    print("  ✗ Bỏ qua xóa bài trùng lặp")
        else:
            print("\nKhông tìm thấy bài đăng trùng lặp trong hệ thống!")
            
    except Exception as e:
        print(f"Có lỗi xảy ra khi kiểm tra bài đăng trùng lặp: {str(e)}")

def fix_js_form_submission():
    """Sửa lỗi JavaScript gửi form nhiều lần"""
    print("\n=== TÌM FILE JAVASCRIPT XỬ LÝ FORM ===")
    
    # Tìm file js có liên quan đến form submission
    import glob
    js_files = glob.glob("**/static/**/*.js", recursive=True)
    form_js_files = []
    
    for js_file in js_files:
        with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            if 'submit' in content and 'form' in content:
                form_js_files.append(js_file)
    
    if form_js_files:
        print(f"Tìm thấy {len(form_js_files)} file JavaScript có thể liên quan đến form:")
        for file in form_js_files:
            print(f"- {file}")
        print("\nĐề xuất: Kiểm tra các file này và thêm code ngăn gửi form nhiều lần")
        print("""
Mẫu code JavaScript để ngăn gửi form nhiều lần:

document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        // Ngăn gửi form nhiều lần
        if (this.classList.contains('submitting')) {
            e.preventDefault();
            return;
        }
        
        // Đánh dấu form đang gửi
        this.classList.add('submitting');
        
        // Vô hiệu hóa nút gửi
        const submitButton = this.querySelector('button[type="submit"]');
        if (submitButton) {
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Đang gửi...';
            submitButton.disabled = true;
            
            // Khôi phục nút sau 5 giây (phòng hờ trường hợp lỗi)
            setTimeout(() => {
                this.classList.remove('submitting');
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }, 5000);
        }
    });
});
        """)
    else:
        print("Không tìm thấy file JavaScript nào xử lý form!")

if __name__ == "__main__":
    try:
        check_duplicate_posts()
        fix_js_form_submission()
        
        print("\n=== GIẢI PHÁP KHÁC ===")
        print("1. Kiểm tra cấu hình CSRF token trong Django settings")
        print("2. Đảm bảo các form có {% csrf_token %}")
        print("3. Thêm validation ở phía server để kiểm tra trùng lặp trước khi lưu")
        print("4. Thêm debounce/throttle cho các button submit trên frontend")
        print("5. Đảm bảo connection ổn định khi chạy trên mạng LAN")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}") 