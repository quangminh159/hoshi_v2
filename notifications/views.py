from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
from .models import Notification
from django.db.models import Count

@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Sắp xếp và phân trang
    notifications = notifications.order_by('-created_at')
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notifications': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'notifications/notifications.html', context)

@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@login_required
def mark_all_as_read(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Có thể lọc theo loại thông báo
    notification_type = request.POST.get('type')
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    )
    
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Cập nhật tất cả các thông báo chưa đọc thành đã đọc
    notifications.update(is_read=True)
    
    return JsonResponse({
        'status': 'success', 
        'count': notifications.count()
    })

@login_required
def delete_notification(request, notification_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    notification.delete()
    
    return JsonResponse({'status': 'success'})

@login_required
def delete_all_notifications(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Có thể lọc theo loại thông báo
    notification_type = request.POST.get('type')
    notifications = Notification.objects.filter(recipient=request.user)
    
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    notifications.delete()
    
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_count(request):
    """
    Lấy số lượng thông báo chưa đọc
    """
    unread_count = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).count()
    
    return JsonResponse({
        'unread_count': unread_count
    }) 