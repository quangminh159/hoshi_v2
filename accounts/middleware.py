from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin

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