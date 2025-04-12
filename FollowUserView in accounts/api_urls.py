from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from accounts.models import UserFollowing

class FollowUserView(APIView):
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
            follow_relationship, created = UserFollowing.objects.get_or_create(
                user=request.user,
                following_user=user_to_follow
            )
            
            if not created:
                # Đã follow trước đó, xóa mối quan hệ (unfollow)
                follow_relationship.delete()
                return Response({
                    'status': 'unfollowed',
                    'followers_count': user_to_follow.get_followers_count(),
                    'following_count': request.user.get_following_count(),
                    'user_id': user_to_follow.id,
                    'follower_id': request.user.id
                })
                
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