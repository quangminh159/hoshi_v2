from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage
from .models import Post, Comment, Like, SavedPost, Hashtag, Media, Mention, PostReport, PostMedia, CommentLike, Notification
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import logging
import traceback

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def home(request):
    logger.info(f"Bắt đầu xử lý trang chủ")
    logger.info(f"Người dùng: {request.user}")
    logger.info(f"Người dùng đã xác thực: {request.user.is_authenticated}")
    
    # Lấy tất cả bài viết, sắp xếp theo thời gian tạo mới nhất
    posts = Post.objects.all().order_by('-created_at')
    logger.info(f"Tổng số bài viết ban đầu: {posts.count()}")
    
    # Nếu người dùng đã xác thực
    if request.user.is_authenticated:
        # Lấy danh sách những người dùng mà người dùng hiện tại đang theo dõi
        following_users = request.user.following.values_list('id', flat=True)
        logger.info(f"Những người dùng đang được theo dõi: {list(following_users)}")
        
        # Nếu có người theo dõi, ưu tiên bài viết của những người đang theo dõi
        if following_users:
            following_posts = posts.filter(
                Q(author__id__in=following_users) | Q(author=request.user)
            )
            logger.info(f"Số bài viết của những người đang theo dõi: {following_posts.count()}")
            
            # Nếu có bài viết của những người đang theo dõi, sử dụng các bài viết này
            if following_posts.exists():
                posts = following_posts
    
    logger.info(f"Tổng số bài viết sau khi lọc: {posts.count()}")
    
    # Kiểm tra và xử lý avatar
    for post in posts:
        if not hasattr(post.author, 'avatar_url'):
            post.author.avatar_url = post.author.get_avatar_url()
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Prefetch bình luận và trả lời
    posts_with_comments = []
    for post in page_obj:
        # Lấy tối đa 3 bình luận gốc cho mỗi bài viết
        root_comments = Comment.objects.filter(post=post, parent=None).order_by('-created_at')[:3]
        
        comments_with_replies = []
        for comment in root_comments:
            # Lấy tối đa 2 trả lời cho mỗi bình luận
            replies = Comment.objects.filter(parent=comment).order_by('-created_at')[:2]
            comments_with_replies.append({
                'comment': comment,
                'replies': replies,
                'replies_count': Comment.objects.filter(parent=comment).count()
            })
        
        posts_with_comments.append({
            'post': post,
            'comments_data': comments_with_replies,
            'total_comments': Comment.objects.filter(post=post).count()
        })
    
    logger.info("Debug - Post Authors:")
    for post_data in posts_with_comments:
        post = post_data['post']
        logger.info(f"Post ID: {post.id}, Author Username: {post.author.username}")
    
    # Log thông tin về việc lọc bài viết
    logger.info(f"Total posts before filtering: {posts.count()}")
    if request.user.is_authenticated:
        logger.info(f"Following users: {list(following_users) if 'following_users' in locals() else 'None'}")
    logger.info(f"Total posts after filtering: {posts.count()}")
    
    # Kiểm tra điều kiện lọc bài viết
    context = {
        'posts_with_data': posts_with_comments,
        'page_obj': page_obj,
    }
    return render(request, 'posts/feed.html', context)

@login_required
def feed(request):
    # Lấy tất cả bài viết, sắp xếp theo thời gian tạo mới nhất
    posts = Post.objects.all().order_by('-created_at')
    
    # Nếu người dùng đã xác thực
    if request.user.is_authenticated:
        # Lấy danh sách những người dùng mà người dùng hiện tại đang theo dõi
        following_users = request.user.following.values_list('id', flat=True)
        
        # Nếu có người theo dõi, ưu tiên bài viết của những người đang theo dõi
        if following_users:
            following_posts = posts.filter(
                Q(author__id__in=following_users) | Q(author=request.user)
            )
            
            # Nếu có bài viết của những người đang theo dõi, sử dụng các bài viết này
            if following_posts.exists():
                posts = following_posts
    
    # Nếu không có bài viết của người theo dõi, sử dụng tất cả bài viết
    logger.info(f"Total posts: {posts.count()}")
    
    # Log chi tiết về từng bài viết
    for post in posts[:10]:  # Log 10 bài viết đầu tiên
        logger.info(f"Post ID: {post.id}, Author: {post.author.username}, Created At: {post.created_at}")
    
    # Kiểm tra và xử lý avatar
    for post in posts:
        if not hasattr(post.author, 'avatar_url'):
            post.author.avatar_url = post.author.get_avatar_url()
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Prefetch bình luận và trả lời
    posts_with_comments = []
    for post in page_obj:
        # Lấy tối đa 3 bình luận gốc cho mỗi bài viết
        root_comments = Comment.objects.filter(post=post, parent=None).order_by('-created_at')[:3]
        
        comments_with_replies = []
        for comment in root_comments:
            # Lấy tối đa 2 trả lời cho mỗi bình luận
            replies = Comment.objects.filter(parent=comment).order_by('-created_at')[:2]
            comments_with_replies.append({
                'comment': comment,
                'replies': replies,
                'replies_count': Comment.objects.filter(parent=comment).count()
            })
        
        posts_with_comments.append({
            'post': post,
            'comments_data': comments_with_replies,
            'total_comments': Comment.objects.filter(post=post).count()
        })
    
    logger.info("Debug - Post Authors:")
    for post_data in posts_with_comments:
        post = post_data['post']
        logger.info(f"Post ID: {post.id}, Author Username: {post.author.username}")
    
    # Log thông tin về việc lọc bài viết
    logger.info(f"Total posts before filtering: {posts.count()}")
    if request.user.is_authenticated:
        logger.info(f"Following users: {list(following_users) if 'following_users' in locals() else 'None'}")
    logger.info(f"Total posts after filtering: {posts.count()}")
    
    # Kiểm tra điều kiện lọc bài viết
    context = {
        'posts_with_data': posts_with_comments,
        'page_obj': page_obj,
    }
    return render(request, 'posts/feed.html', context)

@login_required
def post_detail(request, post_id):
    """Hiển thị chi tiết bài viết"""
    post = get_object_or_404(Post, id=post_id)
    
    # Lấy tất cả comments của bài viết và phân loại
    root_comments = Comment.objects.filter(post=post, parent=None).order_by('created_at')
    
    comments_with_replies = []
    for comment in root_comments:
        # Lấy replies cho mỗi comment
        replies = Comment.objects.filter(parent=comment).order_by('created_at')
        comments_with_replies.append({
            'comment': comment,
            'replies': replies,
            'replies_count': replies.count()
        })
    
    context = {
        'post': post,
        'comments_data': comments_with_replies,
        'total_comments': Comment.objects.filter(post=post).count()
    }
    return render(request, 'posts/post_detail.html', context)

@login_required
def create_post(request):
    if request.method == 'POST':
        try:
            caption = request.POST.get('caption', '').strip()
            location = request.POST.get('location', '').strip()
            media_files = request.FILES.getlist('media')
            
            # Tạo post
            post = Post.objects.create(
                author=request.user,
                caption=caption,
                location=location
            )
            
            # Xử lý media nếu có
            if media_files:
                for index, file in enumerate(media_files):
                    try:
                        # Kiểm tra kích thước file
                        if file.size > settings.MAX_UPLOAD_SIZE:
                            post.delete()
                            messages.error(request, f'Kích thước file không được vượt quá {settings.MAX_UPLOAD_SIZE/1024/1024/1024:.2f}GB')
                            return redirect('posts:create')
                        
                        # Kiểm tra định dạng file
                        if not file.content_type.startswith(('image/', 'video/')):
                            post.delete()
                            messages.error(request, 'Chỉ chấp nhận file ảnh hoặc video')
                            return redirect('posts:create')
                        
                        # Xác định loại media
                        media_type = 'video' if file.content_type.startswith('video') else 'image'
                        
                        # Tạo media object
                        PostMedia.objects.create(
                            post=post,
                            file=file,
                            media_type=media_type,
                            order=index
                        )
                    except Exception as e:
                        # Nếu có lỗi khi tạo media, xóa post và trả về lỗi
                        post.delete()
                        messages.error(request, f'Lỗi khi xử lý file: {str(e)}')
                        return redirect('posts:create')
            
            # Xử lý hashtags
            hashtags = [word[1:] for word in caption.split() if word.startswith('#')]
            for tag_name in hashtags:
                try:
                    hashtag, _ = Hashtag.objects.get_or_create(name=tag_name)
                    hashtag.posts.add(post)
                    hashtag.posts_count = hashtag.posts.count()
                    hashtag.save()
                except Exception as e:
                    # Nếu có lỗi khi tạo hashtag, chỉ log lỗi và tiếp tục
                    print(f"Error creating hashtag {tag_name}: {str(e)}")
            
            # Xử lý mentions
            mentions = [word[1:] for word in caption.split() if word.startswith('@')]
            for username in mentions:
                try:
                    mentioned_user = User.objects.get(username=username)
                    Mention.objects.create(
                        user=mentioned_user,
                        post=post
                    )
                except User.DoesNotExist:
                    # Nếu user không tồn tại, chỉ log lỗi và tiếp tục
                    print(f"User {username} not found")
                except Exception as e:
                    # Nếu có lỗi khác, chỉ log lỗi và tiếp tục
                    print(f"Error creating mention for {username}: {str(e)}")
            
            messages.success(request, 'Đăng bài thành công!')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Lỗi khi tạo bài viết: {str(e)}')
            return redirect('posts:create')
    
    return render(request, 'posts/create_post.html')

@login_required
def edit_post(request, post_id):
    """Chỉnh sửa bài viết"""
    post = get_object_or_404(Post, id=post_id, author=request.user)
    
    if request.method == 'POST':
        try:
            # Cập nhật caption và location
            post.caption = request.POST.get('caption', '').strip()
            post.location = request.POST.get('location', '').strip()
            
            # Xử lý media mới (nếu có)
            new_media_files = request.FILES.getlist('media')
            if new_media_files:
                # Xóa media cũ
                PostMedia.objects.filter(post=post).delete()
                
                # Thêm media mới
                for index, file in enumerate(new_media_files):
                    # Kiểm tra kích thước và loại file
                    if file.size > settings.MAX_UPLOAD_SIZE:
                        messages.error(request, f'Kích thước file không được vượt quá {settings.MAX_UPLOAD_SIZE/1024/1024/1024:.2f}GB')
                        return redirect('posts:edit', post_id=post.id)
                    
                    if not file.content_type.startswith(('image/', 'video/')):
                        messages.error(request, 'Chỉ chấp nhận file ảnh hoặc video')
                        return redirect('posts:edit', post_id=post.id)
                    
                    # Xác định loại media
                    media_type = 'video' if file.content_type.startswith('video') else 'image'
                    
                    # Tạo media object
                    PostMedia.objects.create(
                        post=post,
                        file=file,
                        media_type=media_type,
                        order=index
                    )
            
            # Lưu bài viết
            post.save()
            
            # Xử lý hashtags
            # Xóa hashtags cũ
            post.hashtags.clear()
            
            # Thêm hashtags mới
            hashtags = [word[1:] for word in post.caption.split() if word.startswith('#')]
            for tag_name in hashtags:
                hashtag, _ = Hashtag.objects.get_or_create(name=tag_name)
                hashtag.posts.add(post)
            
            messages.success(request, 'Bài viết đã được cập nhật thành công.')
            return redirect('posts:post_detail', post_id=post.id)
        
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra: {str(e)}')
            return redirect('posts:edit', post_id=post.id)
    
    # Nếu là GET request, hiển thị form chỉnh sửa
    return render(request, 'posts/edit_post.html', {
        'post': post,
        'media_files': post.post_media.all()
    })

@login_required
def delete_post(request, post_id):
    """Xóa bài viết"""
    try:
        # Log thông tin chi tiết về việc xóa bài viết
        logger.info(f"Bắt đầu xóa bài viết: ID={post_id}")
        logger.info(f"Người dùng hiện tại: {request.user.username}")
        
        # Kiểm tra chi tiết về bài viết
        try:
            post = Post.objects.get(id=post_id)
            logger.info(f"Thông tin bài viết: Tác giả={post.author.username}")
        except Post.DoesNotExist:
            logger.error(f"Bài viết {post_id} không tồn tại")
            return JsonResponse({'status': 'error', 'message': 'Bài viết không tồn tại.'}, status=404)
        
        # Kiểm tra quyền sở hữu
        if post.author != request.user:
            logger.error(f"Người dùng {request.user.username} không phải tác giả bài viết")
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xóa bài viết này.'}, status=403)
        
        # Xóa các đối tượng liên quan một cách chi tiết
        # 1. Xóa media
        media_count = post.post_media.count()
        post.post_media.all().delete()
        logger.info(f"Đã xóa {media_count} media files")
        
        # 2. Xóa comments
        comments_count = post.comments.count()
        post.comments.all().delete()
        logger.info(f"Đã xóa {comments_count} comments")
        
        # 3. Xóa likes
        likes_count = post.post_likes.count()
        post.post_likes.all().delete()
        logger.info(f"Đã xóa {likes_count} likes")
        
        # 4. Xóa saved posts
        saved_count = post.saved_by.count()
        post.saved_by.all().delete()
        logger.info(f"Đã xóa {saved_count} saved posts")
        
        # 5. Xóa mentions
        mentions_count = Mention.objects.filter(post=post).count()
        Mention.objects.filter(post=post).delete()
        logger.info(f"Đã xóa {mentions_count} mentions")
        
        # 6. Xóa hashtags
        hashtags_count = post.hashtags.count()
        post.hashtags.clear()
        logger.info(f"Đã xóa {hashtags_count} hashtags")
        
        # 7. Xóa notifications liên quan
        notifications_count = Notification.objects.filter(
            object_id=post.id, 
            content_type__model='post'
        ).count()
        Notification.objects.filter(
            object_id=post.id, 
            content_type__model='post'
        ).delete()
        logger.info(f"Đã xóa {notifications_count} notifications")
        
        # Cuối cùng mới xóa bài viết
        post.delete()
        
        logger.info(f"Đã xóa thành công bài viết {post_id}")
        return JsonResponse({'status': 'success', 'message': 'Bài viết đã được xóa thành công.'})
    
    except Exception as e:
        # Log chi tiết lỗi
        logger.error(f"Lỗi khi xóa bài viết {post_id}: {str(e)}")
        logger.error(f"Chi tiết lỗi: {type(e).__name__}")
        logger.error(f"Trace: {traceback.format_exc()}")
        
        return JsonResponse({'status': 'error', 'message': f'Có lỗi xảy ra khi xóa bài viết: {str(e)}'}, status=500)

@login_required
def like_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    post = get_object_or_404(Post, id=post_id)
    
    # Kiểm tra xem người dùng đã thích bài viết chưa
    like, created = Like.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        # Nếu đã thích, xóa like
        like.delete()
        status = 'unliked'
    else:
        status = 'liked'
    
    # Cập nhật số lượng like
    post.likes_count = post.post_likes.count()
    post.save()
    
    return JsonResponse({
        'status': status,
        'likes_count': post.likes_count
    })

@login_required
def save_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    post = get_object_or_404(Post, id=post_id)
    saved, created = SavedPost.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        saved.delete()
        action = 'unsaved'
    else:
        action = 'saved'
    
    return JsonResponse({'status': action})

@login_required
def add_comment(request, post_id):
    """Thêm bình luận mới cho bài viết"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    post = get_object_or_404(Post, id=post_id)
    
    if post.disable_comments:
        return JsonResponse(
            {'error': 'Comments are disabled for this post'},
            status=400
        )
    
    text = request.POST.get('text')
    reply_to = request.POST.get('reply_to')  # Username của người được trả lời
    
    if not text:
        return JsonResponse(
            {'error': 'Comment text is required'},
            status=400
        )
    
    # Kiểm tra bình luận trùng lặp
    # Tìm bình luận gần nhất của người dùng trong bài viết
    recent_comment = Comment.objects.filter(
        post=post,
        author=request.user,
        text=text
    ).order_by('-created_at').first()
    
    # Nếu đã có bình luận giống hệt được tạo trong 5 giây qua, không tạo mới
    if recent_comment and (timezone.now() - recent_comment.created_at).total_seconds() < 5:
        # Trả về bình luận hiện có thay vì tạo mới
        response_data = {
            'id': recent_comment.id,
            'text': recent_comment.text,
            'author': {
                'id': recent_comment.author.id,
                'username': recent_comment.author.username,
                'avatar': recent_comment.author.avatar.url if recent_comment.author.avatar else None
            },
            'created_at': recent_comment.created_at.isoformat(),
            'is_reply': recent_comment.parent_id is not None
        }
        
        # Thêm thông tin về parent nếu có
        if recent_comment.parent:
            response_data['parent'] = {
                'id': recent_comment.parent.id,
                'author': {
                    'username': recent_comment.parent.author.username
                }
            }
        
        return JsonResponse(response_data)
    
    # Xác định parent_id nếu đây là phản hồi cho một bình luận
    parent_id = None
    parent = None
    if reply_to:
        try:
            # Tìm bình luận gần nhất của người dùng này trong bài viết
            parent = Comment.objects.filter(
                post=post,
                author__username=reply_to
            ).latest('created_at')
            parent_id = parent.id
        except Comment.DoesNotExist:
            pass
    
    comment = Comment.objects.create(
        post=post,
        author=request.user,
        text=text,
        parent_id=parent_id
    )
    
    # Cập nhật số lượng comment
    post.comments_count = post.comments.count()
    post.save()
    
    # Thông báo cho người được trả lời
    if parent and parent.author != request.user:
        Notification.objects.get_or_create(
            recipient=parent.author,
            sender=request.user,
            verb="đã trả lời bình luận của",
            content_object=comment,
            action_object=comment
        )
    
    # Chuẩn bị dữ liệu trả về
    response_data = {
        'id': comment.id,
        'text': comment.text,
        'author': {
            'id': comment.author.id,
            'username': comment.author.username,
            'avatar': comment.author.avatar.url if comment.author.avatar else None
        },
        'created_at': comment.created_at.isoformat(),
        'is_reply': parent_id is not None
    }
    
    # Thêm thông tin về parent nếu có
    if parent:
        response_data['parent'] = {
            'id': parent.id,
            'author': {
                'username': parent.author.username
            }
        }
    
    return JsonResponse(response_data)

@login_required
def delete_comment(request, post_id, comment_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    comment = get_object_or_404(
        Comment,
        id=comment_id,
        post_id=post_id,
        author=request.user
    )
    comment.delete()
    
    # Cập nhật số lượng comment
    post = Post.objects.get(id=post_id)
    post.comments_count = post.comments.count()
    post.save()
    
    return JsonResponse({'status': 'success'})

@login_required
def explore(request):
    # Lọc theo hashtag
    hashtag = request.GET.get('hashtag')
    if hashtag:
        posts = Post.objects.filter(hashtags__name=hashtag)
    else:
        # Hiển thị bài viết phổ biến
        posts = Post.objects.annotate(
            engagement=Count('likes') + Count('comments')
        ).order_by('-engagement')
    
    # Lọc theo media type
    media_type = request.GET.get('media_type')
    if media_type in ['image', 'video']:
        posts = posts.filter(media__media_type=media_type)
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Lấy hashtags phổ biến
    popular_tags = Hashtag.objects.annotate(
        posts_count=Count('posts')
    ).order_by('-posts_count')[:10]
    
    context = {
        'posts': page_obj,
        'popular_tags': popular_tags,
        'current_hashtag': hashtag,
        'current_media_type': media_type
    }
    return render(request, 'posts/explore.html', context)

@login_required
def report_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    post = get_object_or_404(Post, id=post_id)
    reason = request.POST.get('reason')
    
    if not reason:
        return JsonResponse({'error': 'Report reason is required'}, status=400)
        
    PostReport.objects.create(
        user=request.user,
        post=post,
        reason=reason
    )
    
    return JsonResponse({'status': 'success'})

@login_required
def saved_posts(request):
    # Lấy các bài viết đã lưu
    saved_posts = SavedPost.objects.filter(user=request.user).select_related('post', 'post__author')
    
    # Chuyển đổi thành danh sách các bài viết
    posts = [saved_post.post for saved_post in saved_posts]
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'posts': page_obj,
        'is_saved_posts': True,
        'title': 'Bài viết đã lưu'
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def get_post_likes(request, post_id):
    """Lấy danh sách người đã thích bài viết"""
    post = get_object_or_404(Post, id=post_id)
    likes = []
    
    for like in Like.objects.filter(post=post).select_related('user'):
        user = like.user
        likes.append({
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                'avatar': user.avatar.url if user.avatar else None,
                'is_following': request.user.following.filter(id=user.id).exists() if request.user.is_authenticated else False
            }
        })
    
    return JsonResponse({'likes': likes})

@login_required
def like_comment(request, comment_id):
    """Thích/bỏ thích bình luận"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Kiểm tra xem người dùng đã thích bình luận chưa
    like, created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment
    )
    
    # Nếu đã thích thì bỏ thích
    if not created:
        like.delete()
        comment.likes_count = comment.likes.count()
        comment.save()
        return JsonResponse({'status': 'unliked', 'likes_count': comment.likes_count})
    
    # Cập nhật số lượng thích
    comment.likes_count = comment.likes.count()
    comment.save()
    
    # Gửi thông báo cho người viết bình luận
    if comment.author != request.user:
        Notification.objects.get_or_create(
            recipient=comment.author,
            sender=request.user,
            verb="đã thích",
            content_object=comment,
            action_object=comment
        )
    
    return JsonResponse({'status': 'liked', 'likes_count': comment.likes_count})

@login_required
@csrf_exempt
def api_add_comment(request):
    """API endpoint để thêm bình luận (REDIRECT)"""
    # Redirect từ /api/comments/add/ sang /api/posts/comments/add/
    return HttpResponseRedirect('/api/posts/comments/add/')

@login_required
def search(request):
    """
    Tìm kiếm bài viết và người dùng
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'posts/search_results.html', {
            'query': query,
        })
    
    # Tìm kiếm bài viết theo caption hoặc hashtag
    posts = Post.objects.filter(caption__icontains=query) | Post.objects.filter(hashtags__name__icontains=query)
    posts = posts.distinct().order_by('-created_at')
    
    # Tìm kiếm người dùng theo username, first_name, last_name
    users = User.objects.filter(
        username__icontains=query
    ) | User.objects.filter(
        first_name__icontains=query
    ) | User.objects.filter(
        last_name__icontains=query
    )
    users = users.distinct()
    
    # Phân trang cho bài viết
    post_paginator = Paginator(posts, 9)  # 9 bài viết mỗi trang
    post_page = request.GET.get('post_page', 1)
    posts_result = post_paginator.get_page(post_page)
    
    # Phân trang cho người dùng
    user_paginator = Paginator(users, 12)  # 12 người dùng mỗi trang
    user_page = request.GET.get('user_page', 1)
    users_result = user_paginator.get_page(user_page)
    
    return render(request, 'posts/search_results.html', {
        'query': query,
        'posts': posts_result,
        'users': users_result,
    })

@login_required
def api_load_posts(request):
    """API endpoint để tải thêm bài viết cho cuộn vô hạn"""
    page_number = request.GET.get('page', 1)
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1
    
    # Lấy tất cả bài viết, sắp xếp theo thời gian tạo mới nhất
    posts = Post.objects.all().order_by('-created_at')
    
    # Kiểm tra và xử lý avatar
    for post in posts:
        if not hasattr(post.author, 'avatar_url'):
            post.author.avatar_url = post.author.get_avatar_url()
    
    # Phân trang
    posts_per_page = settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 5
    paginator = Paginator(posts, posts_per_page)
    
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        # Nếu trang không tồn tại, trả về một danh sách trống
        return JsonResponse({'posts': [], 'has_next': False})
    
    # Chuẩn bị dữ liệu cho JSON response
    posts_data = []
    for post in page_obj.object_list:
        # Lấy tối đa 3 bình luận gốc cho mỗi bài viết
        root_comments = Comment.objects.filter(post=post, parent=None).order_by('-created_at')[:2]
        
        comments_with_replies = []
        for comment in root_comments:
            # Lấy tối đa 2 trả lời cho mỗi bình luận
            replies = Comment.objects.filter(parent=comment).order_by('-created_at')[:1]
            comments_with_replies.append({
                'comment': {
                    'id': comment.id,
                    'text': comment.text,
                    'created_at': comment.created_at.isoformat(),
                    'author': {
                        'id': comment.author.id,
                        'username': comment.author.username,
                        'avatar': comment.author.avatar.url if comment.author.avatar else None,
                    },
                    'likes_count': comment.likes_count,
                },
                'replies': [{
                    'id': reply.id,
                    'text': reply.text, 
                    'created_at': reply.created_at.isoformat(),
                    'author': {
                        'id': reply.author.id,
                        'username': reply.author.username,
                        'avatar': reply.author.avatar.url if reply.author.avatar else None,
                    },
                    'likes_count': reply.likes_count,
                    'parent_id': reply.parent_id,
                } for reply in replies],
                'replies_count': Comment.objects.filter(parent=comment).count()
            })
        
        # Lấy thông tin về media của bài viết
        media_files = []
        for media in post.post_media.all():
            media_files.append({
                'id': media.id,
                'file_url': media.file.url,
                'media_type': media.media_type,
                'order': media.order
            })
        
        posts_data.append({
            'id': post.id,
            'author': {
                'id': post.author.id,
                'username': post.author.username,
                'avatar': post.author.avatar.url if post.author.avatar else None,
            },
            'caption': post.caption,
            'location': post.location,
            'created_at': post.created_at.isoformat(),
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'is_liked': post.post_likes.filter(user=request.user).exists(),
            'is_saved': post.saved_by.filter(user=request.user).exists(),
            'comments_data': comments_with_replies,
            'media': media_files,
            'disable_comments': post.disable_comments,
            'total_comments': Comment.objects.filter(post=post).count()
        })
    
    return JsonResponse({
        'posts': posts_data,
        'has_next': page_obj.has_next()
    })
