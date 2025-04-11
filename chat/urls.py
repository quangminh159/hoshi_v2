from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api
from . import views

router = DefaultRouter()
router.register(r'conversations', api.ConversationViewSet, basename='conversation')
router.register(r'messages', api.MessageViewSet, basename='message')

app_name = 'chat'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Chat UI views
    path('', views.chat_home, name='home'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('direct/<str:username>/', views.direct_chat, name='direct_chat'),
    path('start-conversation/', views.start_conversation, name='start_conversation'),
] 