#!/bin/bash
# Tool tạo bài viết tự động cho Hoshi
# Tác giả: Claude AI 3.7 Sonnet

echo "================================================"
echo "         Tool tạo bài viết tự động cho Hoshi         "
echo "================================================"
echo

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "[Lỗi] Không tìm thấy Python. Vui lòng cài đặt Python và thử lại."
    exit 1
fi

# Kiểm tra thư viện PIL
if ! python3 -c "import PIL" &> /dev/null; then
    echo "[Cảnh báo] Thư viện PIL (Pillow) chưa được cài đặt."
    echo "Đang cài đặt Pillow..."
    pip3 install Pillow
fi

# Kiểm tra thư viện requests
if ! python3 -c "import requests" &> /dev/null; then
    echo "[Cảnh báo] Thư viện requests chưa được cài đặt."
    echo "Đang cài đặt requests..."
    pip3 install requests
fi

echo
echo "1. Tạo bài viết đơn giản với 1 hình ảnh"
echo "2. Tạo bài viết với nhiều hình ảnh"
echo "3. Tạo bài viết với hình ảnh từ internet"
echo "4. Tạo bài viết hỗn hợp (nhiều chủ đề)"

echo
read -p "Nhập lựa chọn của bạn (1-4): " option

echo
read -p "Nhập tên người dùng để đăng bài: " username

case $option in
    1)
        python3 auto_post_generator.py "$username"
        ;;
    2)
        read -p "Nhập số lượng hình ảnh: " num_images
        python3 auto_post_generator.py "$username" --images "$num_images"
        ;;
    3)
        read -p "Nhập số lượng hình ảnh: " num_images
        python3 auto_post_generator.py "$username" --images "$num_images" --external
        ;;
    4)
        read -p "Nhập số lượng chủ đề/hình ảnh: " num_images
        python3 auto_post_generator.py "$username" --images "$num_images" --mixed
        ;;
    *)
        echo "Lựa chọn không hợp lệ."
        ;;
esac

echo
echo "Nhấn Enter để thoát..."
read 