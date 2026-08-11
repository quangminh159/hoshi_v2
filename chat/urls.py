from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Chat UI views
    path('', views.chat_home, name='home'),
    path('call/', views.call_window, name='call_window'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('message-requests/', views.message_requests, name='message_requests'),
    path('message-requests/<int:conversation_id>/accept/', views.accept_message_request_view, name='accept_message_request'),
    path('message-requests/<int:conversation_id>/decline/', views.decline_message_request_view, name='decline_message_request'),
    path('conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversations/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('upload_attachment/<int:conversation_id>/', views.upload_attachment, name='upload_attachment'),
    path('start/', views.start_conversation, name='start_conversation'),
    path('group/create/', views.create_group, name='create_group'),
    path('conversations/<int:conversation_id>/leave/', views.leave_group, name='leave_group'),
    path('conversations/<int:conversation_id>/rename/', views.rename_group, name='rename_group'),
    path('conversations/<int:conversation_id>/avatar/', views.update_group_avatar, name='update_group_avatar'),
    path('conversations/<int:conversation_id>/add-members/', views.add_group_members, name='add_group_members'),
    path('conversations/<int:conversation_id>/set-admin/', views.set_group_admin, name='set_group_admin'),
    path('conversations/<int:conversation_id>/kick/', views.kick_group_member, name='kick_group_member'),
    path('direct/<str:username>/', views.direct_chat, name='direct_chat'),
    path('delete/<int:conversation_id>/', views.delete_conversation, name='delete_conversation'),
    
    # Giao diện chat mới
    path('new/', views.new_chat, name='new_chat'),
    path('new/<int:conversation_id>/', views.new_chat, name='new_chat_detail'),
    
    # API endpoints
    path('api/online-users/', views.api_online_users, name='api_online_users'),
    path('api/online-users/<int:id>/', views.api_online_users, name='api_online_users_by_id'),
    path('api/chat-messages/<int:id>/', views.api_chat_messages, name='api_chat_messages'),
    path('api/unread/', views.api_unread, name='api_unread'),
    path('api/unread-total/', views.api_unread_total, name='api_unread_total'),
    path('api/link-preview/', views.api_link_preview, name='api_link_preview'),
    path('api/ice-servers/', views.api_ice_servers, name='api_ice_servers'),
    path('api/conversations/<int:conversation_id>/search/', views.api_search_messages, name='api_search_messages'),
]