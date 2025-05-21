from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
import re
import uuid
from user_agents import parse
from .models import Device
from ipware import get_client_ip

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

class DeviceTrackingMiddleware(MiddlewareMixin):
    """
    Middleware theo dõi thiết bị đăng nhập của người dùng.
    Mỗi khi người dùng đăng nhập, middleware sẽ tạo một bản ghi thiết bị mới hoặc cập nhật bản ghi hiện có.
    """
    
    def process_request(self, request):
        # Chỉ xử lý cho người dùng đã đăng nhập
        if not request.user.is_authenticated:
            return None
            
        # Lấy User-Agent và IP
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        client_ip = request.META.get('REMOTE_ADDR', '')
        
        # Bỏ qua bots và crawlers
        if not user_agent_string or 'bot' in user_agent_string.lower() or 'crawl' in user_agent_string.lower():
            return None
            
        try:
            # Parse User-Agent
            user_agent = parse(user_agent_string)
            
            # Xác định loại thiết bị
            if user_agent.is_mobile:
                device_type = 'mobile'
            elif user_agent.is_tablet:
                device_type = 'tablet'
            else:
                device_type = 'desktop'
                
            # Tạo device ID duy nhất hoặc lấy từ session
            device_id = request.session.get('device_id')
            if not device_id:
                device_id = str(uuid.uuid4())
                request.session['device_id'] = device_id
                
            # Tạo tên thiết bị
            browser_family = user_agent.browser.family
            os_family = user_agent.os.family
            device_family = user_agent.device.family
            
            device_name = f"{device_family}"
            if device_family == "Other" or device_family == "Generic Smartphone":
                device_name = f"{os_family} Device"
                
            # Lấy thông tin trình duyệt và hệ điều hành
            browser = f"{browser_family} {user_agent.browser.version_string}"
            os = f"{os_family} {user_agent.os.version_string}"
            
            # Cập nhật hoặc tạo bản ghi thiết bị
            try:
                device = Device.objects.get(device_id=device_id)
                # Cập nhật thông tin thiết bị nếu có thay đổi
                device.ip_address = client_ip
                device.browser = browser
                device.os = os
                device.save(update_fields=['ip_address', 'browser', 'os', 'last_active'])
            except Device.DoesNotExist:
                # Đánh dấu tất cả thiết bị hiện tại là không phải hiện tại
                Device.objects.filter(user=request.user, is_current=True).update(is_current=False)
                
                # Tạo bản ghi thiết bị mới
                Device.objects.create(
                    user=request.user,
                    device_id=device_id,
                    device_type=device_type,
                    device_name=device_name,
                    browser=browser,
                    os=os,
                    ip_address=client_ip,
                    is_current=True
                )
        except Exception:
            # Lỗi khi phân tích User-Agent hoặc lưu thiết bị, bỏ qua
            pass
            
        return None 