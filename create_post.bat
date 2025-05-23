@echo off
rem Tool tạo bài viết tự động cho Hoshi
rem Tác giả: Claude AI 3.7 Sonnet

title Tool tạo bài viết tự động cho Hoshi

echo ================================================
echo         Tool tạo bài viết tự động cho Hoshi
echo ================================================
echo.

rem Kiểm tra Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Lỗi] Không tìm thấy Python. Vui lòng cài đặt Python và thử lại.
    goto end
)

rem Kiểm tra PIL
python -c "import PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Cảnh báo] Thư viện PIL (Pillow) chưa được cài đặt.
    echo Đang cài đặt Pillow...
    pip install Pillow
)

rem Kiểm tra requests
python -c "import requests" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Cảnh báo] Thư viện requests chưa được cài đặt.
    echo Đang cài đặt requests...
    pip install requests
)

echo.
echo 1. Tạo bài viết đơn giản với 1 hình ảnh
echo 2. Tạo bài viết với nhiều hình ảnh
echo 3. Tạo bài viết với hình ảnh từ internet
echo 4. Tạo bài viết hỗn hợp (nhiều chủ đề)

echo.
set /p option=Nhập lựa chọn của bạn (1-4): 

echo.
set /p username=Nhập tên người dùng để đăng bài: 

if "%option%"=="1" (
    python auto_post_generator.py %username%
) else if "%option%"=="2" (
    set /p num_images=Nhập số lượng hình ảnh: 
    python auto_post_generator.py %username% --images %num_images%
) else if "%option%"=="3" (
    set /p num_images=Nhập số lượng hình ảnh: 
    python auto_post_generator.py %username% --images %num_images% --external
) else if "%option%"=="4" (
    set /p num_images=Nhập số lượng chủ đề/hình ảnh: 
    python auto_post_generator.py %username% --images %num_images% --mixed
) else (
    echo Lựa chọn không hợp lệ.
)

:end
echo.
echo Nhấn phím bất kỳ để thoát...
pause > nul 