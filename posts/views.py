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
from .feed_algorithms import get_diverse_feed, get_followed_feed
from django.db import IntegrityError
from .comment_utils import (
    get_root_comment,
    get_root_comments_qs,
    get_thread_replies_qs,
    get_thread_reply_ids,
    resolve_reply_parent,
)

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
def home(request):
    """Trang chủ dùng feed shell nhẹ; bài viết load qua /posts/?format=json."""
    if not request.user.is_authenticated:
        return redirect('account_login')
    return index(request)


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
        following_users = request.user.get_following_user_ids()
        
        # Nếu có người theo dõi, ưu tiên bài viết của những người đang theo dõi
        if following_users:
            following_posts = posts.filter(
                Q(author__id__in=following_users) | Q(author=request.user)
            )
            
            # Nếu có bài viết của những người đang theo dõi, sử dụng các bài viết này
            if following_posts.exists():
                posts = following_posts
    
    # Nếu không có bài viết của người theo dõi, sử dụng tất cả bài viết
    logger.debug("Feed posts queryset ready")
    
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
            root_comments = get_root_comments_qs(post)[:2]
            
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
        root_comments = get_root_comments_qs(post)[:3]
        
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
    
    logger.debug("Feed filtering complete")
    
    # Kiểm tra điều kiện lọc bài viết
    context = {
        'posts_with_data': posts_with_comments,
        'page_obj': page_obj,
    }
    return render(request, 'posts/feed.html', context)

def _deny_private_post_access(request, post, as_json=False):
    """Chặn tương tác với bài của tài khoản riêng tư nếu chưa theo dõi."""
    if post.author.posts_visible_to(request.user):
        return None
    message = 'Bài viết này thuộc tài khoản riêng tư. Hãy theo dõi để xem.'
    if as_json:
        return JsonResponse({'status': 'error', 'message': message}, status=403)
    messages.error(request, message)
    return redirect('posts:index')


@login_required
def post_detail(request, post_id):
    """Hiển thị chi tiết bài viết"""
    post = get_object_or_404(Post, id=post_id)
    
    # Kiểm tra xem tác giả bài viết có chặn người dùng hiện tại không
    if UserBlock.objects.filter(blocker=post.author, blocked=request.user).exists():
        messages.error(request, 'Bạn không thể xem bài viết này vì tác giả đã chặn bạn.')
        return redirect('posts:index')

    denied = _deny_private_post_access(request, post)
    if denied:
        return denied
    
    # Bình luận: nhiều tim + trả lời lên trước, sau đó mới nhất
    root_comments = get_root_comments_qs(post)

    comments_with_replies = []
    for comment in root_comments:
        replies = Comment.objects.filter(parent=comment).order_by('-likes_count', '-created_at')
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
            'replies_count': getattr(comment, 'replies_total', None) or replies.count()
        })
    
    context = {
        'post': post,
        'comments_data': comments_with_replies,
        'total_comments': Comment.objects.filter(post=post).count(),
        'is_liked': Like.objects.filter(user=request.user, post=post).exists(),
    }
    return render(request, 'posts/post_detail.html', context)

def _get_uploaded_media_files(request):
    """Lấy danh sách file media từ request (hỗ trợ nhiều tên field)."""
    for field_name in ('media', 'media[]', 'new_media'):
        files = request.FILES.getlist(field_name)
        if files:
            return files
    return []


def _media_type_for_file(uploaded_file):
    """Xác định loại media từ content-type hoặc phần mở rộng file."""
    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    filename = (uploaded_file.name or '').lower()

    audio_extensions = (
        '.mp3', '.m4a', '.wav', '.ogg', '.aac', '.flac', '.wma', '.opus', '.oga',
    )
    video_extensions = (
        '.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.wmv',
        '.3gp', '.3gpp', '.mpeg', '.mpg', '.flv', '.ts', '.mts',
    )
    image_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif',
    )

    # Audio trước video (ghi âm browser thường ra audio/webm hoặc video/webm)
    if content_type.startswith('audio/'):
        return 'audio'
    if filename.endswith(audio_extensions):
        return 'audio'
    # Voice recording: tên voice-* + webm/m4a/ogg
    if filename.startswith('voice-') and filename.endswith(('.webm', '.m4a', '.ogg', '.mp4')):
        return 'audio'

    if content_type.startswith('video/'):
        return 'video'
    if content_type.startswith('image/'):
        return 'image'

    if filename.endswith(video_extensions):
        return 'video'
    if filename.endswith(image_extensions):
        return 'image'

    # Một số trình duyệt/OS gửi file với content-type chung
    if content_type in ('application/octet-stream', 'binary/octet-stream', 'application/mp4'):
        if filename.endswith(audio_extensions):
            return 'audio'
        if filename.endswith(video_extensions):
            return 'video'
        if filename.endswith(image_extensions):
            return 'image'

    return None


def _is_ajax_request(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


@login_required
def create(request):
    """Create a new post"""
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            media_files = _get_uploaded_media_files(request)
            caption = (form.cleaned_data.get('caption') or '').strip()

            if not media_files and not caption:
                error_message = 'Vui lòng nhập nội dung hoặc chọn ít nhất một ảnh/video/âm thanh.'
                if _is_ajax_request(request):
                    return JsonResponse({'error': error_message}, status=400)
                messages.error(request, error_message)
                return render(request, 'posts/create_post.html', {'form': form})

            post = form.save(commit=False)
            post.author = request.user
            post.caption = caption
            post.save()

            saved_media_count = 0
            upload_errors = []
            max_upload_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)

            for file in media_files:
                media_type = _media_type_for_file(file)
                if not media_type:
                    upload_errors.append(
                        f'File {file.name} không hợp lệ. Chỉ chấp nhận ảnh, video hoặc âm thanh.'
                    )
                    continue

                if file.size > max_upload_size:
                    upload_errors.append(
                        f'File {file.name} vượt quá kích thước cho phép ({max_upload_size // (1024 * 1024)}MB).'
                    )
                    continue

                PostMedia.objects.create(
                    post=post,
                    file=file,
                    media_type=media_type,
                    order=saved_media_count
                )
                saved_media_count += 1

            # Có chọn file nhưng không lưu được cái nào → lỗi (trừ khi đã có caption)
            if media_files and saved_media_count == 0:
                if not caption:
                    post.delete()
                    error_message = ' '.join(upload_errors) if upload_errors else 'Không thể tải lên media.'
                    if _is_ajax_request(request):
                        return JsonResponse({'error': error_message}, status=400)
                    messages.error(request, error_message)
                    return render(request, 'posts/create_post.html', {'form': form})
                for error_message in upload_errors:
                    messages.warning(request, error_message)
            elif upload_errors:
                for error_message in upload_errors:
                    messages.warning(request, error_message)

            if post.caption:
                process_hashtags(post)
                process_mentions(post)

            messages.success(request, 'Bài viết đã được đăng thành công!')
            if _is_ajax_request(request):
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('posts:index'),
                    'post_id': post.id,
                    'media_count': saved_media_count,
                })
            return HttpResponseRedirect(reverse('posts:index'))

        if _is_ajax_request(request):
            return JsonResponse({'error': form.errors.as_json()}, status=400)
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
            new_media_files = _get_uploaded_media_files(request)
            max_upload_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
                
            if new_media_files:
                last_order = PostMedia.objects.filter(post=post).count()
                
                for index, file in enumerate(new_media_files):
                    if file.size > max_upload_size:
                        messages.error(request, f'Kích thước file không được vượt quá {max_upload_size/1024/1024:.0f}MB')
                        return redirect('posts:edit', post_id=post.id)
                    
                    media_type = _media_type_for_file(file)
                    if not media_type:
                        messages.error(request, f'File {file.name} không hợp lệ. Chỉ chấp nhận ảnh, video hoặc âm thanh.')
                        return redirect('posts:edit', post_id=post.id)
                    
                    PostMedia.objects.create(
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
            
            # Cập nhật hashtags/mentions nếu caption thay đổi
            if post.caption != old_caption:
                post.hashtags.clear()
                process_hashtags(post)
                process_mentions(post)
            
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

        denied = _deny_private_post_access(request, post, as_json=True)
        if denied:
            return denied
            
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
    denied = _deny_private_post_access(request, post, as_json=True)
    if denied:
        return denied
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
    """Thêm bình luận vào bài viết (text và/hoặc ảnh/video ngắn/ghi âm)."""
    from .comment_media import validate_comment_image, validate_comment_video, validate_comment_audio

    post = get_object_or_404(Post, id=post_id)

    denied = _deny_private_post_access(
        request, post, as_json=request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if denied:
        return denied

    text = (request.POST.get('text') or '').strip()
    parent_id = request.POST.get('parent_id')
    image = request.FILES.get('image')
    video = request.FILES.get('video')
    audio = request.FILES.get('audio')

    media_count = sum(1 for f in (image, video, audio) if f)
    if not text and media_count == 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Vui lòng nhập nội dung, chọn ảnh/video hoặc ghi âm'
            })
        messages.error(request, 'Vui lòng nhập nội dung, chọn ảnh/video hoặc ghi âm')
        return redirect('posts:post_detail', post_id=post_id)

    if media_count > 1:
        msg = 'Chỉ chọn một trong ảnh, video hoặc ghi âm cho mỗi bình luận'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect('posts:post_detail', post_id=post_id)

    if image:
        err = validate_comment_image(image)
        if err:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': err})
            messages.error(request, err)
            return redirect('posts:post_detail', post_id=post_id)

    if video:
        err = validate_comment_video(video)
        if err:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': err})
            messages.error(request, err)
            return redirect('posts:post_detail', post_id=post_id)

    if audio:
        err = validate_comment_audio(audio)
        if err:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': err})
            messages.error(request, err)
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
    direct_parent = None
    if parent_id:
        try:
            root_parent, direct_parent = resolve_reply_parent(post, parent_id)
            parent = root_parent
        except Comment.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Bình luận gốc không tồn tại'
                })
            messages.error(request, 'Bình luận gốc không tồn tại')
            return redirect('posts:post_detail', post_id=post_id)

    # Tạo bình luận mới
    comment = Comment(
        post=post,
        author=request.user,
        text=text,
        parent=parent,
    )
    if image:
        comment.image = image
    if video:
        comment.video = video
    if audio:
        comment.audio = audio
    comment.save()

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
    notify_parent = direct_parent or parent
    if notify_parent and notify_parent.author != request.user:
        Notification.objects.get_or_create(
            recipient=notify_parent.author,
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
            'text': comment.text or '',
            'image': comment.image_url,
            'image_url': comment.image_url,
            'video': comment.video_url,
            'video_url': comment.video_url,
            'audio': comment.audio_url,
            'audio_url': comment.audio_url,
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

    comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    post = comment.post

    # Người viết comment hoặc chủ bài viết mới được xóa
    if comment.author_id != request.user.id and post.author_id != request.user.id:
        return JsonResponse({'error': 'Bạn không có quyền xóa bình luận này'}, status=403)

    comment.delete()

    post.comments_count = post.comments.count()
    post.save(update_fields=['comments_count'])

    return JsonResponse({'status': 'success'})

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
    if request.GET.get('format') != 'json':
        return render(request, 'posts/feed.html', {
            'feed_type': 'saved',
            'title': 'Bài viết đã lưu',
        })

    posts_per_page = getattr(settings, 'POSTS_PER_PAGE', 12)
    saved_qs = SavedPost.objects.filter(user=request.user).select_related(
        'post', 'post__author'
    ).prefetch_related('post__media').order_by('-created_at')

    posts = [saved_post.post for saved_post in saved_qs]
    paginator = Paginator(posts, posts_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return JsonResponse({
        'posts': prepare_posts_json(page_obj.object_list, request.user, include_comments=True),
        'has_next': page_obj.has_next(),
    })

@login_required
def liked_posts(request):
    if request.GET.get('format') != 'json':
        return render(request, 'posts/feed.html', {
            'feed_type': 'liked',
            'title': 'Bài viết đã thích',
        })

    posts_per_page = getattr(settings, 'POSTS_PER_PAGE', 12)
    liked_qs = Like.objects.filter(user=request.user).select_related(
        'post', 'post__author'
    ).prefetch_related('post__media').order_by('-created_at')

    posts = [like.post for like in liked_qs]
    paginator = Paginator(posts, posts_per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return JsonResponse({
        'posts': prepare_posts_json(page_obj.object_list, request.user, include_comments=True),
        'has_next': page_obj.has_next(),
    })

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
                'is_following': request.user.is_following_user(user) if request.user.is_authenticated else False
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
            'posts': [],
            'users': [],
        })

    posts = (
        Post.objects.filter(caption__icontains=query)
        | Post.objects.filter(hashtags__name__icontains=query)
    )
    posts = posts.select_related('author').prefetch_related('media').distinct().order_by('-created_at')

    blocked_by_users = UserBlock.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    posts = posts.exclude(author_id__in=blocked_by_users)

    following_ids = request.user.get_following_user_ids()
    posts = posts.exclude(
        Q(author__private_account=True)
        & ~Q(author_id__in=following_ids)
        & ~Q(author=request.user)
    )

    users = (
        User.objects.filter(username__icontains=query)
        | User.objects.filter(first_name__icontains=query)
        | User.objects.filter(last_name__icontains=query)
    )
    users = users.exclude(id__in=blocked_by_users).exclude(id=request.user.id).distinct().order_by('username')

    post_paginator = Paginator(posts, 9)
    post_page = request.GET.get('post_page', 1)
    posts_result = post_paginator.get_page(post_page)

    user_paginator = Paginator(users, 12)
    user_page = request.GET.get('user_page', 1)
    users_result = user_paginator.get_page(user_page)

    return render(request, 'posts/search_results.html', {
        'query': query,
        'posts': posts_result,
        'users': users_result,
    })

def _parse_feed_seen_ids(raw_value, limit=80):
    """Parse seen=1,2,3 thành list id (giới hạn độ dài URL)."""
    if not raw_value:
        return []
    ids = []
    seen = set()
    for part in str(raw_value).split(','):
        part = part.strip()
        if not part:
            continue
        try:
            pid = int(part)
        except ValueError:
            continue
        if pid in seen:
            continue
        seen.add(pid)
        ids.append(pid)
        if len(ids) >= limit:
            break
    return ids


@login_required
def api_load_posts(request):
    """API endpoint để tải thêm bài viết cho cuộn vô hạn"""
    page_number = request.GET.get('page', 1)
    feed_type = request.GET.get('feed', 'diverse')

    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1

    if feed_type == 'flowed':
        posts = get_followed_feed(request.user, page_size=12, page=page_number)
    else:
        posts = get_diverse_feed(
            request.user,
            page_size=12,
            page=page_number,
            seed=request.GET.get('seed'),
            seen_ids=_parse_feed_seen_ids(request.GET.get('seen')),
        )

    posts_data = prepare_posts_json(posts, request.user)
    has_next = len(posts) >= 12

    return JsonResponse({
        'posts': posts_data,
        'has_next': has_next,
    })

FEED_COMMENTS_PREVIEW = 2
FEED_COMMENTS_PAGE_SIZE = 7
FEED_REPLIES_PREVIEW = 2
FEED_REPLIES_PAGE_SIZE = 7


def _comment_payload(comment_obj, liked_comment_ids, parent_id=None, user=None, post_author_id=None):
    can_delete = False
    can_edit = False
    if user is not None and getattr(user, 'is_authenticated', False):
        can_edit = comment_obj.author_id == user.id
        can_delete = (
            can_edit
            or (post_author_id is not None and post_author_id == user.id)
        )
    is_edited = False
    if comment_obj.updated_at and comment_obj.created_at:
        is_edited = (comment_obj.updated_at - comment_obj.created_at).total_seconds() > 2
    data = {
        'id': comment_obj.id,
        'text': comment_obj.text or '',
        'image': comment_obj.image_url,
        'image_url': comment_obj.image_url,
        'video': comment_obj.video_url,
        'video_url': comment_obj.video_url,
        'audio': comment_obj.audio_url,
        'audio_url': comment_obj.audio_url,
        'created_at': comment_obj.created_at.isoformat(),
        'updated_at': comment_obj.updated_at.isoformat() if comment_obj.updated_at else None,
        'author_id': comment_obj.author_id,
        'author_username': comment_obj.author.username,
        'likes_count': comment_obj.likes_count,
        'is_liked': comment_obj.id in liked_comment_ids,
        'can_delete': can_delete,
        'can_edit': can_edit,
        'is_edited': is_edited,
    }
    if parent_id is not None:
        data['parent_id'] = parent_id
    return data


def build_comment_replies_data(parent_comment, user, limit=FEED_REPLIES_PREVIEW, offset=0, replies_count=None):
    """Replies for one root comment thread (includes replies-to-replies, shown flat)."""
    root = get_root_comment(parent_comment)
    post = parent_comment.post
    post_author_id = post.author_id
    reply_qs = get_thread_replies_qs(post, root)
    if replies_count is None:
        replies_count = reply_qs.count()

    replies = list(reply_qs[offset:offset + limit])
    reply_ids = [r.id for r in replies]
    liked_comment_ids = set(
        CommentLike.objects.filter(user=user, comment_id__in=reply_ids)
        .values_list('comment_id', flat=True)
    ) if reply_ids else set()

    loaded = offset + len(replies)
    return {
        'replies': [
            _comment_payload(
                r, liked_comment_ids, parent_id=root.id,
                user=user, post_author_id=post_author_id,
            )
            for r in replies
        ],
        'replies_count': replies_count,
        'has_more_replies': loaded < replies_count,
        'next_offset': loaded if loaded < replies_count else None,
        'root_comment_id': root.id,
    }


def build_feed_comments_data(post, user, limit=FEED_COMMENTS_PREVIEW, offset=0):
    """Root comments: nhiều tim + trả lời trước, rồi mới nhất."""
    root_qs = get_root_comments_qs(post)
    root_comments_count = root_qs.count()
    post_author_id = post.author_id

    root_comments = list(root_qs[offset:offset + limit])

    replies_by_parent = {}
    reply_counts = {}
    for comment in root_comments:
        thread_ids = get_thread_reply_ids(post, comment.id)
        reply_counts[comment.id] = len(thread_ids)
        preview = list(
            get_thread_replies_qs(post, comment)[:FEED_REPLIES_PREVIEW]
        )
        replies_by_parent[comment.id] = preview

    root_ids = [c.id for c in root_comments]
    all_comment_ids = root_ids + [
        r.id for replies in replies_by_parent.values() for r in replies
    ]
    liked_comment_ids = set(
        CommentLike.objects.filter(user=user, comment_id__in=all_comment_ids)
        .values_list('comment_id', flat=True)
    ) if all_comment_ids else set()

    comments_data = []
    for comment in root_comments:
        preview_replies = replies_by_parent.get(comment.id, [])
        total_replies = reply_counts.get(comment.id, 0)
        comments_data.append({
            **_comment_payload(
                comment, liked_comment_ids,
                user=user, post_author_id=post_author_id,
            ),
            'replies': [
                _comment_payload(
                    reply, liked_comment_ids, parent_id=comment.id,
                    user=user, post_author_id=post_author_id,
                )
                for reply in preview_replies
            ],
            'replies_count': total_replies,
            'has_more_replies': total_replies > len(preview_replies),
        })

    loaded = offset + len(root_comments)
    return {
        'comments_data': comments_data,
        'root_comments_count': root_comments_count,
        'has_more_comments': loaded < root_comments_count,
        'next_offset': loaded if loaded < root_comments_count else None,
    }


@login_required
def feed_comments_json(request, post_id):
    """Load paginated root comments for feed (session auth, no API router conflict)."""
    post = get_object_or_404(Post, pk=post_id)
    denied = _deny_private_post_access(request, post, as_json=True)
    if denied:
        return denied
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
        limit = min(50, max(1, int(request.GET.get('limit', FEED_COMMENTS_PAGE_SIZE))))
    except (TypeError, ValueError):
        offset, limit = 0, FEED_COMMENTS_PAGE_SIZE
    return JsonResponse(build_feed_comments_data(post, request.user, limit=limit, offset=offset))


@login_required
def feed_comment_replies_json(request, comment_id):
    """Load paginated replies for one root comment on feed."""
    comment = get_object_or_404(Comment, pk=comment_id)
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
        limit = min(50, max(1, int(request.GET.get('limit', FEED_REPLIES_PAGE_SIZE))))
    except (TypeError, ValueError):
        offset, limit = 0, FEED_REPLIES_PAGE_SIZE
    return JsonResponse(
        build_comment_replies_data(comment, request.user, limit=limit, offset=offset)
    )


def prepare_posts_json(posts, user, include_comments=False):
    """Helper để chuẩn bị dữ liệu posts cho JSON responses."""
    post_list = list(posts)
    if not post_list:
        return []

    post_ids = [post.id for post in post_list]
    liked_ids = set(
        Like.objects.filter(user=user, post_id__in=post_ids).values_list('post_id', flat=True)
    )
    saved_ids = set(
        SavedPost.objects.filter(user=user, post_id__in=post_ids).values_list('post_id', flat=True)
    )
    following_ids = set(user.get_following_user_ids()) if user.is_authenticated else set()

    posts_data = []
    for post in post_list:
        media_files = [{
            'id': media.id,
            'file_url': media.file.url,
            'media_type': media.media_type,
            'order': media.order,
        } for media in post.media.all()]

        comments_data = []
        root_comments_count = 0
        has_more_comments = False
        if include_comments:
            feed_comments = build_feed_comments_data(post, user)
            comments_data = feed_comments['comments_data']
            root_comments_count = feed_comments['root_comments_count']
            has_more_comments = feed_comments['has_more_comments']

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
            'updated_at': post.updated_at.isoformat(),
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'is_liked': post.id in liked_ids,
            'is_saved': post.id in saved_ids,
            'disable_comments': post.disable_comments,
            'hide_likes': post.hide_likes,
            'media': media_files,
            'shared_from': (
                {
                    'id': post.shared_from.id,
                    'author': {
                        'id': post.shared_from.author.id,
                        'username': post.shared_from.author.username,
                        'avatar': post.shared_from.author.get_avatar_url(),
                    },
                    'caption': post.shared_from.caption,
                    'location': post.shared_from.location,
                    'created_at': post.shared_from.created_at.isoformat(),
                    'updated_at': post.shared_from.updated_at.isoformat(),
                    'likes_count': post.shared_from.likes_count,
                    'comments_count': post.shared_from.comments_count,
                    'media': [{
                        'id': media.id,
                        'file_url': media.file.url,
                        'media_type': media.media_type,
                        'order': media.order,
                    } for media in post.shared_from.media.all()],
                }
                if post.shared_from_id else None
            ),
            'comments_data': comments_data,
            'root_comments_count': root_comments_count,
            'has_more_comments': has_more_comments,
            'post_type': determine_post_type(user, post, following_ids=following_ids),
            'total_comments': post.comments_count,
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

    posts_per_page = getattr(settings, 'POSTS_PER_PAGE', 12)
    feed_type = request.GET.get('feed', 'diverse')
    is_json_request = request.GET.get('format') == 'json'

    if not is_json_request:
        return render(request, 'posts/feed.html', {
            'feed_type': feed_type,
        })

    if feed_type == 'flowed':
        posts = get_followed_feed(user, page_size=posts_per_page, page=page)
    else:
        posts = get_diverse_feed(
            user,
            page_size=posts_per_page,
            page=page,
            seed=request.GET.get('seed'),
            seen_ids=_parse_feed_seen_ids(request.GET.get('seen')),
        )

    has_more_posts = len(posts) >= posts_per_page

    return JsonResponse({
        'posts': prepare_posts_json(posts, user, include_comments=True),
        'has_next': has_more_posts,
    })

def determine_post_type(user, post, following_ids=None):
    """Nhãn feed nhẹ: flowed nếu đang theo dõi, còn lại discover."""
    if following_ids is None:
        following_ids = set(user.get_following_user_ids()) if user.is_authenticated else set()
    if post.author_id and post.author_id in following_ids:
        return 'flowed'
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
    comments = get_root_comments_qs(post)

    comments_data = []
    for comment in comments:
        replies = Comment.objects.filter(
            parent=comment
        ).select_related('author').order_by('-likes_count', '-created_at')

        data = {
            'comment': comment,
            'replies': replies,
            'replies_count': getattr(comment, 'replies_total', None) or replies.count()
        }
        comments_data.append(data)

    return comments_data

def process_hashtags(post):
    """Extract and process hashtags from post caption"""
    if not post.caption:
        return
    
    # Tìm tất cả các hashtag trong caption
    hashtags = re.findall(r'#(\w+)', post.caption)
    
    # Tạo hoặc lấy hashtag objects và liên kết với bài viết
    for tag_name in hashtags:
        if tag_name:  # Chỉ xử lý nếu tag không rỗng
            try:
                hashtag, created = Hashtag.objects.get_or_create(name=tag_name)
                hashtag.posts.add(post)
            except Exception as e:
                print(f"Error processing hashtag {tag_name}: {str(e)}")


def process_mentions(post):
    """
    Tạo Mention từ @username trong caption.
    Chỉ tạo mới khi chưa có (để gửi thông báo), xóa mention không còn trong caption.
    Chuẩn hóa @token → @username thật (vd: @jack → @jack97) khi resolve được.
    """
    from .mention_utils import normalize_caption_mentions, resolve_mentioned_user

    if post.caption:
        normalized = normalize_caption_mentions(post.caption)
        if normalized != post.caption:
            post.caption = normalized
            post.save(update_fields=['caption'])

    usernames = set()
    if post.caption:
        usernames = {name.lower() for name in re.findall(r'@(\w+)', post.caption)}

    existing = list(
        Mention.objects.filter(post=post, comment__isnull=True).select_related('user')
    )
    existing_by_username = {m.user.username.lower(): m for m in existing}
    keep_user_ids = set()

    for username in usernames:
        user = resolve_mentioned_user(username)
        if not user or user.id == post.author_id:
            continue
        keep_user_ids.add(user.id)
        if user.username.lower() not in existing_by_username:
            Mention.objects.create(user=user, post=post)

    Mention.objects.filter(post=post, comment__isnull=True).exclude(
        user_id__in=keep_user_ids
    ).delete()