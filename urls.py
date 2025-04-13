from django.http import JsonResponse
from django.urls import path, include

# Health check view đơn giản cho Render
def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    # Điểm cuối kiểm tra sức khỏe cho Render
    path('health/', health_check, name='health_check'),
    
    # Bao gồm các URL từ hoshi.urls
    path('', include('hoshi.urls')),
]