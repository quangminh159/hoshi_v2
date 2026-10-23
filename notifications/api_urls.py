from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'notifications', api.NotificationViewSet, basename='notification')

app_name = 'notifications-api'

urlpatterns = [
    path('subscribe/', api.subscribe_webpush, name='webpush_subscribe'),
    path('unsubscribe/', api.unsubscribe_webpush, name='webpush_unsubscribe'),
    path('', include(router.urls)),
] 