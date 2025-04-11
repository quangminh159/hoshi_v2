@echo off
echo ====================================
echo Hoshi Chat Server Starter
echo ====================================

:: Kiểm tra xem venv có tồn tại không
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Kích hoạt môi trường ảo
call venv\Scripts\activate

:: Kiểm tra và cài đặt các gói cần thiết
echo Checking and installing required packages...
pip install -r requirements.txt

:: Khởi động Redis server nếu chưa chạy (nếu có Redis cài đặt trên Windows)
where redis-server >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Starting Redis server...
    start /B redis-server
) else (
    echo Redis server not found. Using in-memory channel layer...
)

:: Mở một terminal mới để chạy Django
echo Starting Django server in a new window...
start cmd /k "call venv\Scripts\activate && python manage.py runserver"

:: Chạy Daphne
echo Starting Daphne server...
python run_chat_server.py

pause 