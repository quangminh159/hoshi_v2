"""
WSGI config cho ứng dụng Hoshi.
"""

import os
import sys
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

logger.info("===== KHỞI TẠO WSGI APPLICATION =====")

# Thiết lập môi trường Django
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')
    logger.info("Đã thiết lập DJANGO_SETTINGS_MODULE = hoshi.settings_render")
except Exception as e:
    logger.error(f"Lỗi khi thiết lập DJANGO_SETTINGS_MODULE: {e}")
    raise

# Import WSGI application từ Django
try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    logger.info("Đã tạo WSGI application thành công")
except Exception as e:
    logger.error(f"Lỗi khi tạo WSGI application: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise

# Tạo alias cho Render
app = application