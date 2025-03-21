# Hoshi - Mạng xã hội chia sẻ khoảnh khắc

Hoshi là một mạng xã hội được xây dựng bằng Django, cho phép người dùng chia sẻ những khoảnh khắc trong cuộc sống thông qua hình ảnh và video.

## Tính năng

- Đăng ký & đăng nhập (email, số điện thoại, username, mật khẩu)
- Xác thực hai lớp (2FA)
- Đăng nhập bằng Google, Facebook, Apple
- Quản lý hồ sơ người dùng
- Đăng bài với nhiều ảnh/video
- Chỉnh sửa ảnh (bộ lọc, cắt, xoay, chỉnh màu)
- Tương tác (thả tim, bình luận, chia sẻ)
- Story & Reels
- Tin nhắn trực tiếp (chat)
- Thông báo thời gian thực
- Tìm kiếm & khám phá
- Theo dõi người dùng
- Và nhiều tính năng khác...

## Yêu cầu hệ thống

- Python 3.8+
- PostgreSQL
- Redis
- Node.js & npm (cho việc biên dịch assets)

## Cài đặt

1. Clone repository:
```bash
git clone https://github.com/yourusername/hoshi.git
cd hoshi
```

2. Tạo và kích hoạt môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Cài đặt các dependencies:
```bash
pip install -r requirements.txt
```

4. Tạo file .env và cấu hình các biến môi trường:
```bash
cp .env.example .env
# Chỉnh sửa file .env với các thông tin cấu hình của bạn
```

5. Tạo database và thực hiện migrate:
```bash
python manage.py migrate
```

6. Tạo superuser:
```bash
python manage.py createsuperuser
```

7. Chạy development server:
```bash
python manage.py runserver
```

## Cấu hình cho production

1. Cài đặt và cấu hình Nginx

2. Cài đặt và cấu hình Gunicorn:
```bash
gunicorn hoshi.wsgi:application
```

3. Cài đặt và cấu hình Supervisor để quản lý các process:
```ini
[program:hoshi]
command=/path/to/venv/bin/gunicorn hoshi.wsgi:application
directory=/path/to/hoshi
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
```

4. Cài đặt và cấu hình Redis cho cache và WebSocket:
```bash
sudo apt-get install redis-server
```

5. Cài đặt và cấu hình Celery cho các tác vụ bất đồng bộ:
```bash
celery -A hoshi worker -l info
celery -A hoshi beat -l info
```

## Đóng góp

Chúng tôi rất hoan nghênh mọi đóng góp! Vui lòng đọc [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết về quy trình đóng góp.

## Giấy phép

Dự án này được phân phối dưới giấy phép MIT. Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## Liên hệ

- Website: 
- Email: quangminh159159@gmail.com
- Facebook: 
- Twitter:  
 