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

## Triển khai lên Render

Render là nền tảng cloud đơn giản và mạnh mẽ để triển khai các ứng dụng web. Dưới đây là hướng dẫn triển khai Hoshi lên Render:

### 1. Chuẩn bị

1. Đăng ký tài khoản tại [Render](https://render.com)
2. Tạo file `render.yaml` trong thư mục gốc của dự án:

```yaml
services:
  - type: web
    name: hoshi
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn config.wsgi:application
    envVars:
      - key: DJANGO_SECRET_KEY
        generateValue: true
      - key: DJANGO_DEBUG
        value: false
      - key: DJANGO_ALLOWED_HOSTS
        value: .onrender.com
      - key: DATABASE_URL
        fromDatabase:
          name: hoshi-db
          property: connectionString
      - key: GOOGLE_CLIENT_ID
        sync: false
      - key: GOOGLE_CLIENT_SECRET
        sync: false

databases:
  - name: hoshi-db
    databaseName: hoshi
    user: hoshi
```

3. Cập nhật file `requirements.txt` để bao gồm thư viện cần thiết:
```
django
gunicorn
whitenoise
dj-database-url
psycopg2-binary
python-decouple
```

### 2. Cấu hình Django cho Render

1. Cập nhật file settings.py để sử dụng các biến môi trường:

```python
# Cấu hình database
import dj_database_url
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
}

# Cấu hình static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cấu hình allowed hosts
ALLOWED_HOSTS = ['.onrender.com', 'localhost', '127.0.0.1']
```

### 3. Triển khai

1. **Tùy chọn 1**: Triển khai thông qua GitHub:
   - Đẩy code lên GitHub
   - Đăng nhập vào Render
   - Chọn "New +" > "Blueprint"
   - Kết nối với repository GitHub
   - Render sẽ tự động đọc file render.yaml và thiết lập dịch vụ

2. **Tùy chọn 2**: Triển khai thủ công:
   - Đăng nhập vào Render
   - Chọn "New +" > "Web Service"
   - Kết nối với repository GitHub
   - Đặt tên dịch vụ: "hoshi"
   - Chọn môi trường: "Python"
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn config.wsgi:application`
   - Thêm các biến môi trường cần thiết

### 4. Cấu hình Database

1. Trong Render Dashboard, tạo PostgreSQL database mới
2. Copy chuỗi kết nối và đặt làm biến môi trường DATABASE_URL

### 5. Cấu hình OAuth

1. Cập nhật URL callback trong Google Cloud Console với domain Render của bạn:
   ```
   https://hoshi.onrender.com/accounts/google/login/callback/
   ```
2. Cập nhật biến môi trường GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET trong Render

### 6. Migrate và tạo superuser

1. Sau khi triển khai thành công, truy cập terminal của service trong Render:
   ```
   python manage.py migrate
   python manage.py createsuperuser
   ```

### 7. Kết quả

Ứng dụng của bạn sẽ có sẵn tại URL:
```
https://hoshi.onrender.com
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

# Hoshi - Hướng dẫn sử dụng Ngrok

## Giới thiệu

Tài liệu này hướng dẫn cách sử dụng Ngrok để cho phép người dùng từ mạng khác truy cập vào ứng dụng Django của bạn.

## Cài đặt và Cấu hình

### 1. Cài đặt Ngrok

- Tải Ngrok từ [trang chủ](https://ngrok.com/download)
- Giải nén file ngrok.zip vào thư mục dự án

### 2. Đăng ký tài khoản Ngrok

- Truy cập [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
- Đăng ký tài khoản miễn phí
- Lấy authtoken từ [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)

### 3. Thiết lập Ngrok

- Chạy file `setup_ngrok.bat` và nhập authtoken của bạn
- Hoặc chạy lệnh sau trong terminal:
  ```
  ngrok config add-authtoken YOUR_AUTHTOKEN
  ```

## Sử dụng

### 1. Chạy ứng dụng với Ngrok (Cách mới - Tự động)

Cách đơn giản nhất là sử dụng script tự động:

1. Nhấp đúp vào file `start_server_with_ngrok.bat`
2. Script sẽ tự động:
   - Khởi động Ngrok
   - Cập nhật cấu hình CSRF trong settings.py và .env
   - Khởi động Django server
   - Hiển thị URL công khai và URL callback

3. Chỉ cần cập nhật URL callback trong Google Cloud Console:
   - Truy cập https://console.cloud.google.com/apis/credentials
   - Chọn OAuth 2.0 Client ID
   - Thêm URL callback từ output của script vào mục "Authorized redirect URIs"
   - Thêm URL chính vào mục "Authorized JavaScript origins"

4. Khi hoàn thành, nhấn phím bất kỳ để dừng cả Ngrok và Django server

### 2. Cập nhật URL tự động (không cần nhập thủ công)

Nếu Ngrok đã chạy và bạn muốn cập nhật cấu hình:

```
python auto_update_ngrok.py
```

Script này sẽ:
- Tự động lấy URL Ngrok hiện tại
- Cập nhật cấu hình CSRF trong settings.py và .env
- Hiển thị URL callback cần cập nhật trong Google/Facebook

### 3. Chạy ứng dụng với Ngrok (Cách cũ - Thủ công)

#### Cách 1: Sử dụng script Python

Chạy lệnh sau:
```
python run_with_ngrok.py
```

Script này sẽ tự động:
- Khởi động Django server
- Tạo tunnel Ngrok
- Hiển thị URL công khai để truy cập ứng dụng

#### Cách 2: Chạy từng bước thủ công

1. Khởi động Django server:
   ```
   python manage.py runserver 0.0.0.0:8000
   ```

2. Trong một terminal khác, chạy Ngrok:
   ```
   ngrok http 8000
   ```

3. Lấy URL công khai từ output của Ngrok

4. Cập nhật cấu hình thủ công:
   ```
   python update_google_credentials.py
   ```

### 4. Sử dụng ứng dụng

- Chia sẻ URL Ngrok cho người dùng
- Người dùng có thể truy cập ứng dụng từ bất kỳ mạng nào
- Đăng nhập bằng Google/Facebook sẽ hoạt động nếu bạn đã cập nhật URL callback

## Lưu ý quan trọng

1. URL Ngrok miễn phí thay đổi mỗi khi khởi động lại Ngrok
2. Mỗi khi URL thay đổi, bạn cần cập nhật lại URL callback trong Google Cloud Console và Facebook Developers
3. Các ràng buộc của gói Ngrok miễn phí:
   - Session hết hạn sau 2 giờ
   - Băng thông giới hạn
   - Không có subdomain cố định
   - Chỉ cho phép 1 tunnel cùng lúc

## Nâng cấp lên Pro

Nếu bạn cần URL cố định và nhiều tính năng hơn, bạn có thể nâng cấp lên Ngrok Pro tại [https://ngrok.com/pricing](https://ngrok.com/pricing)

Với gói Pro, bạn có thể sử dụng lệnh:
```
ngrok http --domain=your-name.ngrok.io 8000
```

## Xử lý sự cố

### Lỗi "Tunnel session has expired"
- Nguyên nhân: Phiên Ngrok đã hết hạn (thường sau 2 giờ với tài khoản miễn phí)
- Giải pháp: Chạy lại file `start_server_with_ngrok.bat` và cập nhật URL callback mới

### Lỗi CSRF "Origin checking failed"
- Nguyên nhân: URL Ngrok chưa được thêm vào CSRF_TRUSTED_ORIGINS
- Giải pháp: Chạy `python auto_update_ngrok.py` hoặc chạy lại `start_server_with_ngrok.bat`

### Lỗi "Error 400: redirect_uri_mismatch"
- Nguyên nhân: URL callback trong Google Cloud Console không khớp với URL Ngrok hiện tại
- Giải pháp: Cập nhật URL callback trong Google Cloud Console theo hướng dẫn của script

### Lỗi "Access blocked: This app's request is invalid"
- Nguyên nhân: OAuth configuration không chính xác
- Giải pháp: Kiểm tra lại Client ID, Client Secret và URL callback trong cả database và Google Cloud Console
 