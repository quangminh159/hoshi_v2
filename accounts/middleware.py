from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

class SuspensionMiddleware:
    """
    Middleware kiểm tra tài khoản bị đình chỉ khi người dùng đăng nhập
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Kiểm tra trạng thái đình chỉ chỉ khi người dùng đã đăng nhập
        if request.user.is_authenticated:
            # Kiểm tra trạng thái đình chỉ
            is_suspended = request.user.check_suspension_status()
            
            # Nếu tài khoản bị đình chỉ, chuyển hướng đến trang thông báo
            if is_suspended:
                # Danh sách các đường dẫn được phép truy cập khi bị đình chỉ
                allowed_paths = [
                    reverse('accounts:suspension_notice'),
                    reverse('accounts:logout'),
                    '/admin/',  # Cho phép admin truy cập
                ]
                
                # Kiểm tra xem đường dẫn hiện tại có được phép không
                current_path = request.path_info
                if not any(current_path.startswith(path) for path in allowed_paths):
                    messages.error(
                        request, 
                        f'Tài khoản của bạn đã bị đình chỉ cho đến {request.user.suspension_end_date.strftime("%d/%m/%Y %H:%M")} '
                        f'với lý do: {request.user.suspension_reason}'
                    )
                    return redirect('accounts:suspension_notice')
                    
        response = self.get_response(request)
        return response 