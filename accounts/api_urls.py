from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from . import api
from .models import UserFollowing

router = DefaultRouter()
router.register(r'users', api.UserViewSet)
router.register(r'devices', api.DeviceViewSet, basename='device')
router.register(r'data-requests', api.DataDownloadRequestViewSet, basename='data-request')

User = get_user_model()

class FollowUserView(APIView):
    """API để theo dõi một người dùng"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, username):
        try:
            user_to_follow = User.objects.get(username=username)
            
            # Không cho phép follow chính mình
            if user_to_follow == request.user:
                return Response(
                    {'error': 'Bạn không thể theo dõi chính mình'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Kiểm tra xem đã follow chưa
            existing_follow = UserFollowing.objects.filter(
                user=request.user,
                following_user=user_to_follow
            ).exists()
            
            if existing_follow:
                # Đã follow trước đó, trả về thông báo lỗi
                return Response({
                    'error': 'Bạn đã theo dõi người dùng này rồi',
                    'status': 'already_following',
                    'followers_count': user_to_follow.get_followers_count(),
                    'following_count': request.user.get_following_count()
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Chưa follow, tạo mối quan hệ mới
            follow_relationship = UserFollowing.objects.create(
                user=request.user,
                following_user=user_to_follow
            )
                
            # Đã follow thành công
            return Response({
                'status': 'following',
                'followers_count': user_to_follow.get_followers_count(),
                'following_count': request.user.get_following_count(),
                'user_id': user_to_follow.id,
                'follower_id': request.user.id,
                'followed_at': follow_relationship.created_at
            })
                
        except User.DoesNotExist:
            return Response(
                {'error': 'Không tìm thấy người dùng'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UnfollowUserView(APIView):
    """API để hủy theo dõi một người dùng"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, username):
        try:
            user_to_unfollow = User.objects.get(username=username)
            
            # Kiểm tra xem có đang follow không
            try:
                follow_relationship = UserFollowing.objects.get(
                    user=request.user,
                    following_user=user_to_unfollow
                )
                
                # Xóa mối quan hệ (unfollow)
                follow_relationship.delete()
                
                # Trả về thông tin sau khi unfollow
                return Response({
                    'status': 'unfollowed',
                    'followers_count': user_to_unfollow.get_followers_count(),
                    'following_count': request.user.get_following_count(),
                    'user_id': user_to_unfollow.id,
                    'follower_id': request.user.id
                })
                
            except UserFollowing.DoesNotExist:
                # Chưa follow, trả về lỗi
                return Response({
                    'error': 'Bạn chưa theo dõi người dùng này',
                    'status': 'not_following',
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            return Response(
                {'error': 'Không tìm thấy người dùng'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UserFollowersView(APIView):
    """API để lấy danh sách người theo dõi của một người dùng"""
    
    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
            
            # Lấy danh sách người theo dõi (followers)
            # Đây là những người đang theo dõi user này
            followers = user.followers_relationships.select_related('user').all()
            
            # Xây dựng dữ liệu phản hồi
            followers_data = []
            for follower_relation in followers:
                follower = follower_relation.user
                is_following = False
                if request.user.is_authenticated:
                    is_following = UserFollowing.objects.filter(
                        user=request.user, 
                        following_user=follower
                    ).exists()
                
                followers_data.append({
                    'id': follower.id,
                    'username': follower.username,
                    'name': f"{follower.first_name} {follower.last_name}".strip(),
                    'avatar': follower.get_avatar_url(),
                    'is_following': is_following
                })
            
            return Response({'followers': followers_data})
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Không tìm thấy người dùng'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UserFollowingView(APIView):
    """API để lấy danh sách người mà một người dùng đang theo dõi"""
    
    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
            
            # Lấy danh sách đang theo dõi (following)
            # Đây là những người mà user đang theo dõi
            following = user.following_relationships.select_related('following_user').all()
            
            # Xây dựng dữ liệu phản hồi
            following_data = []
            for following_relation in following:
                followed_user = following_relation.following_user
                is_following = False
                if request.user.is_authenticated:
                    is_following = UserFollowing.objects.filter(
                        user=request.user, 
                        following_user=followed_user
                    ).exists()
                
                following_data.append({
                    'id': followed_user.id,
                    'username': followed_user.username,
                    'name': f"{followed_user.first_name} {followed_user.last_name}".strip(),
                    'avatar': followed_user.get_avatar_url(),
                    'is_following': is_following
                })
            
            return Response({'following': following_data})
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Không tìm thấy người dùng'}, 
                status=status.HTTP_404_NOT_FOUND
            )

app_name = 'accounts-api'

urlpatterns = [
    path('', include(router.urls)),
    path('follow/<str:username>/', FollowUserView.as_view(), name='follow_user'),
    path('unfollow/<str:username>/', UnfollowUserView.as_view(), name='unfollow_user'),
    path('users/<str:username>/followers/', UserFollowersView.as_view(), name='user_followers'),
    path('users/<str:username>/following/', UserFollowingView.as_view(), name='user_following'),
    path('user-suggestions/', api.user_suggestions, name='user_suggestions'),
    path('hashtag-suggestions/', api.hashtag_suggestions, name='hashtag_suggestions'),
    path('block/', api.block_user, name='block_user'),
    path('unblock/', api.unblock_user, name='unblock_user'),
    path('report/', api.report_user, name='report_user'),
] 