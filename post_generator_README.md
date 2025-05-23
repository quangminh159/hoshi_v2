# Tool Tạo Bài Viết Tự Động cho Hoshi

Tool này giúp tạo các bài viết tự động với nội dung và hình ảnh tự động cho website Hoshi. Đây là một công cụ hữu ích để tạo dữ liệu mẫu nhanh chóng cho mục đích kiểm thử hoặc demo.

## Tính năng

- Tạo bài viết với caption và hashtag tự động
- Tạo hình ảnh tự động với nhiều hiệu ứng đồ họa
- Tải hình ảnh từ Unsplash API (tùy chọn)
- Tạo các bài viết có nhiều hình ảnh với các chủ đề khác nhau
- Tự động xử lý hashtags
- Dễ dàng sử dụng qua giao diện dòng lệnh hoặc script

## Yêu cầu

- Python 3.6 trở lên
- Django (phải được thiết lập đúng với dự án Hoshi)
- Thư viện Pillow (để tạo và xử lý hình ảnh)
- Thư viện Requests (để tải hình ảnh từ internet)

## Cài đặt

1. Đảm bảo rằng bạn đã kích hoạt môi trường ảo Django của dự án Hoshi nếu có
2. Cài đặt các thư viện cần thiết:

```
pip install Pillow requests
```

## Cách sử dụng

### Sử dụng script

Chỉ cần chạy script trên Windows:

```
create_post.bat
```

Hoặc trên Linux/macOS:

```
chmod +x create_post.sh
./create_post.sh
```

Làm theo các hướng dẫn trên màn hình để tạo bài viết.

### Sử dụng trực tiếp từ command line

```
# Tạo bài viết đơn giản với 1 hình ảnh
python auto_post_generator.py [tên_người_dùng]

# Tạo bài viết với nhiều hình ảnh
python auto_post_generator.py [tên_người_dùng] --images [số_lượng]

# Tạo bài viết với hình ảnh từ internet
python auto_post_generator.py [tên_người_dùng] --images [số_lượng] --external

# Tạo bài viết với nhiều chủ đề khác nhau
python auto_post_generator.py [tên_người_dùng] --images [số_lượng] --mixed
```

## Các tùy chọn

- `--images`: Số lượng hình ảnh cần tạo (mặc định: 1)
- `--external`: Sử dụng hình ảnh từ Unsplash thay vì tạo hình ảnh ngẫu nhiên
- `--mixed`: Tạo bài viết với nhiều chủ đề khác nhau

## Ví dụ

1. Tạo bài viết đơn giản cho người dùng "admin":
   ```
   python auto_post_generator.py admin
   ```

2. Tạo bài viết có 3 hình ảnh cho người dùng "testuser":
   ```
   python auto_post_generator.py testuser --images 3
   ```

3. Tạo bài viết với 2 hình ảnh từ internet cho người dùng "john":
   ```
   python auto_post_generator.py john --images 2 --external
   ```

4. Tạo bài viết với 4 chủ đề khác nhau cho người dùng "alice":
   ```
   python auto_post_generator.py alice --images 4 --mixed
   ```

## Ghi chú

- Đảm bảo máy chủ Django đang chạy khi sử dụng công cụ này để có thể xem kết quả ngay
- Các hình ảnh được tạo sẽ được lưu trong thư mục media của dự án
- Công cụ này tạo dữ liệu mẫu, thích hợp cho mục đích kiểm thử và demo
- Không nên sử dụng công cụ này để tạo dữ liệu giả trong môi trường sản xuất

## Khắc phục sự cố

- Nếu gặp lỗi ImportError, hãy đảm bảo bạn đã cài đặt đúng các thư viện yêu cầu
- Nếu gặp lỗi liên quan đến Django, hãy đảm bảo môi trường Django đã được thiết lập đúng
- Nếu hình ảnh không tải được, hãy kiểm tra kết nối internet của bạn hoặc bỏ qua tùy chọn `--external`

---

Được phát triển bởi Claude AI 3.7 Sonnet cho dự án Hoshi. 