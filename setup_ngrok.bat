@echo off
echo === THIẾT LẬP NGROK ===
echo.

REM Kiểm tra xem ngrok.exe đã tồn tại chưa
if not exist ngrok.exe (
  echo Không tìm thấy ngrok.exe!
  echo Vui lòng tải ngrok từ https://ngrok.com/download và giải nén vào thư mục này.
  pause
  exit /b
)

echo Hãy nhập authtoken của bạn (lấy từ https://dashboard.ngrok.com/get-started/your-authtoken)
set /p AUTHTOKEN="Authtoken: "

echo.
echo Đang cấu hình ngrok...
ngrok config add-authtoken %AUTHTOKEN%

echo.
echo Authtoken đã được thêm thành công!
echo.
echo Bây giờ ngrok sẽ tạo tunnel cho server Django của bạn.
echo Nhấn Ctrl+C để dừng ngrok khi bạn muốn kết thúc.
echo.

REM Chạy ngrok HTTP tunnel
ngrok http 8000

pause 