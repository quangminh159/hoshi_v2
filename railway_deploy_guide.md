# Hướng dẫn triển khai Hoshi lên Railway

Đây là hướng dẫn từng bước để triển khai ứng dụng Hoshi lên nền tảng Railway.

## 1. Chuẩn bị

### 1.1 Tạo tài khoản Railway

- Truy cập [Railway](https://railway.app) và đăng ký tài khoản mới
- Xác minh email của bạn

### 1.2 Cài đặt Railway CLI (tùy chọn)

```bash
npm i -g @railway/cli
```

Sau khi cài đặt, đăng nhập:

```bash
railway login
```

## 2. Triển khai lên Railway

### 2.1 Cách 1: Sử dụng Dashboard (Khuyến nghị)

1. Đăng nhập vào [Railway Dashboard](https://railway.app/dashboard)
2. Chọn "New Project" > "Deploy from GitHub repo"
3. Chọn repository chứa mã nguồn Hoshi
4. Railway sẽ tự động phát hiện ứng dụng Django và thiết lập build

### 2.2 Cách 2: Sử dụng CLI

1. Trong thư mục dự án, chạy:
   ```bash
   railway init
   ```
2. Chọn "Empty Project"
3. Triển khai code:
   ```bash
   railway up
   ```

## 3. Thiết lập Database và Redis

### 3.1 Thêm PostgreSQL

1. Trong project dashboard, chọn "New" > "Database" > "PostgreSQL"
2. Railway sẽ tự động tạo biến môi trường `DATABASE_URL`

### 3.2 Thêm Redis (nếu cần)

1. Trong project dashboard, chọn "New" > "Database" > "Redis"
2. Railway sẽ tự động tạo biến môi trường `REDIS_URL`

## 4. Cấu hình

### 4.1 Thiết lập biến môi trường

Trong dashboard, chọn "Variables" và thêm các biến sau:

```
DJANGO_SETTINGS_MODULE=hoshi.settings_railway
SECRET_KEY=<một_khóa_bí_mật_ngẫu_nhiên>
RAILWAY_STATIC_URL=https://<your-app-name>.up.railway.app
DEBUG=False

# OAuth
GOOGLE_CLIENT_ID=<your_google_client_id>
GOOGLE_CLIENT_SECRET=<your_google_client_secret>
FACEBOOK_CLIENT_ID=<your_facebook_client_id>
FACEBOOK_CLIENT_SECRET=<your_facebook_client_secret>

# Email
EMAIL_HOST_USER=<your_email>
EMAIL_HOST_PASSWORD=<your_email_app_password>

# Nếu sử dụng S3 cho media
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_STORAGE_BUCKET_NAME=<your_s3_bucket_name>
AWS_S3_REGION_NAME=ap-southeast-1
```

### 4.2 Chỉnh sửa cấu hình khởi động

Trong dashboard, chọn "Settings" và đảm bảo:

- Build Command: `python -m pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start Command: `gunicorn wsgi_railway:application`

## 5. Chạy migrations và tạo superuser

Sau khi triển khai thành công, truy cập railway shell bằng cách:

1. Trong dashboard, chọn tab "Shell"
2. Chạy các lệnh:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

## 6. Cập nhật OAuth Callbacks

### 6.1 Google OAuth

1. Truy cập [Google Cloud Console](https://console.cloud.google.com)
2. Tìm dự án của bạn và đi đến Credentials
3. Chỉnh sửa OAuth Client
4. Thêm URI chuyển hướng: `https://<your-app-name>.up.railway.app/accounts/google/login/callback/`

### 6.2 Facebook OAuth

1. Truy cập [Facebook Developers](https://developers.facebook.com)
2. Chọn ứng dụng của bạn
3. Vào Settings > Basic
4. Cập nhật App Domains
5. Vào Facebook Login > Settings
6. Thêm URI chuyển hướng: `https://<your-app-name>.up.railway.app/accounts/facebook/login/callback/`

## 7. Cấu hình SocialApp trong Admin

1. Truy cập `https://<your-app-name>.up.railway.app/admin/`
2. Đăng nhập với tài khoản superuser
3. Chọn "Sites" trong "SITES" và cập nhật domain thành `<your-app-name>.up.railway.app`
4. Chọn "Social applications" trong "SOCIAL ACCOUNTS"
5. Thêm hoặc cập nhật các ứng dụng Google và Facebook với thông tin mới

## 8. Kiểm tra và xử lý sự cố

### 8.1 Xem logs

Trong Railway dashboard, chọn tab "Logs" để xem logs của ứng dụng.

### 8.2 Các vấn đề thường gặp và cách xử lý

#### Static files không hoạt động

Đảm bảo:
- `STATIC_ROOT` được cấu hình đúng
- Lệnh `collectstatic` đã chạy trong quá trình build
- `STATICFILES_STORAGE` được thiết lập đúng

#### OAuth không hoạt động

- Kiểm tra URLs callback
- Kiểm tra SocialApp trong admin
- Đảm bảo đã cập nhật Sites trong admin

#### Database không kết nối

- Kiểm tra biến môi trường `DATABASE_URL`
- Đảm bảo đã chạy migrations

## 9. Nâng cấp và bảo trì

### 9.1 Nâng cấp ứng dụng

Khi cần nâng cấp:
1. Cập nhật code local
2. Đẩy lên GitHub
3. Railway sẽ tự động triển khai phiên bản mới

### 9.2 Sao lưu dữ liệu

Sử dụng:
```bash
python manage.py dumpdata > backup.json
```

### 9.3 Khôi phục dữ liệu

```bash
python manage.py loaddata backup.json
``` 