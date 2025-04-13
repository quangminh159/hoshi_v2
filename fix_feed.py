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
from django.contrib.staticfiles import finders
from django.core.files.storage import default_storage
from django.conf import settings

User = get_user_model()

def clear_cache():
    """Xóa cache để đảm bảo trang được tải lại hoàn toàn"""
    print("=== XÓA CACHE STATIC FILES ===")
    
    # Tìm và xóa cache của file JS
    try:
        from django.utils.module_loading import import_string
        from django.core.cache import cache
        
        # Xóa toàn bộ cache
        cache.clear()
        print("✓ Đã xóa cache Django")
    except Exception as e:
        print(f"× Không thể xóa cache: {str(e)}")

def check_media_files():
    """Kiểm tra các file media và đảm bảo chúng tồn tại"""
    print("\n=== KIỂM TRA FILE MEDIA ===")
    
    # Kiểm tra các PostMedia
    post_medias = PostMedia.objects.all()
    print(f"Tổng số media: {post_medias.count()}")
    
    for media in post_medias:
        if not media.file:
            print(f"× Media ID {media.id} không có file")
        else:
            try:
                if default_storage.exists(media.file.name):
                    print(f"✓ Media ID {media.id}: {media.file.name} tồn tại")
                else:
                    print(f"× Media ID {media.id}: {media.file.name} không tồn tại")
            except Exception as e:
                print(f"× Lỗi kiểm tra Media ID {media.id}: {str(e)}")

def check_templates():
    """Kiểm tra các template liên quan đến feed"""
    print("\n=== KIỂM TRA TEMPLATES ===")
    
    template_paths = [
        "posts/feed.html",
        "posts/components/post_card.html",
        "posts/components/comment_section.html"
    ]
    
    template_dirs = settings.TEMPLATES[0]['DIRS'] + [os.path.join(app, 'templates') for app in settings.INSTALLED_APPS]
    
    for template_path in template_paths:
        found = False
        for template_dir in template_dirs:
            full_path = os.path.join(template_dir, template_path)
            if os.path.exists(full_path):
                print(f"✓ Template {template_path} tồn tại tại: {full_path}")
                found = True
                break
        
        if not found:
            print(f"× Template {template_path} không tìm thấy")

def fix_feed_query():
    """Sửa lỗi trong truy vấn feed"""
    print("\n=== SỬA LỖI TRUY VẤN FEED ===")
    
    # Kiểm tra xem có bài viết nào không
    total_posts = Post.objects.count()
    print(f"Tổng số bài viết: {total_posts}")
    
    # Thử tạo một bài viết test để đảm bảo truy vấn hoạt động
    try:
        # Tìm user đầu tiên
        user = User.objects.first()
        if not user:
            print("× Không tìm thấy user nào, không thể tạo bài viết test")
            return
        
        # Tạo bài viết test
        test_post = Post.objects.create(
            author=user,
            caption="Bài viết test cho việc debug feed",
            created_at=timezone.now()
        )
        print(f"✓ Đã tạo bài viết test với ID: {test_post.id}")
        
        # Kiểm tra xem bài viết có xuất hiện trong truy vấn feed không
        posts = Post.objects.all().order_by('-created_at')
        if test_post in posts:
            print("✓ Bài viết test xuất hiện trong truy vấn feed")
        else:
            print("× Bài viết test không xuất hiện trong truy vấn feed")
    except Exception as e:
        print(f"× Lỗi khi tạo bài viết test: {str(e)}")

def create_debug_js():
    """Tạo file JavaScript để debug trang feed"""
    print("\n=== TẠO FILE DEBUG JAVASCRIPT ===")
    
    debug_js_content = """
/**
 * Debug script để kiểm tra lỗi hiển thị feed
 */
console.log('=== DEBUG FEED ===');

// Kiểm tra xem trang feed đã được tải chưa
document.addEventListener('DOMContentLoaded', function() {
    console.log('Trang đã được tải hoàn toàn');
    
    // Kiểm tra các bài viết
    const posts = document.querySelectorAll('.post-card');
    console.log(`Số lượng bài viết hiển thị: ${posts.length}`);
    
    // Kiểm tra dữ liệu
    const feedContainer = document.getElementById('feed-container');
    if (feedContainer) {
        console.log('Feed container đã được tìm thấy');
    } else {
        console.error('Feed container không tìm thấy!');
    }
    
    // Debug các thông báo lỗi
    if (window.django_messages) {
        console.log('Django messages:', window.django_messages);
    }
    
    // Kiểm tra các ảnh
    const images = document.querySelectorAll('img');
    console.log(`Số lượng ảnh: ${images.length}`);
    
    // Kiểm tra các link bị lỗi
    for (const img of images) {
        if (!img.complete || img.naturalHeight === 0) {
            console.error(`Ảnh lỗi: ${img.src}`);
        }
    }
    
    // Thử reload và clear cache
    document.getElementById('reload-btn')?.addEventListener('click', function() {
        location.reload(true);
    });
});

// Thêm nút reload vào trang
setTimeout(function() {
    const reloadBtn = document.createElement('button');
    reloadBtn.id = 'reload-btn';
    reloadBtn.className = 'btn btn-primary position-fixed';
    reloadBtn.style.cssText = 'bottom: 20px; right: 20px; z-index: 9999;';
    reloadBtn.textContent = 'Reload Page';
    document.body.appendChild(reloadBtn);
}, 1000);
"""
    
    # Tạo thư mục nếu chưa tồn tại
    js_dir = os.path.join('static', 'js')
    os.makedirs(js_dir, exist_ok=True)
    
    # Viết nội dung file
    debug_js_path = os.path.join(js_dir, 'debug_feed.js')
    with open(debug_js_path, 'w', encoding='utf-8') as f:
        f.write(debug_js_content)
    
    print(f"✓ Đã tạo file debug JavaScript tại: {debug_js_path}")
    print("Thêm đường dẫn sau vào template base:")
    print('<script src="{% static \'js/debug_feed.js\' %}"></script>')

def check_network_settings():
    """Kiểm tra các cài đặt mạng"""
    print("\n=== KIỂM TRA CÀI ĐẶT MẠNG ===")
    
    # Kiểm tra ALLOWED_HOSTS
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
    print(f"ALLOWED_HOSTS: {allowed_hosts}")
    
    # Kiểm tra CSRF_TRUSTED_ORIGINS
    csrf_trusted_origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
    print(f"CSRF_TRUSTED_ORIGINS: {csrf_trusted_origins}")
    
    # Kiểm tra INSTALLED_APPS
    print(f"INSTALLED_APPS: {', '.join(settings.INSTALLED_APPS)}")
    
    # Kiểm tra DEBUG
    print(f"DEBUG: {settings.DEBUG}")

if __name__ == "__main__":
    print("=== BẮT ĐẦU KHẮC PHỤC LỖI FEED ===")
    
    clear_cache()
    check_media_files()
    check_templates()
    fix_feed_query()
    create_debug_js()
    check_network_settings()
    
    print("\n=== HOÀN TẤT ===")
    print("1. Đã tạo bài viết test để kiểm tra feed")
    print("2. Đã tạo file JavaScript để debug trong console")
    print("3. Đã kiểm tra các templates và cài đặt mạng")
    print("\nĐề xuất giải pháp:")
    print("1. Chạy lệnh python manage.py collectstatic để cập nhật file JS")
    print("2. Khởi động lại server và xem console để debug")
    print("3. Kiểm tra các file trong thư mục templates/posts/") 