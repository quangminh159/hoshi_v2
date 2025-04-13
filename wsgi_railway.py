"""
WSGI config cho Railway.

Nó hiển thị WSGI cho Django khi Web server chạy với cấu hình Railway.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_railway')

application = get_wsgi_application() 