from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'notifications', api.NotificationViewSet, basename='notification')

app_name = 'notifications-api'

urlpatterns = [
    path('', include(router.urls)),
] 