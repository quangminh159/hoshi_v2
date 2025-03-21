from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_list, name='list'),
    path('<int:notification_id>/mark-as-read/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-as-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),
    path('delete-all/', views.delete_all_notifications, name='delete_all'),
    path('unread-count/', views.get_unread_count, name='unread_count'),
] 