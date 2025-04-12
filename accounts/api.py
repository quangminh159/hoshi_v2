from rest_framework import viewsets, generics, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Device, DataDownloadRequest, UserFollowing
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

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        user_to_follow = self.get_object()
        
        # Không cho phép follow chính mình
        if user_to_follow == request.user:
            return Response(
                {'error': 'Bạn không thể theo dõi chính mình'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Kiểm tra xem đã follow chưa
        follow_relationship, created = UserFollowing.objects.get_or_create(
            user=request.user,
            following_user=user_to_follow
        )
        
        if not created:
            # Đã follow trước đó, xóa mối quan hệ (unfollow)
            follow_relationship.delete()
            return Response({'status': 'unfollowed'})
            
        # Cập nhật số lượng follower
        return Response({'status': 'following'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_user(request, username, *args, **kwargs):
    """API endpoint để theo dõi người dùng khác"""
    try:
        user_to_follow = User.objects.get(username=username)
        
        # Không cho phép follow chính mình
        if user_to_follow == request.user:
            return Response(
                {'error': 'Bạn không thể theo dõi chính mình'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Kiểm tra xem đã follow chưa
        follow_relationship, created = UserFollowing.objects.get_or_create(
            user=request.user,
            following_user=user_to_follow
        )
        
        if not created:
            # Đã follow trước đó, xóa mối quan hệ (unfollow)
            follow_relationship.delete()
            return Response({'status': 'unfollowed'})
            
        # Đã follow thành công
        return Response({'status': 'following'})
        
    except User.DoesNotExist:
        return Response(
            {'error': 'Không tìm thấy người dùng'}, 
            status=status.HTTP_404_NOT_FOUND
        )

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

@api_view(['GET'])
def user_suggestions(request):
    """API endpoint để cung cấp gợi ý người dùng khi nhập @"""
    query = request.GET.get('q', '')
    
    # Chỉ hiển thị người dùng khi đã đăng nhập
    if request.user.is_authenticated:
        # Tìm kiếm chỉ trong những người mà user đang follow
        following_users = User.objects.filter(
            followers_relationships__user=request.user,
            username__istartswith=query
        ).order_by('username')[:10]
        
        # Chuyển đổi thành dạng JSON
        result = []
        for user in following_users:
            result.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': user.get_avatar_url(),
                'full_name': f"{user.first_name} {user.last_name}".strip()
            })
    else:
        # Nếu chưa đăng nhập, trả về danh sách trống
        result = []
    
    return Response(result)

@api_view(['GET'])
def hashtag_suggestions(request):
    """API endpoint để cung cấp gợi ý hashtag khi nhập #"""
    query = request.GET.get('q', '')
    
    # Import và sử dụng mô hình Hashtag từ ứng dụng Posts
    from posts.models import Hashtag
    
    # Tìm kiếm hashtag dựa trên query
    hashtags = Hashtag.objects.filter(name__istartswith=query).order_by('-posts_count')[:10]
    
    # Chuyển đổi thành dạng danh sách đơn giản
    result = [hashtag.name for hashtag in hashtags]
    
    return Response(result) 