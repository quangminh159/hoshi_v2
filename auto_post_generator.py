#!/usr/bin/env python
"""
Tool tự động tạo bài viết với hình ảnh cho Hoshi
"""
import os
import sys
import django
import random
import argparse
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.core.files.uploadedfile import InMemoryUploadedFile

# Thiết lập Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

# Import các models sau khi đã thiết lập environment
from posts.models import Post, PostMedia
from django.contrib.auth import get_user_model
from posts.views import process_hashtags

User = get_user_model()

# Danh sách các chủ đề bài viết
TOPICS = [
    "Du lịch", "Ẩm thực", "Công nghệ", "Thời trang", 
    "Thể thao", "Giáo dục", "Sức khỏe", "Âm nhạc",
    "Phim ảnh", "Sách", "Nghệ thuật", "Thiên nhiên",
    "Động vật", "Tình yêu", "Gia đình", "Bạn bè"
]

# Danh sách các hashtag phổ biến
HASHTAGS = [
    "hoshi", "cuộcsống", "vietnam", "saigon", "hanoi", 
    "dulich", "amthuc", "congnghe", "thoitrang",
    "thethao", "giaoduc", "suckhoe", "amnhac",
    "phim", "sach", "nghethuat", "thiennhien"
]

# Danh sách các địa điểm
LOCATIONS = [
    "Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Huế", 
    "Nha Trang", "Đà Lạt", "Hội An", "Phú Quốc",
    "Hạ Long", "Sapa", "Vũng Tàu", "Cần Thơ",
    "Quy Nhơn", "Ninh Bình", "Hà Giang", "Côn Đảo"
]

# Danh sách nội dung mẫu cho bài viết
POST_TEMPLATES = [
    "Hôm nay tôi đã có một ngày tuyệt vời tại {location}. {topic} ở đây thật sự tuyệt vời! #{hashtag1} #{hashtag2}",
    "Khám phá {topic} mới tại {location}. Trải nghiệm tuyệt vời! #{hashtag1} #{hashtag2} #{hashtag3}",
    "Đang tận hưởng {topic} tại {location}. Thật không thể tin được! #{hashtag1} #{hashtag2}",
    "Chuyến đi {location} của tôi thật tuyệt vời với {topic} tuyệt vời. #{hashtag1} #{hashtag2}",
    "Hôm nay tôi đã học được nhiều điều về {topic} tại {location}. #{hashtag1} #{hashtag2}",
    "Chia sẻ khoảnh khắc đẹp về {topic} tại {location}. #{hashtag1} #{hashtag2} #{hashtag3}",
    "Đam mê {topic} không bao giờ dừng lại. {location} là nơi tuyệt vời! #{hashtag1} #{hashtag2}",
    "{location} - nơi tuyệt vời để trải nghiệm {topic}. #{hashtag1} #{hashtag2} #{hashtag3}",
]

def generate_image(topic, location, width=1080, height=1080):
    """Tạo hình ảnh với chủ đề và địa điểm"""
    # Tạo hình ảnh với màu nền ngẫu nhiên
    r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    image = Image.new('RGB', (width, height), color=(r, g, b))
    draw = ImageDraw.Draw(image)
    
    # Vẽ các hình dạng ngẫu nhiên
    for _ in range(20):
        shape_type = random.choice(['circle', 'rectangle', 'line'])
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        fill_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        if shape_type == 'circle':
            radius = random.randint(10, 100)
            draw.ellipse((x1-radius, y1-radius, x1+radius, y1+radius), fill=fill_color)
        elif shape_type == 'rectangle':
            draw.rectangle((x1, y1, x2, y2), fill=fill_color)
        else:
            draw.line((x1, y1, x2, y2), fill=fill_color, width=random.randint(1, 10))
    
    # Thêm nội dung văn bản
    try:
        # Thử sử dụng font hệ thống
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        # Nếu không có font, sử dụng font mặc định
        font = ImageFont.load_default()
    
    # Thêm chủ đề và địa điểm vào hình ảnh
    text = f"{topic} @ {location}"
    text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]
    position = ((width - text_width) // 2, (height - text_height) // 2)
    
    # Tạo hộp chữ nhật xung quanh văn bản
    text_bg = (
        position[0] - 10,
        position[1] - 10,
        position[0] + text_width + 10,
        position[1] + text_height + 10
    )
    draw.rectangle(text_bg, fill=(255, 255, 255, 128))
    
    # Vẽ văn bản
    draw.text(position, text, font=font, fill=(0, 0, 0))
    
    # Thêm timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((10, height - 30), timestamp, font=font, fill=(255, 255, 255))
    
    # Chuyển đổi thành file để upload
    image_io = BytesIO()
    image.save(image_io, format='JPEG')
    image_io.seek(0)
    
    return image_io

def download_random_image(topic):
    """Tải một hình ảnh ngẫu nhiên từ Unsplash API"""
    try:
        # Sử dụng Unsplash API (không yêu cầu key cho một số request cơ bản)
        url = f"https://source.unsplash.com/random/1080x1080/?{topic.replace(' ', ',')}"
        response = requests.get(url, stream=True, timeout=10)
        
        if response.status_code == 200:
            image_io = BytesIO(response.content)
            return image_io
        else:
            print(f"Không thể tải hình ảnh: {response.status_code}")
            return None
    except Exception as e:
        print(f"Lỗi khi tải hình ảnh: {e}")
        return None

def create_post(username, num_images=1, use_external_images=False):
    """Tạo bài viết với nội dung và hình ảnh ngẫu nhiên"""
    try:
        # Tìm user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            print(f"Không tìm thấy người dùng: {username}")
            return None
        
        # Chọn chủ đề và địa điểm ngẫu nhiên
        topic = random.choice(TOPICS)
        location = random.choice(LOCATIONS)
        
        # Chọn hashtags ngẫu nhiên
        hashtags = random.sample(HASHTAGS, min(3, len(HASHTAGS)))
        
        # Tạo nội dung bài viết
        post_template = random.choice(POST_TEMPLATES)
        caption = post_template.format(
            topic=topic,
            location=location,
            hashtag1=hashtags[0],
            hashtag2=hashtags[1],
            hashtag3=hashtags[2] if len(hashtags) > 2 else hashtags[0]
        )
        
        # Tạo bài viết mới
        post = Post.objects.create(
            author=user,
            caption=caption,
            location=location
        )
        
        # Thêm hình ảnh cho bài viết
        for i in range(num_images):
            if use_external_images:
                # Tải hình ảnh từ Unsplash
                image_io = download_random_image(topic)
                if image_io is None:
                    # Nếu không tải được hình ảnh, tạo hình ảnh mặc định
                    image_io = generate_image(topic, location)
            else:
                # Tạo hình ảnh mặc định
                image_io = generate_image(topic, location)
            
            # Tạo tên file
            filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.jpg"
            
            # Tạo đối tượng InMemoryUploadedFile từ BytesIO
            image_file = InMemoryUploadedFile(
                image_io,
                None,
                filename,
                'image/jpeg',
                image_io.getbuffer().nbytes,
                None
            )
            
            # Tạo PostMedia cho bài viết
            PostMedia.objects.create(
                post=post,
                file=image_file,
                media_type='image',
                order=i
            )
        
        # Xử lý hashtags
        process_hashtags(post)
        
        print(f"Đã tạo bài viết thành công: #{post.id}")
        print(f"Nội dung: {caption}")
        print(f"Địa điểm: {location}")
        print(f"Số lượng hình ảnh: {num_images}")
        
        return post
    
    except Exception as e:
        print(f"Lỗi khi tạo bài viết: {e}")
        return None

def create_mixed_media_post(username, num_media=2):
    """Tạo bài viết với nhiều hình ảnh kết hợp"""
    try:
        user = User.objects.get(username=username)
        
        # Chọn chủ đề và địa điểm ngẫu nhiên cho bài viết
        topics = random.sample(TOPICS, min(num_media, len(TOPICS)))
        location = random.choice(LOCATIONS)
        
        # Tạo nội dung bài viết với nhiều chủ đề
        topic_list = ", ".join(topics)
        hashtags = random.sample(HASHTAGS, min(3, len(HASHTAGS)))
        
        caption = f"Album {topic_list} tại {location}. Chia sẻ khoảnh khắc đẹp! #{hashtags[0]} #{hashtags[1]} #{hashtags[2]}"
        
        # Tạo bài viết mới
        post = Post.objects.create(
            author=user,
            caption=caption,
            location=location
        )
        
        # Thêm hình ảnh với các chủ đề khác nhau
        for i, topic in enumerate(topics):
            # Tạo hình ảnh
            image_io = generate_image(topic, location)
            
            # Tạo tên file
            filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.jpg"
            
            # Tạo đối tượng InMemoryUploadedFile từ BytesIO
            image_file = InMemoryUploadedFile(
                image_io,
                None,
                filename,
                'image/jpeg',
                image_io.getbuffer().nbytes,
                None
            )
            
            # Tạo PostMedia cho bài viết
            PostMedia.objects.create(
                post=post,
                file=image_file,
                media_type='image',
                order=i
            )
        
        # Xử lý hashtags
        process_hashtags(post)
        
        print(f"Đã tạo bài viết hỗn hợp thành công: #{post.id}")
        print(f"Nội dung: {caption}")
        print(f"Địa điểm: {location}")
        print(f"Số lượng hình ảnh: {len(topics)}")
        
        return post
    
    except Exception as e:
        print(f"Lỗi khi tạo bài viết hỗn hợp: {e}")
        return None

def main():
    """Hàm chính để chạy công cụ từ command line"""
    parser = argparse.ArgumentParser(description='Tool tạo bài viết tự động cho Hoshi')
    parser.add_argument('username', help='Tên người dùng đăng bài')
    parser.add_argument('--images', type=int, default=1, help='Số lượng hình ảnh (mặc định: 1)')
    parser.add_argument('--external', action='store_true', help='Sử dụng hình ảnh từ Unsplash')
    parser.add_argument('--mixed', action='store_true', help='Tạo bài viết hỗn hợp với nhiều chủ đề')
    
    args = parser.parse_args()
    
    if args.mixed:
        create_mixed_media_post(args.username, args.images)
    else:
        create_post(args.username, args.images, args.external)

if __name__ == "__main__":
    main() 