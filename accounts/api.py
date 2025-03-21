from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Device, DataDownloadRequest
from .serializers import (
    UserSerializer,
    DeviceSerializer,
    DataDownloadRequestSerializer,
    UserSettingsSerializer,
    ChangePasswordSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def settings(self, request):
        user = request.user
        serializer = UserSettingsSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': 'Mật khẩu hiện tại không chính xác.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data['new_password1'])
            user.save()
            return Response({'status': 'Mật khẩu đã được thay đổi'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Device.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        device = self.get_object()
        if device.is_current:
            return Response(
                {'error': 'Không thể đăng xuất khỏi thiết bị hiện tại'},
                status=status.HTTP_400_BAD_REQUEST
            )
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DataDownloadRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DataDownloadRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DataDownloadRequest.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def request_download(self, request):
        # Kiểm tra yêu cầu đang xử lý
        if DataDownloadRequest.objects.filter(
            user=request.user,
            status='pending',
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).exists():
            return Response(
                {'error': 'Bạn đã có một yêu cầu đang được xử lý'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 