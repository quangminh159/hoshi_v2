from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.utils import translation
from django.conf import settings as django_settings
import re
import uuid
from user_agents import parse
from .models import Device
from ipware import get_client_ip


class DebugOpenHostMiddleware:
    """
    Chỉ khi DEBUG=True: bỏ ép CSRF theo Origin/Referer.
    Để ĐT/PC vào bằng mọi IP hoặc ngrok mà không phải sửa .env mỗi lần.
    Production (DEBUG=False) không làm gì.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(django_settings, 'DEBUG', False):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)


class UserLanguageMiddleware(MiddlewareMixin):
    """Activate the authenticated user's preferred language and keep the language cookie in sync."""

    def process_request(self, request):
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return None

        lang = getattr(user, 'language', None) or django_settings.LANGUAGE_CODE
        supported = {code for code, _ in django_settings.LANGUAGES}
        if lang not in supported:
            lang = django_settings.LANGUAGE_CODE

        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        return None

    def process_response(self, request, response):
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return response

        lang = getattr(user, 'language', None)
        if not lang:
            return response

        cookie_name = django_settings.LANGUAGE_COOKIE_NAME
        if request.COOKIES.get(cookie_name) != lang:
            response.set_cookie(
                cookie_name,
                lang,
                max_age=getattr(django_settings, 'LANGUAGE_COOKIE_AGE', 60 * 60 * 24 * 365),
                path=getattr(django_settings, 'LANGUAGE_COOKIE_PATH', '/'),
                domain=getattr(django_settings, 'LANGUAGE_COOKIE_DOMAIN', None),
                secure=getattr(django_settings, 'LANGUAGE_COOKIE_SECURE', False),
                httponly=getattr(django_settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
                samesite=getattr(django_settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
            )
        return response

class AccountStatusMiddleware(MiddlewareMixin):
    """
    Middleware kiểm tra trạng thái tài khoản người dùng.
    Ngăn chặn người dùng bị đình chỉ hoặc bị xóa sử dụng hệ thống.
    """
    
    def is_exempt_url(self, path, user):
        """Các URL được miễn kiểm tra trạng thái tài khoản"""
        # Các URL công khai luôn được miễn
        exempt_paths = [
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/accounts/password/reset/',
            '/legal/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        # Kiểm tra các URL công khai
        for exempt_path in exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        # Admin luôn được miễn kiểm tra
        if user.is_staff or user.is_superuser:
            return True
            
        return False
    
    def process_request(self, request):
        """Xử lý yêu cầu trước khi nó được gửi đến view"""
        # Nếu người dùng không đăng nhập, bỏ qua
        if not request.user.is_authenticated:
            return None
            
        # Lấy đường dẫn hiện tại
        path = request.path
        
        # Nếu URL được miễn kiểm tra, bỏ qua
        if self.is_exempt_url(path, request.user):
            return None
            
        # Kiểm tra trạng thái tài khoản
        if hasattr(request.user, 'is_usable') and not request.user.is_usable():
            # Nếu đây là request API
            if path.startswith('/api/'):
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'Tài khoản của bạn đã bị đình chỉ hoặc bị xóa.',
                    'code': 'account_suspended'
                }, status=403)
            
            # Nếu người dùng bị đình chỉ, đăng xuất và chuyển hướng về trang đăng nhập
            if hasattr(request.user, 'is_suspended') and request.user.is_suspended:
                suspension_reason = getattr(request.user, 'suspension_reason', 'Vi phạm quy định của hệ thống')
                suspension_end_date = getattr(request.user, 'suspension_end_date', None)
                
                logout(request)
                
                message = f'Tài khoản của bạn đã bị đình chỉ. Lý do: {suspension_reason}.'
                if suspension_end_date:
                    message += f' Tài khoản sẽ được kích hoạt lại vào {suspension_end_date.strftime("%d/%m/%Y %H:%M")}.'
                
                messages.error(request, message)
                return redirect(reverse('account_login'))
            
            # Nếu người dùng bị xóa
            if hasattr(request.user, 'is_deleted') and request.user.is_deleted:
                logout(request)
                messages.error(
                    request, 
                    'Tài khoản của bạn đã bị xóa. Vui lòng liên hệ quản trị viên để biết thêm chi tiết.'
                )
                return redirect(reverse('account_login'))
        
        # Tài khoản bình thường, tiếp tục xử lý
        return None


class TwoFactorPendingMiddleware(MiddlewareMixin):
    """Force users with a pending 2FA challenge onto the verify page."""

    ALLOWED_PREFIXES = (
        '/users/verify-2fa-login/',
        '/accounts/logout/',
        '/accounts/login/',
        '/legal/',
        '/static/',
        '/media/',
        '/admin/',
    )

    def process_request(self, request):
        pending_id = request.session.get('pending_2fa_user_id')
        if not pending_id:
            return None

        path = request.path
        for prefix in self.ALLOWED_PREFIXES:
            if path.startswith(prefix):
                return None

        return redirect(reverse('accounts:verify_two_factor_login'))


class DeviceTrackingMiddleware(MiddlewareMixin):
    """
    Theo dõi thiết bị đăng nhập + vị trí theo IP (GPS cập nhật riêng từ client).
    Chỉ sync DB khi IP/UA đổi hoặc mỗi vài phút để tránh ghi liên tục.
    """

    SKIP_PREFIXES = (
        '/static/',
        '/media/',
        '/admin/jsi18n/',
        '/favicon',
    )

    def process_request(self, request):
        if not getattr(request.user, 'is_authenticated', False):
            return None

        path = request.path or ''
        for prefix in self.SKIP_PREFIXES:
            if path.startswith(prefix):
                return None

        user_agent_string = request.META.get('HTTP_USER_AGENT', '') or ''
        ua_l = user_agent_string.lower()
        if not user_agent_string or 'bot' in ua_l or 'crawl' in ua_l or 'spider' in ua_l:
            return None

        try:
            client_ip, _routable = get_client_ip(request)
            if not client_ip:
                client_ip = request.META.get('REMOTE_ADDR') or '0.0.0.0'

            user_agent = parse(user_agent_string)
            if user_agent.is_mobile:
                device_type = 'mobile'
            elif user_agent.is_tablet:
                device_type = 'tablet'
            else:
                device_type = 'desktop'

            device_id = request.session.get('device_id')
            if not device_id:
                device_id = str(uuid.uuid4())
                request.session['device_id'] = device_id

            browser_family = user_agent.browser.family
            os_family = user_agent.os.family
            device_family = user_agent.device.family
            device_name = device_family
            if device_family in ('Other', 'Generic Smartphone', 'Generic Feature Phone'):
                device_name = f'{os_family} Device' if os_family else 'Thiết bị'

            browser = f'{browser_family} {user_agent.browser.version_string}'.strip()
            os_name = f'{os_family} {user_agent.os.version_string}'.strip()

            device = Device.objects.filter(device_id=device_id).first()
            created = False
            ip_changed = False
            if device is None:
                Device.objects.filter(user=request.user, is_current=True).update(is_current=False)
                device = Device.objects.create(
                    user=request.user,
                    device_id=device_id,
                    device_type=device_type,
                    device_name=device_name[:255],
                    browser=browser[:100],
                    os=os_name[:100],
                    ip_address=client_ip,
                    is_current=True,
                )
                created = True
                ip_changed = True
            else:
                if device.user_id != request.user.id:
                    Device.objects.filter(user=request.user, is_current=True).update(is_current=False)
                    device.user = request.user
                    device.is_current = True
                    created = True

                ip_changed = device.ip_address != client_ip
                changed = (
                    created
                    or ip_changed
                    or device.browser != browser[:100]
                    or device.os != os_name[:100]
                    or not device.is_current
                )
                if changed:
                    Device.objects.filter(user=request.user, is_current=True).exclude(pk=device.pk).update(
                        is_current=False
                    )
                    device.ip_address = client_ip
                    device.browser = browser[:100]
                    device.os = os_name[:100]
                    device.device_type = device_type
                    device.device_name = device_name[:255]
                    device.is_current = True
                    device.save(
                        update_fields=[
                            'user',
                            'ip_address',
                            'browser',
                            'os',
                            'device_type',
                            'device_name',
                            'is_current',
                            'last_active',
                        ]
                    )
                else:
                    from django.core.cache import cache

                    touch_key = f'device:touch:{device.pk}'
                    if not cache.get(touch_key):
                        device.save(update_fields=['last_active'])
                        cache.set(touch_key, 1, timeout=180)

            # Geo theo IP (không ghi đè GPS còn mới)
            from django.core.cache import cache
            from .geo import lookup_ip_location

            geo_key = f'device:geodone:{device.pk}:{client_ip}'
            need_geo = (
                not cache.get(geo_key)
                and device.location_source != 'gps'
                and (created or ip_changed or not device.location_label)
            )
            if need_geo:
                geo = lookup_ip_location(client_ip)
                if geo:
                    device.apply_location(
                        label=geo.get('label') or '',
                        city=geo.get('city') or '',
                        region=geo.get('region') or '',
                        country=geo.get('country') or '',
                        country_code=geo.get('country_code') or '',
                        latitude=geo.get('lat'),
                        longitude=geo.get('lon'),
                        accuracy_m=geo.get('accuracy_m'),
                        source='ip',
                    )
                    device.save(
                        update_fields=[
                            'location_label',
                            'city',
                            'region',
                            'country',
                            'country_code',
                            'latitude',
                            'longitude',
                            'location_accuracy_m',
                            'location_source',
                            'location_updated_at',
                        ]
                    )
                cache.set(geo_key, 1, timeout=6 * 60 * 60)

            request.current_device = device
        except Exception:
            pass

        return None
