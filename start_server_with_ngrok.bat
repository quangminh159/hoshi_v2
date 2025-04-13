@echo off
echo === KHỞI ĐỘNG NGROK VÀ DJANGO SERVER ===

REM Kiểm tra xem ngrok đã được cài đặt chưa
if not exist ngrok.exe (
    echo Không tìm thấy ngrok.exe trong thư mục hiện tại.
    echo Vui lòng tải ngrok từ https://ngrok.com/download và giải nén vào thư mục này.
    pause
    exit /b
)

REM Chạy ngrok trong nền
start "Ngrok" ngrok http 8000
echo Đang khởi động ngrok...
timeout /t 5 /nobreak > nul

REM Chạy script cập nhật URL ngrok
echo Đang cập nhật cấu hình ngrok...
python auto_update_ngrok.py

REM Khởi động server Django
echo Đang khởi động Django server...
start "Django" python manage.py runserver 0.0.0.0:8000

echo.
echo === SERVER ĐANG CHẠY ===
echo Nhấn phím bất kỳ để dừng server và ngrok...
pause > nul

REM Dừng các process
taskkill /FI "WINDOWTITLE eq Ngrok*" /F
taskkill /FI "WINDOWTITLE eq Django*" /F

echo Đã dừng server và ngrok.
pause 