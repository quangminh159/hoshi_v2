from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Chat UI views
    path('', views.chat_home, name='home'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversations/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('upload_attachment/<int:conversation_id>/', views.upload_attachment, name='upload_attachment'),
    path('start/', views.start_conversation, name='start_conversation'),
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
]