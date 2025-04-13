"""
Entry point cho Render
Tệp này được sử dụng làm entry point cho nền tảng Render.
"""

import os
import sys
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info("===== KHỞI ĐỘNG ỨNG DỤNG TRÊN RENDER =====")
logger.info("Phiên bản Python: %s", sys.version)

# Cấu hình môi trường trước khi import
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')
logger.info("DJANGO_SETTINGS_MODULE = %s", os.environ.get('DJANGO_SETTINGS_MODULE'))
logger.info("Thư mục hiện tại: %s", os.getcwd())

# Đảm bảo các package cần thiết được cài đặt
required_packages = {
    'dj_database_url': 'dj-database-url==2.1.0',
    'decouple': 'python-decouple==3.8',
    'crispy_bootstrap5': 'crispy-bootstrap5==2022.1',
    'crispy_forms': 'django-crispy-forms==2.1',
    'whitenoise': 'whitenoise==6.6.0',
    'dotenv': 'python-dotenv==1.0.1'
}

for module_name, package_name in required_packages.items():
    try:
        __import__(module_name)
        logger.info("✓ Package %s đã được cài đặt", module_name)
    except ImportError:
        logger.warning("Package %s không được tìm thấy, đang cài đặt...", module_name)
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            logger.info("✓ Đã cài đặt %s thành công", package_name)
        except Exception as e:
            logger.error("Không thể cài đặt %s: %s", package_name, e)

# Import sau khi cài đặt package
try:
    from django.core.wsgi import get_wsgi_application
    
    # Tạo ứng dụng WSGI
    application = get_wsgi_application()
    app = application  # Alias cho Render
    logger.info("✓ WSGI application đã khởi tạo thành công")
    
except Exception as e:
    logger.error("Lỗi khi tạo WSGI application: %s", e)
    import traceback
    logger.error(traceback.format_exc())
    raise

logger.info("===== KHỞI ĐỘNG HOÀN TẤT =====") 