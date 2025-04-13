"""
WSGI config cho Render.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')

application = get_wsgi_application() 