#!/bin/bash
# Script sửa line endings cho tất cả file trong dự án

echo "===== ĐANG SỬA LINE ENDINGS CHO TẤT CẢ FILE ====="

# Kiểm tra xem dos2unix có được cài đặt hay không
if ! command -v dos2unix &> /dev/null; then
    echo "dos2unix không được cài đặt. Sử dụng sed để thay thế CRLF bằng LF."
    find . -type f -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/node_modules/*" -exec sed -i 's/\r$//' {} \;
else
    echo "Sử dụng dos2unix để chuyển đổi các file text sang LF..."
    # Chuyển đổi tất cả các file Python sang LF
    find . -name "*.py" -type f -exec dos2unix {} \;
    
    # Chuyển đổi các file khác sang LF
    find . -name "*.html" -type f -exec dos2unix {} \;
    find . -name "*.css" -type f -exec dos2unix {} \;
    find . -name "*.js" -type f -exec dos2unix {} \;
    find . -name "*.json" -type f -exec dos2unix {} \;
    find . -name "*.md" -type f -exec dos2unix {} \;
    find . -name "*.yml" -type f -exec dos2unix {} \;
    find . -name "*.yaml" -type f -exec dos2unix {} \;
    find . -name "*.sh" -type f -exec dos2unix {} \;
    find . -name "*.txt" -type f -exec dos2unix {} \;
fi

# Thêm quyền thực thi cho các file script
echo "Thêm quyền thực thi cho các file script..."
find . -name "*.sh" -type f -exec chmod +x {} \;
chmod +x app.py wsgi.py wsgi_render.py
chmod +x fix_socialaccount.py health_check.py build_files.sh

echo "===== HOÀN TẤT SỬA LINE ENDINGS =====" 