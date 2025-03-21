from django.urls import path, include
from rest_framework_nested import routers
from . import api

router = routers.DefaultRouter()
router.register(r'rooms', api.ChatRoomViewSet, basename='room')

rooms_router = routers.NestedDefaultRouter(router, r'rooms', lookup='room')
rooms_router.register(r'messages', api.MessageViewSet, basename='room-messages')

app_name = 'chat-api'

urlpatterns = [
    path('', include(router.urls)),
    path('', include(rooms_router.urls)),
] 