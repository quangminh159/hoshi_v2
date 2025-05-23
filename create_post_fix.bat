@echo off
rem Tool tao bai viet tu dong cho Hoshi
rem Tac gia: Claude AI 3.7 Sonnet

title Tool tao bai viet tu dong cho Hoshi

echo ================================================
echo         Tool tao bai viet tu dong cho Hoshi
echo ================================================
echo.

rem Kiem tra Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Loi] Khong tim thay Python. Vui long cai dat Python va thu lai.
    goto end
)

rem Kiem tra PIL
python -c "import PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Canh bao] Thu vien PIL (Pillow) chua duoc cai dat.
    echo Dang cai dat Pillow...
    pip install Pillow
)

rem Kiem tra requests
python -c "import requests" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Canh bao] Thu vien requests chua duoc cai dat.
    echo Dang cai dat requests...
    pip install requests
)

echo.
echo 1. Tao bai viet don gian voi 1 hinh anh
echo 2. Tao bai viet voi nhieu hinh anh
echo 3. Tao bai viet voi hinh anh tu internet
echo 4. Tao bai viet hon hop (nhieu chu de)

echo.
set /p option=Nhap lua chon cua ban (1-4): 

echo.
set /p username=Nhap ten nguoi dung de dang bai: 

if "%option%"=="1" (
    python auto_post_generator.py %username%
) else if "%option%"=="2" (
    set /p num_images=Nhap so luong hinh anh: 
    python auto_post_generator.py %username% --images %num_images%
) else if "%option%"=="3" (
    set /p num_images=Nhap so luong hinh anh: 
    python auto_post_generator.py %username% --images %num_images% --external
) else if "%option%"=="4" (
    set /p num_images=Nhap so luong chu de/hinh anh: 
    python auto_post_generator.py %username% --images %num_images% --mixed
) else (
    echo Lua chon khong hop le.
)

:end
echo.
echo Nhan phim bat ky de thoat...
pause > nul 