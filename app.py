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

# Khởi tạo Django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')
    django.setup()
    logger.info("Đã khởi tạo Django với settings_render")
except Exception as e:
    logger.error(f"Lỗi khi khởi tạo Django: {e}")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
        django.setup()
        logger.info("Đã khởi tạo Django với settings mặc định")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Django với settings mặc định: {e}")
        raise

# Sửa lỗi SocialApp trùng lặp
logger.info("Kiểm tra và sửa lỗi SocialApp trùng lặp")
run_command([sys.executable, "fix_socialaccount.py"])

# Thu thập static files
logger.info("Thu thập static files...")
try:
    from django.core.management import call_command
    call_command('collectstatic', '--noinput')
    logger.info("Đã thu thập static files thành công")
except Exception as e:
    logger.error(f"Lỗi khi thu thập static files: {e}")

# Áp dụng migrations
logger.info("Áp dụng migrations...")
try:
    call_command('migrate', '--noinput')
    logger.info("Đã áp dụng migrations thành công")
except Exception as e:
    logger.error(f"Lỗi khi áp dụng migrations: {e}")

# Khởi động ứng dụng với Gunicorn
logger.info("Khởi động ứng dụng với Gunicorn...")

port = int(os.environ.get('PORT', 8000))
workers = int(os.environ.get('WEB_CONCURRENCY', 3))

from gunicorn.app.wsgiapp import WSGIApplication

class HoshiApplication(WSGIApplication):
    def __init__(self, app_uri, options=None):
        self.options = options or {}
        self.app_uri = app_uri
        super().__init__()

    def load_config(self):
        config = {
            'bind': f'0.0.0.0:{port}',
            'workers': workers,
            'accesslog': '-',
            'errorlog': '-',
            'capture_output': True,
            'loglevel': 'info',
            'preload_app': True
        }
        
        for key, value in config.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key, value)

if __name__ == '__main__':
    try:
        HoshiApplication('hoshi.wsgi').run()
    except Exception as e:
        logger.error(f"Lỗi khi khởi động Gunicorn: {e}")
        raise

logger.info("===== KHỞI ĐỘNG HOÀN TẤT =====")