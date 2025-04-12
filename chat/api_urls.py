from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'conversations', api.ConversationViewSet, basename='conversation')
router.register(r'messages', api.MessageViewSet, basename='message')

app_name = 'chat_api'

urlpatterns = [
    path('', include(router.urls)),
]