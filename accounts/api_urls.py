from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'users', api.UserViewSet)
router.register(r'devices', api.DeviceViewSet, basename='device')
router.register(r'data-requests', api.DataDownloadRequestViewSet, basename='data-request')

app_name = 'accounts-api'

urlpatterns = [
    path('', include(router.urls)),
] 