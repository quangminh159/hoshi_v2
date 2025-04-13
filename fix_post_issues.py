#!/usr/bin/env python
import os
import sys
import django
import logging
from datetime import timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

from django.contrib.auth import get_user_model
from posts.models import Post, Comment, PostMedia
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

User = get_user_model()

def test_create_post():
    """Kiểm tra khả năng tạo bài viết mới"""
    print("=== KIỂM TRA TẠO BÀI VIẾT ===")
    
    # Lấy thông tin user
    user = User.objects.filter(is_active=True).first()
    
    if not user:
        print("× Không tìm thấy user hoạt động nào!")
        return
    
    print(f"Đang kiểm tra với user: {user.username}")
    
    # Kiểm tra số lượng bài viết trước khi tạo
    posts_before = Post.objects.filter(author=user).count()
    print(f"Số bài viết hiện tại của user: {posts_before}")
    
    # Thử tạo bài viết mới
    try:
        with transaction.atomic():
            new_post = Post.objects.create(
                author=user,
                caption="Bài đăng test thủ công - " + timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                created_at=timezone.now()
            )
            print(f"✓ Đã tạo bài viết mới với ID: {new_post.id}")
            
            # Kiểm tra xem bài viết đã được lưu chưa
            post_exists = Post.objects.filter(id=new_post.id).exists()
            print(f"Bài viết tồn tại trong DB: {'✓' if post_exists else '×'}")
            
            # Kiểm tra các field bắt buộc
            print(f"  - author: {new_post.author.username}")
            print(f"  - caption: {new_post.caption}")
            print(f"  - created_at: {new_post.created_at}")
            
            # Kiểm tra số lượng bài viết sau khi tạo
            posts_after = Post.objects.filter(author=user).count()
            print(f"Số bài viết sau khi tạo: {posts_after}")
            print(f"Tăng: {posts_after - posts_before} bài viết")
            
    except ValidationError as e:
        print(f"× Lỗi validation khi tạo bài viết: {str(e)}")
    except Exception as e:
        print(f"× Lỗi khi tạo bài viết: {str(e)}")

def fix_missing_script():
    """Kiểm tra và sửa lỗi thiếu script trong template"""
    print("\n=== KIỂM TRA VÀ SỬA LỖI SCRIPT ===")
    
    # Kiểm tra tag đóng script trong template base
    base_template = "templates/base/base.html"
    
    try:
        with open(base_template, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Kiểm tra thẻ disable_multiple_submissions.js
        if '<script src="{% static \'js/disable_multiple_submissions.js\' %}"></script>' in content:
            print("✓ Đã tìm thấy thẻ script disable_multiple_submissions.js")
            
            # Kiểm tra lỗi tag không đúng
            if "static 'js/disable_multiple_submissions.js'" in content:
                print("× Thẻ script có cú pháp không đúng!")
                
                # Sửa lại tag
                fixed_content = content.replace(
                    "static 'js/disable_multiple_submissions.js'", 
                    "{% static 'js/disable_multiple_submissions.js' %}"
                )
                
                with open(base_template, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print("✓ Đã sửa lại cú pháp thẻ script")
        else:
            print("× Không tìm thấy thẻ script disable_multiple_submissions.js")
    
    except Exception as e:
        print(f"× Lỗi khi kiểm tra template: {str(e)}")

def check_csrf_token():
    """Kiểm tra cấu hình CSRF token"""
    print("\n=== KIỂM TRA CSRF TOKEN ===")
    
    try:
        from django.middleware.csrf import get_token
        from django.http import HttpRequest
        
        # Tạo request giả lập
        request = HttpRequest()
        token = get_token(request)
        
        if token:
            print(f"✓ CSRF token hoạt động: {token[:10]}...")
        else:
            print("× Không thể tạo CSRF token!")
        
        # Kiểm tra cấu hình CSRF trong settings
        from django.conf import settings
        
        csrf_cookie_secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
        csrf_cookie_httponly = getattr(settings, 'CSRF_COOKIE_HTTPONLY', False)
        csrf_cookie_samesite = getattr(settings, 'CSRF_COOKIE_SAMESITE', None)
        
        print(f"CSRF_COOKIE_SECURE: {csrf_cookie_secure}")
        print(f"CSRF_COOKIE_HTTPONLY: {csrf_cookie_httponly}")
        print(f"CSRF_COOKIE_SAMESITE: {csrf_cookie_samesite}")
        
    except Exception as e:
        print(f"× Lỗi khi kiểm tra CSRF token: {str(e)}")

def check_post_form():
    """Kiểm tra form đăng bài"""
    print("\n=== KIỂM TRA FORM ĐĂNG BÀI ===")
    
    # Kiểm tra form trong template feed.html
    feed_template = "templates/posts/feed.html"
    
    try:
        with open(feed_template, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Kiểm tra xem có form đăng bài không
        if 'action="{% url \'posts:create\' %}"' in content:
            print("✓ Đã tìm thấy form đăng bài trong feed.html")
            
            # Kiểm tra CSRF token trong form
            if '{% csrf_token %}' in content:
                print("✓ Form có CSRF token")
            else:
                print("× Form thiếu CSRF token!")
            
            # Kiểm tra encoding type
            if 'enctype="multipart/form-data"' in content:
                print("✓ Form có enctype đúng")
            else:
                print("× Form thiếu enctype=\"multipart/form-data\"!")
            
            # Kiểm tra nút submit
            if 'type="submit"' in content:
                print("✓ Form có nút submit")
            else:
                print("× Form thiếu nút submit!")
            
        else:
            print("× Không tìm thấy form đăng bài trong feed.html")
    
    except Exception as e:
        print(f"× Lỗi khi kiểm tra form: {str(e)}")

def fix_disable_multiple_submissions():
    """Khắc phục lỗi script disable_multiple_submissions.js"""
    print("\n=== SỬA LỖI DISABLE_MULTIPLE_SUBMISSIONS.JS ===")
    
    # Tạo lại file JavaScript
    js_content = """/**
 * Script để ngăn gửi form nhiều lần
 */
document.addEventListener('DOMContentLoaded', function() {
    // Đảm bảo script không chạy nhiều lần
    if (window.formSubmissionHandled) return;
    window.formSubmissionHandled = true;
    
    console.log('Đã tải script prevent multiple submissions');
    
    // Xử lý tất cả các form trên trang
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            console.log('Form đang được gửi:', form);
            
            // Nếu form đã được đánh dấu là đang gửi, ngăn gửi lại
            if (this.classList.contains('submitting')) {
                console.log('Đã chặn gửi form trùng lặp');
                e.preventDefault();
                return false;
            }
            
            // Đánh dấu form đang được gửi
            this.classList.add('submitting');
            console.log('Đã đánh dấu form là đang gửi');
            
            // Tìm nút submit và vô hiệu hóa
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.textContent;
                submitButton.setAttribute('data-original-text', originalText);
                submitButton.textContent = 'Đang gửi...';
                submitButton.disabled = true;
                console.log('Đã vô hiệu hóa nút submit');
            }
        });
    });
});
"""
    
    # Tạo thư mục nếu chưa tồn tại
    js_dir = os.path.join('static', 'js')
    os.makedirs(js_dir, exist_ok=True)
    
    # Lưu nội dung file
    js_path = os.path.join(js_dir, 'disable_multiple_submissions.js')
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"✓ Đã tạo lại file {js_path}")

def check_views():
    """Kiểm tra các view xử lý đăng bài"""
    print("\n=== KIỂM TRA VIEW XỬ LÝ ĐĂNG BÀI ===")
    
    # Kiểm tra view create_post trong posts/views.py
    views_path = "posts/views.py"
    
    try:
        with open(views_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Kiểm tra xem có view create_post không
        if "def create_post(" in content:
            print("✓ Tìm thấy view create_post")
            
            # Kiểm tra validation trùng lặp
            if "time_threshold = timezone.now() - timedelta(minutes=1)" in content:
                print("✓ Có code kiểm tra đăng bài trùng lặp")
                print("  Điều này có thể ngăn bạn đăng bài nếu có nội dung tương tự gần đây!")
            else:
                print("× Không tìm thấy code kiểm tra đăng bài trùng lặp")
                
        else:
            print("× Không tìm thấy view create_post!")
    
    except Exception as e:
        print(f"× Lỗi khi kiểm tra view: {str(e)}")

if __name__ == "__main__":
    print("=== BẮT ĐẦU KHẮC PHỤC LỖI ĐĂNG BÀI ===")
    
    test_create_post()
    fix_missing_script()
    check_csrf_token()
    check_post_form()
    fix_disable_multiple_submissions()
    check_views()
    
    print("\n=== KHẮC PHỤC XONG ===")
    print("1. Đã tạo bài viết test để kiểm tra cơ sở dữ liệu")
    print("2. Đã kiểm tra và sửa lỗi script trong template")
    print("3. Đã tạo lại file JS ngăn đăng bài trùng lặp")
    print("4. Đã kiểm tra form đăng bài và view xử lý")
    print("\nVui lòng chạy lệnh sau để cập nhật static files:")
    print("python manage.py collectstatic --noinput")
    print("\nSau đó khởi động lại server:")
    print("python run_on_network.py") 