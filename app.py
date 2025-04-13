"""
Entry point cho Render
Tệp này được sử dụng làm entry point cho nền tảng Render.
"""

import os
import sys
import logging
import subprocess
import time

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

logger.info("===== KHỞI ĐỘNG ỨNG DỤNG DJANGO TRÊN RENDER =====")

try:
    import django
    logger.info(f"Đã import Django {django.get_version()}")
except ImportError:
    logger.error("Không thể import Django. Kiểm tra cài đặt.")
    sys.exit(1)

# Khởi tạo Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')
try:
    django.setup()
    logger.info("Đã khởi tạo Django với settings_render")
except Exception as e:
    logger.error(f"Lỗi khi khởi tạo Django với settings_render: {e}")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
        django.setup()
        logger.info("Đã khởi tạo Django với settings mặc định")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Django với settings mặc định: {e}")
        raise

def run_command(command):
    """Chạy một lệnh shell và hiển thị output."""
    logger.info(f"Chạy lệnh: {' '.join(command)}")
    try:
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in process.stdout:
            print(line.strip())
            
        process.wait()
        return process.returncode
    except Exception as e:
        logger.error(f"Lỗi khi chạy lệnh {' '.join(command)}: {e}")
        return -1

# Sửa lỗi SocialApp trùng lặp nếu file tồn tại
if os.path.exists("fix_socialaccount.py"):
    logger.info("Kiểm tra và sửa lỗi SocialApp trùng lặp")
    run_command([sys.executable, "fix_socialaccount.py"])
else:
    logger.warning("Không tìm thấy fix_socialaccount.py, bỏ qua bước sửa lỗi SocialApp")

# Tạo ứng dụng WSGI để Gunicorn có thể sử dụng
try:
    from django.core.wsgi import get_wsgi_application
    app = get_wsgi_application()  # Đây là biến mà Gunicorn sẽ tìm kiếm
    logger.info("Đã tạo WSGI application thành công")
except Exception as e:
    logger.error(f"Lỗi khi tạo WSGI application: {e}")
    raise

# Nếu chạy trực tiếp file này
if __name__ == '__main__':
    logger.info("Chạy ứng dụng thông qua file app.py")
    # Thu thập static files
    try:
        from django.core.management import call_command
        call_command('collectstatic', '--noinput')
        logger.info("Đã thu thập static files thành công")
    except Exception as e:
        logger.error(f"Lỗi khi thu thập static files: {e}")

    # Áp dụng migrations
    try:
        call_command('migrate', '--noinput')
        logger.info("Đã áp dụng migrations thành công")
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng migrations: {e}")
    
    # Khởi động server
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Khởi động server tại cổng {port}...")
    try:
        call_command('runserver', f"0.0.0.0:{port}")
    except KeyboardInterrupt:
        logger.info("Đã nhận lệnh dừng server")
    except Exception as e:
        logger.error(f"Lỗi khi khởi động server: {e}")

logger.info("===== KHỞI ĐỘNG HOÀN TẤT =====")