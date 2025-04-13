# Hướng dẫn triển khai Hoshi lên Render

Đây là hướng dẫn chi tiết từng bước để triển khai ứng dụng Hoshi lên nền tảng Render.

## 1. Chuẩn bị

### 1.1 Tạo tài khoản Render

- Truy cập [Render](https://render.com) và đăng ký tài khoản mới
- Xác minh email của bạn

### 1.2 Chuẩn bị mã nguồn

- Đảm bảo đã đẩy code lên GitHub
- Các file sau đã được thêm vào repository:
  - `render.yaml`: Cấu hình service
  - `build_files.sh`: Script build
  - `requirements_render.txt`: Danh sách dependencies cho Render
  - `hoshi/settings_render.py`: Cài đặt cho môi trường Render
  - `wsgi_render.py`: WSGI config cho Render

### 1.3 Cấu trúc thư mục

Đảm bảo cấu trúc thư mục dự án của bạn như sau:
```
hoshi_v2/
├── hoshi/
│   ├── settings.py
│   ├── settings_render.py  # Cài đặt cho Render
│   ├── urls.py
│   ├── wsgi.py
│   └── ...
├── static/
├── templates/
├── accounts/
├── posts/
├── ... (các app khác)
├── build_files.sh          # Script build
├── render.yaml             # Cấu hình Render
├── requirements.txt        # Dependencies local
├── requirements_render.txt # Dependencies cho Render
└── wsgi_render.py          # WSGI cho Render
```

## 2. Triển khai trên Render

### 2.1 Tạo PostgreSQL Database

1. Đăng nhập vào Render Dashboard
2. Chọn "New +" > "PostgreSQL" 
3. Điền thông tin:
   - Name: `hoshi-db`
   - Database: `hoshi`
   - User: `hoshi`
   - Region: Chọn region gần vị trí của bạn (Singapore cho Việt Nam)
4. Chọn plan phù hợp (Free plan đủ cho việc thử nghiệm)
5. Nhấn "Create Database"
6. Sau khi tạo xong, lưu lại thông tin kết nối (Internal Database URL)

### 2.2 Triển khai Web Service

#### Cách 1: Sử dụng Blueprint (Khuyến nghị)

1. Trong Dashboard, chọn "New +" > "Blueprint"
2. Kết nối với GitHub repository của bạn
3. Render sẽ tự động phát hiện file `render.yaml` và cấu hình services
4. Xem lại cấu hình và nhấn "Apply"
5. Điền các biến môi trường cần thiết:
   - `GOOGLE_CLIENT_ID`: Client ID từ Google Cloud Console
   - `GOOGLE_CLIENT_SECRET`: Client Secret từ Google Cloud Console
   - `FACEBOOK_CLIENT_ID`: Client ID từ Facebook Developer
   - `FACEBOOK_CLIENT_SECRET`: Client Secret từ Facebook Developer
   - `EMAIL_HOST_USER`: Email để gửi thông báo
   - `EMAIL_HOST_PASSWORD`: Mật khẩu ứng dụng của email

#### Cách 2: Cấu hình thủ công

1. Trong Dashboard, chọn "New +" > "Web Service"
2. Kết nối với GitHub repository của bạn
3. Điền thông tin:
   - Name: `hoshi`
   - Environment: Python
   - Region: Chọn region gần vị trí của bạn (Singapore cho Việt Nam)
   - Build Command: `sh ./build_files.sh`
   - Start Command: `gunicorn hoshi.wsgi_render:application`
4. Chọn plan phù hợp (Free plan đủ cho việc thử nghiệm)
5. Trong tab "Environment", thêm các biến môi trường cần thiết

### 2.3 Về file requirements_render.txt

File `requirements_render.txt` đã được chuẩn bị với các thư viện cần thiết cho việc triển khai lên Render, bao gồm:

- Core Django: Django, dj-database-url, gunicorn, whitenoise...
- Database: psycopg2-binary cho PostgreSQL
- Authentication: django-allauth cho social login
- UI Components: crispy-forms, bootstrap5...
- Và các dependencies khác cần thiết

Script `build_files.sh` sẽ tự động cài đặt các packages từ file này, thu thập static files và thực hiện migrations.

## 3. Cấu hình sau khi triển khai

### 3.1 Cập nhật URL callback trong Google Cloud Console

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Chọn OAuth 2.0 Client IDs đang sử dụng
3. Thêm URL vào Authorized redirect URIs:
   ```
   https://hoshi.onrender.com/accounts/google/login/callback/
   ```
4. Thêm URL vào Authorized JavaScript origins:
   ```
   https://hoshi.onrender.com
   ```
5. Lưu thay đổi

### 3.2 Cập nhật URL callback trong Facebook Developers

1. Truy cập [Facebook Developers](https://developers.facebook.com/apps/)
2. Chọn ứng dụng của bạn
3. Đi đến Products > Facebook Login > Settings
4. Thêm URL vào Valid OAuth Redirect URIs:
   ```
   https://hoshi.onrender.com/accounts/facebook/login/callback/
   ```
5. Lưu thay đổi

### 3.3 Tạo superuser

1. Trong Render Dashboard, chọn web service `hoshi`
2. Mở tab "Shell"
3. Chạy lệnh:
   ```
   python manage.py createsuperuser
   ```
4. Nhập thông tin người dùng quản trị

### 3.4 Cài đặt SocialApp

Nếu SocialApp records trong database chưa được tạo, bạn cần tạo chúng qua Django admin:

1. Truy cập `https://hoshi.onrender.com/admin` và đăng nhập bằng tài khoản superuser
2. Điều hướng đến "Social applications" trong "Social Accounts"
3. Thêm các applications cho Google và Facebook với Client ID và Secret từ biến môi trường
4. Đảm bảo chọn site đúng (thường là `hoshi.onrender.com`)

## 4. Kiểm tra ứng dụng

1. Truy cập URL của ứng dụng (thường là https://hoshi.onrender.com)
2. Thử đăng nhập bằng tài khoản quản trị vừa tạo
3. Thử đăng nhập bằng Google/Facebook
4. Kiểm tra các chức năng khác của ứng dụng

## 5. Xử lý sự cố

### 5.1 Lỗi khi triển khai

- Kiểm tra logs trong Render Dashboard (tab "Logs")
- Đảm bảo `requirements_render.txt` chứa đầy đủ dependencies
- Kiểm tra cấu hình trong file `settings_render.py`
- Kiểm tra file `build_files.sh` có quyền thực thi

### 5.2 Lỗi OAuth

- Kiểm tra lại URL callback trong Google Cloud Console và Facebook Developers
- Đảm bảo Client ID và Client Secret đã được cài đặt đúng trong Render
- Kiểm tra cấu hình SocialApp trong admin panel
- Xác nhận CSRF_TRUSTED_ORIGINS đã được cấu hình đúng

### 5.3 Lỗi Static Files

- Kiểm tra cấu hình STATIC_ROOT và STATICFILES_STORAGE
- Đảm bảo thư mục static tồn tại trong dự án
- Chạy lại lệnh collectstatic từ shell của Render:
  ```
  python manage.py collectstatic --noinput
  ```

### 5.4 Lỗi Database

- Kiểm tra lại thông tin kết nối database
- Đảm bảo migrations đã được áp dụng
- Chạy lệnh migrate từ shell:
  ```
  python manage.py migrate
  ```

## 6. Nâng cấp

Để nâng cấp ứng dụng trong tương lai:
1. Cập nhật code trên máy local
2. Kiểm tra xem có dependencies mới cần thêm vào `requirements_render.txt` không
3. Đẩy code mới lên GitHub
4. Render sẽ tự động phát hiện và triển khai phiên bản mới

## Bảo trì

- Thường xuyên kiểm tra logs trong Render Dashboard
- Theo dõi việc sử dụng tài nguyên để tối ưu chi phí
- Backup database thường xuyên bằng cách xuất dữ liệu từ admin panel hoặc sử dụng dumpdata:
  ```
  python manage.py dumpdata > backup.json
  ``` 