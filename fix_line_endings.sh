#!/bin/bash
# Script để chuyển đổi ký tự kết thúc dòng sang LF cho các file Python

echo "===== ĐANG SỬA KÝ TỰ KẾT THÚC DÒNG CHO CÁC FILE ====="

# Thiết lập Git để sử dụng LF
echo "Thiết lập Git config..."
git config core.autocrlf false
git config core.eol lf

# Tạo file .gitattributes
echo "Tạo file .gitattributes..."
cat > .gitattributes << 'EOL'
# Set default behavior to automatically normalize line endings
* text=auto eol=lf

# Explicitly declare text files to be normalized
*.py text eol=lf
*.html text eol=lf
*.css text eol=lf
*.js text eol=lf
*.json text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.sh text eol=lf

# Files that will always have CRLF line endings on checkout
*.bat text eol=crlf
*.cmd text eol=crlf
*.ps1 text eol=crlf

# Binary files
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
EOL

# Chuyển đổi các file Python sang LF
echo "Chuyển đổi các file Python sang LF..."
find . -name "*.py" -type f -exec dos2unix {} \;

# Chuyển đổi các file shell script sang LF
echo "Chuyển đổi các file shell script sang LF..."
find . -name "*.sh" -type f -exec dos2unix {} \;

# Thêm quyền thực thi cho các file script
echo "Thêm quyền thực thi cho các file script..."
chmod +x *.sh
chmod +x app.py
chmod +x fix_socialaccount.py
chmod +x patch_socialaccount.py

echo "===== HOÀN TẤT ====="
echo "Đã sửa ký tự kết thúc dòng và thêm quyền thực thi."
echo "Để áp dụng thay đổi vào Git, chạy: git add . && git commit -m 'Fix line endings'" 