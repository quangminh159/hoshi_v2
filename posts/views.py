from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.http import require_POST
from .models import Post, Comment, Like, SavedPost, Hashtag, Media, Mention, PostReport, PostMedia, CommentLike, UserInteraction
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import logging
import traceback
from accounts.models import UserBlock
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification
import re
from datetime import timedelta
from .forms import PostForm, CommentForm, PostReportForm
from .feed_algorithms import get_diverse_feed
from django.db import IntegrityError

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def home(request):
    # Nếu người dùng chưa đăng nhập, chuyển hướng đến trang đăng nhập
    if not request.user.is_authenticated:
        return redirect('account_login')
        
    logger.info(f"Bắt đầu xử lý trang chủ")
    logger.info(f"Người dùng: {request.user}")
    logger.info(f"Người dùng đã xác thực: {request.user.is_authenticated}")
    
    # Lấy tất cả bài viết, sắp xếp ngẫu nhiên mỗi lần tải lại trang
    posts = Post.objects.all().order_by('?')
    logger.info(f"Tổng số bài viết ban đầu: {posts.count()}")
    
    # Lấy danh sách người đã chặn người dùng hiện tại
    blocked_by_users = UserBlock.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    
    # Loại bỏ bài viết từ những người đã chặn người dùng hiện tại
    posts = posts.exclude(author_id__in=blocked_by_users)
    
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
            # Lấy replies cho mỗi comment
            replies = Comment.objects.filter(parent=comment).order_by('created_at')
            replies_with_like = []
            for reply in replies:
                replies_with_like.append({
                    'reply': reply,
                    'is_liked': CommentLike.objects.filter(user=request.user, comment=reply).exists()
                })
            comments_with_replies.append({
                'comment': comment,
                'is_liked': CommentLike.objects.filter(user=request.user, comment=comment).exists(),
                'replies': replies_with_like,
                'replies_count': replies.count()
            })
        
        # Thêm trường is_liked cho post
        post.is_liked = Like.objects.filter(user=request.user, post=post).exists()
        
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
    
    # Thêm debug để kiểm tra media
    for post in page_obj:
        logger.info(f"Post ID: {post.id} has {post.media.count()} media files")
        for media in post.media.all():
            logger.info(f"   - Media: {media.id}, Type: {media.media_type}, File: {media.file}")
    
    # Debug posts_with_data
    logger.info("Debug - Post data structure:")
    for post_data in posts_with_comments:
        post = post_data['post']
        logger.info(f"Post data - ID: {post.id}, Media count: {post.media.count()}")
    
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
    
    # Lấy danh sách người đã chặn người dùng hiện tại
    blocked_by_users = UserBlock.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    
    # Loại bỏ bài viết từ những người đã chặn người dùng hiện tại
    posts = posts.exclude(author_id__in=blocked_by_users)
    
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
    
    # Prefetch related data để tối ưu truy vấn
    posts = posts.select_related('author').prefetch_related(
        'media', 'comments', 'post_likes', 'saved_by'
    )
    
    # Kiểm tra và xử lý avatar
    for post in posts:
        if not hasattr(post.author, 'avatar_url'):
            post.author.avatar_url = post.author.get_avatar_url()
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Kiểm tra nếu yêu cầu JSON format
    if request.GET.get('format') == 'json':
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
            for media in post.media.all():
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
                'hide_likes': post.hide_likes,
                'total_comments': Comment.objects.filter(post=post).count()
            })
        
        return JsonResponse({
            'posts': posts_data,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None
        })
    
    # Prefetch bình luận và trả lời cho HTML response
    posts_with_comments = []
    for post in page_obj:
        # Lấy tối đa 3 bình luận gốc cho mỗi bài viết
        root_comments = Comment.objects.filter(post=post, parent=None).order_by('-created_at')[:3]
        
        comments_with_replies = []
        for comment in root_comments:
            # Lấy tối đa 2 trả lời cho mỗi bình luận
            replies = Comment.objects.filter(parent=comment).order_by('-created_at')[:2]
            replies_with_like = []
            for reply in replies:
                replies_with_like.append({
                    'reply': reply,
                    'is_liked': CommentLike.objects.filter(user=request.user, comment=reply).exists()
                })
            comments_with_replies.append({
                'comment': comment,
                'is_liked': CommentLike.objects.filter(user=request.user, comment=comment).exists(),
                'replies': replies_with_like,
                'replies_count': replies.count()
            })
        
        posts_with_comments.append({
            'post': post,
            'comments_data': comments_with_replies,
            'total_comments': Comment.objects.filter(post=post).count()
        })
    
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
    
    # Kiểm tra xem tác giả bài viết có chặn người dùng hiện tại không
    if UserBlock.objects.filter(blocker=post.author, blocked=request.user).exists():
        messages.error(request, 'Bạn không thể xem bài viết này vì tác giả đã chặn bạn.')
        return redirect('posts:feed')
    
    # Lấy tất cả comments của bài viết và phân loại
    root_comments = Comment.objects.filter(post=post, parent=None).order_by('created_at')
    
    comments_with_replies = []
    for comment in root_comments:
        # Lấy replies cho mỗi comment
        replies = Comment.objects.filter(parent=comment).order_by('created_at')
        replies_with_like = []
        for reply in replies:
            replies_with_like.append({
                'reply': reply,
                'is_liked': CommentLike.objects.filter(user=request.user, comment=reply).exists()
            })
        comments_with_replies.append({
            'comment': comment,
            'is_liked': CommentLike.objects.filter(user=request.user, comment=comment).exists(),
            'replies': replies_with_like,
            'replies_count': replies.count()
        })
    
    context = {
        'post': post,
        'comments_data': comments_with_replies,
        'total_comments': Comment.objects.filter(post=post).count(),
        'is_liked': Like.objects.filter(user=request.user, post=post).exists(),
    }
    return render(request, 'posts/post_detail.html', context)

@login_required
def create(request):
    """Create a new post"""
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            
            # Xử lý nhiều file đa phương tiện
            media_files = request.FILES.getlist('media')
            for index, file in enumerate(media_files):
                # Kiểm tra loại file
                if not file.content_type.startswith('image/') and not file.content_type.startswith('video/'):
                    messages.error(request, f'File {file.name} không hợp lệ. Chỉ chấp nhận file hình ảnh và video.')
                    continue
                
                # Kiểm tra kích thước file (tối đa 10MB)
                if file.size > 10 * 1024 * 1024:
                    messages.error(request, f'File {file.name} vượt quá kích thước cho phép (10MB).')
                    continue
                
                # Xác định loại media
                media_type = 'video' if file.content_type.startswith('video/') else 'image'
                
                # Lưu file
                PostMedia.objects.create(
                    post=post,
                    file=file,
                    media_type=media_type,
                    order=index
                )
            
            # Xử lý hashtags
            if post.caption:
                process_hashtags(post)
                
            messages.success(request, 'Bài viết đã được đăng thành công!')
            return HttpResponseRedirect('/')
    else:
        form = PostForm()
    
    return render(request, 'posts/create_post.html', {
        'form': form
    })

@login_required
def edit_post(request, post_id):
    """Chỉnh sửa bài viết"""
    post = get_object_or_404(Post, id=post_id, author=request.user)
    
    if request.method == 'POST':
        try:
            # Cập nhật caption và location
            old_caption = post.caption
            post.caption = request.POST.get('caption', '').strip()
            post.location = request.POST.get('location', '').strip()
            
            # Xử lý media mới (nếu có)
            new_media_files = []
            
            # Xử lý media từ form
            if 'media' in request.FILES:
                new_media_files = request.FILES.getlist('media')
            # Fallback cho các tên field khác có thể được sử dụng
            elif 'media[]' in request.FILES:
                new_media_files = request.FILES.getlist('media[]')
            elif 'new_media' in request.FILES:
                new_media_files = request.FILES.getlist('new_media')
                
            if new_media_files:
                # Không xóa media cũ, chỉ thêm media mới
                # Lấy số thứ tự cuối cùng hiện tại
                last_order = PostMedia.objects.filter(post=post).count()
                
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
                    media = PostMedia.objects.create(
                        post=post,
                        file=file,
                        media_type=media_type,
                        order=last_order + index
                    )
            
            # Xử lý xóa media nếu có request xóa
            deleted_media_ids = request.POST.get('deleted_media')
            if deleted_media_ids:
                try:
                    deleted_ids = json.loads(deleted_media_ids)
                    if deleted_ids:
                        PostMedia.objects.filter(id__in=deleted_ids, post=post).delete()
                except json.JSONDecodeError:
                    pass
            
            # Cập nhật hashtags nếu caption thay đổi
            if post.caption != old_caption:
                post.hashtags.clear()
                process_hashtags(post)
            
            # Lưu các thay đổi
            post.save()
            
            messages.success(request, 'Bài viết đã được cập nhật thành công!')
            return redirect('posts:post_detail', post_id=post.id)
            
        except Exception as e:
            messages.error(request, f'Lỗi: {str(e)}')
            return redirect('posts:edit', post_id=post.id)
    
    return render(request, 'posts/edit_post.html', {'post': post})

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
        media_count = post.media.count()
        post.media.all().delete()
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
@require_POST
def like_post(request, post_id):
    """Thích hoặc bỏ thích bài viết"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        # Kiểm tra xem người dùng có bị chặn không
        if UserBlock.objects.filter(blocker=post.author, blocked=request.user).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Bạn không thể thích bài viết này.'
            })
            
        if post.likes.filter(id=request.user.id).exists():
            # Nếu người dùng đã thích, bỏ thích
            post.likes.remove(request.user)
            liked = False
        else:
            # Nếu người dùng chưa thích, thêm thích
            post.likes.add(request.user)
            liked = True
            
            # Gửi thông báo cho người viết bài nếu không phải chính họ
            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    content_type=ContentType.objects.get_for_model(Post),
                    object_id=post.id,
                    notification_type='like',
                    text=f"{request.user.username} đã thích bài viết của bạn."
                )
        
        # Trả về số lượt thích mới
        likes_count = post.likes.count()
        
        return JsonResponse({
            'status': 'success',
            'liked': liked,
            'likes_count': likes_count
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
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
@require_POST
def add_comment(request, post_id):
    """Thêm bình luận vào bài viết"""
    post = get_object_or_404(Post, id=post_id)
    
    text = request.POST.get('text')
    parent_id = request.POST.get('parent_id')
    
    if not text:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Nội dung bình luận không được để trống'
            })
        messages.error(request, 'Nội dung bình luận không được để trống')
        return redirect('posts:post_detail', post_id=post_id)
    
    # Kiểm tra xem bài viết có tắt bình luận không
    if post.disable_comments:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Bài viết này đã tắt bình luận'
            })
        messages.error(request, 'Bài viết này đã tắt bình luận')
        return redirect('posts:post_detail', post_id=post_id)
    
    # Nếu là trả lời bình luận, kiểm tra parent comment
    parent = None
    if parent_id:
        try:
            parent = Comment.objects.get(id=parent_id, post=post)
        except Comment.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Bình luận gốc không tồn tại'
                })
            messages.error(request, 'Bình luận gốc không tồn tại')
            return redirect('posts:post_detail', post_id=post_id)
    
    # Tạo bình luận mới
    comment = Comment.objects.create(
        post=post,
        author=request.user,
        text=text,
        parent=parent
    )
    
    # Tăng comment_count
    post.comments_count = post.comments.count()
    post.save()
    
    # Gửi thông báo cho người đăng bài viết
    if post.author != request.user:
        Notification.objects.get_or_create(
            recipient=post.author,
            sender=request.user,
            notification_type='comment',
            text=f"{request.user.username} đã bình luận về bài viết của bạn",
            post=post,
            comment=comment,
            content_type=ContentType.objects.get_for_model(post),
            object_id=post.id
        )
    
    # Gửi thông báo cho người được trả lời
    if parent and parent.author != request.user:
        Notification.objects.get_or_create(
            recipient=parent.author,
            sender=request.user,
            notification_type='comment',
            text=f"{request.user.username} đã trả lời bình luận của bạn",
            post=post,
            comment=comment,
            content_type=ContentType.objects.get_for_model(comment),
            object_id=comment.id
        )
    
    # Nếu là AJAX request, trả về JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'id': comment.id,
            'text': comment.text,
            'created_at': comment.created_at.isoformat(),
            'author': {
                'id': request.user.id,
                'username': request.user.username,
                'avatar': request.user.avatar.url if request.user.avatar else None
            },
            'post_id': post.id,
            'parent_id': parent.id if parent else None
        })
    
    # Nếu không phải AJAX, redirect như bình thường
    messages.success(request, 'Đã thêm bình luận thành công')
    return redirect('posts:post_detail', post_id=post_id)

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
    tag = request.GET.get('tag')
    if tag:
        posts = Post.objects.filter(hashtags__name=tag)
    else:
        # Hiển thị bài viết phổ biến
        posts = Post.objects.annotate(
            engagement=Count('post_likes') + Count('comments')
        ).order_by('-engagement')
    
    # Lọc theo media type
    media_type = request.GET.get('media_type', 'all')
    if media_type in ['image', 'video']:
        posts = posts.filter(media__media_type=media_type)
    
    # Lọc theo sort
    sort = request.GET.get('sort', 'popular')
    if sort == 'recent':
        posts = posts.order_by('-created_at')
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Lấy hashtags phổ biến
    popular_tags = Hashtag.objects.annotate(
        tag_posts_count=Count('posts')
    ).order_by('-tag_posts_count')[:10]
    
    # Kiểm tra nếu yêu cầu JSON format
    if request.GET.get('format') == 'json':
        posts_data = []
        for post in page_obj.object_list:
            media_files = []
            for media in post.media.all():
                media_files.append({
                    'id': media.id,
                    'file': media.file.url,
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
                'is_liked': post.post_likes.filter(user=request.user).exists() if request.user.is_authenticated else False,
                'is_saved': post.saved_by.filter(user=request.user).exists() if request.user.is_authenticated else False,
                'media': media_files,
                'hide_likes': post.hide_likes,
                'disable_comments': post.disable_comments
            })
        
        return JsonResponse({
            'posts': posts_data,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None
        })
    
    context = {
        'posts': page_obj,
        'popular_tags': popular_tags,
        'tag': tag,
        'media_type': media_type,
        'sort': sort
    }
    return render(request, 'posts/explore.html', context)

@login_required
def report_post(request, post_id):
    """View để báo cáo bài viết vi phạm"""
    post = get_object_or_404(Post, id=post_id)
    
    # Kiểm tra xem người dùng có báo cáo bài viết này trước đó không
    existing_report = PostReport.objects.filter(user=request.user, post=post).exists()
    if existing_report:
        messages.info(request, 'Bạn đã báo cáo bài viết này trước đó. Chúng tôi đang xem xét báo cáo của bạn.')
        return redirect('posts:post_detail', post_id=post.id)
    
    # Kiểm tra xem người dùng có báo cáo bài viết của chính họ không
    if post.author == request.user:
        messages.error(request, 'Bạn không thể báo cáo bài viết của chính mình.')
        return redirect('posts:post_detail', post_id=post.id)
    
    if request.method == 'POST':
        form = PostReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.post = post
            
            try:
                report.save()
                messages.success(request, 'Cảm ơn bạn đã báo cáo bài viết này. Chúng tôi sẽ xem xét báo cáo của bạn.')
                return redirect('posts:post_detail', post_id=post.id)
            except IntegrityError:
                # Trong trường hợp unique constraint bị vi phạm
                messages.info(request, 'Bạn đã báo cáo bài viết này trước đó.')
                return redirect('posts:post_detail', post_id=post.id)
    else:
        form = PostReportForm()
    
    return render(request, 'posts/report_post.html', {
        'form': form,
        'post': post
    })

@login_required
def report_post_modal(request, post_id):
    """API để hiển thị modal báo cáo bài viết"""
    if request.method == 'GET':
        post = get_object_or_404(Post, id=post_id)
        form = PostReportForm()
        
        html = render(request, 'posts/report_post_modal.html', {
            'form': form,
            'post': post
        }).content.decode('utf-8')
        
        return JsonResponse({'html': html})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def report_post_ajax(request, post_id):
    """API để báo cáo bài viết qua AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    post = get_object_or_404(Post, id=post_id)
    
    # Kiểm tra xem người dùng có báo cáo bài viết của chính họ không
    if post.author == request.user:
        return JsonResponse({'error': 'Bạn không thể báo cáo bài viết của chính mình.'}, status=403)
    
    # Kiểm tra xem người dùng có báo cáo bài viết này trước đó không
    existing_report = PostReport.objects.filter(user=request.user, post=post).exists()
    if existing_report:
        return JsonResponse({'error': 'Bạn đã báo cáo bài viết này trước đó.'}, status=400)
    
    form = PostReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.user = request.user
        report.post = post
        
        try:
            report.save()
            return JsonResponse({'success': 'Cảm ơn bạn đã báo cáo bài viết này. Chúng tôi sẽ xem xét báo cáo của bạn.'})
        except IntegrityError:
            return JsonResponse({'error': 'Bạn đã báo cáo bài viết này trước đó.'}, status=400)
    else:
        return JsonResponse({'error': form.errors}, status=400)

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
    
    # Chuẩn bị dữ liệu bài viết cho template feed
    posts_with_data = []
    for post in page_obj:
        posts_with_data.append({
            'post': post,
            'post_type': 'saved'
        })
    
    context = {
        'posts_with_data': posts_with_data,
        'page_obj': page_obj,
        'feed_type': 'saved',
        'title': 'Bài viết đã lưu'
    }
    return render(request, 'posts/feed.html', context)

@login_required
def liked_posts(request):
    # Lấy các bài viết đã thích
    liked_posts = Like.objects.filter(user=request.user).select_related('post', 'post__author')
    
    # Chuyển đổi thành danh sách các bài viết
    posts = [like.post for like in liked_posts]
    
    # Phân trang
    paginator = Paginator(posts, settings.POSTS_PER_PAGE if hasattr(settings, 'POSTS_PER_PAGE') else 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Chuẩn bị dữ liệu bài viết cho template feed
    posts_with_data = []
    for post in page_obj:
        posts_with_data.append({
            'post': post,
            'post_type': 'liked'
        })
    
    context = {
        'posts_with_data': posts_with_data,
        'page_obj': page_obj,
        'feed_type': 'liked',
        'title': 'Bài viết đã thích'
    }
    return render(request, 'posts/feed.html', context)

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
    
    # Lọc bỏ bài viết của những người đã chặn người dùng hiện tại
    blocked_by_users = UserBlock.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    posts = posts.exclude(author_id__in=blocked_by_users)
    
    # Tìm kiếm người dùng theo username, first_name, last_name
    users = User.objects.filter(
        username__icontains=query
    ) | User.objects.filter(
        first_name__icontains=query
    ) | User.objects.filter(
        last_name__icontains=query
    )
    
    # Loại bỏ những người đã chặn người dùng hiện tại
    users = users.exclude(id__in=blocked_by_users)
    
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
    feed_type = request.GET.get('feed', 'diverse')
    
    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1
    
    # Tính tổng số bài viết có thể hiển thị cho người dùng
    total_posts = Post.objects.filter(
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=request.user.blocked_users.all()
    ).exclude(
        author__in=request.user.blocked_by.all()
    ).count()

    # Lấy bài viết dựa trên loại feed
    if feed_type == 'flowed':
        # Lấy bài viết từ người đang theo dõi
        following_users = request.user.following.values_list('id', flat=True)
        posts = Post.objects.filter(
            Q(author__id__in=following_users) | Q(author=request.user),
            is_archived=False
        ).order_by('-created_at')
    else:  # diverse feed
        # Sử dụng feed đa dạng với page_size=12 (thay vì 10)
        posts = get_diverse_feed(request.user, page_size=12, page=page_number)
        
    # Chuẩn bị dữ liệu JSON
    posts_data = prepare_posts_json(posts, request.user)
    
    # Tính toán xem còn trang tiếp theo không
    has_next = (page_number * 12) < total_posts

    return JsonResponse({
        'posts': posts_data,
        'has_next': has_next,
        'total_posts': total_posts  # Thêm total_posts vào response
    })

def prepare_posts_json(posts, user):
    """Helper để chuẩn bị dữ liệu posts cho JSON responses"""
    posts_data = []
    for post in posts:
        # Lấy media
        media_files = [{
            'id': media.id,
            'file_url': media.file.url,
            'media_type': media.media_type,
            'order': media.order
        } for media in post.media.all()]
        
        # Lấy comments
        comments_data = []
        for comment in Comment.objects.filter(post=post, parent=None).order_by('-created_at')[:3]:
            replies = Comment.objects.filter(parent=comment).order_by('-created_at')[:2]
            comments_data.append({
                'comment': {
                    'id': comment.id,
                    'text': comment.text,
                    'created_at': comment.created_at.isoformat(),
                    'author': {
                        'id': comment.author.id,
                        'username': comment.author.username,
                        'avatar': comment.author.get_avatar_url(),
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
                        'avatar': reply.author.get_avatar_url(),
                    },
                    'likes_count': reply.likes_count,
                } for reply in replies],
                'replies_count': Comment.objects.filter(parent=comment).count()
            })
        
        # Xác định post type
        post_type = determine_post_type(user, post)
        
        posts_data.append({
            'id': post.id,
            'author': {
                'id': post.author.id,
                'username': post.author.username,
                'avatar': post.author.get_avatar_url(),
            },
            'caption': post.caption,
            'location': post.location,
            'created_at': post.created_at.isoformat(),
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'is_liked': Like.objects.filter(user=user, post=post).exists(),
            'is_saved': SavedPost.objects.filter(user=user, post=post).exists(),
            'media': media_files,
            'comments_data': comments_data,
            'post_type': post_type,
            'total_comments': Comment.objects.filter(post=post).count()
        })
    
    return posts_data

@login_required
def index(request):
    """Display the user's feed"""
    user = request.user
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    # Đặt số lượng bài viết mỗi trang là 12
    posts_per_page = 12
    feed_type = request.GET.get('feed', 'diverse')
    is_json_request = request.GET.get('format') == 'json'
    
    # Tính tổng số bài viết có thể hiển thị
    total_posts = Post.objects.filter(
        is_archived=False,
        author__is_suspended=False
    ).exclude(
        author__in=user.blocked_users.all()
    ).exclude(
        author__in=user.blocked_by.all()
    ).count()

    # Tính toán số trang tối đa
    max_pages = (total_posts // posts_per_page) + (1 if total_posts % posts_per_page > 0 else 0)
    has_more_posts = page < max_pages
    
    # Lấy bài viết cho trang hiện tại
    posts = get_diverse_feed(user, page_size=posts_per_page, page=page)
    
    # Nếu yêu cầu JSON, trả về dữ liệu JSON
    if is_json_request:
        posts_data = []
        for post in posts:
            # Lấy thông tin về media của bài viết
            media_files = []
            for media in post.media.all():
                media_files.append({
                    'id': media.id,
                    'file_url': media.file.url,
                    'media_type': media.media_type,
                    'order': media.order
                })
            
            # Lấy bình luận cho bài viết
            comments_data = []
            for comment_data in get_post_comments(post)[:3]:
                comments_data.append({
                    'comment': {
                        'id': comment_data['comment'].id,
                        'text': comment_data['comment'].text,
                        'created_at': comment_data['comment'].created_at.isoformat(),
                        'author': {
                            'id': comment_data['comment'].author.id,
                            'username': comment_data['comment'].author.username,
                            'avatar': comment_data['comment'].author.get_avatar_url(),
                        }
                    },
                    'replies_count': comment_data['replies_count']
                })
            
            post_type = determine_post_type(user, post)
            
            posts_data.append({
                'id': post.id,
                'author': {
                    'id': post.author.id,
                    'username': post.author.username,
                    'avatar': post.author.get_avatar_url(),
                },
                'caption': post.caption,
                'location': post.location,
                'created_at': post.created_at.isoformat(),
                'likes_count': post.post_likes.count(),
                'comments_count': post.comments.count(),
                'is_liked': post.post_likes.filter(user=user).exists(),
                'is_saved': post.saved_by.filter(user=user).exists(),
                'media': media_files,
                'comments_data': comments_data,
                'total_comments': post.comments.count(),
                'post_type': post_type
            })
        
        return JsonResponse({
            'posts': posts_data,
            'has_next': has_more_posts,
            'total_posts': total_posts  # Thêm total_posts vào response
        })
    
    # Đánh dấu bài viết theo loại để hiển thị nhãn
    posts_with_data = []
    for post in posts:
        # Điền các thông tin chi tiết
        post_data = {
            'post': post,
            'comments_data': get_post_comments(post)[:3],  
            'total_comments': post.comments.count(),
            'total_likes': post.post_likes.count(),
            'is_liked': post.post_likes.filter(user=user).exists(),
            'is_saved': post.saved_by.filter(user=user).exists(),
            'post_type': determine_post_type(user, post)  
        }
        posts_with_data.append(post_data)
    
    # Tracking trải nghiệm feed của người dùng
    track_feed_impression(user, posts)
    
    # Tạo một đối tượng page_obj giả để template có thể sử dụng
    class PageObj:
        def __init__(self, page, has_next):
            self.number = page
            self.has_next_page = has_next
            
        def has_next(self):
            return self.has_next_page
    
    page_obj = PageObj(page, has_more_posts)
    
    return render(request, 'posts/feed.html', {
        'posts_with_data': posts_with_data,
        'feed_type': feed_type,
        'page': page,
        'page_obj': page_obj,
        'total_posts': total_posts  # Thêm total_posts vào context
    })

def determine_post_type(user, post):
    """Xác định loại bài viết để hiển thị nhãn"""
    if post.author in user.following.all():
        return 'flowed'
    
    # Kiểm tra hashtag phổ biến mà người dùng thích
    user_liked_posts = Post.objects.filter(post_likes__user=user)
    user_hashtags = set()
    for liked_post in user_liked_posts:
        user_hashtags.update(liked_post.hashtags.all())
    
    if any(hashtag in post.hashtags.all() for hashtag in user_hashtags):
        return 'recommended'
    
    # Kiểm tra nếu là bài viết có lượt tương tác cao gần đây
    time_threshold = timezone.now() - timezone.timedelta(hours=48)
    recent_likes = post.post_likes.filter(created_at__gte=time_threshold).count()
    recent_comments = post.comments.filter(created_at__gte=time_threshold).count()
    
    if recent_likes >= 10 or recent_comments >= 5:
        return 'trending'
    
    return 'discover'

def track_feed_impression(user, posts):
    """Theo dõi các bài viết được hiển thị cho người dùng"""
    for post in posts:
        # Ghi lại bài viết đã hiển thị
        UserInteraction.objects.create(
            user=user,
            post=post,
            interaction_type='view'
        )

def get_post_comments(post):
    """Helper để lấy comments cho bài viết kèm với thông tin replies"""
    comments = Comment.objects.filter(
        post=post,
        parent=None
    ).select_related('author').order_by('-created_at')
    
    comments_data = []
    for comment in comments:
        replies = Comment.objects.filter(
            parent=comment
        ).select_related('author').order_by('created_at')
        
        data = {
            'comment': comment,
            'replies': replies,
            'replies_count': replies.count()
        }
        comments_data.append(data)
    
    return comments_data

def process_hashtags(post):
    """Extract and process hashtags from post caption"""
    if not post.caption:
        return
    
    # Tìm tất cả các hashtag trong caption
    hashtags = [word[1:] for word in post.caption.split() if word.startswith('#')]
    
    # Tạo hoặc lấy hashtag objects và liên kết với bài viết
    for tag_name in hashtags:
        if tag_name:  # Chỉ xử lý nếu tag không rỗng
            try:
                hashtag, created = Hashtag.objects.get_or_create(name=tag_name)
                hashtag.posts.add(post)
            except Exception as e:
                print(f"Error processing hashtag {tag_name}: {str(e)}")