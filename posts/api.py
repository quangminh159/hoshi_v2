from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.contrib.auth import get_user_model
from .models import Post, Comment, Like, SavedPost, Hashtag, CommentLike
from .serializers import PostSerializer, CommentSerializer, HashtagSerializer
import json
from django.utils import timezone

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
    serializer = PostSerializer(posts, many=True)
    return Response(serializer.data)

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
        
        if not post_id or not text:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        post = Post.objects.get(id=post_id)
        
        if post.disable_comments:
            return Response({'error': 'Comments are disabled for this post'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Kiểm tra bình luận trùng lặp
        # Tìm bình luận gần nhất của người dùng trong bài viết
        recent_comment = Comment.objects.filter(
            post=post,
            author=request.user,
            text=text,
            parent_id=parent_id
        ).order_by('-created_at').first()
        
        # Nếu đã có bình luận giống hệt được tạo trong 5 giây qua, không tạo mới
        if recent_comment and (timezone.now() - recent_comment.created_at).total_seconds() < 5:
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
                'post_id': post_id
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
        
        # Return comment data
        comment_data = {
            'id': comment.id,
            'text': comment.text,
            'author_id': comment.author.id,
            'author_username': comment.author.username,
            'author_avatar': comment.author.avatar.url if comment.author.avatar else None,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M'),
            'likes_count': 0,
            'parent': parent_data,
            'post_id': post_id
        }
        
        return Response({'comment': comment_data})
        
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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