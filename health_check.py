#!/usr/bin/env python
"""
Module cung cấp health check cho Render.
Đây là endpoint "/health/" được sử dụng bởi Render để kiểm tra trạng thái ứng dụng.
"""

import os
import sys
import logging
import django

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_health_view(request):
    """
    View đơn giản trả về 200 OK để chỉ ra rằng ứng dụng đang hoạt động.
    """
    from django.http import JsonResponse
    return JsonResponse({'status': 'ok'})

def add_health_url():
    """
    Thêm health check URL vào URLconf của Django.
    """
    try:
        # Thiết lập Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')
        django.setup()
        
        # Thêm URL pattern cho health check
        from django.urls import path
        from django.urls import get_resolver
        
        # Lấy URL resolver hiện tại
        resolver = get_resolver()
        
        # Kiểm tra xem URL pattern đã tồn tại chưa
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'pattern') and '/health/' in str(pattern.pattern):
                logger.info("Health check URL đã tồn tại.")
                return True
        
        # Nếu chưa tồn tại, thêm vào
        from django.conf import settings
        from django.urls import include
        
        # Lấy ROOT_URLCONF
        root_urlconf = settings.ROOT_URLCONF
        
        # Import URLconf
        urlconf_module = __import__(root_urlconf, {}, {}, [''])
        
        # Thêm health check URL
        urlconf_module.urlpatterns.append(
            path('health/', get_health_view, name='health_check')
        )
        
        logger.info("Đã thêm health check URL.")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi thêm health check URL: {e}")
        return False

if __name__ == "__main__":
    if add_health_url():
        print("Health check URL đã được thêm thành công.")
    else:
        print("Không thể thêm health check URL.")