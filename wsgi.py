"""
WSGI config điểm vào chung cho ứng dụng.
Sẽ import WSGI config đúng tùy vào môi trường.
"""

import os
import sys

# Thử import từ wsgi_render trước (cho môi trường Render)
try:
    from wsgi_render import app, application
    print("Đã load WSGI config cho Render")
# Nếu không thành công, thử import từ hoshi.wsgi (môi trường local)
except ImportError:
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()
        app = application  # Thêm alias app cho Render
        print("Đã load WSGI config từ hoshi.settings")
    except ImportError:
        print("Không thể import WSGI config")
        raise 