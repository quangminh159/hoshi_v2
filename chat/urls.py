from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('<int:room_id>/', views.room_detail, name='room_detail'),
    path('create/', views.create_room, name='create_room'),
    path('<int:room_id>/send/', views.send_message, name='send_message'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('search/', views.search_users, name='search_users'),
    
    # Chức năng mới
    path('<int:room_id>/vanish-mode/toggle/', views.toggle_vanish_mode, name='toggle_vanish_mode'),
    path('message/<int:message_id>/read/', views.mark_message_as_read, name='mark_message_as_read'),
    path('message/<int:message_id>/react/', views.react_to_message, name='react_to_message'),
    path('<int:room_id>/accept/', views.accept_chat_request, name='accept_chat_request'),
    path('<int:room_id>/decline/', views.decline_chat_request, name='decline_chat_request'),
    path('<int:room_id>/mute/toggle/', views.toggle_mute, name='toggle_mute'),
    path('<int:room_id>/messages/', views.get_new_messages, name='get_new_messages'),
] 