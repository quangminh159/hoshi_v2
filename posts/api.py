from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from .models import Post, Comment, Like, SavedPost, Hashtag, CommentLike, PostMedia, Notification, UserInteraction
from .serializers import PostSerializer, CommentSerializer, HashtagSerializer
from django.conf import settings
import json
from django.utils import timezone
from django.core.cache import cache
import time
import hashlib
from django.http import JsonResponse
from django.db.models import Q
from accounts.models import UserBlock

User = get_user_model()

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['caption', 'location', 'author__username']
    
    def get_queryset(self):
        queryset = Post.objects.all()
        
        # Filter by hashtag
        hashtag = self.request.query_params.get('hashtag', None)
        if hashtag:
            queryset = queryset.filter(hashtags__name=hashtag)
        
        # Filter by user
        username = self.request.query_params.get('username', None)
        if username:
            queryset = queryset.filter(author__username=username)
        
        # Filter saved posts
        saved = self.request.query_params.get('saved', None)
        if saved:
            queryset = queryset.filter(saved_by__user=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if created:
            post.likes_count = post.post_likes.count()
            post.save()
            return Response({'status': 'liked'})
        
        like.delete()
        post.likes_count = post.post_likes.count()
        post.save()
        return Response({'status': 'unliked'})
    
    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        post = self.get_object()
        saved, created = SavedPost.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if created:
            return Response({'status': 'saved'})
        
        saved.delete()
        return Response({'status': 'unsaved'})

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Comment.objects.filter(
            post_id=self.kwargs['post_pk'],
            parent=None
        )
    
    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            post_id=self.kwargs['post_pk']
        )
        
        # Update post's comments count
        post = Post.objects.get(id=self.kwargs['post_pk'])
        post.comments_count = post.comments.count()
        post.save()
    
    @action(detail=True, methods=['post'])
    def like(self, request, post_pk=None, pk=None):
        comment = self.get_object()
        
        if request.user in comment.likes.all():
            comment.likes.remove(request.user)
            return Response({'status': 'unliked'})
        
        comment.likes.add(request.user)
        return Response({'status': 'liked'})

class HashtagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HashtagSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Hashtag.objects.annotate(
            posts_count=Count('posts')
        ).order_by('-posts_count')

# New API Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def post_list(request):
    posts = Post.objects.all().order_by('-created_at')
    
    # Lọc theo username nếu có
    username = request.GET.get('username')
    if username:
        posts = posts.filter(author__username=username)
        
    page_number = request.GET.get('page', 1)
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_obj = paginator.get_page(page_number)
    
    serializer = PostSerializer(page_obj.object_list, many=True)
    
    return Response({
        'posts': serializer.data,
        'has_next': page_obj.has_next(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number
    })

@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def post_detail(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = PostSerializer(post)
        return Response(serializer.data)
    elif request.method == 'DELETE':
        if post.author != request.user:
            return Response({'status': 'error', 'message': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        post.delete()
        return Response({'status': 'success'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_post(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    like, created = Like.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        like.delete()
        post.likes_count = post.post_likes.count()
        post.save()
        return Response({'status': 'unliked', 'likes_count': post.likes_count})
    
    post.likes_count = post.post_likes.count()
    post.save()
    return Response({'status': 'liked', 'likes_count': post.likes_count})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_post(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    saved, created = SavedPost.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        saved.delete()
        return Response({'status': 'unsaved'})
    
    return Response({'status': 'saved'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comment_list(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    comments = Comment.objects.filter(post=post, parent=None).order_by('-created_at')
    serializer = CommentSerializer(comments, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request):
    try:
        data = request.data
        post_id = data.get('post_id')
        text = data.get('text')
        parent_id = data.get('parent_id')
        request_id = data.get('request_id', '')
        
        # Log để debug
        print(f"Processing comment request: post_id={post_id}, text={text[:20]}..., parent_id={parent_id}, request_id={request_id}")
        
        # Kiểm tra các tham số bắt buộc
        if not post_id or not text:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo cache key an toàn bằng cách hash nội dung
        comment_content_hash = hashlib.md5(f"{request.user.id}:{post_id}:{text}:{parent_id or ''}".encode()).hexdigest()
        cache_key = f"comment:{comment_content_hash}"
        
        # Kiểm tra xem request_id này đã được xử lý chưa
        if request_id:
            request_cache_key = f"request:{request_id}"
            if cache.get(request_cache_key):
                print(f"Detected duplicate request with request_id={request_id}")
                # Tìm comment gần đây nhất của user có nội dung này
                post = Post.objects.get(id=post_id)
                recent_comment = Comment.objects.filter(
                    post=post,
                    author=request.user,
                    text=text,
                    parent_id=parent_id
                ).order_by('-created_at').first()
                
                if recent_comment:
                    # Trả về comment để tránh client hiển thị lỗi
                    parent_data = None
                    if recent_comment.parent:
                        parent_data = {
                            'id': recent_comment.parent.id,
                            'author_username': recent_comment.parent.author.username
                        }
                    
                    comment_data = {
                        'id': recent_comment.id,
                        'text': recent_comment.text,
                        'author_id': recent_comment.author.id,
                        'author_username': recent_comment.author.username,
                        'author_avatar': recent_comment.author.avatar.url if recent_comment.author.avatar else None,
                        'created_at': recent_comment.created_at.strftime('%d/%m/%Y %H:%M'),
                        'likes_count': recent_comment.likes_count,
                        'parent': parent_data,
                        'post_id': post_id,
                        'is_duplicate': True
                    }
                    
                    return Response({'comment': comment_data, 'message': 'Duplicate request detected'})
            
            # Đánh dấu request_id này đã được xử lý
            cache.set(request_cache_key, True, 300)  # 5 phút
        
        # Kiểm tra xem nội dung comment này đã được gửi gần đây chưa
        if cache.get(cache_key):
            print(f"Detected duplicate comment content via cache: {cache_key}")
            # Tìm comment gần đây nhất của user có nội dung này
            post = Post.objects.get(id=post_id)
            recent_comment = Comment.objects.filter(
                post=post,
                author=request.user,
                text=text,
                parent_id=parent_id
            ).order_by('-created_at').first()
            
            if recent_comment:
                # Trả về comment để tránh client hiển thị lỗi
                parent_data = None
                if recent_comment.parent:
                    parent_data = {
                        'id': recent_comment.parent.id,
                        'author_username': recent_comment.parent.author.username
                    }
                
                comment_data = {
                    'id': recent_comment.id,
                    'text': recent_comment.text,
                    'author_id': recent_comment.author.id,
                    'author_username': recent_comment.author.username,
                    'author_avatar': recent_comment.author.avatar.url if recent_comment.author.avatar else None,
                    'created_at': recent_comment.created_at.strftime('%d/%m/%Y %H:%M'),
                    'likes_count': recent_comment.likes_count,
                    'parent': parent_data,
                    'post_id': post_id,
                    'is_duplicate': True
                }
                
                return Response({'comment': comment_data, 'message': 'Duplicate content detected'})
        
        # Đánh dấu nội dung comment này đã được xử lý
        cache.set(cache_key, True, 30)  # Lưu 30 giây
        
        post = Post.objects.get(id=post_id)
        
        if post.disable_comments:
            return Response({'error': 'Comments are disabled for this post'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra bình luận trùng lặp trong database
        # Lấy bình luận gần đây nhất của người dùng trong bài viết này
        recent_comments = Comment.objects.filter(
            post=post,
            author=request.user,
            text=text,
            parent_id=parent_id
        ).order_by('-created_at')
        
        # Nếu đã có bình luận giống hệt trong vòng 30 giây qua, không tạo mới
        if recent_comments.exists():
            recent_comment = recent_comments.first()
            time_diff = (timezone.now() - recent_comment.created_at).total_seconds()
            
            if time_diff < 30:  # Kiểm tra 30 giây gần nhất
                print(f"Detected duplicate comment within {time_diff} seconds")
                # Lấy parent data nếu có
                parent_data = None
                if recent_comment.parent:
                    parent_data = {
                        'id': recent_comment.parent.id,
                        'author_username': recent_comment.parent.author.username
                    }
                    
                # Trả về bình luận hiện có thay vì tạo mới
                comment_data = {
                    'id': recent_comment.id,
                    'text': recent_comment.text,
                    'author_id': recent_comment.author.id,
                    'author_username': recent_comment.author.username,
                    'author_avatar': recent_comment.author.avatar.url if recent_comment.author.avatar else None,
                    'created_at': recent_comment.created_at.strftime('%d/%m/%Y %H:%M'),
                    'likes_count': recent_comment.likes_count,
                    'parent': parent_data,
                    'post_id': post_id,
                    'is_duplicate': True  # Đánh dấu là bình luận trùng lặp
                }
                
                return Response({'comment': comment_data})
        
        # Create the comment
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            text=text,
            parent_id=parent_id
        )
        
        # Update post comments count
        post.comments_count = post.comments.count()
        post.save()
        
        # Get parent comment data if any
        parent_data = None
        if parent_id:
            try:
                parent_comment = Comment.objects.get(id=parent_id)
                parent_data = {
                    'id': parent_comment.id,
                    'author_username': parent_comment.author.username
                }
            except Comment.DoesNotExist:
                pass
        
        # Trả về dữ liệu comment
        comment_data = {
            'id': comment.id,
            'text': comment.text,
            'author_id': request.user.id,
            'author_username': request.user.username,
            'author_avatar': request.user.avatar.url if request.user.avatar else None,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M'),
            'likes_count': 0,
            'parent': parent_data,
            'post_id': post_id,
            'is_duplicate': False
        }
        
        # Tạo thông báo nếu là reply
        if parent_id:
            try:
                parent_comment = Comment.objects.get(id=parent_id)
                
                # Nếu author của comment gốc không phải current user
                if parent_comment.author != request.user:
                    Notification.objects.create(
                        recipient=parent_comment.author,
                        sender=request.user,
                        notification_type='comment_reply',
                        text=f"{request.user.username} đã trả lời bình luận của bạn",
                        post=post,
                        comment=comment
                    )
            except Comment.DoesNotExist:
                pass
        # Nếu không phải reply, tạo thông báo cho author của post
        elif post.author != request.user:
            Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='comment',
                text=f"{request.user.username} đã bình luận về bài viết của bạn",
                post=post,
                comment=comment
            )
        
        return Response({
            'comment': comment_data
        })
    except Exception as e:
        print(f"Error in add_comment: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, pk):
    """API endpoint để xóa bình luận"""
    try:
        comment = Comment.objects.get(pk=pk)
        
        # Chỉ tác giả của comment hoặc tác giả của bài viết mới có quyền xóa
        if comment.author != request.user and comment.post.author != request.user:
            return Response({'error': 'Bạn không có quyền xóa bình luận này'}, status=status.HTTP_403_FORBIDDEN)
        
        # Lưu post_id trước khi xóa comment để cập nhật số lượng comment sau đó
        post_id = comment.post.id
        
        # Xóa comment
        comment.delete()
        
        # Cập nhật số lượng comment của bài viết
        post = Post.objects.get(id=post_id)
        post.comments_count = post.comments.count()
        post.save()
        
        return Response({'success': True, 'message': 'Đã xóa bình luận'})
        
    except Comment.DoesNotExist:
        return Response({'error': 'Không tìm thấy bình luận'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_comment(request, pk):
    """API endpoint để thích bình luận"""
    try:
        comment = Comment.objects.get(pk=pk)
        
        # Kiểm tra xem đã like chưa
        like, created = CommentLike.objects.get_or_create(
            user=request.user,
            comment=comment
        )
        
        if not created:
            # Nếu đã like, xóa like
            like.delete()
            # Cập nhật số lượng like
            comment.likes_count = comment.comment_likes.count()
            comment.save()
            return Response({'status': 'unliked', 'likes_count': comment.likes_count})
        
        # Nếu chưa like, cập nhật số lượng like
        comment.likes_count = comment.comment_likes.count()
        comment.save()
        return Response({'status': 'liked', 'likes_count': comment.likes_count})
        
    except Comment.DoesNotExist:
        return Response({'error': 'Không tìm thấy bình luận'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_post(request, post_id):
    """API endpoint để chỉnh sửa bài viết"""
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return Response({'status': 'error', 'message': 'Không tìm thấy bài viết'}, status=status.HTTP_404_NOT_FOUND)
    
    # Kiểm tra quyền sở hữu
    if post.author != request.user:
        return Response({'status': 'error', 'message': 'Bạn không có quyền chỉnh sửa bài viết này'}, 
                        status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Cập nhật thông tin cơ bản của bài viết
        if 'caption' in request.data:
            post.caption = request.data['caption']
        
        if 'location' in request.data:
            post.location = request.data['location']
        
        if 'disable_comments' in request.data:
            post.disable_comments = request.data['disable_comments'] == 'true'
        
        if 'hide_likes' in request.data:
            post.hide_likes = request.data['hide_likes'] == 'true'
        
        # Lưu thay đổi
        post.save()
        
        # Xử lý xóa phương tiện
        if 'deleted_media' in request.data:
            deleted_media_ids = json.loads(request.data['deleted_media'])
            if deleted_media_ids:
                PostMedia.objects.filter(id__in=deleted_media_ids, post=post).delete()
        
        # Xử lý thêm phương tiện mới
        if 'new_media' in request.FILES:
            new_media_files = request.FILES.getlist('new_media')
            for index, file in enumerate(new_media_files):
                # Kiểm tra kích thước file
                if file.size > settings.MAX_UPLOAD_SIZE:
                    return Response({
                        'status': 'error',
                        'message': f'Kích thước file không được vượt quá {settings.MAX_UPLOAD_SIZE/1024/1024:.2f}MB'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Xác định loại media
                media_type = 'video' if file.content_type.startswith('video') else 'image'
                
                # Tính order là index cuối cùng hiện tại + index mới
                last_order = PostMedia.objects.filter(post=post).count()
                
                # Tạo media object mới
                PostMedia.objects.create(
                    post=post,
                    file=file,
                    media_type=media_type,
                    order=last_order + index
                )
        
        # Xử lý hashtags
        if 'caption' in request.data:
            # Xóa tất cả hashtag cũ
            post.hashtags.clear()
            
            # Tìm và thêm hashtags mới
            hashtags = [word[1:] for word in post.caption.split() if word.startswith('#')]
            for tag_name in hashtags:
                hashtag, _ = Hashtag.objects.get_or_create(name=tag_name)
                hashtag.posts.add(post)
        
        return Response({
            'status': 'success',
            'message': 'Đã cập nhật bài viết thành công',
            'post': {
                'id': post.id,
                'caption': post.caption,
                'location': post.location,
                'disable_comments': post.disable_comments,
                'hide_likes': post.hide_likes
            }
        })
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Có lỗi xảy ra: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    """API endpoint để xóa bài viết"""
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return Response({'status': 'error', 'message': 'Không tìm thấy bài viết'}, 
                        status=status.HTTP_404_NOT_FOUND)
    
    # Kiểm tra quyền sở hữu
    if post.author != request.user:
        return Response({'status': 'error', 'message': 'Bạn không có quyền xóa bài viết này'}, 
                        status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Xóa các đối tượng liên quan trước
        # 1. Xóa media
        post.media.all().delete()
        
        # 2. Xóa comments
        post.comments.all().delete()
        
        # 3. Xóa likes
        post.post_likes.all().delete()
        
        # 4. Xóa saved posts
        post.saved_by.all().delete()
        
        # 5. Xóa hashtags
        post.hashtags.clear()
        
        # Cuối cùng xóa bài viết
        post.delete()
        
        return Response({
            'status': 'success',
            'message': 'Đã xóa bài viết thành công'
        })
    
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Có lỗi xảy ra: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hashtag_suggestions(request):
    """API endpoint để gợi ý hashtag khi người dùng nhập caption"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse([], safe=False)
    
    # Tìm các hashtag phù hợp với chuỗi tìm kiếm
    suggestions = Hashtag.objects.filter(name__icontains=query)
    
    # Sắp xếp theo số lượng bài viết sử dụng hashtag này
    suggestions = suggestions.annotate(posts_count=Count('posts')).order_by('-posts_count')[:10]
    
    # Chỉ trả về tên hashtag
    result = [tag.name for tag in suggestions]
    
    return JsonResponse(result, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_suggestions(request):
    """API endpoint để gợi ý người dùng khi người dùng nhập @mention"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse([], safe=False)
    
    # Tìm các người dùng phù hợp với chuỗi tìm kiếm
    suggestions = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).distinct()[:10]
    
    # Lấy danh sách những người đã chặn người dùng hiện tại
    blocked_by_users = UserBlock.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    
    # Loại bỏ người dùng đã chặn người dùng hiện tại
    suggestions = suggestions.exclude(id__in=blocked_by_users)
    
    # Chuyển đổi thành JSON response
    result = []
    for user in suggestions:
        result.append({
            'username': user.username,
            'avatar_url': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else '/static/images/default-avatar.png',
            'full_name': f"{user.first_name} {user.last_name}".strip()
        })
    
    return JsonResponse(result, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_interaction(request):
    """API endpoint để theo dõi tương tác người dùng với bài viết"""
    try:
        post_id = request.data.get('post_id')
        interaction_type = request.data.get('interaction_type')
        duration = request.data.get('duration', 0)
        
        if not post_id or not interaction_type:
            return Response({'error': 'Thiếu thông tin bắt buộc'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra xem loại tương tác có hợp lệ không
        valid_types = [choice[0] for choice in UserInteraction.INTERACTION_TYPES]
        if interaction_type not in valid_types:
            return Response({'error': 'Loại tương tác không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lấy bài viết
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Không tìm thấy bài viết'}, status=status.HTTP_404_NOT_FOUND)
        
        # Lưu tương tác
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type=interaction_type,
            duration=duration
        )
        
        return Response({'status': 'success'})
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_post(request):
    try:
        data = request.data
        post_id = data.get('post_id')
        caption = data.get('caption', '')
        as_new_post = data.get('as_new_post', True)
        
        # Kiểm tra bài viết tồn tại
        try:
            original_post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Bài viết không tồn tại'
            }, status=404)
        
        # Kiểm tra người dùng bị chặn - Sửa tên trường từ blocking_user/blocked_user thành blocker/blocked
        if UserBlock.objects.filter(
            Q(blocker=original_post.author, blocked=request.user) | 
            Q(blocker=request.user, blocked=original_post.author)
        ).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Không thể chia sẻ bài viết này'
            }, status=403)
        
        # Nếu chia sẻ như bài viết mới
        if as_new_post:
            # Tạo nội dung bài viết với định dạng mới
            # Chỉ thêm caption của người dùng và liên kết đến bài gốc
            shared_content = caption
            if caption:
                shared_content += "\n\n"
            
            # Thêm thông tin rằng đây là bài chia sẻ với icon
            shared_content += f"📄 Đã chia sẻ bài viết của @{original_post.author.username}\n"
            
            # Thêm URL bài viết gốc
            shared_content += f"🔗 /posts/{post_id}/"
            
            # Tạo bài viết mới
            new_post = Post.objects.create(
                author=request.user,
                caption=shared_content,
                shared_from=original_post
            )
            
            # Không sao chép media, chỉ tham chiếu đến bài viết gốc
            
            # Tạo thông báo cho chủ bài viết gốc
            if request.user != original_post.author:
                from notifications.models import Notification
                from django.contrib.contenttypes.models import ContentType
                Notification.objects.create(
                    recipient=original_post.author,
                    sender=request.user,
                    notification_type='share',
                    text=f"{request.user.username} đã chia sẻ bài viết của bạn",
                    post=new_post,
                    original_post=original_post,
                    content_type=ContentType.objects.get_for_model(new_post),
                    object_id=new_post.id
                )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã chia sẻ bài viết thành công',
                'post_id': new_post.id
            })
        else:
            # Chức năng chia sẻ nhanh (hiện chưa triển khai)
            # Có thể thêm chức năng chia sẻ qua tin nhắn hoặc trên profile
            return JsonResponse({
                'status': 'success',
                'message': 'Đã chia sẻ bài viết thành công'
            })
            
    except Exception as e:
        print(f"Error sharing post: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Có lỗi xảy ra khi chia sẻ bài viết'
        }, status=500) 